"""데이터 검토: '침투 선택지' 방법론이 의존하는 StatsBomb 360 프리즈프레임이
2022 월드컵 조별리그 48경기에서 얼마나 신뢰할 수 있는지 - 특히 수비 라인 뒤
공간의 `visible_area` 커버리지가 팀 간 비교를 허용할 만큼 균질한지 - 확인하는
일회성 검토 스크립트.

korea_qatar2022/ 착수 전 데이터 검토 단계 산출물이며, 결과는
korea_qatar2022/PLAN.md에 기록한다.
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

# 침투 밴드 격자는 상황마다 모양이 같고 x 범위만 달라진다. 상황이 2만 건이 넘어
# 매번 meshgrid를 새로 만들면 비용이 크므로, 단위 격자를 한 번만 만들어 두고
# 상황마다 x축만 늘려 쓴다.
_BAND_U, _BAND_Y = np.meshgrid(np.linspace(0, 1, 15), np.linspace(2, 78, 25))
_BAND_U = _BAND_U.ravel()
_BAND_Y = _BAND_Y.ravel()

def band_visibility(path, def_line, band_width):
    """침투 밴드 [def_line, def_line + band_width] x [2, 78]의 가시 격자점 비율."""
    if path is None or def_line >= 119.5:
        return np.nan
    x_max = min(120.0, def_line + band_width)
    if x_max <= def_line:
        return np.nan
    points = np.column_stack((def_line + _BAND_U * (x_max - def_line), _BAND_Y))
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
        'bad_visible_area': bad_va,  # 선수 행이 아니라 프레임 단위 개수
    }

    # ===== B. 전제 검증 =====
    # 기록된 선수 좌표가 그 프레임 visible_area 안에 있는 비율. 선수 행마다
    # Path를 새로 만들면 230만 번이 되므로 프레임 단위로 한 번에 판정한다.
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

    # ===== 선제골 시각 계산 =====
    goal_events = events[(events['type'] == 'Shot') & (events['shot_outcome'] == 'Goal')]
    first_goal_minute = goal_events.iloc[0]['minute'] if not goal_events.empty else None

    # ===== 상황별 행 생성 =====
    events = events.copy()
    events['x'] = [loc[0] if isinstance(loc, (list, np.ndarray)) and len(loc) == 2 else np.nan
                   for loc in events['location']]
    progression_events = events[(events['type'] == 'Pass') & events['x'].between(30, 80)]

    home_team, away_team = match_info['home_team'], match_info['away_team']
    situation_rows = []

    for event_id, team, period, minute, second, ball_x in zip(
            progression_events['id'], progression_events['team'],
            progression_events['period'], progression_events['minute'],
            progression_events['second'], progression_events['x']):
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

        # 액터·골키퍼를 뺀 아군 필드플레이어 (최대 9명)
        mate_x = frame_loc[is_mate & (~is_keeper) & (~is_actor), 0]
        mate_x = mate_x[~np.isnan(mate_x)]

        situation_rows.append({
            'match_id': match_id,
            'stage': match_info['competition_stage'],
            'team': team,
            'opponent': away_team if team == home_team else home_team,
            'period': period,
            'minute': minute,
            'second': second,
            'ball_x': round(float(ball_x), 2),
            'def_line': round(def_line, 2),
            'band15': round(band15, 3) if not np.isnan(band15) else np.nan,
            'band10': round(band10, 3) if not np.isnan(band10) else np.nan,
            'vis_depth': round(float(coords[:, 0].max()) - def_line, 2),
            'n_opp_visible': int(opponent_x.size),
            'n_tm_visible': int(min(mate_x.size, 9)),
            'n_beyond': int((mate_x > def_line).sum()),
            'pre_first_goal': first_goal_minute is None or minute < first_goal_minute,
        })

    return a_row, b_row, situation_rows


# ===== 메인 로직 =====
print("2022 FIFA World Cup 조별리그 360 데이터 검토")
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

# ===== situations.parquet 저장 =====
situations_df = pd.DataFrame(all_situations)
situations_path = CACHE_DIR / 'situations.pkl'
situations_df.to_pickle(situations_path.with_suffix('.pkl'))
print(f"situations.parquet 저장 완료: {len(situations_df)} 행")
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
    if row['n_360_events'] == 0:
        a_flags.append(f"[FLAG A] match_id {row['match_id']}: 360 프레임 0개")
    if row['bad_visible_area'] > 0:
        a_flags.append(f"[FLAG A] match_id {row['match_id']}: 이상 visible_area {row['bad_visible_area']}개")

print()
print("A 전체 합산:")
print(f"  총 경기: {len(a_group_df)}")
print(f"  총 프레임 행: {a_group_df['n_frame_rows'].sum()}")
cache_size_mb = sum(
    (f.stat().st_size for f in CACHE_DIR.glob('*.parquet') if f.exists() and 'situations' not in f.name),
    sum(f.stat().st_size for f in CACHE_DIR.glob('*.pkl') if f.exists())
) / (1024 * 1024)
print(f"  캐시 폴더 용량: {cache_size_mb:.1f} MB")
print(f"  다운로드 시간: {total_download_time:.1f}초")

# ===== B. 전제 검증 =====
print()
print("\n[B] 선수 위치 검증 (location이 visible_area 안)")
print("=" * 80)
b_df = pd.DataFrame(b_results)
b_group_df = b_df[b_df['match_id'].isin(group_matches['match_id'])].copy()
if not b_group_df.empty:
    overall_ratio = np.mean(b_group_df['location_in_visible_area_ratio'])
    min_ratio = b_group_df['location_in_visible_area_ratio'].min()
    print(f"전체 비율: {overall_ratio:.3f}")
    print(f"경기별 최솟값: {min_ratio:.3f}")

    b_flags = []
    if overall_ratio < 0.95:
        b_flags.append(f"[FLAG B] 전체 비율 {overall_ratio:.3f} < 0.95")
    if min_ratio < 0.90:
        b_flags.append(f"[FLAG B] 경기별 최솟값 {min_ratio:.3f} < 0.90")
else:
    b_flags = []

# ===== C. 침투 밴드 가시율 (팀별 32행, 조별리그만) =====
print()
print("\n[C] 침투 밴드 가시율 (조별리그, 팀별 3경기 합산)")
print("=" * 80)

group_situations = situations_df[situations_df['stage'] == 'Group Stage'].copy()
if not group_situations.empty:
    team_data = {}
    for team in group_situations['team'].unique():
        team_data[team] = {
            'band15_values': [],
            'band10_values': [],
            'vis_depth_values': [],
            'visible_def': [],
            'visible_atk': [],
            'n_beyond_values': [],
            'pre_goal_obs': 0,
            'total_obs': 0,
        }

    for _, row in group_situations.iterrows():
        team = row['team']
        if pd.notna(row['band15']):
            team_data[team]['band15_values'].append(row['band15'])
        if pd.notna(row['band10']):
            team_data[team]['band10_values'].append(row['band10'])
        if pd.notna(row['vis_depth']):
            team_data[team]['vis_depth_values'].append(row['vis_depth'])
        team_data[team]['visible_def'].append(row['n_opp_visible'])
        team_data[team]['visible_atk'].append(row['n_tm_visible'])
        team_data[team]['n_beyond_values'].append(row['n_beyond'])
        if row['pre_first_goal']:
            team_data[team]['pre_goal_obs'] += 1
        team_data[team]['total_obs'] += 1

    c_rows = []
    for team in sorted(team_data.keys()):
        data = team_data[team]
        if data['total_obs'] == 0:
            continue

        c_row = {
            'team': team,
            'n_progressions': data['total_obs'],
            'band15_mean': round(np.mean(data['band15_values']), 3) if data['band15_values'] else np.nan,
            'band15_median': round(np.median(data['band15_values']), 3) if data['band15_values'] else np.nan,
            'band10_mean': round(np.mean(data['band10_values']), 3) if data['band10_values'] else np.nan,
            'vis_depth_median': round(np.median(data['vis_depth_values']), 3) if data['vis_depth_values'] else np.nan,
            'visible_def_median': round(np.median(data['visible_def']), 1) if data['visible_def'] else np.nan,
            'visible_atk_median': round(np.median(data['visible_atk']), 1) if data['visible_atk'] else np.nan,
            'n_beyond_mean': round(np.mean(data['n_beyond_values']), 3) if data['n_beyond_values'] else np.nan,
            'pre_goal_obs': data['pre_goal_obs'],
        }
        c_rows.append(c_row)

    c_df = pd.DataFrame(c_rows).sort_values('band15_mean', ascending=False)
    print(c_df.to_string(index=False))

    # C 플래그
    c_flags = []
    band15_means = c_df['band15_mean'].values
    band15_means = band15_means[~np.isnan(band15_means)]

    if len(band15_means) > 0:
        std_band15 = np.std(band15_means)
        range_band15 = np.max(band15_means) - np.min(band15_means)
        ratio_band15 = np.max(band15_means) / np.min(band15_means) if np.min(band15_means) > 0 else np.inf

        if std_band15 > 0.05:
            c_flags.append(f"[FLAG C] band15 표준편차 {std_band15:.4f} > 0.05")
        if range_band15 > 0.15:
            c_flags.append(f"[FLAG C] band15 범위 {range_band15:.4f} > 0.15")
        if ratio_band15 > 1.5:
            c_flags.append(f"[FLAG C] band15 최댓값/최솟값 {ratio_band15:.3f} > 1.5")

        for _, row in c_df.iterrows():
            if row['band15_mean'] < 0.15:
                c_flags.append(f"[FLAG C] {row['team']}: band15 평균 {row['band15_mean']:.3f} < 0.15")

    print()
    print("C 전체 분포 (조별리그 32팀):")
    print(f"  band15 평균: {np.mean(band15_means):.3f}")
    print(f"  band15 중앙값: {np.median(band15_means):.3f}")
    print(f"  band15 Q1/Q2/Q3: {np.percentile(band15_means, 25):.3f} / {np.percentile(band15_means, 50):.3f} / {np.percentile(band15_means, 75):.3f}")

    n_high = np.sum(band15_means >= 0.5)
    n_low = np.sum(band15_means < 0.3)
    print(f"  band15 >= 0.5인 팀: {n_high}/{len(band15_means)} ({100*n_high/len(band15_means):.1f}%)")
    print(f"  band15 < 0.3인 팀: {n_low}/{len(band15_means)} ({100*n_low/len(band15_means):.1f}%)")

    # 보조 표: 팀-경기 94행
    print()
    print("C 보조 표 (팀-경기별, 참고용):")
    print("=" * 80)
    team_match_rows = []
    for _, row in group_situations.iterrows():
        team_match_rows.append({
            'team': row['team'],
            'opponent': row['opponent'],
            'match_id': row['match_id'],
            'n_progressions': 1,  # 집계는 나중에
        })

    tm_df = pd.DataFrame(team_match_rows)
    tm_agg = tm_df.groupby(['team', 'opponent', 'match_id']).size().reset_index(name='n_progressions')
    tm_agg = tm_agg.sort_values(['team', 'match_id'])
    print(tm_agg.to_string(index=False))

    # 팀-경기 조합이 96이 아닌 이유
    expected_combinations = 32 * 3
    actual_combinations = len(tm_agg)
    print()
    print(f"팀-경기 조합: {actual_combinations}개 (예상 {expected_combinations}개)")
    if actual_combinations < expected_combinations:
        print(f"  차이: {expected_combinations - actual_combinations}개 조합이 전진 상황 0건")

else:
    c_flags = []
    print("(데이터 없음)")

# ===== D. 표본량 편차 =====
print()
print("\n[D] 표본량 편차 (팀별 3경기 합산, 조별리그)")
print("=" * 80)

d_df = c_df[['team', 'n_progressions', 'pre_goal_obs']].copy()
d_df = d_df.rename(columns={'n_progressions': 'd1_obs', 'pre_goal_obs': 'd2_obs'})

if not d_df.empty:
    print("D1 & D2 (팀별 합산):")
    print(d_df.to_string(index=False))

    d_flags = []
    n_prog = d_df['d1_obs'].values
    n_pre = d_df['d2_obs'].values

    if len(n_prog) > 0:
        ratio_d1 = np.max(n_prog) / np.min(n_prog) if np.min(n_prog) > 0 else np.inf
        if ratio_d1 > 3.0:
            d_flags.append(f"[FLAG D1] 최대/최소 관측 수 비율 {ratio_d1:.2f} > 3.0")
        if (n_prog < 100).any():
            low_teams = d_df[d_df['d1_obs'] < 100]
            for _, row in low_teams.iterrows():
                d_flags.append(f"[FLAG D1] {row['team']}: 관측 수 {row['d1_obs']} < 100")

    if len(n_pre) > 0:
        if (n_pre < 30).any():
            low_teams_d2 = d_df[d_df['d2_obs'] < 30]
            for _, row in low_teams_d2.iterrows():
                d_flags.append(f"[FLAG D2] {row['team']}: 선제골 이전 관측 수 {row['d2_obs']} < 30")

        median_pre = np.median(n_pre)
        if median_pre < 60:
            d_flags.append(f"[FLAG D2] 중앙값 {median_pre:.1f} < 60")
else:
    d_flags = []

# ===== E. 한국 4경기 =====
print()
print("\n[E] 한국 4경기 개별 분석")
print("=" * 80)

korea_situations = situations_df[situations_df['team'] == 'South Korea'].copy()
if not korea_situations.empty:
    e_rows = []
    for _, row in korea_situations.iterrows():
        e_rows.append({
            'match_id': row['match_id'],
            'stage': row['stage'],
            'opponent': row['opponent'],
            'team': row['team'],
            'n_progressions': 1,
        })

    e_df = pd.DataFrame(e_rows)
    e_agg = e_df.groupby(['match_id', 'stage', 'opponent', 'team']).size().reset_index(name='n_progressions')
    e_agg = e_agg.sort_values('match_id')

    e_detail_rows = []
    for match_id in e_agg['match_id'].unique():
        match_situations = korea_situations[korea_situations['match_id'] == match_id]
        if match_situations.empty:
            continue

        stage = match_situations.iloc[0]['stage']
        opponent = match_situations.iloc[0]['opponent']

        band15_vals = match_situations['band15'].dropna()
        vis_depth_vals = match_situations['vis_depth'].dropna()
        n_beyond_vals = match_situations['n_beyond'].dropna()

        e_detail_rows.append({
            'match_id': match_id,
            'stage': stage,
            'opponent': opponent,
            'n_progressions': len(match_situations),
            'band15_mean': round(np.mean(band15_vals), 3) if len(band15_vals) > 0 else np.nan,
            'vis_depth_median': round(np.median(vis_depth_vals), 3) if len(vis_depth_vals) > 0 else np.nan,
            'visible_atk_median': round(np.median(match_situations['n_tm_visible']), 1),
            'n_beyond_mean': round(np.mean(n_beyond_vals), 3) if len(n_beyond_vals) > 0 else np.nan,
            'pre_goal_obs': match_situations['pre_first_goal'].sum(),
        })

    e_detail_df = pd.DataFrame(e_detail_rows).sort_values('match_id')
    print(e_detail_df.to_string(index=False))
    e_flags = []
else:
    e_flags = []
    print("(한국 데이터 없음)")

# ===== 모든 플래그 종합 =====
print()
print("\n" + "=" * 80)
print("자동 플래그 종합")
print("=" * 80)

all_flags = a_flags + b_flags + c_flags + d_flags + e_flags
if all_flags:
    for flag in all_flags:
        print(flag)
    print()
    print(f"총 플래그: {len(all_flags)}")
else:
    print("플래그 없음")
