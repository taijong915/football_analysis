"""데이터 검토: 구역 기반 전진 경로(zone_progression) 방법론이 의존하는
location / pass_end_location 필드가 스페인 유로 2024 7경기에서 얼마나
신뢰할 수 있는지 확인하는 일회성 검토 스크립트.

spain_euro2024/zone_progression/ 착수 전 데이터 검토 단계 산출물이며,
결과는 spain_euro2024/PLAN.md에 기록한다.
"""
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from src.data_loader import get_competition_matches, get_match_events

COMPETITION_ID = 55  # UEFA Euro
SEASON_ID = 282      # 2024
TEAM = "Spain"

matches = get_competition_matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
spain_matches = matches[(matches['home_team'] == TEAM) | (matches['away_team'] == TEAM)].copy()
spain_matches = spain_matches.sort_values('match_date')

rows = []
for _, match in spain_matches.iterrows():
    match_id = match['match_id']
    opponent = match['away_team'] if match['home_team'] == TEAM else match['home_team']
    stage = match['competition_stage']

    events = get_match_events(match_id=match_id)
    spain_events = events[events['team'] == TEAM]
    passes = spain_events[spain_events['type'] == 'Pass']

    n_passes = len(passes)
    loc_na = passes['location'].isna().sum()
    end_loc_na = passes['pass_end_location'].isna().sum()

    # location이 [x, y] 리스트가 아닌 이상값(예: 스칼라, 길이 다른 리스트) 확인
    def is_bad_point(v):
        if isinstance(v, list):
            return len(v) != 2
        return False  # NaN 등 결측은 위에서 이미 별도 집계

    loc_bad = passes['location'].apply(is_bad_point).sum()
    end_loc_bad = passes['pass_end_location'].apply(is_bad_point).sum()

    rows.append({
        'stage': stage,
        'opponent': opponent,
        'n_passes': n_passes,
        'location_na': loc_na,
        'location_na_pct': round(loc_na / n_passes * 100, 2) if n_passes else None,
        'end_location_na': end_loc_na,
        'end_location_na_pct': round(end_loc_na / n_passes * 100, 2) if n_passes else None,
        'location_bad_shape': loc_bad,
        'end_location_bad_shape': end_loc_bad,
    })

result = pd.DataFrame(rows)
print(result.to_string(index=False))
print()
print("전체 패스 수:", result['n_passes'].sum())
print("location 결측 합계:", result['location_na'].sum())
print("pass_end_location 결측 합계:", result['end_location_na'].sum())
