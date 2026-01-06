# logic_utils.py
import logging

GRID_WIDTH = 6  # 게임판 가로 길이 (세피리아 표준)


def offset_to_coord(offset):
    """
    1차원 인덱스 오프셋(예: -7, 6)을 2차원 좌표(dx, dy)로 변환합니다.
    기준: (0,0)에서 시작. x는 오른쪽+, y는 아래쪽+
    """
    # 1. 일단 몫과 나머지로 대략적인 위치를 잡습니다.
    dy = offset // GRID_WIDTH
    dx = offset % GRID_WIDTH

    # 2. 보정 로직 (핵심!)
    # 예: -7의 경우 -> dy=-2, dx=5가 나옵니다.
    # 하지만 시각적으로 -7은 "한 줄 위(-1)의 왼쪽(-1)" 즉 (-1, -1)이어야 합니다.
    # 따라서 dx가 3(절반)보다 크면, "왼쪽에서 넘어온 것"으로 간주하여 보정합니다.
    if dx > 3:
        dx -= GRID_WIDTH
        dy += 1

    return dx, dy


def rotate_point(dx, dy):
    """
    (dx, dy) 좌표를 시계방향으로 90도 회전합니다.
    수학 공식: (x, y) -> (-y, x)
    """
    return -dy, dx


def rotate_keyword(key):
    """
    특수 키워드(ROW, COL 등)를 90도 회전시킵니다.
    """
    rotation_map = {
        'ROW': 'COL',
        'COL': 'ROW',
        'TOP': 'RIGHT',
        'RIGHT': 'BOTTOM',
        'BOTTOM': 'LEFT',
        'LEFT': 'TOP',
        'SLASH': 'BACK_SLASH',  # / -> \
        'BACK_SLASH': 'SLASH'  # \ -> /
    }
    return rotation_map.get(key, key)  # 매핑 안 되면 그대로 반환 (예: UNLOCK)


def get_rotated_directions(directions, rotation_count=0):
    """
    석판의 directions 리스트를 입력받아, rotation_count(0~3)만큼 회전시킨
    새로운 directions 리스트를 반환합니다.
    """
    new_directions = []

    for _ in range(rotation_count):
        # 90도씩 누적 회전이 아니라, 원본에서 한 번에 계산하려면 로직이 복잡하니
        # 그냥 1번씩 반복해서 돌리는 게 안전합니다.
        temp_dirs = []
        source = directions if _ == 0 else new_directions

        for d_key, d_val in source:
            new_key, new_val = d_key, d_val

            # 1. Key가 정수(오프셋)인 경우 -> 좌표로 변환 -> 회전 -> 다시 오프셋?
            # 아니요, 알고리즘 단계에서는 '좌표(dx, dy)'를 그대로 쓰는 게 훨씬 편합니다.
            if isinstance(d_key, int):
                dx, dy = offset_to_coord(d_key)
                rx, ry = rotate_point(dx, dy)
                # 좌표 상태로 유지 (나중에 그리드에 놓을 때 편함)
                new_key = (rx, ry)

                # 1-1. 이미 변환된 좌표 튜플인 경우 ((x, y))
            elif isinstance(d_key, tuple):
                rx, ry = rotate_point(d_key[0], d_key[1])
                new_key = (rx, ry)

            # 2. Key가 문자열(키워드)인 경우
            elif isinstance(d_key, str):
                new_key = rotate_keyword(d_key)

            temp_dirs.append((new_key, new_val))

        new_directions = temp_dirs

    # 회전이 0번이면(초기 상태) 정수 오프셋을 좌표로만 변환해서 반환
    if rotation_count == 0:
        cleaned_dirs = []
        for d_key, d_val in directions:
            if isinstance(d_key, int):
                d_key = offset_to_coord(d_key)
            cleaned_dirs.append((d_key, d_val))
        return cleaned_dirs

    return new_directions


# [테스트용 출력 함수]
if __name__ == "__main__":
    # 예시: '미래' 석판 (방향: -7, -6, -5, -1)
    # 모양: ㅗ 모양과 유사
    example_dirs = [(-7, 1), (-6, 1), (-5, 1), (-1, 1)]

    print("=== '미래' 석판 회전 테스트 ===")
    for i in range(4):
        print(f"회전 {i}번 (90도 * {i}):")
        rotated = get_rotated_directions(example_dirs, i)

        # 시각적으로 출력
        visual_map = [['.'] * 7 for _ in range(7)]  # 7x7 그리드
        center = 3
        visual_map[center][center] = "O"  # 중심

        for key, val in rotated:
            if isinstance(key, tuple):  # 좌표인 경우만
                dx, dy = key
                if 0 <= center + dy < 7 and 0 <= center + dx < 7:
                    visual_map[center + dy][center + dx] = "X"

        for row in visual_map:
            print(" ".join(row))
        print("-" * 20)