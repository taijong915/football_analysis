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
