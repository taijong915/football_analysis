"""좌우 비대칭 통계 검증(asymmetry_stats) 프로토타입

두 가지 지표를 각각 매치별 "왼쪽 비율"로 계산하고, 0.5(완전 대칭)와의 차이를
paired t-test(scipy.stats.ttest_1samp, mu=0.5)로 검정한다.

1. **구역 점유 좌/우 비율**: zone_progression과 같은 30구역 그리드에서 성공 패스
   시작 위치가 왼쪽/오른쪽 채널에 속하는 비율. "왼쪽 쏠림"(구역 기반 전진 경로의
   관찰) 주장을 검정한다. 전체 구역 기준과, 실제 쏠림이 관찰된 Att-Mid 가로단만
   좁힌 기준 둘 다 본다 (데이터 검토에서 확인한 두 스코프).
2. **패스 네트워크 노드 좌/우 비율**: `position` 라벨을 좌/우로 나눠, 7경기 모두에
   공통으로 존재하는 4개 역할군(Back/Center Back/Defensive Midfield/Wing)의 슬롯별
   패스 시도 수를 합산한 좌/우 비율. "구조 유지"(패스 네트워크의 관찰) 주장을
   검정한다 - 목적지(구역)는 왼쪽으로 쏠려도, 선수 관여도(패스 수) 자체는 좌우
   대칭적일 수 있다는 가설을 확인한다.

데이터 검토(scripts/review_asymmetry_stats_data.py)에서 확인한 대로 7경기 모두
좌/우 표본이 충분하고(구역 기준 132~370개, Att-Mid 기준 26~142개), 역할군 4개는
7경기 전부에서 좌우 대응 쌍으로 존재한다.

검증을 마치고 spain_euro2024/asymmetry_stats/07_spain_euro2024_asymmetry_stats.ipynb로
옮겨 7경기 전체를 실행했다. 결과는 spain_euro2024/asymmetry_stats/RESULTS.md 참고.
이 스크립트는 그 승격 과정을 추적할 수 있도록 남겨둔 것이다.
"""
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from mplsoccer import Pitch

from src.data_loader import get_competition_matches, get_match_events

COMPETITION_ID = 55  # UEFA Euro
SEASON_ID = 282      # 2024
TEAM = "Spain"

pitch = Pitch(pitch_type='statsbomb', positional=True)
x_edges = pitch.dim.positional_x
y_edges = pitch.dim.positional_y
ATT_MID_XI = 3

LEFT_Y = {0, 1}
RIGHT_Y = {3, 4}
COMMON_ROLE_STEMS = ['Back', 'Center Back', 'Defensive Midfield', 'Wing']


def zone_index(x, y):
    xi = np.clip(np.searchsorted(x_edges, x, side='right') - 1, 0, len(x_edges) - 2)
    yi = np.clip(np.searchsorted(y_edges, y, side='right') - 1, 0, len(y_edges) - 2)
    return xi, yi


def match_zone_ratios(events: pd.DataFrame) -> dict:
    passes = events[(events['type'] == 'Pass') & (events['team'] == TEAM)].copy()
    passes = passes[passes['pass_outcome'].isna() & passes['pass_recipient'].notna()]
    passes['x'] = passes['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
    passes['y'] = passes['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)
    passes = passes.dropna(subset=['x', 'y'])

    zi = passes.apply(lambda r: zone_index(r['x'], r['y']), axis=1, result_type='expand')
    passes['xi'], passes['yi'] = zi[0], zi[1]

    left_all = (passes['yi'].isin(LEFT_Y)).sum()
    right_all = (passes['yi'].isin(RIGHT_Y)).sum()

    att_mid = passes[passes['xi'] == ATT_MID_XI]
    left_am = (att_mid['yi'].isin(LEFT_Y)).sum()
    right_am = (att_mid['yi'].isin(RIGHT_Y)).sum()

    return {
        'zone_all_left_ratio': left_all / (left_all + right_all),
        'zone_att_mid_left_ratio': left_am / (left_am + right_am),
    }


def match_network_ratio(events: pd.DataFrame) -> float:
    team_events = events[events['team'] == TEAM]
    player_position = (
        team_events.dropna(subset=['position'])
        .groupby('player')['position']
        .agg(lambda s: s.value_counts().idxmax())
    )

    passes = events[(events['type'] == 'Pass') & (events['team'] == TEAM)].copy()
    passes = passes[passes['pass_outcome'].isna() & passes['pass_recipient'].notna()]
    passes['passer_position'] = passes['player'].map(player_position)

    slot_pass_count = passes.dropna(subset=['passer_position']).groupby('passer_position').size()

    left_total = sum(slot_pass_count.get(f'Left {stem}', 0) for stem in COMMON_ROLE_STEMS)
    right_total = sum(slot_pass_count.get(f'Right {stem}', 0) for stem in COMMON_ROLE_STEMS)
    return left_total / (left_total + right_total)


matches = get_competition_matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
spain_matches = matches[(matches['home_team'] == TEAM) | (matches['away_team'] == TEAM)].copy()
spain_matches = spain_matches.sort_values('match_date')

rows = []
for _, match in spain_matches.iterrows():
    match_id = match['match_id']
    opponent = match['away_team'] if match['home_team'] == TEAM else match['home_team']
    stage = match['competition_stage']

    events = get_match_events(match_id=match_id)
    zone_ratios = match_zone_ratios(events)
    network_ratio = match_network_ratio(events)

    rows.append({
        'match': f"{stage} vs {opponent}",
        **zone_ratios,
        'network_left_ratio': network_ratio,
    })

result = pd.DataFrame(rows)
print(result.to_string(index=False))
print()

metrics = [
    ('zone_all_left_ratio', '#00f0ff', 'Zone occupancy (all zones)'),
    ('zone_att_mid_left_ratio', '#ffe14d', 'Zone occupancy (Att-Mid only)'),
    ('network_left_ratio', '#ff5cad', 'Pass network (4 role pairs)'),
]

for col, _, label in metrics:
    t_stat, p_value = stats.ttest_1samp(result[col], popmean=0.5)
    print(f"{label}: mean={result[col].mean():.3f}, sd={result[col].std():.3f}, "
          f"t({len(result)-1})={t_stat:.3f}, p={p_value:.4f}")

fig, ax = plt.subplots(figsize=(9, 6))
fig.set_facecolor('#1e1e1e')
ax.set_facecolor('#1e1e1e')

y_positions = np.arange(len(result))
for i, (col, color, label) in enumerate(metrics):
    offset = (i - 1) * 0.22
    ax.scatter(result[col], y_positions + offset, color=color, s=70, label=label, zorder=3)

ax.axvline(0.5, color='white', linestyle='--', linewidth=1, alpha=0.7, zorder=1)
ax.set_yticks(y_positions)
ax.set_yticklabels(result['match'], color='white', fontsize=9)
ax.set_xlabel('Left ratio (0.5 = symmetric)', color='white', fontsize=10)
ax.tick_params(axis='x', colors='white')
ax.invert_yaxis()
for spine in ax.spines.values():
    spine.set_color('#555555')
ax.legend(loc='upper left', bbox_to_anchor=(1.01, 1), facecolor='#1e1e1e', edgecolor='#555555',
          labelcolor='white', fontsize=9)
ax.set_title('Spain Left/Right Asymmetry by Match', color='white', fontsize=13, fontweight='bold', pad=14)
fig.tight_layout()

out_dir = os.path.join('data', 'asymmetry_stats_prototype')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'spain_asymmetry_stats_prototype.png')
fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
print('saved', out_path)
