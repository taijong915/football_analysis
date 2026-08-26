"""데이터 검토: 좌우 비대칭 통계 검증(asymmetry_stats) 방법론이 의존하는 데이터가
스페인 유로 2024 7경기에서 통계 검정(t-test/부트스트랩 등)에 쓸 만한지 확인하는
일회성 검토 스크립트.

방법론 요약(PLAN.md 분석 질문 5)은 두 갈래다.
1. 구역 기반 전진 경로의 "왼쪽 쏠림" 검증: 경기별 성공 패스의 시작 위치가 왼쪽/중앙/
   오른쪽 y채널(zone_progression과 동일한 30구역 그리드 기준) 중 어디에 속하는지 집계해,
   경기별 좌/우 표본 수 분포를 확인한다 - 전체 구역 기준과, 실제 편중이 관찰된
   Att-Mid 가로단(zone_progression/RESULTS.md에서 언급된 "Att-Mid/Left Wide" 근거)
   기준 두 가지를 모두 본다.
2. 패스 네트워크의 "구조 유지" 검증: 경기별 스페인 `position` 라벨을 좌/중앙/우로
   분류해, 왼쪽-오른쪽 포지션이 경기마다 대칭적으로(예: Left Back <-> Right Back)
   존재하는지, 포메이션 변경(백4<->백3 등)으로 좌우 포지션 라벨 집합 자체가
   달라지는 경기가 있는지 확인한다 - 노드별 패스 수 비교가 성립하려면 좌우 포지션이
   대응 쌍을 이뤄야 하기 때문이다.

location/pass_end_location 결측률은 이미 zone_progression 데이터 검토
(scripts/review_zone_progression_data.py, 동일 7경기)에서 0건으로 확인했으므로
여기서는 재검증하지 않는다. position 컬럼 결측률/Tactical Shift 빈도도 패스 네트워크
데이터 검토에서 이미 확인했으므로(PLAN.md 방법론 요약 참고), 여기서는 좌/우 라벨
분류·대칭성만 추가로 본다.

spain_euro2024/asymmetry_stats/ 착수 전 데이터 검토 단계 산출물이며,
결과는 spain_euro2024/PLAN.md에 기록한다.
"""
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
from mplsoccer import Pitch

from src.data_loader import get_competition_matches, get_match_events

COMPETITION_ID = 55  # UEFA Euro
SEASON_ID = 282      # 2024
TEAM = "Spain"

pitch = Pitch(pitch_type='statsbomb', positional=True)
x_edges = pitch.dim.positional_x
y_edges = pitch.dim.positional_y
ATT_MID_XI = 3  # zone_progression 30구역 그리드에서 'Att-Mid' 가로단 인덱스 (0=Def Box .. 5=Att Box)

LEFT_Y = {0, 1}   # Left Wide, Left HS
RIGHT_Y = {3, 4}  # Right HS, Right Wide


def zone_index(x, y):
    xi = np.clip(np.searchsorted(x_edges, x, side='right') - 1, 0, len(x_edges) - 2)
    yi = np.clip(np.searchsorted(y_edges, y, side='right') - 1, 0, len(y_edges) - 2)
    return xi, yi


def classify_position_side(position: str) -> str:
    if not isinstance(position, str):
        return 'Unknown'
    if position.startswith('Left'):
        return 'Left'
    if position.startswith('Right'):
        return 'Right'
    return 'Central'


matches = get_competition_matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
spain_matches = matches[(matches['home_team'] == TEAM) | (matches['away_team'] == TEAM)].copy()
spain_matches = spain_matches.sort_values('match_date')

zone_rows = []
position_rows = []

for _, match in spain_matches.iterrows():
    match_id = match['match_id']
    opponent = match['away_team'] if match['home_team'] == TEAM else match['home_team']
    stage = match['competition_stage']

    events = get_match_events(match_id=match_id)

    # --- 1. 구역 기반 좌/중앙/우 표본 수 ---
    passes = events[
        (events['type'] == 'Pass') & (events['team'] == TEAM)
    ].copy()
    passes = passes[passes['pass_outcome'].isna() & passes['pass_recipient'].notna()]
    passes['x'] = passes['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
    passes['y'] = passes['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)
    passes = passes.dropna(subset=['x', 'y'])

    zi = passes.apply(lambda r: zone_index(r['x'], r['y']), axis=1, result_type='expand')
    passes['xi'], passes['yi'] = zi[0], zi[1]

    n_left_all = (passes['yi'].isin(LEFT_Y)).sum()
    n_right_all = (passes['yi'].isin(RIGHT_Y)).sum()
    n_central_all = len(passes) - n_left_all - n_right_all

    att_mid = passes[passes['xi'] == ATT_MID_XI]
    n_left_am = (att_mid['yi'].isin(LEFT_Y)).sum()
    n_right_am = (att_mid['yi'].isin(RIGHT_Y)).sum()

    zone_rows.append({
        'stage': stage, 'opponent': opponent,
        'n_passes_total': len(passes),
        'left_all': n_left_all, 'central_all': n_central_all, 'right_all': n_right_all,
        'att_mid_left': n_left_am, 'att_mid_right': n_right_am,
    })

    # --- 2. position 라벨 좌/우 대칭성 ---
    spain_events = events[events['team'] == TEAM].dropna(subset=['position'])
    positions = spain_events['position'].unique()
    sides = pd.Series([classify_position_side(p) for p in positions], index=positions)
    left_labels = sorted(sides[sides == 'Left'].index.tolist())
    right_labels = sorted(sides[sides == 'Right'].index.tolist())

    # Left/Right 접두어를 뗀 나머지 부분이 같은 라벨끼리 짝이 맞는지 확인 (예: Left Back <-> Right Back)
    left_stems = {lbl.replace('Left ', '', 1) for lbl in left_labels}
    right_stems = {lbl.replace('Right ', '', 1) for lbl in right_labels}
    unmatched = (left_stems - right_stems) | (right_stems - left_stems)

    position_rows.append({
        'stage': stage, 'opponent': opponent,
        'n_left_labels': len(left_labels), 'n_right_labels': len(right_labels),
        'left_labels': ', '.join(left_labels),
        'right_labels': ', '.join(right_labels),
        'unmatched_stems': ', '.join(sorted(unmatched)) if unmatched else '(없음)',
    })

zone_df = pd.DataFrame(zone_rows)
position_df = pd.DataFrame(position_rows)

print('=== 1. 경기별 좌/중앙/우 성공 패스 표본 수 (전체 구역 기준) ===')
print(zone_df[['stage', 'opponent', 'n_passes_total', 'left_all', 'central_all', 'right_all']].to_string(index=False))
print()
print('=== 1-1. Att-Mid 가로단만 (왼쪽 쏠림이 관찰된 zone_progression 결과의 근거 구역) ===')
print(zone_df[['stage', 'opponent', 'att_mid_left', 'att_mid_right']].to_string(index=False))
print()
print('=== 2. 경기별 position 라벨 좌/우 대칭성 ===')
print(position_df.to_string(index=False))
