"""데이터 검토: "왼쪽 쏠림의 이유"(chain_outcomes) 방법론이 의존하는 Shot 이벤트가
스페인 유로 2024 7경기에서 얼마나 신뢰할 수 있는지, 기존 possession 체인 정의와
연결(같은 possession id)될 수 있는지 확인하는 일회성 검토 스크립트.

블로그 초안에서 "왜 왼쪽이었는가"에 대한 근거가 없다는 지적을 받아, 세 갈래로
원인을 보강하기로 했다.
1. 득점/슈팅 효율: 슈팅 위치(location)를 왼쪽/중앙/오른쪽으로 분류해, 실제 슈팅·xG·
   골이 어느 쪽에서 더 많이/효율적으로 나왔는지 확인한다.
2. 체인-슈팅 연결: possession_chains에서 이미 정의한 "체인"(같은 possession 안에서
   이어진 성공 패스 2회 이상)이 같은 possession 안에서 Shot으로 끝났는지 확인해,
   왼쪽으로 끝난 체인과 오른쪽으로 끝난 체인의 "슈팅 전환율"을 비교한다.
3. 크로스/어시스트 위치: "왼쪽에서 컷백/크로스가 더 자주 나왔을 것"이라는 후속
   가설을 검증하려면 `pass_goal_assist`/`pass_shot_assist`/`pass_cross` 플래그가
   실제로 존재하고 표본이 충분한지 확인해야 한다.

spain_euro2024/chain_outcomes/ 착수 전 데이터 검토 단계 산출물이며,
결과는 spain_euro2024/PLAN.md에 기록한다.
"""
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
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
    shots = events[(events['type'] == 'Shot') & (events['team'] == TEAM)]

    n_shots = len(shots)
    loc_na = shots['location'].isna().sum()
    xg_na = shots['shot_statsbomb_xg'].isna().sum() if 'shot_statsbomb_xg' in shots.columns else n_shots
    outcome_na = shots['shot_outcome'].isna().sum()
    n_goals = (shots['shot_outcome'] == 'Goal').sum()

    # 이미 정의한 "체인"(같은 possession 안 성공 패스 2회 이상)과 같은 possession인 슈팅이 몇 개인지
    passes = events[
        (events['type'] == 'Pass') & (events['team'] == TEAM) & (events['possession_team'] == TEAM)
    ].copy()
    passes = passes[passes['pass_outcome'].isna() & passes['pass_recipient'].notna()]
    chain_sizes = passes.groupby('possession').size()
    valid_possessions = set(chain_sizes[chain_sizes >= 2].index)

    shots_in_chain = shots[shots['possession'].isin(valid_possessions)]
    n_shots_in_chain = len(shots_in_chain)

    all_passes = events[(events['type'] == 'Pass') & (events['team'] == TEAM)]

    def bool_count(col):
        return int(all_passes[col].fillna(False).sum()) if col in all_passes.columns else 0

    rows.append({
        'stage': stage, 'opponent': opponent,
        'n_shots': n_shots, 'location_na': loc_na, 'xg_na': xg_na, 'outcome_na': outcome_na,
        'n_goals': n_goals, 'n_chains': len(valid_possessions), 'n_shots_in_chain': n_shots_in_chain,
        'n_goal_assist': bool_count('pass_goal_assist'), 'n_shot_assist': bool_count('pass_shot_assist'),
        'n_cross': bool_count('pass_cross'),
    })

result = pd.DataFrame(rows)
print(result.to_string(index=False))
print()
print('전체 슈팅 수:', result['n_shots'].sum())
print('전체 골 수:', result['n_goals'].sum())
print('체인과 연결된 슈팅 수(전체 대비):', result['n_shots_in_chain'].sum(), '/', result['n_shots'].sum())
print('골 어시스트 합계:', result['n_goal_assist'].sum())
print('슈팅 어시스트 합계:', result['n_shot_assist'].sum())
print('크로스 합계:', result['n_cross'].sum())
