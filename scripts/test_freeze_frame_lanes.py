"""`plot_freeze_frame(lane_split=True)` 확장 검증 - 레인 경계와 채널/중앙 구분이
의도대로 동작하는지 극단값 장면을 그려 눈으로 확인하는 샌드박스 스크립트.

분석 워크플로우 2-1의 다섯 번째 절차("극단값 장면을 눈으로 본다")에 해당한다.
`korea_qatar2022/PLAN.md`의 2차 확장 재실행 3번 단계이며, 여기서 그림이 정의와
어긋나면 코드가 아니라 조작적 정의로 되돌아간다.

세 가지 장면을 고른다:
1. 채널 최댓값 - 채널 카운트가 가장 큰 상황. 세는 규칙이 과다 계상하지 않는지.
2. 채널 0 + 중앙 최다 - "컷백 받으러 중앙에 서 있는" 장면. 2차 확장이 1차 정의와
   갈라지는 지점이라, 여기서 청록 실선 링이 0개여야 정의가 의도대로 동작한 것이다.
3. 포르투갈 전형 - 채널 카운트가 팀 평균에 가장 가까운 상황(선정 기준은
   `DECISIONS.md` 2026-09-10 "중앙값 대신 평균" 항목과 같다). 8강까지 갔는데
   채널 지표는 하위권인 팀이 실제로 어떤 그림인지 확인한다.

산출물은 샌드박스 출력이므로 `data/processed/`에 둔다(주제 폴더 산출물이 아니다).

실행 (프로젝트 루트에서):
    .venv\\Scripts\\python.exe scripts/test_freeze_frame_lanes.py
"""
import os
import sys
from pathlib import Path

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')
import numpy as np
import pandas as pd

from src.visualizer import plot_freeze_frame

CACHE = Path('data/raw/wc2022_360')
OUT = Path('data/processed')
OUT.mkdir(parents=True, exist_ok=True)

LAUNCH_DEPTH = 5.0
TEAM_KR = {'South Korea': '대한민국', 'Argentina': '아르헨티나', 'Portugal': '포르투갈',
           'Brazil': '브라질', 'Spain': '스페인', 'Japan': '일본', 'Senegal': '세네갈',
           'Germany': '독일', 'Uruguay': '우루과이', 'Ghana': '가나', 'Croatia': '크로아티아',
           'Morocco': '모로코', 'Switzerland': '스위스', 'Serbia': '세르비아',
           'Cameroon': '카메룬', 'Ecuador': '에콰도르', 'Netherlands': '네덜란드',
           'Qatar': '카타르', 'Iran': '이란', 'England': '잉글랜드', 'Wales': '웨일스',
           'United States': '미국', 'Mexico': '멕시코', 'Poland': '폴란드',
           'Saudi Arabia': '사우디아라비아', 'Australia': '호주', 'Denmark': '덴마크',
           'Tunisia': '튀니지', 'France': '프랑스', 'Costa Rica': '코스타리카',
           'Canada': '캐나다', 'Belgium': '벨기에'}


def kr(team: str) -> str:
    return TEAM_KR.get(team, team)


def link_event(row: pd.Series):
    """situations 행 -> 원본 Pass 이벤트 + 그 이벤트의 360 프레임 행 그룹.

    `korea_qatar2022/05_snapshot_contrast.py`의 같은 이름 함수와 동일한 방식이다
    (situations에 event_id가 없어 match_id + team + 시각 + ball_x로 특정한다).
    """
    events = pd.read_pickle(CACHE / f"events_{row['match_id']}.pkl")
    frames = pd.read_pickle(CACHE / f"frames_{row['match_id']}.pkl")
    cand = events[(events['team'] == row['team']) & (events['minute'] == row['minute']) &
                  (events['second'] == row['second']) & (events['type'] == 'Pass')].copy()
    cand['_x'] = [round(float(loc[0]), 2) if isinstance(loc, (list, np.ndarray)) else np.nan
                  for loc in cand['location']]
    cand = cand[np.isclose(cand['_x'], row['ball_x'], atol=0.01)]
    if len(cand) != 1:
        raise RuntimeError(f"이벤트 특정 실패 ({row['team']} {int(row['minute'])}:"
                           f"{int(row['second']):02d}): {len(cand)}건")
    event = cand.iloc[0]
    frame = frames[frames['id'] == event['id']]
    if frame.empty:
        raise RuntimeError(f"프레임 없음: {event['id']}")
    return event, frame


def render(row: pd.Series, name: str, title: str, note: str) -> dict:
    """한 장면을 그리고, 그림이 세는 수와 situations 저장값이 맞는지 검산한다."""
    event, frame = link_event(row)
    ball = event['location']

    subtitle = (f"{kr(row['team'])} vs {kr(row['opponent'])} · "
                f"{int(row['minute'])}:{int(row['second']):02d} · "
                f"공 x={row['ball_x']:.1f} · 보이는 상대 {int(row['n_opp_visible'])}명 · "
                f"사이드 가시율 {row['vis_launch_wide']:.2f} / 중앙 {row['vis_launch_center']:.2f}")

    fig, ax = plot_freeze_frame(
        frame, ball_location=ball, launch_depth=LAUNCH_DEPTH, lane_split=True,
        title=title, subtitle=subtitle,
        team_name=kr(row['team']), opponent_name=kr(row['opponent']))
    path = OUT / f'test_lane_{name}.png'
    fig.savefig(path, dpi=130, bbox_inches='tight', facecolor=fig.get_facecolor())
    matplotlib.pyplot.close(fig)

    # 그림의 카운트는 제목 문자열에서 되읽지 않고, 같은 규칙을 여기서 다시 계산해
    # situations 저장값과 대조한다(그림과 pkl이 어긋나면 둘 중 하나가 틀린 것이다).
    xy = np.array([loc if isinstance(loc, (list, np.ndarray)) and len(loc) == 2
                   else (np.nan, np.nan) for loc in frame['location']], dtype=float)
    is_mate = frame['teammate'].to_numpy(bool)
    is_kp = frame['keeper'].to_numpy(bool)
    is_ac = frame['actor'].to_numpy(bool)
    ok = ~np.isnan(xy[:, 0])
    def_line = xy[(~is_mate) & (~is_kp) & ok, 0].max()
    mate = is_mate & (~is_kp) & (~is_ac) & ok
    sel = mate & (xy[:, 0] <= def_line) & (xy[:, 0] >= def_line - LAUNCH_DEPTH) & (xy[:, 0] > ball[0])
    center = (xy[:, 1] >= 30) & (xy[:, 1] <= 50)
    recomputed = {'channel': int((sel & ~center).sum()), 'center': int((sel & center).sum())}
    stored = {'channel': int(row['n_channel5']), 'center': int(row['n_center5'])}
    match = recomputed == stored

    print(f"  [{name}] {kr(row['team'])} {int(row['minute'])}:{int(row['second']):02d}  "
          f"채널 {stored['channel']} / 중앙 {stored['center']}  "
          f"라인 x={row['def_line']:.1f}  {'검산 OK' if match else '검산 불일치!'}")
    if not match:
        print(f"    저장값 {stored} vs 그림 재계산 {recomputed}")
    print(f"    {note}")
    print(f"    -> {path}")
    return {'name': name, 'match': match, 'stored': stored, 'recomputed': recomputed}


def main() -> None:
    s = pd.read_pickle(CACHE / 'situations_lanes.pkl')
    g = s[(s['stage'] == 'Group Stage') & (~s['setpiece']) & (s['in_scope'])].copy()
    print(f"채택 범위 조별리그 오픈플레이: {len(g)}건\n")

    results = []

    # 1. 채널 최댓값 - 동점이면 보이는 상대가 많은 쪽(관측이 나은 쪽)을 고른다.
    top = g.sort_values(['n_channel5', 'n_opp_visible'], ascending=False).iloc[0]
    results.append(render(
        top, 'channel_max',
        f"채널 침투 선택지 최댓값 - {kr(top['team'])}",
        "규칙이 과다 계상하지 않는지: 청록 실선 링이 전부 사이드/하프스페이스에 있고 "
        "라인 앞 5m 안, 공보다 앞이어야 한다."))

    # 2. 채널 0 + 중앙 최다 - 1차 정의라면 크게 셌을 장면이 0으로 떨어져야 한다.
    cand = g[g['n_channel5'] == 0].sort_values(['n_center5', 'n_opp_visible'], ascending=False)
    results.append(render(
        cand.iloc[0], 'center_only',
        f"채널 0 · 중앙 최다 - {kr(cand.iloc[0]['team'])}",
        "2차 확장이 1차 정의와 갈라지는 지점: 컷백을 받으러 중앙에 선 선수는 "
        "점선 링(대조군)이고 실선 링은 0개여야 한다."))

    # 3. 포르투갈 전형 - 팀 평균에 가장 가까운 상황.
    por = g[g['team'] == 'Portugal'].copy()
    target = por['n_channel5'].mean()
    por['_d'] = (por['n_channel5'] - target).abs()
    por = por.sort_values(['_d', 'n_opp_visible'], ascending=[True, False])
    results.append(render(
        por.iloc[0], 'portugal_typical',
        f"포르투갈 전형 (팀 평균 {target:.2f}에 가장 가까운 장면)",
        "8강까지 갔는데 채널 지표는 하위권인 팀의 평균적 그림."))

    print()
    print("=" * 70)
    bad = [r for r in results if not r['match']]
    if bad:
        print(f"검산 불일치 {len(bad)}건 - 그림과 situations_lanes.pkl이 어긋난다.")
        sys.exit(1)
    print("검산 통과: 세 장면 모두 그림의 카운트 규칙이 situations_lanes.pkl과 일치한다.")
    print("=" * 70)


if __name__ == '__main__':
    main()
