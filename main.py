# 세피리아 석판 배치기
from tkinter import *
from tkinter import ttk, messagebox  # messagebox 추가
import tkinter.font
import ctypes
import os
import logging
import copy  # 객체 복사를 위해 필요
from PIL import Image, ImageTk
# 모듈화
from models import Artifact, Tablet
from data import artifacts, tablets
from solver import run_solver

# 로깅 설정
logging.basicConfig(
    filename='inventorier_debug.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s: %(message)s',
    encoding='utf-8',
    filemode='w'
)

logging.getLogger('PIL').setLevel(logging.WARNING)
logging.info("===프로그램 시작===")

# [초기 설정 및 경로]
base_dir = os.path.dirname(os.path.abspath(__file__))
image_dir = os.path.join(base_dir, "tablets_images")
art_image_dir = os.path.join(base_dir, "artifacts_images")

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    ctypes.windll.user32.SetProcessDPIAware()

# 전역 변수
USER_INV_NUM = 0
all_frames = {}
root = Tk()
root.title("sephiria inventorier")

# [디자인 설정]
BG_COLOR = "white"
root.configure(bg=BG_COLOR)
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=1)

FONT_NAME = "Galmuri11"
DEFAULT_FONT_SIZE = 9
main_font = tkinter.font.Font(family=FONT_NAME, size=DEFAULT_FONT_SIZE)
root.option_add("*Font", main_font)
root.option_add("*Background", BG_COLOR)

# 버튼 스타일
BTN_STYLE = {
    "relief": "solid", "bd": 1, "bg": BG_COLOR,
    "activebackground": "#f0f0f0", "cursor": "hand2"
}

# [이미지 캐싱]
IMAGE_CACHE = {}


def load_cached_image(file_name, directory, size):
    full_path = os.path.join(directory, file_name)
    key = (full_path, size)
    if key in IMAGE_CACHE: return IMAGE_CACHE[key]
    if os.path.exists(full_path):
        try:
            pil_image = Image.open(full_path)
            pil_image = pil_image.resize(size, Image.Resampling.BILINEAR)
            tk_image = ImageTk.PhotoImage(pil_image)
            IMAGE_CACHE[key] = tk_image
            return tk_image
        except Exception as e:
            logging.error(f"[ERROR] {file_name} 로드 실패: {e}")
            return None
    return None


def preload_all_images():
    logging.info("=== 리소스 프리로딩 시작 ===")
    for t in tablets:
        load_cached_image(f"{t.name}.PNG", image_dir, (50, 50))
    for a in artifacts:
        load_cached_image(f"{a.name}.PNG", art_image_dir, (50, 50))
        # 세부 설정창용 작은 이미지도 미리 로드
        load_cached_image(f"{a.name}.PNG", art_image_dir, (40, 40))

    all_combos = set()
    for a in artifacts:
        if a.combo:
            all_combos.update(a.combo)
        else:
            all_combos.add('무속성')
    for combo in list(all_combos):
        load_cached_image(f"{combo}.png", art_image_dir, (20, 20))
    logging.info("=== 프리로딩 완료 ===")


# [검증 함수]
def validate_number(P):
    if P == "": return True
    return P.isdigit()


vcmd = (root.register(validate_number), '%P')



def set_center_window(root, width, height):
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    x = (screen_width - width) // 2
    y = (screen_height - height) // 2
    root.geometry(f"{width}x{height}+{x}+{y}")


# ==========================================
# [화면 전환 함수]
# ==========================================
def show_frame(frame_name):
    if frame_name in all_frames:
        all_frames[frame_name].tkraise()


# ==========================================
# [UI 1: 인벤토리 입력]
# ==========================================
def get_input_inventory():
    frame_inv = Frame(root, bg=BG_COLOR)
    frame_inv.grid(row=0, column=0, sticky="nsew")
    all_frames["inv"] = frame_inv

    center_frame = Frame(frame_inv, bg=BG_COLOR)
    center_frame.place(relx=0.5, rely=0.1, anchor="n")

    Label(center_frame, text="인벤토리 칸 수를 입력해주세요.", width=27, height=3, fg="black", bg=BG_COLOR, anchor='e').grid(row=0,
                                                                                                                column=0,                                                                               padx=10)
    entry = Entry(center_frame, width=20, validate='key', validatecommand=vcmd)
    entry.grid(row=0, column=1, padx=10)

    def conf_button_click():
        inv_text = entry.get()
        if inv_text.isdigit():
            global USER_INV_NUM
            USER_INV_NUM = int(inv_text)
            logging.info(f"입력받은 칸 수: {USER_INV_NUM}")
            frame_inv.pack_forget()  # grid_forget 대신 pack_forget? 기존 코드 유지
            show_frame("main_tab")
        else:
            logging.warning("숫자 미입력")

    Button(center_frame, text="확인", command=conf_button_click, **BTN_STYLE).grid(row=0, column=2)


# ==========================================
# [UI 2: 석판 선택]
# ==========================================
def get_input_tablet():
    frame_main_tab = Frame(root, bg=BG_COLOR)
    frame_main_tab.grid(row=0, column=0, sticky="nsew")
    all_frames["main_tab"] = frame_main_tab

    Label(frame_main_tab, text="석판 선택 화면입니다.", bg=BG_COLOR).pack(pady=20)
    frame_status_list = Frame(frame_main_tab, bg=BG_COLOR)
    frame_status_list.pack(pady=10)

    TIER_COLORS = {'common': 'black', 'uncommon': '#00AA00', 'rare': '#0000FF', 'legendary': '#FFD700'}

    def update_status_label():
        for widget in frame_status_list.winfo_children(): widget.destroy()
        Label(frame_status_list, text="[보유 현황]", fg="black", bg=BG_COLOR, font=(FONT_NAME, 10, "bold")).pack()
        owned = [t for t in tablets if t.quant > 0]
        if not owned:
            Label(frame_status_list, text="없음", fg="gray", bg=BG_COLOR).pack()
        else:
            tier_order = {'common': 1, 'uncommon': 2, 'rare': 3, 'legendary': 4}
            for t in sorted(owned, key=lambda x: tier_order.get(x.tier, 99)):
                Label(frame_status_list, text=f"[{t.tier}] {t.name}: {t.quant}개", fg=TIER_COLORS.get(t.tier, 'black'),
                      bg=BG_COLOR, font=(FONT_NAME, 9)).pack(anchor="w")

    # [내부 함수] 등급별 상세 입력 화면
    def print_tablets_by_tier(target_tier, tier_korean_name):
        entry_map = {}
        frame_name = f"{target_tier}_tab"
        current_frame = Frame(root, bg=BG_COLOR)
        current_frame.grid(row=0, column=0, sticky="nsew")
        all_frames[frame_name] = current_frame
        show_frame(frame_name)

        current_frame.grid_columnconfigure(0, weight=1)

        center_frame = Frame(current_frame, bg=BG_COLOR)
        # 위쪽에 고정, 천장과 약간 띄움
        center_frame.grid(row=0, column=0, sticky="n", pady=30)

        target_list = [t for t in tablets if t.tier == target_tier]

        # 열 개수 동적 계산
        import math
        ITEMS_PER_COL_GROUP = 11
        total_items = len(target_list)
        needed_groups = math.ceil(total_items / ITEMS_PER_COL_GROUP)
        if needed_groups < 1: needed_groups = 1

        total_cols = needed_groups * 4

        # 1. 제목
        Label(center_frame, text=f"{tier_korean_name} 석판 개수 입력", height=2,
              fg="black", bg=BG_COLOR, font=(FONT_NAME, 12, "bold")).grid(row=0, column=0, columnspan=total_cols)

        # 2. 버튼 (상단 배치)
        def back_button_click():
            for tablet, widget in entry_map.items():
                val = widget.get()
                if val.isdigit():
                    tablet.quant = int(val)
                elif val == "":
                    tablet.quant = 0
            update_status_label()
            current_frame.destroy()
            show_frame("main_tab")

        btn_back = Button(center_frame, text="저장 후 뒤로 가기", command=back_button_click, **BTN_STYLE)
        btn_back.grid(row=1, column=0, columnspan=total_cols, pady=(0, 20))

        # 3. 아이템 배치
        for i, tablet in enumerate(target_list):
            row_idx = (i % ITEMS_PER_COL_GROUP) + 2
            col_group = i // ITEMS_PER_COL_GROUP
            col_base = col_group * 4
            pad_x_img = (40, 5) if col_group > 0 else 5

            file_name = f"{tablet.name}.PNG"
            tk_image = load_cached_image(file_name, image_dir, (50, 50))

            if tk_image:
                label_img = Label(center_frame, image=tk_image, bg=BG_COLOR)
                label_img.image = tk_image
                label_img.grid(row=row_idx, column=col_base, sticky='w', padx=pad_x_img, pady=2)
            else:
                Label(center_frame, text="[No Img]", bg=BG_COLOR).grid(row=row_idx, column=col_base, padx=pad_x_img)

            Label(center_frame, text=tablet.name, fg="black", bg=BG_COLOR, anchor='n').grid(row=row_idx,
                                                                                            column=col_base + 1,
                                                                                            sticky='w', padx=5)
            Label(center_frame, text='개수:', fg="black", bg=BG_COLOR, anchor='n').grid(row=row_idx, column=col_base + 2,
                                                                                      sticky='w', padx=(25, 2))

            entry = Entry(center_frame, width=5, validate='key', validatecommand=vcmd)
            entry.grid(row=row_idx, column=col_base + 3, sticky='w', padx=(5, 15))
            entry_map[tablet] = entry

            if tablet.quant > 0:
                entry.insert(0, str(tablet.quant))

    def next_button_click():
        get_input_artifact()

    def prev_button_click():
        if "inv" in all_frames:
            all_frames["inv"].grid(row=0, column=0, sticky="nsew")
            show_frame("inv")

    # 등급별 선택 버튼들
    btn_common = Button(frame_main_tab, text="일반 석판", command=lambda: print_tablets_by_tier('common', '일반'),
                        **BTN_STYLE)
    btn_common.pack(pady=3)
    btn_uncommon = Button(frame_main_tab, text="고급 석판", command=lambda: print_tablets_by_tier('uncommon', '고급'),
                          **BTN_STYLE)
    btn_uncommon.pack(pady=3)
    btn_rare = Button(frame_main_tab, text="희귀 석판", command=lambda: print_tablets_by_tier('rare', '희귀'), **BTN_STYLE)
    btn_rare.pack(pady=3)
    btn_legend = Button(frame_main_tab, text="전설 석판", command=lambda: print_tablets_by_tier('legendary', '전설'),
                        **BTN_STYLE)
    btn_legend.pack(pady=3)

    bottom_btn_frame = Frame(frame_main_tab, bg=BG_COLOR)
    bottom_btn_frame.pack(pady=20)

    # 하단 네비게이션 버튼
    btn_prev = Button(bottom_btn_frame, text="이전으로", command=prev_button_click, **BTN_STYLE)
    btn_prev.pack(side="left", padx=10)

    btn_next = Button(bottom_btn_frame, text="다음으로", command=lambda: next_button_click(), **BTN_STYLE)
    btn_next.pack(side="left", padx=10)

    update_status_label()


# ==========================================
# [UI 3: 아티팩트 개수 선택]
# ==========================================
def get_input_artifact():
    # 콤보 색상 정의 등은 동일
    COMBO_COLORS = {
        '동료': '#A0522D', '신비': '#800080', '빙하': '#00BFFF', '견고': '#696969',
        '그림자': '#2F4F4F', '호수': '#1E90FF', '바람노래': '#32CD32', '마법공학': '#FF1493',
        '얼음무구': '#ADD8E6', '행성': '#4B0082', '정밀': '#DC143C', '잉걸불': '#FF4500',
        '먹구름': '#708090', '수호': '#FFD700', '아카데미': '#4169E1', '태양검': '#FF8C00',
        '무속성': '#333333', '교섭': '#008080', '저주': '#8B0000'
    }

    frame_main_art = Frame(root, bg=BG_COLOR)
    frame_main_art.grid(row=0, column=0, sticky="nsew")
    all_frames["main_art"] = frame_main_art
    show_frame("main_art")

    Label(frame_main_art, text="아티팩트 보유 개수를 선택해주세요.", bg=BG_COLOR).pack(pady=20)
    frame_status_list = Frame(frame_main_art, bg=BG_COLOR)
    frame_status_list.pack(pady=10)

    def update_artifact_status():
        for w in frame_status_list.winfo_children(): w.destroy()
        Label(frame_status_list, text="[선택된 아티팩트]", fg="black", bg=BG_COLOR, font=(FONT_NAME, 10, "bold")).pack()
        owned = [a for a in artifacts if a.quant > 0]
        if not owned:
            Label(frame_status_list, text="없음", fg="gray", bg=BG_COLOR).pack()
        else:
            for a in sorted(owned, key=lambda x: x.name):
                c_str = ",".join(a.combo) if a.combo else "무속성"
                pri_color = COMBO_COLORS.get(list(a.combo)[0] if a.combo else '무속성', 'black')
                Label(frame_status_list, text=f"{a.name} ({c_str}): {a.quant}개", fg=pri_color, bg=BG_COLOR,
                      font=(FONT_NAME, 9, "bold")).pack(anchor="w")

        # [내부 함수] 콤보별 상세 입력 화면
    def print_combo_page(target_combo):
        entry_map = {}
        frame_name = f"{target_combo}_art_tab"

        # [1. 선언] 여기서 current_frame을 먼저 만들어야 합니다.
        current_frame = Frame(root, bg=BG_COLOR)
        current_frame.grid(row=0, column=0, sticky="nsew")
        all_frames[frame_name] = current_frame
        show_frame(frame_name)

        title_color = COMBO_COLORS.get(target_combo, 'black')

        # 리스트 필터링
        if target_combo == '무속성':
            target_list = [a for a in artifacts if not a.combo]
        else:
            target_list = [a for a in artifacts if target_combo in a.combo]

        # 동적 열 계산
        ROWS_PER_COL = 10
        total_items = len(target_list)
        import math
        needed_cols = math.ceil(total_items / ROWS_PER_COL)
        if needed_cols < 2: needed_cols = 2

        # [2. 설정] 선언이 끝난 후에 설정을 바꿔야 합니다.
        # 화면 전체(current_frame)의 가로축(Column 0)에 가중치를 줘서
        # 내부에 들어갈 center_frame이 좌우로 움직일 공간을 만듭니다.
        current_frame.grid_columnconfigure(0, weight=1)

        # [3. 내부 프레임 배치]
        center_frame = Frame(current_frame, bg=BG_COLOR)
        # sticky="n": 위쪽에 붙임
        center_frame.grid(row=0, column=0, sticky="n", pady=30)

        # 제목 라벨
        Label(center_frame, text=f"[{target_combo}] 아티팩트 개수 입력",
              height=2, fg=title_color, bg=BG_COLOR, font=(FONT_NAME, 12, "bold")
              ).grid(row=0, column=0, columnspan=needed_cols * 4)

        # 버튼
        def back_button_click():
            for art, widget in entry_map.items():
                val = widget.get()
                q = int(val) if val.isdigit() else 0
                if art.is_unique and q > 1:
                    messagebox.showwarning("경고",
                                           f"'{art.name}'은(는) 고유 아티팩트입니다.\n최대 1개까지만 보유 가능합니다.\n(1개로 자동 저장됩니다.)")
                    q = 1
                art.quant = q

            update_artifact_status()
            current_frame.destroy()
            show_frame("main_art")

        btn_back = Button(center_frame, text="저장 후 뒤로 가기", command=back_button_click, **BTN_STYLE)
        btn_back.grid(row=1, column=0, columnspan=needed_cols * 4, pady=(0, 20))

        # Grid 열 설정 (center_frame 내부)
        for group in range(needed_cols):
            base = group * 4
            center_frame.grid_columnconfigure(base, uniform="img")
            center_frame.grid_columnconfigure(base + 1, uniform="name")
            center_frame.grid_columnconfigure(base + 2, uniform="lbl")
            center_frame.grid_columnconfigure(base + 3, uniform="ent")

        # 아이템 배치
        for i, artifact in enumerate(target_list):
            row_idx = (i % ROWS_PER_COL) + 2
            col_group = i // ROWS_PER_COL
            col_base = col_group * 4
            pad_x_img = (40, 5) if col_group > 0 else 5

            file_name = f"{artifact.name}.PNG"
            tk_image = load_cached_image(file_name, art_image_dir, (50, 50))

            # 이미지
            if tk_image:
                label_img = Label(center_frame, image=tk_image, bg=BG_COLOR)
                label_img.image = tk_image
                label_img.grid(row=row_idx, column=col_base, sticky='w', padx=pad_x_img, pady=2)
            else:
                Label(center_frame, text="[Img X]", bg=BG_COLOR).grid(row=row_idx, column=col_base, padx=pad_x_img)

            # 이름
            label_name = Label(center_frame, text=artifact.name, fg="black", bg=BG_COLOR, anchor='w')
            label_name.grid(row=row_idx, column=col_base + 1, sticky='ew', padx=2)

            # 개수 라벨
            label_q = Label(center_frame, text='개수:', fg="gray", bg=BG_COLOR, anchor='e')
            label_q.grid(row=row_idx, column=col_base + 2, sticky='e', padx=2)

            # 입력창
            entry = Entry(center_frame, width=5, validate='key', validatecommand=vcmd)
            entry.grid(row=row_idx, column=col_base + 3, sticky='w', padx=(2, 15))
            entry_map[artifact] = entry

            if artifact.quant > 0:
                entry.insert(0, str(artifact.quant))

    # 버튼 목록 생성
    all_c = set()
    for a in artifacts:
        if a.combo: all_c.update(a.combo)

    s_combos = sorted(list(all_c))
    if any(not a.combo for a in artifacts):
        if '무속성' in s_combos: s_combos.remove('무속성')
        s_combos.append('무속성')
    if '' in s_combos: s_combos.remove('')

    bc = Frame(frame_main_art, bg=BG_COLOR)
    bc.pack(pady=10)

    if s_combos:
        sp = (len(s_combos) + 1) // 2
        for i, c in enumerate(s_combos):
            icon = load_cached_image(f"{c}.png", art_image_dir, (20, 20))
            b = Button(bc, text=f"  {c}" if icon else c, image=icon, compound="left",
                       command=lambda x=c: print_combo_page(x), anchor="w", width=140, height=23, padx=10, **BTN_STYLE)
            if icon: b.image = icon
            b.grid(row=i % sp, column=i // sp, padx=5, pady=2)

    def next_click():
        # 개수 입력이 완료되면 세부 설정 화면으로 이동
        get_artifact_details()

    def prev_click():
        show_frame("main_tab")

    bf = Frame(frame_main_art, bg=BG_COLOR)
    bf.pack(pady=20)
    Button(bf, text="이전으로", command=prev_click, **BTN_STYLE).pack(side="left", padx=10)
    Button(bf, text="다음으로", command=next_click, **BTN_STYLE).pack(side="left", padx=10)
    update_artifact_status()


def get_artifact_details():
    frame_name = "art_details"
    frame_detail = Frame(root, bg=BG_COLOR)
    frame_detail.grid(row=0, column=0, sticky="nsew")
    all_frames[frame_name] = frame_detail
    show_frame(frame_name)

    # -----------------------------------------------------------
    # [0. 사전 체크: 특수 아티팩트 보유 여부 확인]
    # -----------------------------------------------------------
    has_devotion_badge = False
    has_hourglass = False
    has_key = False

    # 위치(좌/우) 선택이 필요한 아티팩트가 있는지 확인
    # 대립의 천칭 OR 영원의 식
    has_position_select = False

    total_hourglass_count = 0

    for art in artifacts:
        if art.quant > 0:
            if art.name == "헌신의 휘장":
                has_devotion_badge = True
            elif art.name == "대립의 천칭" or art.name == "영원의 식":  # [New] 영원의 식 추가
                has_position_select = True
            elif art.name == "빛나는 모래시계":
                has_hourglass = True
                total_hourglass_count = art.quant
            elif art.name == "캘세더니 열쇠":
                has_key = True

    # -----------------------------------------------------------
    # [1. 가용 포인트 & UNLOCK 개수 계산]
    # -----------------------------------------------------------
    temp_inv_num = USER_INV_NUM if USER_INV_NUM > 0 else 36
    GRID_WIDTH = 6
    grid_height = (temp_inv_num + GRID_WIDTH - 1) // GRID_WIDTH

    total_capacity = 0
    total_unlocks = 0

    for t in tablets:
        if t.quant > 0:
            t_points = 0
            has_unlock_feature = False
            for d in t.directions:
                key, val = d[0], d[1]
                if val == 'UNLOCK': has_unlock_feature = True

                if isinstance(key, str):
                    if key == 'ROW':
                        t_points += 5
                    elif key in ['TOP', 'BOTTOM']:
                        t_points += 6
                    elif key == 'COL':
                        t_points += (grid_height - 1)
                    elif key == 'SLASH':
                        t_points += (min(GRID_WIDTH, grid_height) - 1)
                elif isinstance(key, int):
                    if isinstance(val, int) and val > 0: t_points += val

            total_capacity += t.quant * t_points
            if has_unlock_feature: total_unlocks += t.quant

    # -----------------------------------------------------------
    # [상단 정보 라벨]
    # -----------------------------------------------------------
    Label(frame_detail, text="아티팩트 세부 설정", bg=BG_COLOR, font=(FONT_NAME, 12, "bold")).pack(pady=(15, 5))

    info_frame = Frame(frame_detail, bg=BG_COLOR)
    info_frame.pack(pady=(0, 10))

    cap_text_var = StringVar()
    cap_text_var.set(f"필수 강화: 0 / 가용: {total_capacity}")
    cap_label = Label(info_frame, textvariable=cap_text_var, bg=BG_COLOR, fg="blue", font=(FONT_NAME, 10))
    cap_label.pack(anchor="center")

    unlock_text_var = StringVar()
    unlock_text_var.set(f"UNLOCK 사용: 0 / {total_unlocks}")
    unlock_label = Label(info_frame, textvariable=unlock_text_var, bg=BG_COLOR, fg="green", font=(FONT_NAME, 10))
    unlock_label.pack(anchor="center")

    hg_text_var = StringVar()
    if has_hourglass:
        hg_text_var.set(f"모래시계 사용: 0 / {total_hourglass_count}")
        hg_label = Label(info_frame, textvariable=hg_text_var, bg=BG_COLOR, fg='#DAA520', font=(FONT_NAME, 10))
        hg_label.pack(anchor="center")

    # -----------------------------------------------------------
    # [스크롤 영역]
    # -----------------------------------------------------------
    canvas = Canvas(frame_detail, bg=BG_COLOR, highlightthickness=0)
    scrollbar = Scrollbar(frame_detail, orient="vertical", command=canvas.yview)
    scrollable_frame = Frame(canvas, bg=BG_COLOR)

    scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    canvas.pack(side="left", fill="both", expand=True, padx=20)
    scrollbar.pack(side="right", fill="y")

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    # -----------------------------------------------------------
    # [헤더 구성]
    # -----------------------------------------------------------
    header_f = Frame(scrollable_frame, bg=BG_COLOR)
    header_f.pack(fill="x", pady=5)

    col_widths = [50, 160, 110, 60, 60]  # 기본 5개

    if has_position_select: col_widths.append(100)  # [New] 좌우 배치 열 (천칭 or 영원의식)
    if has_devotion_badge: col_widths.append(90)
    if has_hourglass: col_widths.append(80)
    if has_key: col_widths.append(100)

    for i, w in enumerate(col_widths):
        header_f.grid_columnconfigure(i, minsize=w)

    # 열 인덱스 계산
    col_idx_pos = -1
    col_idx_devotion = -1
    col_idx_hourglass = -1
    col_idx_key = -1

    current_col = 5

    if has_position_select:
        col_idx_pos = current_col
        current_col += 1
    if has_devotion_badge:
        col_idx_devotion = current_col
        current_col += 1
    if has_hourglass:
        col_idx_hourglass = current_col
        current_col += 1
    if has_key:
        col_idx_key = current_col
        current_col += 1

    Label(header_f, text="이미지", bg=BG_COLOR).grid(row=0, column=0)
    Label(header_f, text="이름", bg=BG_COLOR).grid(row=0, column=1)
    Label(header_f, text="강화 / 최대", bg=BG_COLOR).grid(row=0, column=2)
    Label(header_f, text="필수", bg=BG_COLOR).grid(row=0, column=3)
    Label(header_f, text="해제", bg=BG_COLOR, fg="green").grid(row=0, column=4)

    if has_position_select:
        Label(header_f, text="좌우 배치", bg=BG_COLOR).grid(row=0, column=col_idx_pos)
    if has_devotion_badge:
        Label(header_f, text="헌신의 휘장", bg=BG_COLOR, fg="#A0522D").grid(row=0, column=col_idx_devotion)
    if has_hourglass:
        Label(header_f, text="모래시계", bg=BG_COLOR, fg="#DAA520").grid(row=0, column=col_idx_hourglass)
    if has_key:
        Label(header_f, text="열쇠 속성", bg=BG_COLOR, fg="purple").grid(row=0, column=col_idx_key)

    instance_widgets = []

    # -----------------------------------------------------------
    # [실시간 계산 함수]
    # -----------------------------------------------------------
    def calculate_realtime(*args):
        current_required = 0
        current_unlocks_used = 0
        current_hourglass_used = 0

        for item in instance_widgets:
            if item['priority_var'].get():
                base_art = item['base_art']
                val_str = item['enchant_ent'].get()
                current_lv = int(val_str) if val_str.isdigit() else 0
                needed = max(0, base_art.max_level - current_lv)
                current_required += needed

            if item['unlock_var'] and item['unlock_var'].get():
                current_unlocks_used += 1

            if item.get('hourglass_var') and item['hourglass_var'].get():
                current_hourglass_used += 1

        cap_text_var.set(f"필수 강화: {current_required} / 가용: {total_capacity}")
        cap_label.configure(fg="red" if current_required > total_capacity else "blue")
        unlock_text_var.set(f"UNLOCK 사용: {current_unlocks_used} / {total_unlocks}")
        unlock_label.configure(fg="red" if current_unlocks_used > total_unlocks else "green")

        if has_hourglass:
            hg_text_var.set(f"모래시계 사용: {current_hourglass_used} / {total_hourglass_count}")
            hg_label.configure(fg="red" if current_hourglass_used > total_hourglass_count else "#DAA520")

    # -----------------------------------------------------------
    # [리스트 생성 루프]
    # -----------------------------------------------------------
    # 알고리즘용 constraint를 가진 아티팩트 목록('UNLOCK' 석판으로 해제 불가능한)
    NON_UNLOCKABLE_ARTS = ["빛나는 모래시계", "조화의 수정", "하얀 종이"]
    for art in artifacts:
        if art.quant > 0:
            for i in range(art.quant):
                row_f = Frame(scrollable_frame, bg=BG_COLOR, pady=2)
                row_f.pack(fill="x")

                for col_idx, width in enumerate(col_widths):
                    row_f.grid_columnconfigure(col_idx, minsize=width)

                # 1~5 기본 컬럼
                tk_img = load_cached_image(f"{art.name}.PNG", art_image_dir, (40, 40))
                l = Label(row_f, image=tk_img, bg=BG_COLOR)
                l.image = tk_img
                l.grid(row=0, column=0)

                name_str = art.name + (f" #{i + 1}" if art.quant > 1 else "")
                Label(row_f, text=name_str, anchor='w', bg=BG_COLOR).grid(row=0, column=1, sticky='w')

                enc_frame = Frame(row_f, bg=BG_COLOR)
                enc_frame.grid(row=0, column=2)
                ent_lv = Entry(enc_frame, width=3, justify='center', validate='key', validatecommand=vcmd)
                ent_lv.insert(0, "0")
                ent_lv.pack(side="left")
                ent_lv.bind("<KeyRelease>", calculate_realtime)
                Label(enc_frame, text=f"/ {art.max_level}", fg="gray", bg=BG_COLOR).pack(side="left")

                var_pri = BooleanVar(value=False)
                Checkbutton(row_f, variable=var_pri, bg=BG_COLOR, activebackground=BG_COLOR,
                            command=calculate_realtime).grid(row=0, column=3)

                var_unlock = None
                if art.constraint and art.name not in NON_UNLOCKABLE_ARTS:
                    var_unlock = BooleanVar(value=False)
                    Checkbutton(row_f, variable=var_unlock, bg=BG_COLOR, activebackground=BG_COLOR,
                                command=calculate_realtime).grid(row=0, column=4)
                else:
                    Label(row_f, text="-", bg=BG_COLOR, fg="lightgray").grid(row=0, column=4)

                # 6. 좌우 배치 (대립의 천칭 / 영원의 식)
                cb_pos = None
                if has_position_select:
                    # [New] 두 아티팩트 모두 여기서 처리
                    if art.name in ["대립의 천칭", "영원의 식"]:
                        cb_pos = ttk.Combobox(row_f, values=["좌측", "우측"], width=4, state="readonly")
                        cb_pos.set("좌측")
                        cb_pos.grid(row=0, column=col_idx_pos)
                    else:
                        Label(row_f, text="-", bg=BG_COLOR, fg="lightgray").grid(row=0, column=col_idx_pos)

                # 7. 헌신의 휘장
                var_devotion = None
                if has_devotion_badge:
                    if art.is_unit:
                        var_devotion = BooleanVar(value=False)
                        Checkbutton(row_f, variable=var_devotion, bg=BG_COLOR, activebackground=BG_COLOR) \
                            .grid(row=0, column=col_idx_devotion)
                    else:
                        Label(row_f, text="-", bg=BG_COLOR, fg="lightgray").grid(row=0, column=col_idx_devotion)

                # 8. 빛나는 모래시계
                var_hourglass = None
                if has_hourglass:
                    if art.is_spell:
                        var_hourglass = BooleanVar(value=False)
                        Checkbutton(row_f, variable=var_hourglass, bg=BG_COLOR, activebackground=BG_COLOR,
                                    command=calculate_realtime).grid(row=0, column=col_idx_hourglass)
                    else:
                        Label(row_f, text="-", bg=BG_COLOR, fg="lightgray").grid(row=0, column=col_idx_hourglass)

                # 9. 캘세더니 열쇠
                cb_key = None
                if has_key:
                    if art.name == "캘세더니 열쇠":
                        cb_key = ttk.Combobox(row_f, values=["견고", "잉걸불", "빙하", "마법공학"], width=7, state="readonly")
                        cb_key.set("견고")
                        cb_key.grid(row=0, column=col_idx_key)
                    else:
                        Label(row_f, text="-", bg=BG_COLOR, fg="lightgray").grid(row=0, column=col_idx_key)

                instance_widgets.append({
                    'base_art': art,
                    'enchant_ent': ent_lv,
                    'priority_var': var_pri,
                    'unlock_var': var_unlock,
                    'scale_cb': cb_pos,  # [New] 이름 변경됨 (cb_scale -> cb_pos)
                    'devotion_var': var_devotion,
                    'hourglass_var': var_hourglass,
                    'key_cb': cb_key
                })

    def validate_and_start():
        # 'UNLOCK' 석판으로 하나의 제약만 없애야 할 때
        PARTIAL_UNLOCK_RULES = {
            "다용도 벨트": {'bottom'}
        }
        final_instances = []
        required_points = 0
        unlocks_used = 0
        hourglass_used = 0

        for item in instance_widgets:
            base = item['base_art']
            instance = copy.deepcopy(base)
            instance.quant = 1

            val_str = item['enchant_ent'].get()
            cur_enc = int(val_str) if val_str.isdigit() else 0
            if cur_enc > instance.max_level: cur_enc = instance.max_level
            instance.current_enchant = cur_enc
            instance.priority = item['priority_var'].get()

            if instance.priority:
                required_points += max(0, instance.max_level - instance.current_enchant)

            if item['unlock_var'] and item['unlock_var'].get():
                unlocks_used += 1
                # 부분 해제 규칙
                if instance.name in PARTIAL_UNLOCK_RULES:
                    if instance.constraint:
                        instance.constraint -= PARTIAL_UNLOCK_RULES[instance.name]
                else:
                    instance.constraint = set()

            # 좌우 배치 저장 (천칭, 영원의 식 공용)
            if item['scale_cb']:
                instance.scale_position = item['scale_cb'].get()

            if item['devotion_var'] and item['devotion_var'].get():
                instance.apply_devotion = True

            if item.get('hourglass_var') and item['hourglass_var'].get():
                hourglass_used += 1
                instance.apply_hourglass = True

            if item.get('key_cb'):
                selected_combo = item['key_cb'].get()
                instance.combo = {selected_combo}

            final_instances.append(instance)

        warnings = []
        if required_points > total_capacity: warnings.append(f"- 필수 강화량 부족 ({required_points} > {total_capacity})")
        if unlocks_used > total_unlocks: warnings.append(f"- UNLOCK 석판 부족 ({unlocks_used} > {total_unlocks})")
        if has_hourglass and hourglass_used > total_hourglass_count:
            warnings.append(f"- 모래시계 개수 초과 ({hourglass_used} > {total_hourglass_count})")

        if warnings:
            if not messagebox.askyesno("경고", "다음 문제가 있습니다:\n" + "\n".join(warnings) + "\n\n진행할까요?"): return

        arrangement(USER_INV_NUM, tablets, final_instances)

    def prev_click():
        show_frame("main_art")

    bf = Frame(frame_detail, bg=BG_COLOR)
    bf.pack(pady=10)
    Button(bf, text="이전으로", command=prev_click, **BTN_STYLE).pack(side="left", padx=10)
    Button(bf, text="배치 시작", command=validate_and_start, **BTN_STYLE).pack(side="left", padx=10)


# ==========================================
# [알고리즘 실행 및 결과 표시]
# ==========================================
def arrangement(inv_num, tablets, artifacts):
    logging.info(f"--- 배치 알고리즘 시작 ---")

    # 1. 데이터 평탄화 (Flatten)
    # 알고리즘 엔진은 '수량(quant)' 개념을 모르고 개별 객체로 다룹니다.
    flat_items = []

    # 아티팩트: 이미 개별 인스턴스로 쪼개져서 넘어옴
    for art in artifacts:
        flat_items.append(art)

    # 석판: 'quant' 수량만큼 복제해서 리스트에 넣어야 함
    for tab in tablets:
        if tab.quant > 0:
            for _ in range(tab.quant):
                # 깊은 복사를 해야 서로 다른 회전값을 가질 수 있음
                new_tab = copy.deepcopy(tab)
                new_tab.quant = 1  # 개별 객체이므로 1로 설정
                flat_items.append(new_tab)

    logging.info(f"배치할 총 아이템 수: {len(flat_items)}")

    if len(flat_items) > inv_num:
        messagebox.showerror("오류", f"아이템 개수({len(flat_items)})가 인벤토리 칸 수({inv_num})보다 많습니다!")
        return

    # 2. 로딩 창 띄우기 (계산하는 동안 사용자가 알 수 있게)
    loading_win = Toplevel(root)
    loading_win.title("계산 중...")
    set_center_window(loading_win, 300, 100)
    Label(loading_win, text="최적의 배치를 찾는 중입니다...\n잠시만 기다려주세요.", pady=20).pack()
    loading_win.update()  # 화면 갱신 강제 수행

    # 3. Solver 실행 (3초간 계산)
    # 여기서 solver.py의 run_solver가 호출됩니다.
    try:
        best_solution = run_solver(inv_num, flat_items, max_time=3)
    except Exception as e:
        loading_win.destroy()
        logging.error(f"알고리즘 에러: {e}")
        messagebox.showerror("에러", f"배치 중 오류가 발생했습니다:\n{e}")
        return

    loading_win.destroy()

    # 4. 결과 화면 보여주기
    show_result_window(best_solution)


# ==========================================
# [결과 화면 표시 (이미지 & 회전 & 인벤 제한 적용)]
# ==========================================
def show_result_window(solution):
    """계산된 Grid를 시각적으로 보여주는 창"""
    res_win = Toplevel(root)

    # 점수 표시
    res_win.title(f"배치 결과 (점수: {solution.score})")
    set_center_window(res_win, 600, 750)

    # 캔버스 생성
    canvas = Canvas(res_win, bg="white")
    canvas.pack(fill="both", expand=True)

    # 이미지 참조 유지용 리스트 (가비지 컬렉션 방지)
    canvas.image_refs = []

    CELL_SIZE = 70  # 이미지 잘 보이게 칸 키움
    IMG_SIZE = 60  # 안에 들어갈 이미지 크기
    MARGIN = 20

    grid = solution.grid
    rows = len(grid)
    cols = len(grid[0])

    # 캔버스 크기 자동 조절
    can_w = MARGIN * 2 + cols * CELL_SIZE
    can_h = MARGIN * 2 + rows * CELL_SIZE
    res_win.geometry(f"{can_w}x{can_h + 60}")

    for r in range(rows):
        for c in range(cols):
            # 현재 칸의 인덱스 (0부터 시작)
            cell_idx = r * 6 + c

            x1 = MARGIN + c * CELL_SIZE
            y1 = MARGIN + r * CELL_SIZE
            x2 = x1 + CELL_SIZE
            y2 = y1 + CELL_SIZE
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2

            # [Req 2] 인벤토리 칸 수 초과 시 '잠긴 칸' 처리
            if cell_idx >= USER_INV_NUM:
                # 빗금 친 회색 칸 그리기
                canvas.create_rectangle(x1, y1, x2, y2, fill="#404040", outline="gray")
                canvas.create_line(x1, y1, x2, y2, fill="#606060", width=2)
                canvas.create_line(x1, y2, x2, y1, fill="#606060", width=2)
                continue  # 아이템 그리지 않음

            # 정상 칸 테두리
            canvas.create_rectangle(x1, y1, x2, y2, outline="lightgray")

            cell = grid[r][c]
            if cell:
                item = cell['item']
                rot = cell['rotation']  # 0, 1, 2, 3

                # 배경색 (구분감)
                bg_col = "#E0F7FA" if item.item_type == 'Artifact' else "#FFF3E0"
                if item.name == "빛나는 모래시계": bg_col = "#FFF9C4"
                if item.name == "헌신의 휘장": bg_col = "#FFCCBC"

                canvas.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2, fill=bg_col, outline="")

                # [Req 1, 3] 이미지 로드 및 회전 처리
                # 기존 캐시된 PhotoImage는 회전이 안 되므로, PIL로 새로 엽니다.
                try:
                    target_dir = art_image_dir if item.item_type == 'Artifact' else image_dir
                    img_path = os.path.join(target_dir, f"{item.name}.PNG")

                    if os.path.exists(img_path):
                        pil_img = Image.open(img_path)
                        pil_img = pil_img.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.BILINEAR)

                        # 석판이면 회전 적용 (PIL rotate는 시계반대방향이 기준이라 음수 사용)
                        # 1(90도) -> -90
                        if item.item_type == 'Tablet' and rot > 0:
                            pil_img = pil_img.rotate(-90 * rot)

                        tk_img = ImageTk.PhotoImage(pil_img)

                        # 캔버스에 그리기
                        canvas.create_image(center_x, center_y, image=tk_img)
                        canvas.image_refs.append(tk_img)  # 참조 유지
                    else:
                        # 이미지가 없으면 텍스트로 대체
                        canvas.create_text(center_x, center_y, text=item.name[:4], font=(FONT_NAME, 8))

                except Exception as e:
                    logging.error(f"이미지 처리 중 오류: {e}")
                    canvas.create_text(center_x, center_y, text="Err", font=(FONT_NAME, 8))

                # 디버깅용: 텍스트로 회전값 작게 표시 (선택사항)
                if rot > 0:
                    canvas.create_text(x2-10, y2-10, text=f"R{rot}", font=("Arial", 7), fill="red")

    # 닫기 버튼
    Button(res_win, text="닫기", command=res_win.destroy, **BTN_STYLE).pack(side='bottom', pady=10)


# [실행부]
set_center_window(root, 1024, 768)
root.resizable(True, True)
preload_all_images()
get_input_inventory()
get_input_tablet()
show_frame("inv")
root.mainloop()