"""Football Data Visualization Utilities using mplsoccer & matplotlib
"""
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from mplsoccer import Pitch, VerticalPitch, PyPizza
from typing import Optional, Tuple, List


def create_standard_pitch(pitch_type: str = 'statsbomb',
                          pitch_color: str = '#1e1e1e',
                          line_color: str = '#c7d5cc',
                          vertical: bool = False) -> Tuple[Pitch, plt.Figure, plt.Axes]:
    """기본 축구 경기장(Pitch) 객체 및 Figure/Axes를 생성합니다.

    Args:
        pitch_type (str): 피치 좌표계 ('statsbomb', 'opta', 'tracab', 'wyscout' 등)
        pitch_color (str): 잔디/배경 색상
        line_color (str): 라인 색상
        vertical (bool): 세로 방향 여부

    Returns:
        tuple: (Pitch 객체, fig, ax)
    """
    if vertical:
        pitch = VerticalPitch(pitch_type=pitch_type, pitch_color=pitch_color, line_color=line_color,
                              line_zorder=2, half=False)
    else:
        pitch = Pitch(pitch_type=pitch_type, pitch_color=pitch_color, line_color=line_color,
                      line_zorder=2, half=False)
    
    fig, ax = pitch.draw(figsize=(12, 8))
    fig.set_facecolor(pitch_color)
    return pitch, fig, ax


def plot_shot_map(events_df: pd.DataFrame,
                  team_name: Optional[str] = None,
                  player_name: Optional[str] = None,
                  title: str = "Shot Map (xG Analysis)") -> Tuple[plt.Figure, plt.Axes]:
    """슈팅 맵과 xG(기대 득점)를 시각화합니다."""
    shots = events_df[events_df['type'] == 'Shot'].copy()
    if team_name:
        shots = shots[shots['team'] == team_name]
    if player_name:
        shots = shots[shots['player'] == player_name]

    pitch = Pitch(pitch_type='statsbomb', pitch_color='#141414', line_color='#7c7c7c', half=True)
    fig, ax = pitch.draw(figsize=(10, 8))
    fig.set_facecolor('#141414')

    # x, y 좌표 분리
    shots['x'] = shots['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
    shots['y'] = shots['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)
    shots['shot_statsbomb_xg'] = shots.get('shot_statsbomb_xg', 0.05).fillna(0.05)

    goals = shots[shots['shot_outcome'] == 'Goal']
    non_goals = shots[shots['shot_outcome'] != 'Goal']

    # 골이 아닌 슛 (회색/빨간색)
    pitch.scatter(non_goals['x'], non_goals['y'],
                  s=non_goals['shot_statsbomb_xg'] * 700 + 40,
                  c='#ff4b4b', alpha=0.6, edgecolors='white',
                  label='No Goal / Saved', ax=ax)

    # 골 (골드/초록색)
    pitch.scatter(goals['x'], goals['y'],
                  s=goals['shot_statsbomb_xg'] * 700 + 40,
                  c='#00ff85', alpha=0.9, edgecolors='white', marker='*',
                  label='Goal', ax=ax)

    ax.legend(loc='lower center', facecolor='#141414', edgecolor='white', labelcolor='white',
              fontsize=11, ncol=2)
    ax.set_title(title, fontsize=16, color='white', pad=20, fontweight='bold')
    return fig, ax


def plot_pass_map(events_df: pd.DataFrame,
                  player_name: str,
                  title: Optional[str] = None) -> Tuple[plt.Figure, plt.Axes]:
    """특정 선수의 패스 성공/실패 맵을 시각화합니다."""
    passes = events_df[(events_df['type'] == 'Pass') & (events_df['player'] == player_name)].copy()
    
    passes['x'] = passes['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
    passes['y'] = passes['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)
    passes['end_x'] = passes['pass_end_location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
    passes['end_y'] = passes['pass_end_location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)

    complete_passes = passes[passes['pass_outcome'].isna()]
    incomplete_passes = passes[passes['pass_outcome'].notna()]

    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1a1a2e', line_color='#e94560')
    fig, ax = pitch.draw(figsize=(12, 8))
    fig.set_facecolor('#1a1a2e')

    # 성공 패스
    pitch.arrows(complete_passes['x'], complete_passes['y'],
                 complete_passes['end_x'], complete_passes['end_y'],
                 color='#00f0ff', alpha=0.7, width=2, headwidth=4, headlength=4,
                 label=f'Completed ({len(complete_passes)})', ax=ax)

    # 실패 패스
    pitch.arrows(incomplete_passes['x'], incomplete_passes['y'],
                 incomplete_passes['end_x'], incomplete_passes['end_y'],
                 color='#ff2e63', alpha=0.5, width=1.5, headwidth=3, headlength=3,
                 label=f'Incomplete ({len(incomplete_passes)})', ax=ax)

    ax.legend(loc='lower center', facecolor='#1a1a2e', edgecolor='white', labelcolor='white',
              fontsize=11, ncol=2)
    display_title = title if title else f"Pass Map: {player_name}"
    ax.set_title(display_title, fontsize=16, color='white', pad=20, fontweight='bold')
    return fig, ax


def plot_pass_network(events_df: pd.DataFrame,
                      team_name: str,
                      lineup_df: Optional[pd.DataFrame] = None,
                      minute_range: Optional[Tuple[float, Optional[float]]] = None,
                      min_pass_count: int = 2,
                      title: Optional[str] = None) -> Tuple[plt.Figure, plt.Axes]:
    """팀의 패스 네트워크(선수 평균 위치 + 선수 간 연결)를 시각화합니다.

    Args:
        events_df (pd.DataFrame): 경기 이벤트 데이터 (data_loader.get_match_events)
        team_name (str): 분석할 팀 이름
        lineup_df (pd.DataFrame, optional): data_loader.get_match_lineups(...)[team_name].
            제공하면 player_nickname으로 라벨을 표시합니다 (예: 성이 두 개인 스페인 선수 표기 오류 방지).
        minute_range (tuple, optional): (시작 분, 끝 분)으로 이 구간의 패스만 사용
            (시작 분 이상 ~ 끝 분 미만). 끝 분에 None을 주면 경기 끝까지 열어둡니다.
            지정하지 않으면 (0, 해당 팀의 첫 교체 시각)을 자동으로 사용해 선발 라인업이
            고정된 구간만 분석합니다 (교체가 없으면 경기 전체).
        min_pass_count (int): 이 횟수 미만으로 연결된 선수 쌍은 표시하지 않습니다 (노이즈 제거).
        title (str, optional): 차트 제목

    Returns:
        tuple: (fig, ax)
    """
    if minute_range is None:
        subs = events_df[(events_df['type'] == 'Substitution') & (events_df['team'] == team_name)]
        first_sub_minute = subs['minute'].min() if not subs.empty else np.inf
        minute_range = (0, first_sub_minute)

    min_minute, max_minute = minute_range
    max_minute = np.inf if max_minute is None else max_minute

    passes = events_df[
        (events_df['type'] == 'Pass')
        & (events_df['team'] == team_name)
        & (events_df['minute'] >= min_minute)
        & (events_df['minute'] < max_minute)
    ].copy()
    passes = passes[passes['pass_outcome'].isna() & passes['pass_recipient'].notna()]

    passes['x'] = passes['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
    passes['y'] = passes['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)

    player_pos = passes.groupby('player').agg(x=('x', 'mean'), y=('y', 'mean'), pass_count=('x', 'count'))

    pair_counts = passes.groupby(['player', 'pass_recipient']).size().reset_index(name='count')
    pair_counts['pair'] = pair_counts.apply(
        lambda row: tuple(sorted([row['player'], row['pass_recipient']])), axis=1
    )
    pair_agg = pair_counts.groupby('pair')['count'].sum().reset_index()
    pair_agg = pair_agg[pair_agg['count'] >= min_pass_count]

    if lineup_df is not None:
        name_map = dict(zip(lineup_df['player_name'], lineup_df['player_nickname'].fillna(lineup_df['player_name'])))
    else:
        name_map = {}

    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e1e1e', line_color='#c7d5cc')
    fig, ax = pitch.draw(figsize=(12, 8))
    fig.set_facecolor('#1e1e1e')

    for _, row in pair_agg.iterrows():
        p1, p2 = row['pair']
        if p1 not in player_pos.index or p2 not in player_pos.index:
            continue
        x1, y1 = player_pos.loc[p1, ['x', 'y']]
        x2, y2 = player_pos.loc[p2, ['x', 'y']]
        pitch.lines(x1, y1, x2, y2, lw=row['count'] * 0.6, color='#00f0ff', alpha=0.6, zorder=1, ax=ax)

    pitch.scatter(
        player_pos['x'], player_pos['y'],
        s=player_pos['pass_count'] * 25,
        color='#e94560', edgecolors='white', linewidth=1.5, zorder=2, ax=ax,
    )

    for name, row in player_pos.iterrows():
        display_name = name_map.get(name, name)
        pitch.annotate(display_name, xy=(row['x'], row['y']), c='white', va='center', ha='center',
                        fontsize=9, fontweight='bold', zorder=3, ax=ax)

    display_title = title if title else f"{team_name} Pass Network"
    ax.set_title(display_title, fontsize=14, color='white', pad=20, fontweight='bold')
    return fig, ax


def _abbreviate_position(position: str) -> str:
    """StatsBomb 포지션명을 약어로 변환합니다 (예: 'Right Center Back' -> 'RCB')."""
    if position == 'Goalkeeper':
        return 'GK'
    return ''.join(word[0] for word in position.split())


def plot_pass_network_by_position(events_df: pd.DataFrame,
                                  team_name: str,
                                  lineup_df: Optional[pd.DataFrame] = None,
                                  min_pass_count: int = 2,
                                  title: Optional[str] = None) -> Tuple[plt.Figure, Tuple[plt.Axes, plt.Axes]]:
    """포지션(역할) 슬롯을 노드로 삼아 경기 전체(교체 포함) 패스 네트워크를 시각화합니다.

    `plot_pass_network()`와 달리 노드가 "선수"가 아니라 "포지션 슬롯"(예: Right Defensive
    Midfield)이라, 교체로 선수가 바뀌어도 같은 슬롯이면 패스가 계속 합산됩니다 — 경기 시간
    전체를 하나의 네트워크로 볼 수 있는 대신, 어떤 선수가 그 슬롯을 맡았는지는 별도 패널에서
    확인해야 합니다. 오른쪽 패널에 포지션별 선수 로스터와 교체 시각(첫 등장 시각의 근사치)을
    함께 표시합니다.

    각 선수의 슬롯은 해당 선수의 전체 이벤트에서 가장 자주 등장한 `position` 값(최빈값)으로
    정합니다. `position` 컬럼의 결측률·`Tactical Shift`(포메이션 변경) 빈도는 대회/경기마다
    달라질 수 있으므로 새 대상 데이터로 확인 후 사용하세요 (`.claude/rules/analysis-workflow.md`
    "데이터 검토" 단계, `.claude/rules/statsbomb-data-notes.md` 참고). `Tactical Shift`가 일어나면
    한 선수가 여러 포지션에 걸치거나, 로스터 상 교체 쌍이 실제 `Substitution` 이벤트의 OUT/IN
    선수와 정확히 일치하지 않을 수 있습니다(2024 유로 결승 88~92분 구간에서 실제로 관찰됨).

    Args:
        events_df (pd.DataFrame): 경기 이벤트 데이터 (data_loader.get_match_events)
        team_name (str): 분석할 팀 이름
        lineup_df (pd.DataFrame, optional): data_loader.get_match_lineups(...)[team_name].
            제공하면 player_nickname으로 로스터 패널의 이름을 표시합니다.
        min_pass_count (int): 이 횟수 미만으로 연결된 포지션 쌍은 표시하지 않습니다.
        title (str, optional): 차트 제목

    Returns:
        tuple: (fig, (ax_pitch, ax_roster))
    """
    team_events = events_df[events_df['team'] == team_name]

    player_position = (
        team_events.dropna(subset=['position'])
        .groupby('player')['position']
        .agg(lambda s: s.value_counts().idxmax())
    )

    passes = events_df[
        (events_df['type'] == 'Pass') & (events_df['team'] == team_name)
    ].copy()
    passes = passes[passes['pass_outcome'].isna() & passes['pass_recipient'].notna()]

    passes['x'] = passes['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
    passes['y'] = passes['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)

    passes['passer_position'] = passes['player'].map(player_position)
    passes['recipient_position'] = passes['pass_recipient'].map(player_position)
    passes = passes.dropna(subset=['passer_position', 'recipient_position'])

    slot_pos = passes.groupby('passer_position').agg(x=('x', 'mean'), y=('y', 'mean'), pass_count=('x', 'count'))

    pair_counts = passes.groupby(['passer_position', 'recipient_position']).size().reset_index(name='count')
    pair_counts['pair'] = pair_counts.apply(
        lambda row: tuple(sorted([row['passer_position'], row['recipient_position']])), axis=1
    )
    pair_agg = pair_counts.groupby('pair')['count'].sum().reset_index()
    pair_agg = pair_agg[pair_agg['count'] >= min_pass_count]

    if lineup_df is not None:
        name_map = dict(zip(lineup_df['player_name'], lineup_df['player_nickname'].fillna(lineup_df['player_name'])))
    else:
        name_map = {}

    # 포지션별 등장 선수와 첫 등장 시각(교체 시점의 근사치) - 시간순
    slot_history = {}
    for position, group in team_events.dropna(subset=['position']).groupby('position'):
        first_seen = group.groupby('player')['minute'].min().sort_values()
        slot_history[position] = list(first_seen.items())

    fig, (ax_pitch, ax_roster) = plt.subplots(1, 2, figsize=(18, 8), gridspec_kw={'width_ratios': [2.3, 1]})
    fig.set_facecolor('#1e1e1e')

    pitch = Pitch(pitch_type='statsbomb', pitch_color='#1e1e1e', line_color='#c7d5cc')
    pitch.draw(ax=ax_pitch)

    for _, row in pair_agg.iterrows():
        p1, p2 = row['pair']
        if p1 not in slot_pos.index or p2 not in slot_pos.index:
            continue
        x1, y1 = slot_pos.loc[p1, ['x', 'y']]
        x2, y2 = slot_pos.loc[p2, ['x', 'y']]
        pitch.lines(x1, y1, x2, y2, lw=row['count'] * 0.5, color='#00f0ff', alpha=0.6, zorder=1, ax=ax_pitch)

    pitch.scatter(
        slot_pos['x'], slot_pos['y'],
        s=slot_pos['pass_count'] * 15,
        color='#e94560', edgecolors='white', linewidth=1.5, zorder=2, ax=ax_pitch,
    )

    # 노드에는 포지션 약어만 표시(선수 체인은 오른쪽 로스터 패널에서 확인) - 중앙 포지션끼리 겹치는 것을 방지
    for position, row in slot_pos.iterrows():
        pitch.annotate(_abbreviate_position(position), xy=(row['x'], row['y']), c='white', va='center', ha='center',
                        fontsize=10, fontweight='bold', zorder=3, ax=ax_pitch)

    display_title = title if title else f"{team_name} Pass Network by Position"
    ax_pitch.set_title(display_title, fontsize=14, color='white', pad=20, fontweight='bold')

    # 오른쪽 패널: 포지션별 로스터 + 교체 시각 (수비 -> 공격 순, x좌표 기준)
    ax_roster.set_facecolor('#1e1e1e')
    ax_roster.axis('off')
    ax_roster.set_title('Lineup by Position (substitution minute in parentheses)',
                         fontsize=11, color='white', fontweight='bold', loc='left')

    ordered_positions = slot_pos.sort_values('x').index.tolist()
    for i, position in enumerate(ordered_positions):
        history = slot_history.get(position, [])
        parts = []
        for j, (player, minute) in enumerate(history):
            name = name_map.get(player, player)
            parts.append(name if j == 0 else f"{name} ({int(minute)}')")
        chain = ' → '.join(parts)
        abbr = _abbreviate_position(position)
        ax_roster.text(0, 0.94 - i * 0.09, f"{abbr:<4}{chain}", color='white', fontsize=10,
                        family='monospace', transform=ax_roster.transAxes)

    return fig, (ax_pitch, ax_roster)


def plot_pizza_chart(params: List[str], values: List[float],
                     player_name: str, sub_title: str = "Percentile Rank vs Position") -> Tuple[plt.Figure, plt.Axes]:
    """선수의 스탯 백분위수를 피자(Pizza / Radar) 차트로 시각화합니다."""
    # 슬라이스 색상 설정
    slice_colors = ["#1A78CF"] * 3 + ["#FF9300"] * 3 + ["#D70232"] * (len(params) - 6 if len(params) > 6 else 2)
    text_colors = ["#F2F2F2"] * len(params)

    baker = PyPizza(
        params=params,
        background_color="#181818",
        straight_line_color="#EBEBE9",
        straight_line_lw=1,
        last_circle_lw=1,
        other_circle_lw=1,
        other_circle_ls="-."
    )

    fig, ax = baker.make_pizza(
        values,
        figsize=(8, 8),
        param_location=110,
        slice_colors=slice_colors[:len(params)],
        value_colors=text_colors,
        value_bck_colors=slice_colors[:len(params)],
        kwargs_slices=dict(edgecolor="#F2F2F2", zorder=2, linewidth=1),
        kwargs_params=dict(color="#F2F2F2", fontsize=11, va="center"),
        kwargs_values=dict(color="#F2F2F2", fontsize=10, zorder=3,
                           bbox=dict(edgecolor="#F2F2F2", facecolor="1", boxstyle="round,pad=0.2", lw=1))
    )

    fig.text(0.515, 0.97, player_name, size=18, ha="center", color="#F2F2F2", weight="bold")
    fig.text(0.515, 0.93, sub_title, size=11, ha="center", color="#B0B0B0")
    return fig, ax
