"""왼쪽 쏠림의 이유(chain_outcomes) 프로토타입

블로그 초안이 "왼쪽으로 쏠렸다"는 결과만 보여주고 "왜"는 다루지 않는다는 피드백을
받아, 세 갈래로 원인을 보강한다.

1. **체인-슈팅 연결(득점/슈팅 효율)**: possession_chains에서 이미 정의한 "체인"
   (같은 possession 안에서 이어진 성공 패스 2회 이상, `_prepare_chain_passes`)이
   같은 possession 안에서 Shot으로 끝났는지 확인해, 왼쪽/오른쪽으로 끝난 체인의
   "슈팅 전환율"과 xG·골을 비교한다.
2. **선수 조합 밀도**: 패스 네트워크의 포지션 슬롯 쌍(passer_position, recipient_position)
   집계를 재사용해, 왼쪽 슬롯끼리의 연결(Left-Left)과 오른쪽 슬롯끼리의 연결
   (Right-Right)의 총 패스 수를 7경기 합산으로 비교한다 - "왼쪽 조합이 더 자주
   호흡을 맞췄는가"를 정량적으로 본다.
3. **크로스/어시스트 위치**: "왼쪽에서 컷백/크로스가 더 자주 올라왔는가"라는 후속
   피드백을 받아 추가했다. `pass_goal_assist`/`pass_shot_assist`/`pass_cross` 플래그가
   참인 패스의 시작 위치를 왼쪽/중앙/오른쪽으로 분류해 비교한다.

데이터 검토(scripts/review_chain_outcomes_data.py)에서 확인한 대로 7경기 전체
Shot 이벤트는 location/xg/outcome 결측이 0건이고, 전체 슈팅 123개 중 111개(90%)가
기존 체인 정의와 같은 possession으로 연결된다. pass_goal_assist/pass_shot_assist/
pass_cross는 7경기 합산 각각 12/96/89건이다.

검증을 마치고 spain_euro2024/chain_outcomes/08_spain_euro2024_chain_outcomes.ipynb로
옮겨 7경기 전체를 실행했다. 결과는 spain_euro2024/chain_outcomes/RESULTS.md 참고.
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
from mplsoccer import Pitch
from scipy import stats

from src.data_loader import get_competition_matches, get_match_events
from src.visualizer import _prepare_chain_passes, _chain_length_by_final_side, _zone_index

COMPETITION_ID = 55
SEASON_ID = 282
TEAM = "Spain"

pitch = Pitch(pitch_type='statsbomb', positional=True)
x_edges = pitch.dim.positional_x
y_edges = pitch.dim.positional_y
LEFT_Y = {0, 1}
RIGHT_Y = {3, 4}


def _side_of_location(loc):
    if not isinstance(loc, list):
        return None
    xi, yi = _zone_index(loc[0], loc[1], x_edges, y_edges)
    if yi in LEFT_Y:
        return 'Left'
    if yi in RIGHT_Y:
        return 'Right'
    return 'Central'


def _bool_col(df, col):
    if col in df.columns:
        return df[col].fillna(False).astype(bool)
    return pd.Series(False, index=df.index)


def match_assist_locations(events: pd.DataFrame) -> dict:
    """골 어시스트/슈팅 어시스트/크로스 패스의 시작 위치(왼쪽/중앙/오른쪽)를 센다."""
    passes = events[(events['type'] == 'Pass') & (events['team'] == TEAM)].copy()
    passes['side'] = passes['location'].apply(_side_of_location)

    ga = passes[_bool_col(passes, 'pass_goal_assist')]
    sa = passes[_bool_col(passes, 'pass_shot_assist')]
    cr = passes[_bool_col(passes, 'pass_cross')]

    return {
        'goal_assist_L': (ga['side'] == 'Left').sum(), 'goal_assist_C': (ga['side'] == 'Central').sum(),
        'goal_assist_R': (ga['side'] == 'Right').sum(),
        'shot_assist_L': (sa['side'] == 'Left').sum(), 'shot_assist_C': (sa['side'] == 'Central').sum(),
        'shot_assist_R': (sa['side'] == 'Right').sum(),
        'cross_L': (cr['side'] == 'Left').sum(), 'cross_R': (cr['side'] == 'Right').sum(),
    }


def match_chain_outcomes(events: pd.DataFrame) -> pd.DataFrame:
    """체인별(possession id, 패스 수, 좌/중/우, 슈팅 여부, xG, 골 여부)을 반환한다."""
    passes = _prepare_chain_passes(events, TEAM, min_chain_length=2, x_edges=x_edges, y_edges=y_edges)
    summary = _chain_length_by_final_side(passes)

    shots = events[(events['type'] == 'Shot') & (events['team'] == TEAM)]
    shot_agg = shots.groupby('possession').agg(
        xg=('shot_statsbomb_xg', 'sum'),
        n_shots=('shot_statsbomb_xg', 'count'),
        n_goals=('shot_outcome', lambda s: (s == 'Goal').sum()),
    )

    summary = summary.join(shot_agg, on='possession')
    summary[['xg', 'n_shots', 'n_goals']] = summary[['xg', 'n_shots', 'n_goals']].fillna(0)
    summary['has_shot'] = summary['n_shots'] > 0
    return summary


def match_role_pair_density(events: pd.DataFrame) -> dict:
    """포지션 슬롯 쌍 패스 수를 Left-Left / Right-Right / Cross(한쪽만 L/R) / Central 포함으로 나눠 합산한다."""
    team_events = events[events['team'] == TEAM]
    player_position = (
        team_events.dropna(subset=['position'])
        .groupby('player')['position']
        .agg(lambda s: s.value_counts().idxmax())
    )

    passes = events[(events['type'] == 'Pass') & (events['team'] == TEAM)].copy()
    passes = passes[passes['pass_outcome'].isna() & passes['pass_recipient'].notna()]
    passes['passer_position'] = passes['player'].map(player_position)
    passes['recipient_position'] = passes['pass_recipient'].map(player_position)
    passes = passes.dropna(subset=['passer_position', 'recipient_position'])

    def side(pos):
        if pos.startswith('Left'):
            return 'L'
        if pos.startswith('Right'):
            return 'R'
        return 'C'

    passes['passer_side'] = passes['passer_position'].map(side)
    passes['recipient_side'] = passes['recipient_position'].map(side)

    counts = {'L-L': 0, 'R-R': 0, 'Cross': 0, 'Central-involved': 0}
    for _, row in passes.iterrows():
        s1, s2 = row['passer_side'], row['recipient_side']
        if s1 == 'L' and s2 == 'L':
            counts['L-L'] += 1
        elif s1 == 'R' and s2 == 'R':
            counts['R-R'] += 1
        elif s1 == 'C' or s2 == 'C':
            counts['Central-involved'] += 1
        else:
            counts['Cross'] += 1
    return counts


matches = get_competition_matches(competition_id=COMPETITION_ID, season_id=SEASON_ID)
spain_matches = matches[(matches['home_team'] == TEAM) | (matches['away_team'] == TEAM)].copy()
spain_matches = spain_matches.sort_values('match_date')

chain_rows = []
density_rows = []
assist_rows = []
for _, match in spain_matches.iterrows():
    match_id = match['match_id']
    opponent = match['away_team'] if match['home_team'] == TEAM else match['home_team']
    stage = match['competition_stage']

    events = get_match_events(match_id=match_id)

    co = match_chain_outcomes(events)
    for side in ['Left', 'Right', 'Central']:
        side_df = co[co['final_side'] == side]
        chain_rows.append({
            'match': f"{stage} vs {opponent}", 'side': side,
            'n_chains': len(side_df), 'n_chains_with_shot': int(side_df['has_shot'].sum()),
            'xg': round(side_df['xg'].sum(), 3), 'n_goals': int(side_df['n_goals'].sum()),
        })

    density = match_role_pair_density(events)
    density_rows.append({'match': f"{stage} vs {opponent}", **density})

    assist = match_assist_locations(events)
    assist_rows.append({'match': f"{stage} vs {opponent}", **assist})

chain_df = pd.DataFrame(chain_rows)
density_df = pd.DataFrame(density_rows)
assist_df = pd.DataFrame(assist_rows)

agg = chain_df.groupby('side')[['n_chains', 'n_chains_with_shot', 'xg', 'n_goals']].sum()
agg['shot_rate'] = (agg['n_chains_with_shot'] / agg['n_chains']).round(3)
agg['xg_per_chain'] = (agg['xg'] / agg['n_chains']).round(4)
print('=== 체인 side별 슈팅 전환/xG/골 (7경기 합산) ===')
print(agg.to_string())
print()

print('=== 경기별 역할군 쌍 패스 수 (L-L / R-R / Cross / Central-involved) ===')
print(density_df.to_string(index=False))
print()
totals = density_df[['L-L', 'R-R', 'Cross', 'Central-involved']].sum()
print('7경기 합산:')
print(totals.to_string())

density_df['ll_ratio'] = density_df['L-L'] / (density_df['L-L'] + density_df['R-R'])
t_stat, p_value = stats.ttest_1samp(density_df['ll_ratio'], popmean=0.5)
print()
print(f"L-L 비율: mean={density_df['ll_ratio'].mean():.3f}, sd={density_df['ll_ratio'].std():.3f}, "
      f"t(6)={t_stat:.3f}, p={p_value:.4f}")

print()
print('=== 골 어시스트/슈팅 어시스트/크로스 위치 (경기별) ===')
print(assist_df.to_string(index=False))

ga_totals = assist_df[['goal_assist_L', 'goal_assist_C', 'goal_assist_R']].sum()
sa_totals = assist_df[['shot_assist_L', 'shot_assist_C', 'shot_assist_R']].sum()
print()
print('골 어시스트 합계:', ga_totals.to_dict())
print('슈팅 어시스트 합계:', sa_totals.to_dict())

sa_sub = assist_df[(assist_df['shot_assist_L'] + assist_df['shot_assist_R']) > 0].copy()
sa_sub['ratio'] = sa_sub['shot_assist_L'] / (sa_sub['shot_assist_L'] + sa_sub['shot_assist_R'])
t_sa, p_sa = stats.ttest_1samp(sa_sub['ratio'], popmean=0.5)
print(f"슈팅 어시스트 L 비율: mean={sa_sub['ratio'].mean():.3f}, t({len(sa_sub)-1})={t_sa:.3f}, p={p_sa:.4f}")

assist_df['cross_ratio'] = assist_df['cross_L'] / (assist_df['cross_L'] + assist_df['cross_R'])
t_cr, p_cr = stats.ttest_1samp(assist_df['cross_ratio'], popmean=0.5)
print(f"크로스 L 비율: mean={assist_df['cross_ratio'].mean():.3f}, t(6)={t_cr:.3f}, p={p_cr:.4f}")

# --- 시각화 ---
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 5.5))
fig.set_facecolor('#1e1e1e')

for ax in (ax1, ax2, ax3):
    ax.set_facecolor('#1e1e1e')
    for spine in ax.spines.values():
        spine.set_color('#555555')
    ax.tick_params(colors='white')

side_order = ['Left', 'Central', 'Right']
side_colors = {'Left': '#ffe14d', 'Central': '#00f0ff', 'Right': '#ff5cad'}
x = np.arange(len(side_order))
ax1.bar(x, [agg.loc[s, 'xg_per_chain'] for s in side_order],
        color=[side_colors[s] for s in side_order])
ax1.set_xticks(x)
ax1.set_xticklabels(side_order, color='white')
ax1.set_ylabel('xG per chain', color='white')
ax1.set_title('Chain efficiency by final side', color='white', fontweight='bold')
for i, s in enumerate(side_order):
    ax1.text(i, agg.loc[s, 'xg_per_chain'] + 0.001,
              f"{agg.loc[s, 'shot_rate']*100:.0f}% shot rate\n{int(agg.loc[s, 'n_goals'])} goals",
              ha='center', color='white', fontsize=8)

y_positions = np.arange(len(density_df))
ax2.scatter(density_df['ll_ratio'], y_positions, color='#ffe14d', s=70, zorder=3)
ax2.axvline(0.5, color='white', linestyle='--', linewidth=1, alpha=0.7)
ax2.set_yticks(y_positions)
ax2.set_yticklabels(density_df['match'], color='white', fontsize=8)
ax2.invert_yaxis()
ax2.set_xlabel('Left-Left pass ratio among L-L + R-R\n(0.5 = symmetric)', color='white', fontsize=9)
ax2.set_title('Left vs right combination density', color='white', fontweight='bold')

y3 = np.arange(len(assist_df))
ax3.scatter(assist_df['cross_ratio'], y3, color='#00f0ff', s=70, zorder=3)
ax3.axvline(0.5, color='white', linestyle='--', linewidth=1, alpha=0.7)
ax3.set_yticks(y3)
ax3.set_yticklabels(assist_df['match'], color='white', fontsize=8)
ax3.invert_yaxis()
ax3.set_xlabel('Left cross ratio among L + R crosses\n(0.5 = symmetric)', color='white', fontsize=9)
ax3.set_title('Cross origin: left vs right', color='white', fontweight='bold')

fig.tight_layout()
out_dir = os.path.join('data', 'chain_outcomes_prototype')
os.makedirs(out_dir, exist_ok=True)
out_path = os.path.join(out_dir, 'spain_chain_outcomes_prototype.png')
fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
print('saved', out_path)
