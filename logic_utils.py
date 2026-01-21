# logic_utils.py
import logging

GRID_WIDTH = 6

def offset_to_coord(offset):
    """1차원 오프셋 -> 2차원 좌표(dx, dy) 변환"""
    dy = offset // GRID_WIDTH
    dx = offset % GRID_WIDTH
    if dx > 3:
        dx -= GRID_WIDTH
        dy += 1
    return dx, dy

def rotate_point(dx, dy):
    """(dx, dy) 시계방향 90도 회전 -> (-dy, dx)"""
    return -dy, dx

def rotate_keyword(key):
    """특수 키워드 회전"""
    rotation_map = {
        'ROW': 'COL', 'COL': 'ROW',
        'TOP': 'RIGHT', 'RIGHT': 'BOTTOM', 'BOTTOM': 'LEFT', 'LEFT': 'TOP',
        'SLASH': 'BACK_SLASH', 'BACK_SLASH': 'SLASH'
    }
    return rotation_map.get(key, key)

def get_rotated_directions(directions, rotation_count=0):
    """방향 리스트 회전"""
    if rotation_count == 0:
        cleaned = []
        for k, v in directions:
            if isinstance(k, int): k = offset_to_coord(k)
            cleaned.append((k, v))
        return cleaned

    new_dirs = []
    source = directions
    for _ in range(rotation_count):
        temp = []
        for k, v in source:
            if isinstance(k, int):
                dx, dy = offset_to_coord(k)
                nk = rotate_point(dx, dy)
            elif isinstance(k, tuple):
                nk = rotate_point(k[0], k[1])
            elif isinstance(k, str):
                nk = rotate_keyword(k)
            else:
                nk = k
            temp.append((nk, v))
        source = temp
        new_dirs = temp
    return new_dirs

def analyze_grid_topology(rows, cols):
    """
    그리드의 각 칸이 가진 지형적 특성(가로/세로/대각선 길이 등)을 미리 계산
    """
    topo = {
        'row_len': [[0]*cols for _ in range(rows)],
        'col_len': [[0]*cols for _ in range(rows)],
        'slash_len': [[0]*cols for _ in range(rows)],
        'center_score': [[0]*cols for _ in range(rows)],
    }

    center_r, center_c = (rows-1)/2, (cols-1)/2

    for r in range(rows):
        for c in range(cols):
            # 1. 가로/세로 길이
            topo['row_len'][r][c] = cols
            topo['col_len'][r][c] = rows

            # 2. 대각선 길이 (중심에 가까울수록 김)
            dist_from_center = abs(r - center_r) + abs(c - center_c)
            topo['slash_len'][r][c] = max(1, min(rows, cols) - int(dist_from_center * 0.5))

            # 3. 중앙 집중 점수 (아티팩트 명당 판별용)
            # 중앙(0)에서 멀어질수록 점수 차감
            topo['center_score'][r][c] = 20 - int(dist_from_center * 2)

    return topo