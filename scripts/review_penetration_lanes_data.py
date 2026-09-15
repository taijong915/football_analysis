"""침투 조작적 정의를 채널 침투 선택지(레인 제한 + 파이널 서드 포함)로 확장하기로
확정한 뒤(`DECISIONS.md` 2026-09-14), 그 근거가 된 검토(1)~(6)이 스크래치패드
일회성 실행이라 재현 불가능한 상태다. 이 스크립트는 그 검토를 재현 가능하게
정리하고, 확장 정의가 의존하는 새 필드(레인별 카운트, 레인별 가시율, 수비 라인
근방 기하)를 `situations_lanes.pkl`(v2)로 생성한다.
"""
import os
import sys
import time
import warnings
from pathlib import Path

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from statsbombpy import sb
from matplotlib.path import Path as MplPath
from src.data_loader import get_competition_matches, get_match_events

# 캐시 폴더
CACHE_DIR = Path('data/raw/wc2022_360')
CACHE_DIR.mkdir(parents=True, exist_ok=True)

COMPETITION_ID = 43  # FIFA World Cup
SEASON_ID = 106      # 2022

# 2022 조별리그 통과(16강 진출) 16팀 - StatsBomb 팀명 기준
ADVANCED = {
    'Netherlands', 'United States', 'Argentina', 'Australia', 'Japan', 'Croatia',
    'Brazil', 'South Korea', 'England', 'Senegal', 'France', 'Poland', 'Morocco',
    'Spain', 'Portugal', 'Switzerland',
}

def cache_frames(match_id):
    """360 프레임 데이터를 캐시에서 로드하거나 다운로드."""
    cache_parquet = CACHE_DIR / f'frames_{match_id}.parquet'
    cache_pickle = CACHE_DIR / f'frames_{match_id}.pkl'

    if cache_parquet.exists():
        return pd.read_parquet(cache_parquet)
    if cache_pickle.exists():
        return pd.read_pickle(cache_pickle)

    try:
        frames = sb.frames(match_id=match_id, fmt='dataframe')
        try:
            frames.to_parquet(cache_parquet)
        except Exception:
            frames.to_pickle(cache_pickle)
        return frames
    except Exception as e:
        print(f"  [ERROR] match_id {match_id}: {e}")
        return None

def get_events_cache(match_id):
    """이벤트 데이터를 캐시에서 로드하거나 다운로드.

    이벤트에는 location 같은 리스트 컬럼이 섞여 있어 to_parquet이 실패한다.
    실패를 그냥 넘기면 캐시가 한 건도 남지 않아 실행할 때마다 전 경기를 다시
    내려받게 되므로(48경기 기준 약 580초), 프레임과 같이 pickle로 받아낸다.
    """
    cache_parquet = CACHE_DIR / f'events_{match_id}.parquet'
    cache_pickle = CACHE_DIR / f'events_{match_id}.pkl'

    if cache_parquet.exists():
        return pd.read_parquet(cache_parquet)
    if cache_pickle.exists():
        return pd.read_pickle(cache_pickle)

    events = get_match_events(match_id=match_id)
    try:
        events.to_parquet(cache_parquet)
    except Exception:
        events.to_pickle(cache_pickle)
    return events

def parse_visible_area(va):
    """가시 영역을 (N, 2) 좌표 배열로. x, y가 번갈아 나오는 평평한 리스트를 편다.

    좌표가 3쌍 미만이면 다각형이 되지 않으므로 None을 돌려준다.
    """
    if not isinstance(va, (list, np.ndarray)) or len(va) < 6:
        return None
    try:
        coords = np.asarray(va, dtype=float).reshape(-1, 2)
    except Exception:
        return None
    return coords if len(coords) >= 3 else None

# 침투 밴드 격자는 상황마다 모양이 같고 x 범위만 달라진다. 상황이 3만 건이 넘어
# 매번 meshgrid를 새로 만들면 비용이 크므로, 단위 격자를 한 번만 만들어 두고
# 상황마다 x축만 늘려 쓴다.
_BAND_U, _BAND_Y = np.meshgrid(np.linspace(0, 1, 15), np.linspace(2, 78, 25))
_BAND_U = _BAND_U.ravel()
_BAND_Y = _BAND_Y.ravel()

# 레인별 가시율용 단위 격자
_LANE_GRIDS = {}

def _get_lane_grid(y_ranges, n_y=25):
    """레인별 격자 캐시 - 상황마다 재사용.

    사이드(y<18, y>62)와 하프스페이스(18~30, 50~62)는 피치 좌우에 한 띠씩,
    모두 두 조각으로 나뉜다. 한쪽 띠만 재면 왼쪽 절반의 가시율을 레인 전체의
    가시율로 착각하게 되므로, 띠 목록을 받아 전부 합쳐 격자를 만든다.
    """
    key = (tuple(tuple(r) for r in y_ranges), n_y)
    if key not in _LANE_GRIDS:
        y_vals = np.concatenate([np.linspace(lo, hi, n_y) for lo, hi in y_ranges])
        u_vals = np.linspace(0, 1, 15)
        u_grid, y_grid = np.meshgrid(u_vals, y_vals)
        _LANE_GRIDS[key] = (u_grid.ravel(), y_grid.ravel())
    return _LANE_GRIDS[key]

def band_visibility(path, def_line, band_width):
    """침투 밴드 [def_line, def_line + band_width] x [2, 78]의 가시 격자점 비율."""
    if path is None or def_line >= 119.5:
        return np.nan
    x_max = min(120.0, def_line + band_width)
    if x_max <= def_line:
        return np.nan
    points = np.column_stack((def_line + _BAND_U * (x_max - def_line), _BAND_Y))
    return float(path.contains_points(points).mean())

def launch_visibility(path, def_line, depth=10):
    """출발 구역 [def_line - depth, def_line] x [2, 78]의 가시 격자점 비율.

    침투 선택지는 수비 라인 뒤가 아니라 라인 바로 앞(온사이드)에서 출발하므로,
    실제로 커버리지를 확인해야 하는 구역은 여기다. 공과 수비 라인 사이라
    중계 카메라가 거의 항상 담는다(라인 뒤 0.33 vs 이 구역 0.80).
    """
    if path is None:
        return np.nan
    lo = max(0.0, def_line - depth)
    if def_line <= lo:
        return np.nan
    points = np.column_stack((lo + _BAND_U * (def_line - lo), _BAND_Y))
    return float(path.contains_points(points).mean())

def lane_visibility(path, def_line, y_ranges, depth=10):
    """레인별 출발 구역 가시율.

    [def_line - depth, def_line] x (y_ranges가 지정한 띠들)의 가시 격자점 비율.
    구역이 화면에 잡혔는지는 그 구역에 아군이 있었는지와 무관하므로, 아군
    유무로 값을 비우지 않는다(비우면 "선수가 보일 때만 가시율이 기록되는"
    편향이 생겨 2번 단계의 공변량으로 쓸 수 없다).
    """
    if path is None:
        return np.nan
    lo = max(0.0, def_line - depth)
    if def_line <= lo:
        return np.nan

    u_vals, y_vals = _get_lane_grid(y_ranges)
    points = np.column_stack((lo + u_vals * (def_line - lo), y_vals))
    return float(path.contains_points(points).mean())

def build_frame_index(frames):
    """프레임 DataFrame을 이벤트별로 미리 쪼개 둔다.

    상황마다 frames 전체를 id로 걸러내면 경기당 800회 x 4만 행의 선형 스캔이
    된다(48경기 약 3.6분). id로 정렬해 경계를 한 번만 찾고 (시작, 끝) 슬라이스로
    바꾸면 조회가 사전 접근이 된다. visible_area는 한 프레임의 모든 선수가
    공유하므로 프레임당 한 번만 파싱하고 Path 객체도 재사용한다.
    """
    frames = frames.sort_values('id', kind='stable')
    ids = frames['id'].to_numpy()
    locations = np.array(
        [loc if isinstance(loc, (list, np.ndarray)) and len(loc) == 2 else (np.nan, np.nan)
         for loc in frames['location']], dtype=float)
    visible_areas = frames['visible_area'].to_numpy()

    slices, polygons, paths = {}, {}, {}
    if len(ids) > 0:
        starts = np.r_[0, np.flatnonzero(ids[1:] != ids[:-1]) + 1]
        ends = np.r_[starts[1:], len(ids)]
        for start, end in zip(starts, ends):
            event_id = ids[start]
            coords = parse_visible_area(visible_areas[start])
            slices[event_id] = (start, end)
            polygons[event_id] = coords
            paths[event_id] = MplPath(coords) if coords is not None else None

    return {
        'locations': locations,
        'slices': slices,
        'polygons': polygons,
        'paths': paths,
        'teammate': frames['teammate'].to_numpy(bool),
        'keeper': frames['keeper'].to_numpy(bool),
        'actor': frames['actor'].to_numpy(bool),
    }

def get_formation_info(events, match_info):
    """경기의 양 팀 포메이션 정보 추출."""
    xi = events[events['type'] == 'Starting XI']
    home_team = match_info['home_team']
    away_team = match_info['away_team']

    formations = {}
    for team in [home_team, away_team]:
        team_xi = xi[xi['team'] == team]
        if not team_xi.empty:
            tactics = team_xi.iloc[0].get('tactics', {})
            form = tactics.get('formation', np.nan)
            formations[team] = form
        else:
            formations[team] = np.nan

    return formations

def analyze_match(match_id, match_info):
    """한 경기를 분석하여 A·B 행 + 상황별 행 list 반환."""
    start_time = time.time()
    print(f"  {match_id}...", end='', flush=True)

    frames = cache_frames(match_id)
    if frames is None or frames.empty:
        print(" [NO FRAMES]")
        return None, None, []

    events = get_events_cache(match_id)
    if events is None or events.empty:
        print(" [NO EVENTS]")
        return None, None, []

    index = build_frame_index(frames)
    locations = index['locations']
    teammate, keeper, actor = index['teammate'], index['keeper'], index['actor']

    elapsed = time.time() - start_time
    print(f" ({elapsed:.1f}s, {len(frames)} frame rows)")

    # ===== A. 커버리지·용량 =====
    n_events = len(events)
    n_360_events = int(events['id'].isin(set(index['slices'])).sum())
    coverage_360 = n_360_events / n_events if n_events > 0 else 0
    bad_va = sum(1 for coords in index['polygons'].values() if coords is None)

    a_row = {
        'match_id': match_id,
        'home_team': match_info['home_team'],
        'away_team': match_info['away_team'],
        'n_events': n_events,
        'n_360_events': n_360_events,
        'coverage': round(coverage_360, 3),
        'n_frame_rows': len(frames),
        'bad_visible_area': bad_va,
    }

    # ===== B. 전제 검증 =====
    in_area_count = 0
    total_count = 0
    for event_id, (start, end) in index['slices'].items():
        path = index['paths'][event_id]
        if path is None:
            continue
        points = locations[start:end]
        valid = ~np.isnan(points[:, 0])
        if not valid.any():
            continue
        total_count += int(valid.sum())
        in_area_count += int(path.contains_points(points[valid]).sum())

    b_row = {
        'match_id': match_id,
        'location_in_visible_area_ratio': round(in_area_count / total_count, 3) if total_count else 0,
    }

    # ===== 선제골 시각 및 포메이션 =====
    goal_events = events[(events['type'] == 'Shot') & (events['shot_outcome'] == 'Goal')]
    first_goal_minute = goal_events.iloc[0]['minute'] if not goal_events.empty else None

    formations = get_formation_info(events, match_info)

    # ===== 상황별 행 생성 =====
    events = events.copy()
    events['x'] = [loc[0] if isinstance(loc, (list, np.ndarray)) and len(loc) == 2 else np.nan
                   for loc in events['location']]

    # x.between(30, 120) - 변경: 110이 아니라 120까지 (in_scope로 필터)
    progression_events = events[(events['type'] == 'Pass') & events['x'].between(30, 120)]

    home_team, away_team = match_info['home_team'], match_info['away_team']
    situation_rows = []

    for event_id, team, period, minute, second, ball_x, pass_type in zip(
            progression_events['id'], progression_events['team'],
            progression_events['period'], progression_events['minute'],
            progression_events['second'], progression_events['x'],
            progression_events['pass_type']):
        span = index['slices'].get(event_id)
        if span is None:
            continue
        start, end = span
        coords = index['polygons'][event_id]
        if coords is None:
            continue
        path = index['paths'][event_id]

        frame_loc = locations[start:end]
        is_mate, is_keeper, is_actor = teammate[start:end], keeper[start:end], actor[start:end]

        # 오프사이드 라인 근사 = 상대 필드플레이어(골키퍼 제외) x의 최댓값
        opponent_x = frame_loc[(~is_mate) & (~is_keeper), 0]
        opponent_x = opponent_x[~np.isnan(opponent_x)]
        if opponent_x.size == 0:
            continue
        def_line = float(opponent_x.max())

        band15 = band_visibility(path, def_line, 15)
        band10 = band_visibility(path, def_line, 10)
        vis_launch = launch_visibility(path, def_line, 10)

        # in_scope 플래그
        in_scope = (30 <= ball_x) and (ball_x < 110)

        # 액터·골키퍼를 뺀 아군 필드플레이어 x와 y
        mate_mask = is_mate & (~is_keeper) & (~is_actor)
        mate_xy = frame_loc[mate_mask]
        mate_xy_valid = mate_xy[~np.isnan(mate_xy[:, 0]) & ~np.isnan(mate_xy[:, 1])]

        mate_x = mate_xy_valid[:, 0]
        mate_y = mate_xy_valid[:, 1]

        # 온사이드 조건
        onside_ahead = (mate_x <= def_line) & (mate_x > ball_x)

        # 레인 정의 (y는 0-80 피치 좌표)
        def get_lane(y_arr):
            """각 선수의 y 좌표에서 레인을 구분 - numpy 배열 지원."""
            side = (y_arr < 18) | (y_arr > 62)
            half = ((18 <= y_arr) & (y_arr < 30)) | ((50 < y_arr) & (y_arr <= 62))
            center = (30 <= y_arr) & (y_arr <= 50)
            return side, half, center

        side, half, center = get_lane(mate_y)
        channel = side | half

        # 카운트: onside_ahead & 밴드 & 레인
        def count_by_band_lane(onside_mask, mate_x, band_threshold, lane_mask):
            """특정 밴드와 레인의 침투 선택지 수."""
            in_band = mate_x >= def_line - band_threshold
            return int((onside_mask & in_band & lane_mask).sum())

        n_side5 = count_by_band_lane(onside_ahead, mate_x, 5, side)
        n_half5 = count_by_band_lane(onside_ahead, mate_x, 5, half)
        n_center5 = count_by_band_lane(onside_ahead, mate_x, 5, center)
        n_channel5 = n_side5 + n_half5

        n_side10 = count_by_band_lane(onside_ahead, mate_x, 10, side)
        n_half10 = count_by_band_lane(onside_ahead, mate_x, 10, half)
        n_center10 = count_by_band_lane(onside_ahead, mate_x, 10, center)
        n_channel10 = n_side10 + n_half10

        n_center15 = count_by_band_lane(onside_ahead, mate_x, 15, center)
        n_channel15 = int((onside_ahead & (mate_x >= def_line - 15) & channel).sum())

        n_center_nb = int((onside_ahead & center).sum())
        n_channel_nb = int((onside_ahead & channel).sum())

        # 기존 컬럼들
        n_launch = int((onside_ahead & (mate_x >= def_line - 10)).sum())
        n_launch5 = int((onside_ahead & (mate_x >= def_line - 5)).sum())
        n_beyond = int((mate_x > def_line).sum())

        # 레인별 가시율
        vis_launch_wide = lane_visibility(path, def_line, ((2, 18), (62, 78)))
        vis_launch_half = lane_visibility(path, def_line, ((18, 30), (50, 62)))
        vis_launch_center = lane_visibility(path, def_line, ((30, 50),))

        # 수비 라인 근방 기하
        opp_mask = (~is_mate) & (~is_keeper)
        opp_near = frame_loc[opp_mask]
        opp_near_valid = opp_near[~np.isnan(opp_near[:, 0])]

        opp_x = opp_near_valid[:, 0]
        near_def_mask = opp_x >= def_line - 10
        near_def_y = opp_near_valid[near_def_mask, 1]

        n_def_near = int(near_def_mask.sum())
        if len(near_def_y) >= 2:
            sorted_y = np.sort(near_def_y)
            gaps = np.diff(sorted_y)
            max_def_gap = float(np.max(gaps)) if len(gaps) > 0 else np.nan
        else:
            max_def_gap = np.nan

        # 포메이션
        own_formation = formations.get(team, np.nan)
        opp_formation = formations.get(away_team if team == home_team else home_team, np.nan)
        opp_backline = int(str(int(opp_formation))[0]) if pd.notna(opp_formation) else np.nan

        situation_rows.append({
            'match_id': match_id,
            'stage': match_info['competition_stage'],
            'team': team,
            'opponent': away_team if team == home_team else home_team,
            'period': period,
            'minute': minute,
            'second': second,
            'ball_x': round(float(ball_x), 2),
            'in_scope': in_scope,
            'def_line': round(def_line, 2),
            'band15': round(band15, 3) if not np.isnan(band15) else np.nan,
            'band10': round(band10, 3) if not np.isnan(band10) else np.nan,
            'vis_depth': round(float(coords[:, 0].max()) - def_line, 2),
            'n_opp_visible': int(opponent_x.size),
            'vis_launch': round(vis_launch, 3) if not np.isnan(vis_launch) else np.nan,
            'vis_launch_wide': round(vis_launch_wide, 3) if not np.isnan(vis_launch_wide) else np.nan,
            'vis_launch_half': round(vis_launch_half, 3) if not np.isnan(vis_launch_half) else np.nan,
            'vis_launch_center': round(vis_launch_center, 3) if not np.isnan(vis_launch_center) else np.nan,
            'n_tm_visible': int(min(mate_x.size, 9)),
            'n_launch': n_launch,
            'n_launch5': n_launch5,
            'n_side5': n_side5,
            'n_half5': n_half5,
            'n_center5': n_center5,
            'n_channel5': n_channel5,
            'n_side10': n_side10,
            'n_half10': n_half10,
            'n_center10': n_center10,
            'n_channel10': n_channel10,
            'n_center15': n_center15,
            'n_channel15': n_channel15,
            'n_center_nb': n_center_nb,
            'n_channel_nb': n_channel_nb,
            'n_beyond': n_beyond,
            'n_def_near': n_def_near,
            'max_def_gap': max_def_gap,
            'own_formation': own_formation,
            'opp_formation': opp_formation,
            'opp_backline': opp_backline,
            'setpiece': not pd.isna(pass_type),
            'pre_first_goal': first_goal_minute is None or minute < first_goal_minute,
        })

    return a_row, b_row, situation_rows


# 경기 간 재현성 계산 함수 (korea_qatar2022/01_team_comparison.py에서 복사)
def avg_pairwise_corr(pivot: pd.DataFrame) -> float:
    """팀 x 경기(0/1/2) 표에서 경기쌍 간 팀 순위 상관의 평균 - 경기 간 재현성."""
    cols = list(pivot.columns)
    vals = [pivot[i].corr(pivot[j]) for a, i in enumerate(cols) for j in cols[a + 1:]]
    return float(np.mean(vals)) if len(vals) > 0 else np.nan


# ===== 메인 로직 =====
print("2022 FIFA World Cup 침투 선택지 - 레인 분해 데이터 검토")
print("=" * 80)
print()

matches = get_competition_matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
group_matches = matches[matches['competition_stage'] == 'Group Stage'].copy()
group_matches = group_matches.sort_values('match_date')

print(f"조별리그 경기: {len(group_matches)}")

korea_ko = matches[
    (matches['match_id'] == 3869253) &
    ((matches['home_team'] == 'South Korea') | (matches['away_team'] == 'South Korea'))
]

all_matches = pd.concat([group_matches, korea_ko], ignore_index=True).drop_duplicates(subset=['match_id'])
print(f"분석 대상: {len(group_matches)} (조별리그) + 1 (한국 16강) = {len(all_matches)}")
print()

a_results = []
b_results = []
all_situations = []

start_download = time.time()
for _, match in all_matches.iterrows():
    match_id = match['match_id']
    is_ko = match_id in korea_ko['match_id'].values if not korea_ko.empty else False

    if is_ko:
        print(f"[한국 16강전] {match_id} {match['home_team']} vs {match['away_team']}")

    a, b, situations = analyze_match(match_id, match)

    if a is not None:
        a_results.append(a)
    if b is not None:
        b_results.append(b)
    all_situations.extend(situations)

total_download_time = time.time() - start_download
print()

# ===== situations_lanes.pkl 저장 =====
situations_df = pd.DataFrame(all_situations)
situations_path = CACHE_DIR / 'situations_lanes.pkl'
situations_df.to_pickle(situations_path)
print(f"situations_lanes.pkl 저장 완료: {len(situations_df)} 행")
print(f"컬럼: {', '.join(situations_df.columns.tolist())}")
print()

# 신규 컬럼 결측률
new_cols = ['in_scope', 'vis_launch_wide', 'vis_launch_half', 'vis_launch_center',
            'n_side5', 'n_half5', 'n_center5', 'n_channel5',
            'n_side10', 'n_half10', 'n_center10', 'n_channel10',
            'n_center15', 'n_channel15', 'n_center_nb', 'n_channel_nb',
            'n_def_near', 'max_def_gap', 'own_formation', 'opp_formation', 'opp_backline']

print("신규 컬럼 결측률:")
for col in new_cols:
    if col in situations_df.columns:
        na_rate = situations_df[col].isna().sum() / len(situations_df)
        print(f"  {col:20s}: {na_rate*100:5.2f}%")

print()

# ===== A. 커버리지 표 (조별리그만) =====
print("\n[A] 경기별 커버리지·용량")
print("=" * 80)
a_df = pd.DataFrame(a_results)
a_group_df = a_df[a_df['match_id'].isin(group_matches['match_id'])].copy()
print(a_group_df.to_string(index=False))

a_flags = []
for _, row in a_group_df.iterrows():
    if row['coverage'] < 0.80:
        a_flags.append(f"[FLAG A] match_id {row['match_id']}: 360 커버리지 {row['coverage']} < 0.80")

print()
print("A 전체 합산:")
print(f"  총 경기: {len(a_group_df)}")
print(f"  총 프레임 행: {a_group_df['n_frame_rows'].sum()}")

# ===== B. 전제 검증 =====
print()
print("\n[B] 선수 위치 검증 (location이 visible_area 안)")
print("=" * 80)
b_df = pd.DataFrame(b_results)
b_group_df = b_df[b_df['match_id'].isin(group_matches['match_id'])].copy()
if not b_group_df.empty:
    overall_ratio = b_group_df['location_in_visible_area_ratio'].mean()
    print(f"전체 비율: {overall_ratio:.3f}")

    b_flags = []
    if overall_ratio < 0.95:
        b_flags.append(f"[FLAG B] 전체 비율 {overall_ratio:.3f} < 0.95")
else:
    b_flags = []

# ===== C. ball_x 10m 구간별 표 (검토 1) =====
print()
print("\n[C] ball_x 10m 구간별 표 (검토 1)")
print("=" * 80)

group_situations = situations_df[situations_df['stage'] == 'Group Stage'].copy()
openplay_situations = group_situations[~group_situations['setpiece']].copy()

if not openplay_situations.empty:
    c_rows = []
    bins = [(30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100), (100, 110), (110, 120)]

    for lo, hi in bins:
        mask = (openplay_situations['ball_x'] >= lo) & (openplay_situations['ball_x'] < hi)
        subset = openplay_situations[mask]

        if not subset.empty:
            n_situations = len(subset)
            pct_beyond = 100.0 * (subset['ball_x'] > subset['def_line']).sum() / n_situations if n_situations > 0 else 0
            n_opp_visible_mean = subset['n_opp_visible'].mean()
            vis_launch_mean = subset['vis_launch'].mean()
            n_launch5_mean = subset['n_launch5'].mean()

            c_rows.append({
                'ball_x': f"{lo}-{hi}",
                '건수': n_situations,
                '공>라인(%)': round(pct_beyond, 2),
                '상대관측': round(n_opp_visible_mean, 2),
                '라인앞가시율': round(vis_launch_mean, 3) if not np.isnan(vis_launch_mean) else np.nan,
                'n_launch5': round(n_launch5_mean, 3) if not np.isnan(n_launch5_mean) else np.nan,
            })

    c_df = pd.DataFrame(c_rows)
    print(c_df.to_string(index=False))

    # 로우 블록 상황 수
    print()
    print("로우 블록 상황 (def_line >= 100):")
    low_block = openplay_situations[openplay_situations['def_line'] >= 100]
    lb_30_80 = len(low_block[(low_block['ball_x'] >= 30) & (low_block['ball_x'] < 80)])
    lb_80_110 = len(low_block[(low_block['ball_x'] >= 80) & (low_block['ball_x'] < 110)])
    print(f"  ball_x 30-80: {lb_30_80}")
    print(f"  ball_x 80-110: {lb_80_110}")

    c_flags = []
else:
    c_flags = []
    print("(데이터 없음)")

# ===== D. 레인별 분해 (검토 2) =====
print()
print("\n[D] 레인별 분해 (검토 2)")
print("=" * 80)

if not openplay_situations.empty:
    # 30-80과 80-110 구간 분리
    d1_situations = openplay_situations[(openplay_situations['ball_x'] >= 30) & (openplay_situations['ball_x'] < 80)]
    d2_situations = openplay_situations[(openplay_situations['ball_x'] >= 80) & (openplay_situations['ball_x'] < 110)]

    d_rows = []
    for label, subset in [('30-80', d1_situations), ('80-110', d2_situations)]:
        if not subset.empty:
            d_rows.append({
                '구간': label,
                'n_side5': round(subset['n_side5'].mean(), 3),
                'n_half5': round(subset['n_half5'].mean(), 3),
                'n_center5': round(subset['n_center5'].mean(), 3),
                'n_channel5': round(subset['n_channel5'].mean(), 3),
            })

    d_df = pd.DataFrame(d_rows)
    print(d_df.to_string(index=False))

    # 10m 구간별 레인 분해
    print()
    print("10m 구간별 레인 분해:")
    d_detail_rows = []
    for lo, hi in [(30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100), (100, 110)]:
        mask = (openplay_situations['ball_x'] >= lo) & (openplay_situations['ball_x'] < hi)
        subset = openplay_situations[mask]

        if not subset.empty:
            d_detail_rows.append({
                'ball_x': f"{lo}-{hi}",
                'n_side5': round(subset['n_side5'].mean(), 3),
                'n_half5': round(subset['n_half5'].mean(), 3),
                'n_center5': round(subset['n_center5'].mean(), 3),
            })

    d_detail_df = pd.DataFrame(d_detail_rows)
    print(d_detail_df.to_string(index=False))

    d_flags = []
else:
    d_flags = []

# ===== E. 재현성 비교 (검토 3) =====
print()
print("\n[E] 재현성 비교 (검토 3)")
print("=" * 80)

if not openplay_situations.empty:
    # E-1: x 80-110, 레인만 바꿔 비교
    e1_situations = openplay_situations[(openplay_situations['ball_x'] >= 80) & (openplay_situations['ball_x'] < 110)]

    if not e1_situations.empty:
        # 팀별 경기별 피벗
        per_match_raw = (e1_situations.groupby(['team', 'match_id'])
                        .agg(m_full=('n_launch5', 'mean'), m_ch=('n_channel5', 'mean'), m_ctr=('n_center5', 'mean'))
                        .reset_index())
        per_match_raw['slot'] = per_match_raw.groupby('team').cumcount()

        e1_rows = []

        for label, col, orig_col in [('전레인(n_launch5)', 'm_full', 'n_launch5'), ('채널(n_channel5)', 'm_ch', 'n_channel5'), ('중앙(n_center5)', 'm_ctr', 'n_center5')]:
            pivot = per_match_raw.pivot(index='team', columns='slot', values=col)
            corr_val = avg_pairwise_corr(pivot) if len(pivot.columns) > 1 else np.nan

            e1_rows.append({
                '정의': label,
                '평균': round(e1_situations[orig_col].mean(), 3),
                '재현성': round(corr_val, 3) if not np.isnan(corr_val) else np.nan,
            })

        e1_df = pd.DataFrame(e1_rows)
        print("E-1. x 80-110, 레인 비교 (5m 밴드):")
        print(e1_df.to_string(index=False))

    # E-2: x 80-110, 채널 고정, 밴드 폭 비교
    print()
    print("E-2. x 80-110, 채널, 밴드 폭 비교:")

    e2_situations = openplay_situations[(openplay_situations['ball_x'] >= 80) & (openplay_situations['ball_x'] < 110)]
    e2_cols = ['n_channel5', 'n_channel10', 'n_channel15', 'n_channel_nb']
    e2_rows = []

    for col in e2_cols:
        if col in e2_situations.columns:
            per_match_e2 = (e2_situations.groupby(['team', 'match_id'])[col].mean().reset_index())
            per_match_e2['slot'] = per_match_e2.groupby('team').cumcount()
            pivot_e2 = per_match_e2.pivot(index='team', columns='slot', values=col)
            corr_e2 = avg_pairwise_corr(pivot_e2) if len(pivot_e2.columns) > 1 else np.nan

            label_map = {'n_channel5': '5m', 'n_channel10': '10m', 'n_channel15': '15m', 'n_channel_nb': '무제한'}
            e2_rows.append({
                '밴드': label_map.get(col, col),
                '재현성': round(corr_e2, 3) if not np.isnan(corr_e2) else np.nan,
            })

    e2_df = pd.DataFrame(e2_rows)
    print(e2_df.to_string(index=False))

    # E-3: 후보 정의 비교
    print()
    print("E-3. 후보 정의 비교 (평균 / 재현성 / 진출 상관):")

    e3_rows = []

    # x30-80, 전레인
    e3_1 = openplay_situations[(openplay_situations['ball_x'] >= 30) & (openplay_situations['ball_x'] < 80)]
    if not e3_1.empty:
        per_match_e3_1 = (e3_1.groupby(['team', 'match_id'])['n_launch5'].mean().reset_index())
        per_match_e3_1['slot'] = per_match_e3_1.groupby('team').cumcount()
        pivot_e3_1 = per_match_e3_1.pivot(index='team', columns='slot', values='n_launch5')
        rep_e3_1 = avg_pairwise_corr(pivot_e3_1) if len(pivot_e3_1.columns) > 1 else np.nan

        # 16강 진출 상관
        team_avgs_e3_1 = e3_1.groupby('team')['n_launch5'].mean()
        advanced_dict = {t: (t in ADVANCED) for t in team_avgs_e3_1.index}
        adv_vals = np.array([advanced_dict.get(t, False) for t in team_avgs_e3_1.index]).astype(float)
        corr_e3_1 = np.corrcoef(team_avgs_e3_1.values, adv_vals)[0, 1] if len(adv_vals) > 1 else np.nan

        e3_rows.append({
            '정의': 'x30-80, 전레인',
            '평균': round(e3_1['n_launch5'].mean(), 3),
            '재현성': round(rep_e3_1, 3) if not np.isnan(rep_e3_1) else np.nan,
            '진출상관': round(corr_e3_1, 3) if not np.isnan(corr_e3_1) else np.nan,
        })

    # x30-110, 전레인
    e3_2 = openplay_situations[(openplay_situations['ball_x'] >= 30) & (openplay_situations['ball_x'] < 110)]
    if not e3_2.empty:
        per_match_e3_2 = (e3_2.groupby(['team', 'match_id'])['n_launch5'].mean().reset_index())
        per_match_e3_2['slot'] = per_match_e3_2.groupby('team').cumcount()
        pivot_e3_2 = per_match_e3_2.pivot(index='team', columns='slot', values='n_launch5')
        rep_e3_2 = avg_pairwise_corr(pivot_e3_2) if len(pivot_e3_2.columns) > 1 else np.nan

        team_avgs_e3_2 = e3_2.groupby('team')['n_launch5'].mean()
        adv_vals_2 = np.array([advanced_dict.get(t, False) for t in team_avgs_e3_2.index]).astype(float)
        corr_e3_2 = np.corrcoef(team_avgs_e3_2.values, adv_vals_2)[0, 1] if len(adv_vals_2) > 1 else np.nan

        e3_rows.append({
            '정의': 'x30-110, 전레인',
            '평균': round(e3_2['n_launch5'].mean(), 3),
            '재현성': round(rep_e3_2, 3) if not np.isnan(rep_e3_2) else np.nan,
            '진출상관': round(corr_e3_2, 3) if not np.isnan(corr_e3_2) else np.nan,
        })

    # x30-110, 채널
    if not e3_2.empty:
        per_match_e3_3 = (e3_2.groupby(['team', 'match_id'])['n_channel5'].mean().reset_index())
        per_match_e3_3['slot'] = per_match_e3_3.groupby('team').cumcount()
        pivot_e3_3 = per_match_e3_3.pivot(index='team', columns='slot', values='n_channel5')
        rep_e3_3 = avg_pairwise_corr(pivot_e3_3) if len(pivot_e3_3.columns) > 1 else np.nan

        team_avgs_e3_3 = e3_2.groupby('team')['n_channel5'].mean()
        adv_vals_3 = np.array([advanced_dict.get(t, False) for t in team_avgs_e3_3.index]).astype(float)
        corr_e3_3 = np.corrcoef(team_avgs_e3_3.values, adv_vals_3)[0, 1] if len(adv_vals_3) > 1 else np.nan

        e3_rows.append({
            '정의': 'x30-110, 채널',
            '평균': round(e3_2['n_channel5'].mean(), 3),
            '재현성': round(rep_e3_3, 3) if not np.isnan(rep_e3_3) else np.nan,
            '진출상관': round(corr_e3_3, 3) if not np.isnan(corr_e3_3) else np.nan,
        })

    # x80-110, 채널
    if not e1_situations.empty:
        per_match_e3_4 = (e1_situations.groupby(['team', 'match_id'])['n_channel5'].mean().reset_index())
        per_match_e3_4['slot'] = per_match_e3_4.groupby('team').cumcount()
        pivot_e3_4 = per_match_e3_4.pivot(index='team', columns='slot', values='n_channel5')
        rep_e3_4 = avg_pairwise_corr(pivot_e3_4) if len(pivot_e3_4.columns) > 1 else np.nan

        team_avgs_e3_4 = e1_situations.groupby('team')['n_channel5'].mean()
        adv_vals_4 = np.array([advanced_dict.get(t, False) for t in team_avgs_e3_4.index]).astype(float)
        corr_e3_4 = np.corrcoef(team_avgs_e3_4.values, adv_vals_4)[0, 1] if len(adv_vals_4) > 1 else np.nan

        e3_rows.append({
            '정의': 'x80-110, 채널',
            '평균': round(e1_situations['n_channel5'].mean(), 3),
            '재현성': round(rep_e3_4, 3) if not np.isnan(rep_e3_4) else np.nan,
            '진출상관': round(corr_e3_4, 3) if not np.isnan(corr_e3_4) else np.nan,
        })

    e3_df = pd.DataFrame(e3_rows)
    print(e3_df.to_string(index=False))

    e_flags = []
else:
    e_flags = []

# ===== F. 레인 폭 보정 (검토 4) =====
print()
print("\n[F] 레인 폭 보정 (검토 4)")
print("=" * 80)

if not openplay_situations.empty:
    f_situations = openplay_situations[(openplay_situations['ball_x'] >= 30) & (openplay_situations['ball_x'] < 110)]

    if not f_situations.empty:
        # 레인 폭: 사이드 36m, 하프 24m, 중앙 20m
        f_rows = []

        # 사이드
        side_mean = f_situations['n_side5'].mean()
        side_per_m = side_mean / 36.0 if not np.isnan(side_mean) else np.nan

        # 하프
        half_mean = f_situations['n_half5'].mean()
        half_per_m = half_mean / 24.0 if not np.isnan(half_mean) else np.nan

        # 중앙
        center_mean = f_situations['n_center5'].mean()
        center_per_m = center_mean / 20.0 if not np.isnan(center_mean) else np.nan

        f_rows.append({
            '레인': '사이드',
            '평균': round(side_mean, 3),
            '미터당': round(side_per_m, 3) if not np.isnan(side_per_m) else np.nan,
            '폭(m)': 36,
        })
        f_rows.append({
            '레인': '하프스페이스',
            '평균': round(half_mean, 3),
            '미터당': round(half_per_m, 3) if not np.isnan(half_per_m) else np.nan,
            '폭(m)': 24,
        })
        f_rows.append({
            '레인': '중앙',
            '평균': round(center_mean, 3),
            '미터당': round(center_per_m, 3) if not np.isnan(center_per_m) else np.nan,
            '폭(m)': 20,
        })

        f_df = pd.DataFrame(f_rows)
        print(f_df.to_string(index=False))

    f_flags = []
else:
    f_flags = []

# ===== G. 상대 선발 백라인 vs 보이는 수비 (검토 5) =====
print()
print("\n[G] 상대 선발 백라인 vs 보이는 수비 (검토 5)")
print("=" * 80)

if not openplay_situations.empty:
    # 범위는 채택 정의와 같은 x 30-110이다. 2026-09-14 스크래치 검토가 이 범위로
    # 돌았음이 재현으로 확인됐다(x30-80으로 재면 상황 수 22,209 / n_def_near 3.85로
    # 어긋나고, x30-110이면 29,692건 / 4.41 / 4.17로 맞는다).
    g_situations = openplay_situations[(openplay_situations['ball_x'] >= 30) & (openplay_situations['ball_x'] < 110)]
    g_situations = g_situations[g_situations['opp_formation'].notna()]

    if not g_situations.empty:
        g_situations_cp = g_situations.copy()
        g_situations_cp['opp_backline_actual'] = g_situations_cp['opp_backline'].astype(int)

        # 백라인별 상황 수
        g_counts = g_situations_cp['opp_backline_actual'].value_counts().sort_index()
        print("상대 선발 백라인 상황 수:")
        for bl, count in g_counts.items():
            print(f"  백{bl}: {count}")

        print()

        # 백3(또는 5) vs 백4 비교
        g_rows = []

        for backline_group, backline_vals, label in [
            (3, [3, 5], '백3 (수비시 백5)'),
            (4, [4], '백4'),
        ]:
            mask = g_situations_cp['opp_backline_actual'].isin(backline_vals)
            subset = g_situations_cp[mask]

            if not subset.empty:
                n_situations = len(subset)
                n_def_near_mean = subset['n_def_near'].mean()
                max_def_gap_mean = subset['max_def_gap'].mean()

                g_rows.append({
                    '선발백라인': label,
                    '상황수': n_situations,
                    'n_def_near_평균': round(n_def_near_mean, 2),
                    'max_def_gap_평균': round(max_def_gap_mean, 2),
                })

        g_df = pd.DataFrame(g_rows)
        print(g_df.to_string(index=False))

        # 상관 계산
        print()
        print("상관:")

        # 실제 백라인 인원 코딩: 백3=3, 백4=4
        backline_coded = g_situations_cp['opp_backline_actual'].copy()
        backline_coded[backline_coded == 5] = 3  # 백5는 백3 그룹

        corr1 = np.corrcoef(backline_coded, g_situations_cp['n_def_near'])[0, 1]

        # max_def_gap NaN 제외
        valid_gap = ~g_situations_cp['max_def_gap'].isna()
        if valid_gap.sum() > 1:
            corr2 = np.corrcoef(backline_coded[valid_gap], g_situations_cp.loc[valid_gap, 'max_def_gap'])[0, 1]
            corr3 = np.corrcoef(g_situations_cp.loc[valid_gap, 'n_def_near'], g_situations_cp.loc[valid_gap, 'max_def_gap'])[0, 1]
        else:
            corr2 = np.nan
            corr3 = np.nan

        print(f"  corr(백라인인원, n_def_near) = {round(corr1, 3)}")
        print(f"  corr(백라인인원, max_def_gap) = {round(corr2, 3) if not np.isnan(corr2) else 'nan'}")
        print(f"  corr(n_def_near, max_def_gap) = {round(corr3, 3) if not np.isnan(corr3) else 'nan'}")

        print()
        print(f"총 상황 수: {len(g_situations_cp)}")

    g_flags = []
else:
    g_flags = []

# ===== H. 백라인별 채널 침투 선택지 (검토 6) =====
print()
print("\n[H] 백라인별 채널 침투 선택지 (검토 6)")
print("=" * 80)

if not openplay_situations.empty:
    h_situations = openplay_situations[(openplay_situations['ball_x'] >= 30) & (openplay_situations['ball_x'] < 110)]
    h_situations = h_situations[h_situations['opp_formation'].notna()]

    if not h_situations.empty:
        h_situations_cp = h_situations.copy()
        h_situations_cp['opp_backline_actual'] = h_situations_cp['opp_backline'].astype(int)

        h_rows = []

        for backline_vals, label in [
            ([3, 5], '백3'),
            ([4], '백4'),
        ]:
            mask = h_situations_cp['opp_backline_actual'].isin(backline_vals)
            subset = h_situations_cp[mask]

            if not subset.empty:
                n_channel5_mean = subset['n_channel5'].mean()

                h_rows.append({
                    '백라인': label,
                    'n_channel5_평균': round(n_channel5_mean, 3),
                })

        h_df = pd.DataFrame(h_rows)
        print(h_df.to_string(index=False))

        # 하프만 따로
        print()
        print("n_half5만 따로:")
        h_half_rows = []

        for backline_vals, label in [
            ([3, 5], '백3'),
            ([4], '백4'),
        ]:
            mask = h_situations_cp['opp_backline_actual'].isin(backline_vals)
            subset = h_situations_cp[mask]

            if not subset.empty:
                n_half5_mean = subset['n_half5'].mean()

                h_half_rows.append({
                    '백라인': label,
                    'n_half5_평균': round(n_half5_mean, 3),
                })

        h_half_df = pd.DataFrame(h_half_rows)
        print(h_half_df.to_string(index=False))

        # 한국 상대 포메이션
        print()
        print("한국 4경기 상대 선발 포메이션 (확인용):")
        korea_all = situations_df[situations_df['team'] == 'South Korea'].copy()
        if not korea_all.empty:
            korea_matches = korea_all[['match_id', 'opponent', 'opp_formation']].drop_duplicates('match_id')
            for _, row in korea_matches.iterrows():
                form_str = str(int(row['opp_formation'])) if pd.notna(row['opp_formation']) else 'N/A'
                print(f"  vs {row['opponent']}: {form_str}")

        # 조별리그 백3 통계
        print()
        print("조별리그 백3 선발 통계:")
        group_formations = group_situations[group_situations['opp_formation'].notna()].copy()
        group_formations['opp_backline_actual'] = group_formations['opp_backline'].astype(int)

        # 기준은 상황 수가 아니라 팀-경기 수다 (조별리그 96 팀-경기 중 몇 건이
        # 백3 선발이었는지). 상황 수로 세면 점유율이 높은 팀에 가중치가 실린다.
        back3 = group_formations[group_formations['opp_backline_actual'] == 3]
        back3_team_matches = back3[['match_id', 'opponent']].drop_duplicates()
        all_team_matches = group_formations[['match_id', 'opponent']].drop_duplicates()

        print(f"  백3 선발 팀-경기: {len(back3_team_matches)} / {len(all_team_matches)}")
        print(f"  백3 팀 수: {back3_team_matches['opponent'].nunique()}")
        print(f"  (참고) 백3 상황 수: {len(back3)}")

    h_flags = []
else:
    h_flags = []

# ===== I. 레인별 가시율 (신규, 2번 단계 입력) =====
print()
print("\n[I] 레인별 가시율 (신규)")
print("=" * 80)

if not openplay_situations.empty:
    i_situations = openplay_situations[(openplay_situations['ball_x'] >= 30) & (openplay_situations['ball_x'] < 110)]

    if not i_situations.empty:
        # 1. 전체 평균·중앙값·결측률
        print("1. 채택 범위(x 30-110) 전체 통계:")

        i_metrics = ['vis_launch', 'vis_launch_wide', 'vis_launch_half', 'vis_launch_center']
        i1_rows = []

        for col in i_metrics:
            if col in i_situations.columns:
                vals = i_situations[col].dropna()
                i1_rows.append({
                    '지표': col,
                    '평균': round(vals.mean(), 3) if len(vals) > 0 else np.nan,
                    '중앙값': round(vals.median(), 3) if len(vals) > 0 else np.nan,
                    '결측률(%)': round(100 * i_situations[col].isna().sum() / len(i_situations), 2),
                })

        i1_df = pd.DataFrame(i1_rows)
        print(i1_df.to_string(index=False))

        # 2. 팀별 평균 + 표준편차
        print()
        print("2. 팀별(32팀) 평균:")

        team_stats = i_situations.groupby('team')[i_metrics].mean()
        team_stats_rounded = team_stats.round(3)
        team_stats_rounded['std_vis_launch'] = i_situations.groupby('team')['vis_launch'].std().round(3)
        team_stats_rounded['std_vis_launch_wide'] = i_situations.groupby('team')['vis_launch_wide'].std().round(3)
        team_stats_rounded['std_vis_launch_half'] = i_situations.groupby('team')['vis_launch_half'].std().round(3)
        team_stats_rounded['std_vis_launch_center'] = i_situations.groupby('team')['vis_launch_center'].std().round(3)

        print(team_stats_rounded.to_string())

        # 3. 상관
        print()
        print("3. 상관 (레인 가시율 vs def_line, n_opp_visible):")

        for col in i_metrics:
            corr_def = np.corrcoef(i_situations[col].dropna(), i_situations.loc[i_situations[col].notna(), 'def_line'])[0, 1]
            corr_opp = np.corrcoef(i_situations[col].dropna(), i_situations.loc[i_situations[col].notna(), 'n_opp_visible'])[0, 1]

            print(f"  {col:20s}: corr(def_line)={round(corr_def, 3)}, corr(n_opp_visible)={round(corr_opp, 3)}")

        # 4. 가시율 차이가 가장 큰 팀 5개
        print()
        print("4. vis_launch_wide - vis_launch_center 차이가 가장 큰 팀 5개:")

        team_means = i_situations.groupby('team')[['vis_launch_wide', 'vis_launch_center']].mean()
        team_means['diff'] = team_means['vis_launch_wide'] - team_means['vis_launch_center']
        # 사이드가 중앙보다 항상 덜 보이므로 차이는 전부 음수다. 부호대로 정렬하면
        # "가장 큰 팀"이 아니라 "가장 작은 팀"이 뽑히므로 절댓값으로 정렬한다.
        team_means_sorted = team_means.reindex(
            team_means['diff'].abs().sort_values(ascending=False).index)

        i4_rows = []
        for i, (team, row) in enumerate(team_means_sorted.head(5).iterrows(), 1):
            i4_rows.append({
                '순위': i,
                '팀': team,
                'wide': round(row['vis_launch_wide'], 3),
                'center': round(row['vis_launch_center'], 3),
                '차이': round(row['diff'], 3),
            })

        i4_df = pd.DataFrame(i4_rows)
        print(i4_df.to_string(index=False))

    i_flags = []
else:
    i_flags = []

# ===== J. 2026-09-14 스크래치 검토값 대조 =====
# 검토 (1)~(6)은 원래 스크래치패드에서 일회성으로 돌아 재현이 불가능했다. 이 절은
# 그때 나온 값을 상수로 박아두고 지금 계산과 대조해, 나중에 코드를 고쳤을 때 결론이
# 조용히 바뀌는 것을 잡는다. 건수는 상대오차 5%, 평균·상관은 절대차 0.03이 기준이다.
print()
print("\n" + "=" * 80)
print("[J] 2026-09-14 스크래치 검토값 대조")
print("=" * 80)

j_flags = []


def check(label, actual, expected, kind='mean'):
    """실측값을 기대값과 대조해 출력하고, 어긋나면 플래그를 남긴다."""
    if actual is None or (isinstance(actual, float) and np.isnan(actual)):
        j_flags.append(f"[FLAG J] {label}: 계산 불가 (기대 {expected})")
        print(f"  [FLAG] {label:38s} 실측 nan       기대 {expected}")
        return
    if kind == 'count':
        ok = abs(actual - expected) <= max(1, 0.05 * expected)
        line = f"  {'[FLAG] ' if not ok else '       '}{label:38s} 실측 {actual:>9,d}  기대 {expected:>9,d}"
    else:
        ok = abs(actual - expected) <= 0.03
        line = f"  {'[FLAG] ' if not ok else '       '}{label:38s} 실측 {actual:>9.3f}  기대 {expected:>9.3f}"
    print(line)
    if not ok:
        j_flags.append(f"[FLAG J] {label}: 실측 {actual} vs 기대 {expected}")


op = openplay_situations
op_scope = op[(op['ball_x'] >= 30) & (op['ball_x'] < 110)]

# (1) 구간별 건수·평균
check('C 총 건수 (x30-120)', len(op[op['ball_x'] >= 30]), 30444, 'count')
for lo, hi, n_exp, launch_exp in [(70, 80, 4074, 1.44), (80, 90, 3646, 1.77),
                                  (90, 100, 2628, 2.06), (100, 110, 1209, 1.57),
                                  (110, 120, 749, 0.21)]:
    sub = op[(op['ball_x'] >= lo) & (op['ball_x'] < hi)]
    check(f'C {lo}-{hi} 건수', len(sub), n_exp, 'count')
    check(f'C {lo}-{hi} n_launch5', sub['n_launch5'].mean(), launch_exp)

low_block = op[op['def_line'] >= 100]
check('C 로우블록 x30-80 건수',
      len(low_block[(low_block['ball_x'] >= 30) & (low_block['ball_x'] < 80)]), 545, 'count')
check('C 로우블록 x80-110 건수',
      len(low_block[(low_block['ball_x'] >= 80) & (low_block['ball_x'] < 110)]), 5253, 'count')


def team_metric(df, col):
    """팀 평균 / 경기 간 재현성 / 16강 진출 상관."""
    per_match = df.groupby(['team', 'match_id'])[col].mean().reset_index()
    per_match['slot'] = per_match.groupby('team').cumcount()
    rep = avg_pairwise_corr(per_match.pivot(index='team', columns='slot', values=col))
    team_mean = df.groupby('team')[col].mean()
    adv = np.array([t in ADVANCED for t in team_mean.index], dtype=float)
    return float(df[col].mean()), rep, float(np.corrcoef(team_mean.to_numpy(), adv)[0, 1])


# (3) 후보 정의 비교 - 채택 정의(x30-110 채널)가 이 주제의 결론을 지탱하는 표다
for label, df_sub, col, exp in [
    ('E3 x30-80 전레인', op[(op['ball_x'] >= 30) & (op['ball_x'] < 80)], 'n_launch5', (1.13, 0.319, 0.316)),
    ('E3 x30-110 전레인', op_scope, 'n_launch5', (1.31, 0.403, 0.279)),
    ('E3 x30-110 채널', op_scope, 'n_channel5', (0.77, 0.447, 0.363)),
    ('E3 x80-110 채널', op[(op['ball_x'] >= 80) & (op['ball_x'] < 110)], 'n_channel5', (0.92, 0.258, 0.346)),
]:
    mean_v, rep_v, corr_v = team_metric(df_sub, col)
    check(f'{label} 평균', mean_v, exp[0])
    check(f'{label} 재현성', rep_v, exp[1])
    check(f'{label} 진출상관', corr_v, exp[2])

# (5)(6) 상대 백라인 - 범위는 채택 정의와 같은 x30-110
gj = op_scope[op_scope['opp_formation'].notna()].copy()
gj['bl'] = gj['opp_backline'].astype(int).replace({5: 3})
b3, b4 = gj[gj['bl'] == 3], gj[gj['bl'] == 4]
check('G 백3 상황 수', len(b3), 9399, 'count')
check('G 백4 상황 수', len(b4), 20307, 'count')
check('G 백3 n_def_near', b3['n_def_near'].mean(), 4.41)
check('G 백4 n_def_near', b4['n_def_near'].mean(), 4.17)
check('G corr(백라인, n_def_near)',
      float(np.corrcoef(gj['bl'], gj['n_def_near'])[0, 1]), -0.065)
gap_ok = gj['max_def_gap'].notna()
check('G corr(백라인, max_def_gap)',
      float(np.corrcoef(gj.loc[gap_ok, 'bl'], gj.loc[gap_ok, 'max_def_gap'])[0, 1]), 0.005)
check('G corr(n_def_near, max_def_gap)',
      float(np.corrcoef(gj.loc[gap_ok, 'n_def_near'], gj.loc[gap_ok, 'max_def_gap'])[0, 1]), -0.346)
check('H 백3 상대 n_channel5', b3['n_channel5'].mean(), 0.785)
check('H 백4 상대 n_channel5', b4['n_channel5'].mean(), 0.766)

# ===== 모든 플래그 종합 =====
print()
print("\n" + "=" * 80)
print("자동 플래그 종합")
print("=" * 80)

all_flags = a_flags + b_flags + c_flags + d_flags + e_flags + f_flags + g_flags + h_flags + i_flags + j_flags

if all_flags:
    for flag in all_flags:
        print(flag)
    print()
    print(f"총 플래그: {len(all_flags)}")
else:
    print("플래그 없음")

print()
print("=" * 80)
print(f"실행 완료 (소요 시간: {total_download_time:.1f}초)")
print("=" * 80)
