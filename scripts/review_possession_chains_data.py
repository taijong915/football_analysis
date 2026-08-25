"""데이터 검토: possession 체인 추적(possession_chains) 방법론이 의존하는
possession / possession_team 필드가 스페인 유로 2024 7경기에서 얼마나
신뢰할 수 있는지, 체인 길이 분포가 시퀀스 분석에 쓸 만한지 확인하는
일회성 검토 스크립트.

spain_euro2024/possession_chains/ 착수 전 데이터 검토 단계 산출물이며,
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

    possession_na = events['possession'].isna().sum()
    n_events = len(events)
    n_possessions = events['possession'].nunique()

    # 같은 possession 번호 안에 상대 팀 이벤트도 섞여 들어오므로
    # team과 possession_team을 함께 걸러야 정확한 "스페인 소유 구간"이 된다.
    spain_pass = events[
        (events['team'] == TEAM)
        & (events['possession_team'] == TEAM)
        & (events['type'] == 'Pass')
        & (events['pass_outcome'].isna())
    ]
    chain_lengths = spain_pass.groupby('possession').size()

    rows.append({
        'stage': stage,
        'opponent': opponent,
        'possession_na': possession_na,
        'n_events': n_events,
        'n_possessions': n_possessions,
        'spain_possessions_with_pass': chain_lengths.shape[0],
        'chain_mean': round(chain_lengths.mean(), 2) if len(chain_lengths) else None,
        'chain_median': chain_lengths.median() if len(chain_lengths) else None,
        'chain_max': chain_lengths.max() if len(chain_lengths) else None,
        'chain_min': chain_lengths.min() if len(chain_lengths) else None,
    })

result = pd.DataFrame(rows)
print(result.to_string(index=False))
print()
print("possession 결측 합계:", result['possession_na'].sum())
