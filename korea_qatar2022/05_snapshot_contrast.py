"""프리즈프레임 대비 스냅샷 (PLAN "예상 산출물" 절 마지막 항목).

침투 선택지 지표가 실제로 무엇을 세는지 눈으로 보여주는 스냅샷 두 쌍이다.

- 패널 1: 아르헨티나 전형 장면  vs  한국 전형 장면 (조별리그 오픈플레이)
- 패널 2: 한국 조별리그 전형 장면  vs  한국 16강 브라질전 전형 장면

선정 규칙(PLAN 원안 "중앙값에 가장 가까운 상황"의 수정판): 대상 팀/경기의
오픈플레이 전진 상황 중 채널 침투 선택지 개수(`n_channel5`)가 **그 표본의
평균에 가장 가까운** 상황을 뽑는다. 원안이 중앙값을 쓰려 했으나 주요 팀들의
중앙값이 모두 겹쳐(분포가 0/1/2에 쏠림) 팀 차이를 담지 못했다. 차이는 평균에
있으므로 평균을 기준으로 바꿨다. 동점 처리는 `n_opp_visible` ->
`vis_launch_wide` -> `def_line` -> `ball_x` 순서로 그 표본의 중앙값에 가장
가까운 상황을 고른다(관측 조건이 이 주제의 핵심 변수이므로 `n_opp_visible`을
가장 먼저 맞춘다). 최종 동점은 이른 시각 우선이되, **킥오프 직후(전·후반 시작
3분)는 후보에서 뺀다** - 킥오프 대형은 그 팀이 경기를 어떻게 풀었는지를
대표하지 않는다(2026-09-15 레인 확장 검증에서 포르투갈 전형이 0:11로 뽑힌 뒤
추가한 규칙).

평균 기준이어도 강조되는 링 개수 자체는 장면마다 비슷할 수 있다(사용자와 합의된
한계). 팀 차이는 "그런 장면이 얼마나 자주 나오는가"이므로 각 장면 캡션·
`snapshot_notes.md`에 분포를 함께 적는다. 그리고 세 장면의 **맥락**(보이는 상대
수, 추정 라인 깊이)은 서로 크게 달라, 그 대비가 관측 조건 편향을 눈으로 보여준다.

레인 확장(2026-09-14 정의) 이후 그림은 `lane_split=True`로 그린다 - 레인 경계가
깔리고 채널(실선 청록 링)과 중앙(점선 청록 링)이 나뉘어 표시된다.

산출물(`korea_qatar2022/processed/`):
- fig_snapshot_argentina.png      - 패널 1 왼쪽 (아르헨티나 조별리그 전형)
- fig_snapshot_korea_group.png    - 패널 1 오른쪽 / 패널 2 왼쪽 (한국 조별리그 전형)
- fig_snapshot_korea_brazil.png   - 패널 2 오른쪽 (한국 브라질전 전형)
- snapshot_notes.md               - 선정 방식, 장면별 수치, 분포, 한계

실행 (프로젝트 루트에서):
    .venv\\Scripts\\python.exe korea_qatar2022/05_snapshot_contrast.py
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

from src.visualizer import plot_freeze_frame, _ensure_korean_font

CACHE = Path('data/raw/wc2022_360')
OUT = Path('korea_qatar2022/processed')
OUT.mkdir(parents=True, exist_ok=True)

BRAZIL_MATCH = 3869253
LAUNCH_DEPTH = 5.0  # 기본 지표 (PLAN "조작적 정의")
OPP_KR = {'Portugal': '포르투갈', 'Uruguay': '우루과이', 'Ghana': '가나', 'Brazil': '브라질',
          'Poland': '폴란드', 'Saudi Arabia': '사우디아라비아', 'Mexico': '멕시코'}
TEAM_KR = {'South Korea': '대한민국', 'Argentina': '아르헨티나'}


def select_typical(df: pd.DataFrame) -> tuple[pd.Series, float, dict]:
    """표본에서 '전형' 상황 한 건을 고른다. 반환: (행, 평균 n_channel5, 분포dict).

    평균은 표본 전체로 재되, 뽑는 장면은 킥오프 직후를 뺀다. 2026-09-15 레인
    확장 검증에서 포르투갈 전형이 0:11로 뽑혔는데, 킥오프 대형은 그 팀이 경기를
    어떻게 풀었는지를 대표하지 않는다. 평균 계산에서까지 빼면 지표 정의와
    어긋나므로 후보에서만 제외한다.
    """
    target = float(df['n_channel5'].mean())
    kickoff = (df['minute'] < 3) | ((df['minute'] >= 45) & (df['minute'] < 48))
    cand = df[~kickoff]
    if cand.empty:
        cand = df
    med_opp = df['n_opp_visible'].median()
    med_vis = df['vis_launch_wide'].median()
    med_def = df['def_line'].median()
    med_ball = df['ball_x'].median()
    ranked = cand.assign(
        _a=(cand['n_channel5'] - target).abs(),
        _o=(cand['n_opp_visible'] - med_opp).abs(),
        _b=(cand['vis_launch_wide'] - med_vis).abs(),
        _c=(cand['def_line'] - med_def).abs(),
        _d=(cand['ball_x'] - med_ball).abs(),
    ).sort_values(['_a', '_o', '_b', '_c', '_d', 'minute', 'second'])
    dist = df['n_channel5'].value_counts(normalize=True).sort_index().round(3).to_dict()
    return ranked.iloc[0], target, dist


def link_event(row: pd.Series) -> tuple[pd.Series, pd.DataFrame]:
    """situations 행 -> 원본 Pass 이벤트 + 그 이벤트의 360 프레임 행 그룹."""
    events = pd.read_pickle(CACHE / f"events_{row['match_id']}.pkl")
    frames = pd.read_pickle(CACHE / f"frames_{row['match_id']}.pkl")
    cand = events[(events['team'] == row['team']) & (events['minute'] == row['minute']) &
                  (events['second'] == row['second']) & (events['type'] == 'Pass')].copy()
    # situations의 ball_x = round(event.location[0], 2). 같은 초에 패스가 여러 개면
    # 이 값으로 유일하게 특정한다.
    cand['_x'] = [round(float(loc[0]), 2) if isinstance(loc, (list, np.ndarray)) else np.nan
                  for loc in cand['location']]
    cand = cand[np.isclose(cand['_x'], row['ball_x'], atol=0.01)]
    if len(cand) != 1:
        raise RuntimeError(f"이벤트 특정 실패 ({row['team']} {int(row['minute'])}:{int(row['second']):02d}): "
                           f"{len(cand)}건")
    event = cand.iloc[0]
    frame = frames[frames['id'] == event['id']]
    if frame.empty:
        raise RuntimeError(f"프레임 없음: {event['id']}")
    return event, frame


def render(row: pd.Series, target: float, dist: dict, name: str) -> dict:
    event, frame = link_event(row)
    team_kr = TEAM_KR.get(row['team'], row['team'])
    opp_kr = OPP_KR.get(row['opponent'], row['opponent'])

    # 프리즈프레임이 프레임에서 직접 다시 계산한 def_line이 저장값과 맞는지 검산
    xy = np.array([(float(l[0]), float(l[1])) if isinstance(l, (list, np.ndarray)) else (np.nan, np.nan)
                   for l in frame['location']])
    is_mate = frame['teammate'].to_numpy(bool)
    is_kp = frame['keeper'].to_numpy(bool)
    opp_field = (~is_mate) & (~is_kp) & ~np.isnan(xy[:, 0])
    recomputed = float(xy[opp_field, 0].max())
    assert abs(recomputed - row['def_line']) < 0.05, (name, recomputed, row['def_line'])

    title = f"{team_kr} vs {opp_kr} - {int(row['minute'])}:{int(row['second']):02d}"
    fig, _ = plot_freeze_frame(frame, ball_location=event['location'],
                               launch_depth=LAUNCH_DEPTH, lane_split=True, title=title,
                               team_name=team_kr, opponent_name=opp_kr)
    path = OUT / f'fig_snapshot_{name}.png'
    fig.savefig(path, dpi=140, facecolor=fig.get_facecolor(), bbox_inches='tight')
    matplotlib.pyplot.close(fig)

    dist_str = ', '.join(f'{k}명 {v:.0%}' for k, v in dist.items() if round(v, 2) > 0)
    return {
        'name': name, 'file': path.name, 'team': row['team'], 'opponent': opp_kr,
        'minute': f"{int(row['minute'])}'{int(row['second']):02d}",
        'n_channel5': int(row['n_channel5']), 'n_center5': int(row['n_center5']),
        'n_channel10': int(row['n_channel10']),
        'n_beyond': int(row['n_beyond']), 'vis_launch': round(float(row['vis_launch']), 2),
        'vis_wide': round(float(row['vis_launch_wide']), 2),
        'def_line': round(float(row['def_line']), 1), 'ball_x': round(float(row['ball_x']), 1),
        'n_opp_visible': int(row['n_opp_visible']), 'sample_mean': round(target, 2),
        'dist': dist_str,
    }


def main() -> None:
    _ensure_korean_font()
    s = pd.read_pickle(CACHE / 'situations_lanes.pkl')
    s = s[s['in_scope']]

    arg = s[(s['stage'] == 'Group Stage') & (s['team'] == 'Argentina') & (~s['setpiece'])]
    kor_g = s[(s['stage'] == 'Group Stage') & (s['team'] == 'South Korea') & (~s['setpiece'])]
    kor_b = s[(s['team'] == 'South Korea') & (s['match_id'] == BRAZIL_MATCH) & (~s['setpiece'])]

    jobs = [
        (arg, 'argentina'),
        (kor_g, 'korea_group'),
        (kor_b, 'korea_brazil'),
    ]

    print("=" * 78)
    print("프리즈프레임 대비 스냅샷")
    print("=" * 78)
    results = []
    for df, name in jobs:
        row, target, dist = select_typical(df)
        info = render(row, target, dist, name)
        results.append(info)
        print(f"\n[{name}] {info['team']} vs {info['opponent']} {info['minute']}")
        print(f"  표본 {len(df)}건, 평균 n_channel5 = {target:.2f}, 분포: {info['dist']}")
        print(f"  선정 장면: 채널 5m {info['n_channel5']}명 / 중앙 5m {info['n_center5']}명 / "
              f"채널 10m {info['n_channel10']}명 / 오프사이드 위치 {info['n_beyond']}명")
        print(f"  맥락: 화면에 잡힌 상대 {info['n_opp_visible']}명, 추정 라인 x={info['def_line']}, "
              f"공 x={info['ball_x']}, 사이드 가시율 {info['vis_wide']}")
        print(f"  -> {info['file']}")

    _write_notes(results, len(arg), len(kor_g), len(kor_b))
    print(f"\n저장: {OUT / 'snapshot_notes.md'}")


def _write_notes(results: list[dict], n_arg: int, n_kor_g: int, n_kor_b: int) -> None:
    r = {x['name']: x for x in results}
    lines = [
        "# 프리즈프레임 대비 스냅샷 - 선정 방식과 장면별 수치",
        "",
        "`korea_qatar2022/05_snapshot_contrast.py`의 산출물. 채널 침투 선택지 지표가 실제로",
        "무엇을 세는지, 그리고 관측 조건이 그 값을 어떻게 미는지 눈으로 보여준다.",
        "",
        "## 패널 구성",
        "",
        "- **패널 1** (지표가 세는 것): `fig_snapshot_argentina.png` (왼쪽) vs `fig_snapshot_korea_group.png` (오른쪽)",
        "- **패널 2** (같은 한국, 관측 조건만 다른 두 경기): `fig_snapshot_korea_group.png` (왼쪽) vs `fig_snapshot_korea_brazil.png` (오른쪽)",
        "",
        "## 선정 방식",
        "",
        "대상 표본(팀/경기의 오픈플레이 전진 상황 x 30-110, 세트피스 제외) 중 채널 침투",
        "선택지 개수(`n_channel5`)가 **그 표본의 평균에 가장 가까운** 상황을 뽑았다. PLAN",
        "원안은 중앙값을 쓰려 했으나 주요 팀들의 중앙값이 모두 겹쳐(분포가 0/1/2에 쏠림)",
        "팀 차이를 담지 못했다. 차이는 평균에 있어 기준을 평균으로 바꿨다. 동점은",
        "`n_opp_visible` -> `vis_launch_wide` -> `def_line` -> `ball_x` 순으로 표본 중앙값에",
        "가장 가까운 상황을, 그래도 동점이면 이른 시각을 골랐다. 단 **킥오프 직후(전·후반",
        "시작 3분)는 후보에서 제외**한다 - 킥오프 대형은 그 팀이 경기를 어떻게 풀었는지를",
        "대표하지 않기 때문이며, 평균 계산에서는 빼지 않는다(지표 정의와 어긋나므로).",
        "",
        "**한계(사용자와 합의)**: 평균 기준이어도 장면마다 링 개수 자체는 비슷할 수 있다.",
        "팀 차이는 \"그런 장면이 얼마나 자주 나오는가\"이므로 아래 분포를 함께 본다.",
        "대신 세 장면의 **맥락**(화면에 잡힌 상대 수, 추정 라인 깊이)은 크게 다르고,",
        "그 대비가 이 스냅샷의 핵심이다.",
        "",
        "## 장면별 수치",
        "",
        "| | 아르헨티나 (조별) | 한국 (조별) | 한국 (브라질전) |",
        "| :--- | :--- | :--- | :--- |",
        f"| 파일 | `{r['argentina']['file']}` | `{r['korea_group']['file']}` | `{r['korea_brazil']['file']}` |",
        f"| 상대 · 시각 | {r['argentina']['opponent']} {r['argentina']['minute']} | "
        f"{r['korea_group']['opponent']} {r['korea_group']['minute']} | "
        f"{r['korea_brazil']['opponent']} {r['korea_brazil']['minute']} |",
        f"| 채널 5m (실선 청록 링) | {r['argentina']['n_channel5']}명 | {r['korea_group']['n_channel5']}명 | {r['korea_brazil']['n_channel5']}명 |",
        f"| 중앙 5m (점선 청록 링) | {r['argentina']['n_center5']}명 | {r['korea_group']['n_center5']}명 | {r['korea_brazil']['n_center5']}명 |",
        f"| 채널 10m | {r['argentina']['n_channel10']}명 | {r['korea_group']['n_channel10']}명 | {r['korea_brazil']['n_channel10']}명 |",
        f"| 오프사이드 위치 (주황 링) | {r['argentina']['n_beyond']}명 | {r['korea_group']['n_beyond']}명 | {r['korea_brazil']['n_beyond']}명 |",
        f"| 화면에 잡힌 상대 | {r['argentina']['n_opp_visible']}명 | {r['korea_group']['n_opp_visible']}명 | {r['korea_brazil']['n_opp_visible']}명 |",
        f"| 추정 오프사이드 라인 x | {r['argentina']['def_line']} | {r['korea_group']['def_line']} | {r['korea_brazil']['def_line']} |",
        f"| 출발 구역 가시율 (전 폭) | {r['argentina']['vis_launch']} | {r['korea_group']['vis_launch']} | {r['korea_brazil']['vis_launch']} |",
        f"| 사이드 레인 가시율 | {r['argentina']['vis_wide']} | {r['korea_group']['vis_wide']} | {r['korea_brazil']['vis_wide']} |",
        "",
        "## 표본 분포 (`n_channel5` 값의 비율)",
        "",
        f"- 아르헨티나 조별리그 ({n_arg}건, 평균 {r['argentina']['sample_mean']}): {r['argentina']['dist']}",
        f"- 한국 조별리그 ({n_kor_g}건, 평균 {r['korea_group']['sample_mean']}): {r['korea_group']['dist']}",
        f"- 한국 브라질전 ({n_kor_b}건, 평균 {r['korea_brazil']['sample_mean']}): {r['korea_brazil']['dist']}",
        "",
        "전형 장면 한 장으로는 팀 차이가 드러나지 않으므로 분포를 함께 봐야 한다.",
        "차이는 \"채널에 사람이 한 명이라도 있었던 상황이 얼마나 잦은가\"에 있다.",
        "",
        "## 읽는 법",
        "",
        "- 실선 청록 링 = 채널 침투 선택지(패스 시점에 온사이드이면서 라인 앞 5m 안,",
        "  공보다 앞이고 사이드 또는 하프스페이스에 있는 아군).",
        "  점선 청록 링 = 같은 조건인데 중앙(골에어리어 폭)에 있는 아군 - 컷백을 받으러",
        "  서는 자리라 침투로 세지 않고 대조군으로만 쓴다.",
        "  주황 링 = 라인을 이미 넘은 아군(규칙상 오프사이드 위치, 대조군).",
        "  보라 링 = 공 소유자(패스하는 선수, 자기 팀 색 마커 위에 표시).",
        "- 가로 점선 = 레인 경계(y=18/30/50/62). 피치 라인 기준이며 상대 배치와 무관하다.",
        "- 빨간 세로 점선 = 추정 오프사이드 라인(화면에 잡힌 상대 필드플레이어 x의 최댓값).",
        "- 바깥 어두운 구역 = `visible_area` 밖. 카메라에 안 잡혀 선수가 기록되지 않은 곳이다.",
        f"- **패널 2가 이 주제의 요점**: 같은 한국인데 브라질전은 카메라가 상대를 "
        f"{r['korea_brazil']['n_opp_visible']}명 담아",
        f"  라인이 x={r['korea_brazil']['def_line']}로 깊게 잡히고, 조별리그 장면은 상대가 "
        f"{r['korea_group']['n_opp_visible']}명뿐이라 라인이 x={r['korea_group']['def_line']}로 얕다.",
        "  경기력이 아니라 화면 구성이 지표를 흔든다는 것을 한 쌍으로 보여준다.",
        "",
        "> 전형 장면은 늦은 시각(90분+)에 걸릴 수 있다. 킥오프 직후만 후보에서 빼고 그 밖의",
        "> 시각은 따지지 않기 때문이며, 점유 기반 지표라 경기 후반이 특별히 비대표적이지는",
        "> 않다. 각 그림 제목에 정확한 시각을 표기했다.",
    ]
    (OUT / 'snapshot_notes.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
