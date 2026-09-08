"""plot_freeze_frame() 프로토타입 - StatsBomb 360 프리즈프레임 스냅샷 시각화.

한 이벤트 시점의 전 선수 좌표를 피치에 찍고, "침투 선택지" 정의가 실제로
무엇을 세는지 눈으로 검증하기 위한 함수다. `korea_qatar2022/PLAN.md`의
방법론 6번(정의 검토의 "극단값 장면을 눈으로 본다")에 해당한다.

검증되면 `src/visualizer.py`로 승격한다.

실행:
    .venv\\Scripts\\python.exe scripts/test_freeze_frame.py
산출물은 `data/processed/`에 저장한다(샌드박스 검증 산출물이므로
주제 폴더가 아니라 공용 폴더).
"""
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
from typing import Optional, Tuple

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Polygon
from mplsoccer import Pitch

# 제목·범례에 한글을 쓰므로 한글 폰트를 지정한다. 지정하지 않으면 글자가
# 두부(tofu) 상자로 깨진다. Windows 기본 탑재 폰트를 쓰되, 없으면 무시한다.
for _font in ('Malgun Gothic', 'NanumGothic', 'Gulim'):
    if _font in {f.name for f in matplotlib.font_manager.fontManager.ttflist}:
        plt.rcParams['font.family'] = _font
        break
plt.rcParams['axes.unicode_minus'] = False

CACHE_DIR = Path('data/raw/wc2022_360')
OUTPUT_DIR = Path('data/processed')

# 침투 선택지 정의 파라미터 (korea_qatar2022/PLAN.md "조작적 정의" 절)
LAUNCH_DEPTH = 5.0    # 라인 앞 몇 m까지를 출발 구역으로 볼 것인가 (기본 지표)


def _unpack(loc) -> Tuple[float, float]:
    """StatsBomb의 [x, y] 리스트를 (x, y)로. 형태가 아니면 (nan, nan)."""
    if isinstance(loc, (list, np.ndarray)) and len(loc) >= 2:
        return float(loc[0]), float(loc[1])
    return np.nan, np.nan


def _parse_visible_area(va) -> Optional[np.ndarray]:
    """가시 영역을 (N, 2) 배열로. x, y가 번갈아 나오는 평평한 리스트를 편다."""
    if not isinstance(va, (list, np.ndarray)) or len(va) < 6:
        return None
    try:
        coords = np.asarray(va, dtype=float).reshape(-1, 2)
    except Exception:
        return None
    return coords if len(coords) >= 3 else None


def plot_freeze_frame(frame_df: pd.DataFrame,
                      ball_location=None,
                      launch_depth: float = LAUNCH_DEPTH,
                      title: str = '',
                      subtitle: str = '',
                      pitch_color: str = '#1e1e1e',
                      line_color: str = '#c7d5cc') -> Tuple[plt.Figure, plt.Axes]:
    """360 프리즈프레임 한 장을 피치에 그린다.

    행동 팀(`teammate=True`)이 x=120 방향으로 공격하는 좌표계를 전제한다.
    추정 오프사이드 라인(상대 필드플레이어 x의 최댓값)을 세로선으로 긋고,
    그 앞 `launch_depth` m 구간(출발 구역)을 띠로 칠한다. 침투 선택지로
    카운트되는 선수와 오프사이드 위치의 선수를 서로 다른 색으로 강조해,
    정의가 의도대로 동작하는지 눈으로 확인할 수 있게 한다.

    `visible_area` 밖은 어둡게 덮어 "안 보여서 기록되지 않은 구역"을 숨기지
    않고 드러낸다 - 이 데이터의 최대 한계이므로 그림에서 감추면 안 된다.

    Args:
        frame_df (pd.DataFrame): 한 이벤트의 프레임 행들. `teammate`, `actor`,
            `keeper`, `location`, `visible_area` 컬럼 필요.
        ball_location: 공 위치 `[x, y]`. None이면 `actor` 선수 위치를 쓴다.
        launch_depth (float): 출발 구역 깊이(m). 기본 5.
        title (str): 제목
        subtitle (str): 부제(경기·시각·지표값 등)
        pitch_color (str): 잔디 색상
        line_color (str): 라인 색상

    Returns:
        tuple: (fig, ax). 저장은 호출부에서 `fig.savefig(...)`로 처리한다.
    """
    pitch = Pitch(pitch_type='statsbomb', pitch_color=pitch_color,
                  line_color=line_color, line_zorder=2)
    fig, ax = pitch.draw(figsize=(13, 8.5))
    fig.set_facecolor(pitch_color)

    xy = np.array([_unpack(l) for l in frame_df['location']], dtype=float)
    is_mate = frame_df['teammate'].to_numpy(bool)
    is_keeper = frame_df['keeper'].to_numpy(bool)
    is_actor = frame_df['actor'].to_numpy(bool)
    valid = ~np.isnan(xy[:, 0])

    # 가시 영역 밖을 어둡게 덮는다. 피치 전체를 덮는 사각형 안에 가시 영역을
    # 구멍으로 뚫는 방식인데, matplotlib의 기본 채우기 규칙(nonzero)에서는
    # 바깥 고리와 안쪽 고리의 감김 방향이 반대여야 구멍이 뚫린다.
    coords = _parse_visible_area(frame_df['visible_area'].iloc[0])
    if coords is not None:
        inner = coords[:-1] if np.allclose(coords[0], coords[-1]) else coords

        def _signed_area(p):
            x, y = p[:, 0], p[:, 1]
            return 0.5 * float(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

        outer = np.array([[0, 0], [120, 0], [120, 80], [0, 80]], dtype=float)
        if np.sign(_signed_area(inner)) == np.sign(_signed_area(outer)):
            inner = inner[::-1]

        ring = np.vstack([outer, outer[:1], inner, inner[:1]])
        P = matplotlib.path.Path
        codes = ([P.MOVETO] + [P.LINETO] * 3 + [P.CLOSEPOLY]
                 + [P.MOVETO] + [P.LINETO] * (len(inner) - 1) + [P.CLOSEPOLY])
        ax.add_patch(matplotlib.patches.PathPatch(
            P(ring, codes), facecolor='#000000', alpha=0.6,
            edgecolor='none', zorder=1.5))
        ax.add_patch(Polygon(inner, closed=True, fill=False, edgecolor='#f0c419',
                             linestyle=(0, (4, 3)), linewidth=1.3, alpha=0.85, zorder=3))

    # 추정 오프사이드 라인 = 상대 필드플레이어 x의 최댓값
    opp_field = (~is_mate) & (~is_keeper) & valid
    def_line = float(xy[opp_field, 0].max()) if opp_field.any() else np.nan

    ball_x = np.nan
    if ball_location is not None:
        ball_x, ball_y = _unpack(ball_location)
    elif (is_actor & valid).any():
        ball_x, ball_y = xy[is_actor & valid][0]

    n_launch = n_offside = 0
    if not np.isnan(def_line):
        ax.axvline(def_line, color='#ff6b6b', linestyle='--', linewidth=1.6,
                   alpha=0.9, zorder=3)
        ax.axvspan(max(0, def_line - launch_depth), def_line, color='#2ec4b6',
                   alpha=0.16, zorder=1.6)
        # mplsoccer는 y축을 반전시키므로 음수 y가 피치 위쪽이다.
        ax.text(def_line, -2.5, f'추정 오프사이드 라인 x={def_line:.1f}',
                color='#ff6b6b', fontsize=9.5, ha='center', va='bottom', zorder=4,
                bbox=dict(facecolor=pitch_color, edgecolor='none', pad=1.5, alpha=0.85))

        mate_field = is_mate & (~is_keeper) & (~is_actor) & valid
        ahead = xy[:, 0] > ball_x if not np.isnan(ball_x) else np.ones(len(xy), bool)
        launch_sel = mate_field & (xy[:, 0] <= def_line) & (xy[:, 0] >= def_line - launch_depth) & ahead
        offside_sel = mate_field & (xy[:, 0] > def_line)
        n_launch, n_offside = int(launch_sel.sum()), int(offside_sel.sum())

        # 강조: 침투 선택지(청록 링) / 오프사이드 위치(주황 링)
        if launch_sel.any():
            ax.scatter(xy[launch_sel, 0], xy[launch_sel, 1], s=520, facecolors='none',
                       edgecolors='#2ec4b6', linewidths=2.6, zorder=5)
        if offside_sel.any():
            ax.scatter(xy[offside_sel, 0], xy[offside_sel, 1], s=520, facecolors='none',
                       edgecolors='#ff9f1c', linewidths=2.6, zorder=5)

    # 선수 마커
    def _draw(sel, **kw):
        if sel.any():
            ax.scatter(xy[sel, 0], xy[sel, 1], zorder=6, **kw)

    _draw(is_mate & (~is_keeper) & (~is_actor) & valid, s=210, c='#4ea8de',
          edgecolors='white', linewidths=0.9, label='아군')
    _draw((~is_mate) & (~is_keeper) & valid, s=210, c='#e5e5e5',
          edgecolors='#333333', linewidths=0.9, label='상대')
    _draw(is_mate & is_keeper & valid, s=230, c='#4ea8de', marker='s',
          edgecolors='white', linewidths=0.9, label='아군 GK')
    _draw((~is_mate) & is_keeper & valid, s=230, c='#e5e5e5', marker='s',
          edgecolors='#333333', linewidths=0.9, label='상대 GK')
    _draw(is_actor & valid, s=330, c='#ffd166', marker='*',
          edgecolors='#333333', linewidths=0.8, label='공 소유자')

    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.02), ncol=5, frameon=False,
              labelcolor='#c7d5cc', fontsize=9.5)

    head = title or '360 프리즈프레임'
    counts = f'침투 선택지 {n_launch}명 (라인 앞 {launch_depth:.0f}m) · 오프사이드 위치 {n_offside}명'
    ax.set_title(f'{head}\n{subtitle}\n{counts}' if subtitle else f'{head}\n{counts}',
                 color='#c7d5cc', fontsize=13, pad=18)
    fig.text(0.5, -0.02,
             '노란 점선 = visible_area 경계. 바깥 어두운 구역은 화면에 안 잡혀 선수가 기록되지 않은 곳이다.',
             color='#8d99ae', fontsize=9, ha='center')
    return fig, ax


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sit = pd.read_pickle(CACHE_DIR / 'situations.pkl')
    g = sit[(sit['stage'] == 'Group Stage') & (~sit['setpiece'])].copy()

    # 검증용 장면 선정: 정의가 극단에서 어떻게 동작하는지 본다
    korea = g[g['team'] == 'South Korea']
    targets = [
        ('max_launch', g.loc[g['n_launch5'].idxmax()], '침투 선택지 최댓값 장면'),
        ('zero_launch', g[(g['n_launch5'] == 0) & (g['vis_launch'] > 0.9)].iloc[0],
         '침투 선택지 0명 + 출발 구역이 거의 다 보이는 장면'),
        ('max_offside', g.loc[g['n_beyond'].idxmax()], '오프사이드 위치 선수 최댓값 장면'),
        ('korea_typical',
         korea.iloc[(korea['n_launch5'] - korea['n_launch5'].median()).abs().argsort().iloc[0]],
         '한국의 전형적 장면 (침투 선택지 중앙값에 가장 가까움)'),
        ('low_visibility', g.loc[g['vis_launch'].idxmin()], '출발 구역이 거의 안 보이는 장면'),
    ]

    print('검증 장면 렌더링')
    print('=' * 78)
    for name, row, desc in targets:
        frames = pd.read_pickle(CACHE_DIR / f"frames_{row['match_id']}.pkl")
        ev = pd.read_pickle(CACHE_DIR / f"events_{row['match_id']}.pkl")
        hit = ev[(ev['team'] == row['team']) & (ev['minute'] == row['minute']) &
                 (ev['second'] == row['second']) & (ev['type'] == 'Pass')]
        if hit.empty:
            print(f'  [SKIP] {name}: 원본 이벤트를 못 찾음')
            continue
        event = hit.iloc[0]
        frame = frames[frames['id'] == event['id']]
        if frame.empty:
            print(f'  [SKIP] {name}: 프레임 없음')
            continue

        fig, _ = plot_freeze_frame(
            frame, ball_location=event['location'], launch_depth=LAUNCH_DEPTH,
            title=desc,
            subtitle=(f"{row['team']} vs {row['opponent']} · {int(row['minute'])}'"
                      f"{int(row['second']):02d} · 출발 구역 가시율 {row['vis_launch']:.2f}"))
        out = OUTPUT_DIR / f'test_freeze_frame_{name}.png'
        fig.savefig(out, dpi=120, facecolor=fig.get_facecolor(), bbox_inches='tight')
        plt.close(fig)
        print(f"  {name:15s} {row['team']:13s} n_launch5={row['n_launch5']} "
              f"n_beyond={row['n_beyond']} vis={row['vis_launch']:.2f} -> {out.name}")

    print('\n표에 기록된 값과 그림에 표시된 개수가 일치하는지 눈으로 대조할 것.')


if __name__ == '__main__':
    main()
