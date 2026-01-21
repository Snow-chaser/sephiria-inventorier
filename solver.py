# solver.py
import random
import copy
import time
import logging
from logic_utils import get_rotated_directions, analyze_grid_topology

GRID_WIDTH = 6


class Solution:
    def __init__(self, inv_num, items, topo_data):
        self.inv_num = inv_num
        self.grid_height = (inv_num + GRID_WIDTH - 1) // GRID_WIDTH
        self.grid = [[None for _ in range(GRID_WIDTH)] for _ in range(self.grid_height)]
        self.topo_data = topo_data

        # 1. 아이템 그룹핑
        self.groups = self.preprocess_items(items)
        # 2. 스마트 배치
        self.fill_grid_smartly()
        # 3. 점수 계산
        self.score = self.evaluate()

    def preprocess_items(self, items):
        """아이템들을 분석하여 묶음(Cluster)과 개별(Single)로 분류"""
        pool = items[:]
        groups = []

        # [Rule 1] 마법서 + 모래시계 (가로 2칸 고정)
        hourglasses = [x for x in pool if
                       x.item_type == 'Artifact' and x.name == '빛나는 모래시계' and getattr(x, 'apply_hourglass', False)]
        spells = [x for x in pool if x.item_type == 'Artifact' and getattr(x, 'is_spell', False)]

        for hg in hourglasses:
            if not spells: break
            target_spell = spells.pop(0)

            if hg in pool: pool.remove(hg)
            if target_spell in pool: pool.remove(target_spell)

            groups.append({
                'type': 'H_PAIR',
                'items': [hg, target_spell],
                'priority': 100
            })

        # 헌신의 휘장 + 동료
        badges = [x for x in pool if x.item_type == 'Artifact' and x.name == '헌신의 휘장']
        for badge in badges:
            devoted_units = [x for x in pool if x.item_type == 'Artifact' and getattr(x, 'apply_devotion', False)]

            if devoted_units:
                # 휘장 + 유닛들 리스트 생성
                row_group = [badge]

                # 최대 5개까지만 추가 가능 (Grid 폭이 6이므로 휘장 포함 6개 초과 불가)
                available_slots = GRID_WIDTH - 1

                took_units = []
                for u in devoted_units:
                    if len(took_units) >= available_slots: break  # 칸 부족하면 컷
                    if u in pool:
                        row_group.append(u)
                        took_units.append(u)
                        pool.remove(u)

                if badge in pool: pool.remove(badge)

                groups.append({
                    'type': 'H_ROW_GROUP',  # [New] 가로줄 묶음 타입
                    'items': row_group,
                    'priority': 90
                })

        # [Rule 3] VIP 석판
        vip_keywords = ['ROW', 'COL', 'SLASH', 'BACK_SLASH', 'UNLOCK']
        vips = []
        others = []

        for item in pool:
            if item.item_type == 'Tablet':
                is_vip = False
                for d_key, _ in item.directions:
                    if isinstance(d_key, str) and d_key in vip_keywords:
                        is_vip = True
                        break
                if is_vip:
                    vips.append(item)
                else:
                    others.append(item)
            else:
                others.append(item)

        for v in vips:
            groups.append({'type': 'VIP_TABLET', 'items': [v], 'priority': 50})

        # 나머지
        for o in others:
            prio = 10
            if o.item_type == 'Artifact':
                if o.priority: prio = 30
                if o.name == '캘세더니 열쇠': prio = 40
                if o.constraint and 'harmony' in o.constraint: prio = 35

                if getattr(o, 'scale_position', None): prio = 40

            groups.append({'type': 'SINGLE', 'items': [o], 'priority': prio})

        groups.sort(key=lambda x: x['priority'], reverse=True)
        return groups

    def fill_grid_smartly(self):
        center_coords = self.get_sorted_coords(method='center')

        for group in self.groups:
            g_type = group['type']
            items = group['items']
            item = items[0]

            if g_type == 'H_PAIR':
                self.place_horizontal_pair(items, center_coords)

            elif g_type == 'H_ROW_GROUP':  #가로줄 배치 호출
                self.place_horizontal_group(items)

            elif g_type == 'VIP_TABLET':
                self.place_vip_tablet(item)

            elif g_type == 'SINGLE':
                if item.name == '캘세더니 열쇠':
                    self.place_calcedony_key(item)
                elif getattr(item, 'scale_position', None):
                    self.place_left_right_item(item)
                elif item.constraint and 'harmony' in item.constraint:
                    self.place_single_item(item, center_coords)
                else:
                    self.place_single_item(item, center_coords)

    def is_valid_cell(self, r, c):
        if not (0 <= r < self.grid_height and 0 <= c < GRID_WIDTH): return False
        if (r * GRID_WIDTH + c) >= self.inv_num: return False
        return True

    def place_horizontal_group(self, items):
        """ 헌신의 휘장 + 동료들을 한 줄에 연속 배치"""
        req_len = len(items)
        if req_len > GRID_WIDTH: return  # 물리적 불가

        # 중앙 행부터 탐색 (Grid 높이의 중간)
        rows = list(range(self.grid_height))
        rows.sort(key=lambda r: abs(r - (self.grid_height - 1) / 2))

        for r in rows:
            # 해당 행에서 연속된 빈 칸 찾기 (Sliding Window)
            # 최대한 중앙에 오도록 시작점(c) 조정
            possible_starts = []
            for c in range(GRID_WIDTH - req_len + 1):
                # c부터 c+req_len까지 비어있는지 확인
                is_empty = True
                for k in range(req_len):
                    if self.grid[r][c + k] is not None:
                        is_empty = False
                        break
                if is_empty:
                    possible_starts.append(c)

            if possible_starts:
                # 가능한 시작점 중 가장 중앙에 가까운 것 선택
                possible_starts.sort(key=lambda x: abs((x + req_len / 2) - GRID_WIDTH / 2))
                best_c = possible_starts[0]

                # 배치
                for k in range(req_len):
                    self.grid[r][best_c + k] = {'item': items[k], 'rotation': 0}
                return  # 성공

    def place_horizontal_pair(self, items, coords):
        """[모래시계][마법서] 배치"""
        for r, c in coords:
            if c + 1 < GRID_WIDTH:
                if self.grid[r][c] is None and self.grid[r][c + 1] is None:
                    self.grid[r][c] = {'item': items[0], 'rotation': 0}
                    self.grid[r][c + 1] = {'item': items[1], 'rotation': 0}
                    return

    def place_vip_tablet(self, tablet):
        """지형 점수가 가장 높은 곳에 배치"""
        best_r, best_c, best_rot = -1, -1, 0
        max_score = -1

        for r in range(self.grid_height):
            for c in range(GRID_WIDTH):
                if self.grid[r][c] is not None: continue

                rots = range(4) if tablet.turnable else [0]
                for rot in rots:
                    score = 0
                    dirs = get_rotated_directions(tablet.directions, rot)
                    for k, v in dirs:
                        if k == 'ROW':
                            score += self.topo_data['row_len'][r][c] * 10
                        elif k == 'COL':
                            score += self.topo_data['col_len'][r][c] * 10
                        elif k == 'SLASH':
                            score += self.topo_data['slash_len'][r][c] * 15
                        elif isinstance(k, tuple):
                            tr, tc = r + k[1], c + k[0]
                            if 0 <= tr < self.grid_height and 0 <= tc < GRID_WIDTH:
                                score += self.topo_data['center_score'][tr][tc]

                    if score > max_score:
                        max_score = score
                        best_r, best_c, best_rot = r, c, rot

        if best_r != -1:
            self.grid[best_r][best_c] = {'item': tablet, 'rotation': best_rot}

    def place_calcedony_key(self, item):
        """캘세더니 열쇠 배치"""
        target_combo = list(item.combo)[0] if item.combo else None
        combo_order = ['견고', '잉걸불', '빙하', '마법공학']

        target_mod = -1
        if target_combo in combo_order:
            target_mod = combo_order.index(target_combo)

        cols = list(range(GRID_WIDTH))
        cols.sort(key=lambda x: abs(x - 2.5))

        if target_mod != -1:
            for r in range(self.grid_height):
                if r % 4 == target_mod:
                    for c in cols:
                        if self.grid[r][c] is None:
                            self.grid[r][c] = {'item': item, 'rotation': 0}
                            return

        self.place_single_item(item, self.get_sorted_coords('center'))

    def place_left_right_item(self, item):
        """좌우 배치 아이템"""
        is_left = (item.scale_position == "좌측")
        target_cols = [0, 1, 2] if is_left else [3, 4, 5]
        target_cols.sort(key=lambda x: abs(x - 2.5))

        for c in target_cols:
            for r in range(self.grid_height):
                if self.grid[r][c] is None:
                    self.grid[r][c] = {'item': item, 'rotation': 0}
                    return

        self.place_single_item(item, self.get_sorted_coords('center'))

    def place_single_item(self, item, coords):
        """단순 빈칸 배치"""
        for r, c in coords:
            if self.grid[r][c] is None:
                self.grid[r][c] = {'item': item, 'rotation': 0}
                return

    def get_sorted_coords(self, method='center'):
        coords = [(r, c) for r in range(self.grid_height) for c in range(GRID_WIDTH)]
        if method == 'center':
            center_r, center_c = (self.grid_height - 1) / 2, (GRID_WIDTH - 1) / 2
            coords.sort(key=lambda p: (p[0] - center_r) ** 2 + (p[1] - center_c) ** 2)
        return coords

    def evaluate(self):
        """최종 점수 계산"""
        total_score = 0

        for r in range(self.grid_height):
            for c in range(GRID_WIDTH):
                cell = self.grid[r][c]
                if not cell: continue
                item = cell['item']

                # 조화의 수정
                if item.item_type == 'Artifact' and item.constraint and 'harmony' in item.constraint:
                    neighbor_levels = 0
                    for nr in range(r - 1, r + 2):
                        for nc in range(c - 1, c + 2):
                            if (nr, nc) == (r, c): continue
                            if 0 <= nr < self.grid_height and 0 <= nc < GRID_WIDTH:
                                n_cell = self.grid[nr][nc]
                                if n_cell and n_cell['item'].item_type == 'Artifact':
                                    neighbor_levels += n_cell['item'].current_enchant
                    total_score += neighbor_levels

                if item.item_type == 'Tablet':
                    dirs = get_rotated_directions(item.directions, cell['rotation'])
                    for k, v in dirs:
                        if isinstance(k, str):
                            pass
                        elif isinstance(k, tuple):
                            tr, tc = r + k[1], c + k[0]
                            if 0 <= tr < self.grid_height and 0 <= tc < GRID_WIDTH:
                                target = self.grid[tr][tc]
                                if target and target['item'].item_type == 'Artifact':
                                    t_item = target['item']
                                    p = v if isinstance(v, int) else 1

                                    if t_item.name == '캘세더니 열쇠':
                                        combo_order = ['견고', '잉걸불', '빙하', '마법공학']
                                        row_combo = combo_order[tr % 4]
                                        if t_item.combo and row_combo not in t_item.combo:
                                            p = 0

                                    if getattr(t_item, 'scale_position', None):
                                        is_left_req = (t_item.scale_position == "좌측")
                                        is_left_real = (tc < GRID_WIDTH / 2)
                                        if is_left_req != is_left_real:
                                            p = 0

                                    if t_item.priority: p *= 2
                                    total_score += p
        return total_score

    def mutate(self):
        r, c = random.randint(0, self.grid_height - 1), random.randint(0, GRID_WIDTH - 1)
        if self.grid[r][c] and self.grid[r][c]['item'].item_type == 'Tablet':
            if self.grid[r][c]['item'].turnable:
                self.grid[r][c]['rotation'] = (self.grid[r][c]['rotation'] + 1) % 4


def run_solver(inv_num, flat_items, max_time=3):
    rows = (inv_num + GRID_WIDTH - 1) // GRID_WIDTH
    topo_data = analyze_grid_topology(rows, GRID_WIDTH)

    current_sol = Solution(inv_num, flat_items, topo_data)
    best_sol = copy.deepcopy(current_sol)

    start_time = time.time()
    while time.time() - start_time < max_time:
        next_sol = copy.deepcopy(current_sol)
        next_sol.mutate()
        next_score = next_sol.evaluate()

        if next_score >= current_sol.score:
            current_sol = next_sol
            if next_score > best_sol.score:
                best_sol = copy.deepcopy(next_sol)

    return best_sol