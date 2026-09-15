"""2차원 비교 (분석 질문 3): 전진 상황의 '양' x 상황당 채널 침투 선택지 '밀도'.

질문 1~2에서 침투 선택지는 상대 수비 라인 깊이·점유 볼륨과 강하게 얽혀 있음을
확인했다. 이 스크립트는 그 얽힘을 감추지 않고 **드러내기 위해** 두 축으로 나눠
그린다:

- x축 (양)   = 팀이 만든 전진 상황 수 (조별리그 3경기 합산)
- y축 (밀도) = 상황당 채널 침투 선택지 (관측 조건 보정 = 질문 1~2의 잔차 지표)
- 색         = 그 팀이 도달한 최종 라운드

'점유 볼륨'(오픈플레이 패스 총량)은 전진 상황 수와 r=0.99로 사실상 같은 축이다.
따라서 x축을 통제한 잔차가 곧 점유 볼륨을 통제한 밀도이며, 두 번째 패널이
"양을 걷어내면 무엇이 남는가"를 보여준다.

이 두 축이 **지표가 낮은 팀에 섞여 있는 두 유형**을 갈라준다. 채널 침투 선택지가
적은 팀에는 성격이 반대인 둘이 있다 - **모로코형**(양이 적다 = 밀어붙일 일이
없었다)과 **포르투갈형**(양은 많은데 밀도가 낮다 = 밀어붙이는데 못 뚫었다).
사분면 출력과 그림의 사분면 라벨이 이 구분을 담는다.

산출물(`korea_qatar2022/processed/`):
- volume_density.csv          - 팀별 양/밀도/라운드/잔차
- fig_volume_density.png      - 2패널 산점도 (원본 / 양 통제 후)
"""
import os
import sys
from pathlib import Path

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

from src.visualizer import _ensure_korean_font

CACHE = Path('data/raw/wc2022_360')
OUT = Path('korea_qatar2022/processed')
OUT.mkdir(parents=True, exist_ok=True)

COND_COLS = ['n_opp_visible', 'max_vis_x', 'band15',
             'vis_launch_wide', 'vis_launch_half', 'vis_launch_center']

# 2022 카타르 월드컵 각 팀의 최종 도달 라운드
ROUND = {
    4: ['Argentina', 'France'],                                              # 결승
    3: ['Croatia', 'Morocco'],                                               # 4강
    2: ['Netherlands', 'Brazil', 'England', 'Portugal'],                     # 8강
    1: ['Australia', 'Poland', 'Japan', 'Switzerland',                       # 16강
        'United States', 'Senegal', 'Spain', 'South Korea'],
}
ROUND_NAME = {0: '조별 탈락', 1: '16강', 2: '8강', 3: '4강', 4: '결승'}
TEAM_ROUND = {t: r for r, ts in ROUND.items() for t in ts}

TEAM_KR = {
    'South Korea': '한국', 'Brazil': '브라질', 'Spain': '스페인', 'Japan': '일본',
    'Germany': '독일', 'Senegal': '세네갈', 'Argentina': '아르헨티나', 'France': '프랑스',
    'Netherlands': '네덜란드', 'Portugal': '포르투갈', 'England': '잉글랜드',
    'Croatia': '크로아티아', 'Morocco': '모로코', 'Costa Rica': '코스타리카',
    'Iran': '이란', 'Poland': '폴란드', 'Belgium': '벨기에', 'Mexico': '멕시코',
    'Switzerland': '스위스', 'United States': '미국', 'Australia': '호주',
    'Denmark': '덴마크', 'Uruguay': '우루과이', 'Ecuador': '에콰도르',
    'Ghana': '가나', 'Cameroon': '카메룬', 'Serbia': '세르비아', 'Wales': '웨일스',
    'Tunisia': '튀니지', 'Qatar': '카타르', 'Saudi Arabia': '사우디', 'Canada': '캐나다',
}


def ols_residuals(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def possession_volume(match_ids) -> dict:
    """팀별 오픈플레이 패스 총량 = '점유 볼륨' 대리 지표."""
    vol = {}
    for mid in match_ids:
        ev = pd.read_pickle(CACHE / f'events_{mid}.pkl')
        op = ev[(ev['type'] == 'Pass') & ev['pass_type'].isna()]
        for team, cnt in op['team'].value_counts().items():
            vol[team] = vol.get(team, 0) + int(cnt)
    return vol


def main() -> None:
    s = pd.read_pickle(CACHE / 'situations_lanes.pkl')
    g = s[(s['stage'] == 'Group Stage') & (~s['setpiece']) & (s['in_scope'])].copy()
    g['max_vis_x'] = g['def_line'] + g['vis_depth']
    g = g.dropna(subset=COND_COLS)

    # 관측 조건 보정 밀도 (질문 1~2와 동일)
    Xc = g[COND_COLS].to_numpy(float)
    g['adj5'] = ols_residuals(Xc, g['n_channel5'].to_numpy(float))
    g['adj10'] = ols_residuals(Xc, g['n_channel10'].to_numpy(float))
    g['adjc'] = ols_residuals(Xc, g['n_center5'].to_numpy(float))

    group_mids = sorted(s.loc[s['stage'] == 'Group Stage', 'match_id'].unique())
    vol = possession_volume(group_mids)

    tm = g.groupby('team').agg(
        volume=('n_channel5', 'size'),          # x축: 전진 상황 수 (양)
        density_raw5=('n_channel5', 'mean'),
        density_raw10=('n_channel10', 'mean'),
        density5=('adj5', 'mean'),              # y축: 관측 조건 보정 밀도
        density10=('adj10', 'mean'),
        density_center=('adjc', 'mean'),        # 대조군: 중앙 밀도(보정)
        def_line=('def_line', 'mean'),          # 상대 최종 수비 라인 깊이(얽힘 진단용)
    )
    tm['op_passes'] = [vol[t] for t in tm.index]
    tm['round'] = [TEAM_ROUND.get(t, 0) for t in tm.index]
    tm['round_name'] = [ROUND_NAME[r] for r in tm['round']]
    tm['advanced'] = (tm['round'] >= 1).astype(int)
    tm['team_kr'] = [TEAM_KR.get(t, t) for t in tm.index]

    # 점유 볼륨(오픈플레이 패스 총량)을 통제한 밀도 잔차.
    # 전진 상황 수와 r=0.99라 어느 쪽을 통제해도 결과는 거의 같다.
    tm['density5_vc'] = ols_residuals(tm[['op_passes']].to_numpy(float),
                                     tm['density5'].to_numpy(float))
    tm['density10_vc'] = ols_residuals(tm[['op_passes']].to_numpy(float),
                                      tm['density10'].to_numpy(float))

    # ===== 진단 =====
    def c(a, b):
        return np.corrcoef(tm[a], tm[b])[0, 1]

    print("=" * 68)
    print("얽힘 진단 (팀 단위, n=32)")
    print("=" * 68)
    print(f"전진 상황 수  vs  오픈플레이 패스 총량 : r={c('volume', 'op_passes'):+.3f}  (사실상 같은 축)")
    print()
    print(f"밀도(보정 5m)   vs 양      : r={c('density5', 'volume'):+.3f}")
    print(f"밀도(보정 5m)   vs 점유볼륨: r={c('density5', 'op_passes'):+.3f}")
    print(f"밀도(원시 10m)  vs 점유볼륨: r={c('density_raw10', 'op_passes'):+.3f}")
    print(f"밀도 vs 상대 라인 깊이: 원시 r={c('density_raw5', 'def_line'):+.3f} / "
          f"보정 r={c('density5', 'def_line'):+.3f}")
    print(f"채널 밀도 vs 중앙 밀도(둘 다 보정): r={c('density5', 'density_center'):+.3f}")
    print()
    adv = tm['advanced'].to_numpy(float)
    for col, label in [('density_raw10', '밀도 원시 10m'), ('density5', '밀도 보정 5m'),
                       ('density10', '밀도 보정 10m')]:
        raw = np.corrcoef(tm[col], adv)[0, 1]
        vc = np.corrcoef(ols_residuals(tm[['op_passes']].to_numpy(float),
                                       tm[col].to_numpy(float)), adv)[0, 1]
        print(f"{label:>14s}  진출상관 {raw:+.3f}  ->  점유 볼륨 통제 후 {vc:+.3f}")
    print()

    kor = tm.loc['South Korea']
    print("한국:")
    print(f"  전진 상황 수 : {int(kor['volume'])}건  (32팀 중 {int(tm['volume'].rank()[('South Korea')])}위 / 최저 = 1위)")
    print(f"  밀도 보정 5m : {kor['density5']:+.3f}  (중앙값 {tm['density5'].median():+.3f})")
    print(f"  양 통제 후   : {kor['density5_vc']:+.3f}")
    print()

    q_x = tm['volume'].median()
    q_y = tm['density5'].median()
    # 사분면 이름에 "지표가 낮은 두 유형"을 박아둔다. 채널 침투 선택지가 적은 팀은
    # 양이 적어서(모로코형) 낮을 수도, 양은 많은데 못 뚫어서(포르투갈형) 낮을 수도
    # 있다. 둘은 축구적으로 정반대인데 지표 하나로는 구분되지 않는다.
    quad = {
        '많음+높음 (밀어붙이고 뚫었다)': tm[(tm.volume >= q_x) & (tm.density5 >= q_y)],
        '많음+낮음 (포르투갈형 - 밀어붙이는데 못 뚫었다)': tm[(tm.volume >= q_x) & (tm.density5 < q_y)],
        '적음+높음 (적게 가도 채널을 열었다)': tm[(tm.volume < q_x) & (tm.density5 >= q_y)],
        '적음+낮음 (모로코형 - 밀어붙일 일이 없었다)': tm[(tm.volume < q_x) & (tm.density5 < q_y)],
    }
    for name, sub in quad.items():
        adv_n = int(sub['advanced'].sum())
        print(f"  [{name}] {len(sub)}팀, 진출 {adv_n}팀: {', '.join(sub['team_kr'])}")
    print()
    for t, label in [('Morocco', '모로코'), ('Portugal', '포르투갈')]:
        row = tm.loc[t]
        print(f"  {label}: 양 {int(row['volume'])}건(중앙값 {int(q_x)}), "
              f"밀도 {row['density5']:+.3f}(중앙값 {q_y:+.3f}) -> "
              f"{'양이 적어서 낮다' if row['volume'] < q_x else '양은 많은데 낮다'}")

    # ===== 저장 =====
    cols = ['team_kr', 'round', 'round_name', 'advanced', 'volume', 'op_passes',
            'density_raw5', 'density_raw10', 'density5', 'density10',
            'density_center', 'density5_vc', 'density10_vc', 'def_line']
    out = tm[cols].copy()
    out.insert(0, 'team', out.index)
    out.sort_values('density5', ascending=False).round(4).to_csv(
        OUT / 'volume_density.csv', index=False, encoding='utf-8-sig')
    print(f"\n저장: {OUT / 'volume_density.csv'}")

    _write_notes(tm, quad, q_x, q_y)
    print(f"저장: {OUT / 'volume_density_notes.md'}")

    _ensure_korean_font()
    _fig(tm)
    print("그림 저장 완료")


def _write_notes(tm: pd.DataFrame, quad: dict, q_x: float, q_y: float) -> None:
    """질문 3 관찰 메모를 계산값으로 생성한다(손으로 고치지 말 것)."""
    def c(a, b):
        return np.corrcoef(tm[a], tm[b])[0, 1]

    adv = tm['advanced'].to_numpy(float)
    vc5 = np.corrcoef(tm['density5_vc'], adv)[0, 1]
    kor = tm.loc['South Korea']

    lines = [
        "# 양 x 밀도 관찰 메모 (질문 3)",
        "",
        "`02_volume_density.py`가 실행 때마다 새로 쓰는 파일이다. 손으로 고치지 말 것.",
        "",
        "## 두 축",
        "",
        "- x축 \"양\" = 전진 상황 수(조별리그 3경기 합산). 오픈플레이 패스 총량(점유 볼륨)과 "
        f"r={c('volume', 'op_passes'):+.3f}로 사실상 같은 축이다.",
        f"- 밀도는 상대 최종 수비 라인 깊이와도 얽힌다: 원시 r={c('density_raw5', 'def_line'):+.3f} / "
        f"보정 r={c('density5', 'def_line'):+.3f}.",
        "- y축 \"밀도\" = 상황당 채널 침투 선택지(관측 조건 보정 잔차).",
        "",
        "## 얽힘",
        "",
        f"- 밀도 vs 양: r={c('density5', 'volume'):+.3f} / 밀도 vs 점유 볼륨: "
        f"r={c('density5', 'op_passes'):+.3f}",
        f"- 채널 밀도 vs 중앙 밀도(둘 다 보정): r={c('density5', 'density_center'):+.3f}",
        f"- **점유 볼륨을 통제하면 진출 상관이 줄어든다**: "
        f"{np.corrcoef(tm['density5'], adv)[0, 1]:+.3f} -> {vc5:+.3f}. "
        "\"채널에 사람이 많은 팀이 이긴다\"의 일부는 \"공을 더 가진 팀이 이긴다\"로 설명된다.",
        "",
        "## 사분면 - 지표가 낮은 두 유형",
        "",
        f"경계는 32팀 중앙값(양 {int(q_x):,}건 / 밀도 {q_y:+.3f}).",
        "",
        "| 사분면 | 팀 수 | 16강 진출 | 팀 |",
        "| :--- | ---: | ---: | :--- |",
    ]
    for name, sub in quad.items():
        lines.append(f"| {name} | {len(sub)} | {int(sub['advanced'].sum())} | "
                     f"{', '.join(sub['team_kr'])} |")
    lines += [
        "",
        f"- 모로코: 양 {int(tm.loc['Morocco', 'volume']):,}건, 밀도 "
        f"{tm.loc['Morocco', 'density5']:+.3f} - 밀어붙일 일이 없어서 낮다.",
        f"- 포르투갈: 양 {int(tm.loc['Portugal', 'volume']):,}건, 밀도 "
        f"{tm.loc['Portugal', 'density5']:+.3f} - 밀어붙이는데 못 뚫었다.",
        "- 밀도 하나만 인용하면 이 둘이 구분되지 않는다.",
        "",
        "## 한국",
        "",
        f"- 전진 상황 수 {int(kor['volume']):,}건 (32팀 중 "
        f"{int(tm['volume'].rank()['South Korea'])}위, 최저 = 1위)",
        f"- 밀도 보정 {kor['density5']:+.3f} (중앙값 {q_y:+.3f})",
        f"- 양을 통제한 잔차 {kor['density5_vc']:+.3f} - 전진 볼륨 대비로는 평범하다.",
        "",
        "## 산출물",
        "",
        "- `volume_density.csv` - 팀별 양/밀도/중앙 밀도/라운드/잔차",
        "- `fig_volume_density.png` - 2패널 산점도 (원본 / 점유 볼륨 통제 후)",
    ]
    (OUT / 'volume_density_notes.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


# ---------------------------------------------------------------------------
BG = '#15181c'
FG = '#e8e8e8'
KOR = '#ff4b4b'
ROUND_COLORS = ['#5b6472', '#3b82f6', '#22c55e', '#f59e0b', '#fde047']  # 조별~결승


def _scatter(ax, tm, ycol, xcol, xlabel, ylabel, title, draw_fit=True, hline=None,
             vline=None, quad_labels=False):
    ax.set_facecolor(BG)
    cmap = ListedColormap(ROUND_COLORS)
    norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5, 4.5], cmap.N)

    x, y = tm[xcol].to_numpy(float), tm[ycol].to_numpy(float)
    ax.scatter(x, y, c=tm['round'], cmap=cmap, norm=norm, s=70,
               edgecolors='#0c0e11', linewidths=0.6, zorder=3)

    if draw_fit:
        b1, b0 = np.polyfit(x, y, 1)
        xs = np.array([x.min(), x.max()])
        r = np.corrcoef(x, y)[0, 1]
        ax.plot(xs, b0 + b1 * xs, color='#9aa0a6', lw=1.3, ls='--', zorder=2,
                label=f'추세선  r={r:+.2f}')
        # 사분면 라벨을 아래쪽 양 끝에 두므로 범례는 위로 올린다(겹침 방지).
        ax.legend(loc='upper left' if quad_labels else 'lower right',
                  frameon=False, labelcolor=FG, fontsize=8.5)
    if hline is not None:
        ax.axhline(hline, color='#3a3f46', lw=1, ls=':')
    if vline is not None:
        ax.axvline(vline, color='#3a3f46', lw=1, ls=':')
    if quad_labels and hline is not None and vline is not None:
        # 아래 두 사분면에만 이름을 단다 - 이 글의 관심사가 "지표가 낮은 팀"이라서다.
        for xs, ha, text in [(0.02, 'left', '적음 + 낮음\n"모로코형" 밀어붙일 일이 없었다'),
                             (0.98, 'right', '많음 + 낮음\n"포르투갈형" 밀어붙이는데 못 뚫었다')]:
            ax.text(xs, 0.015, text, transform=ax.transAxes, ha=ha, va='bottom',
                    fontsize=8, color='#6d747c', linespacing=1.6, zorder=1)

    for t, row in tm.iterrows():
        is_kor = t == 'South Korea'
        ax.annotate(row['team_kr'], (row[xcol], row[ycol]),
                    xytext=(4, 3), textcoords='offset points',
                    fontsize=6.5 if not is_kor else 9,
                    color=KOR if is_kor else '#b8bdc2',
                    fontweight='bold' if is_kor else 'normal', zorder=4)
        if is_kor:
            ax.scatter([row[xcol]], [row[ycol]], facecolors='none',
                       edgecolors=KOR, s=190, lw=2, zorder=5)

    ax.set_xlabel(xlabel, color=FG, fontsize=9.5)
    ax.set_ylabel(ylabel, color=FG, fontsize=9.5)
    ax.set_title(title, color=FG, fontsize=11, pad=10)
    ax.tick_params(colors=FG, labelsize=8)
    for sp in ax.spines.values():
        sp.set_color('#3a3f46')


def _fig(tm: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(15, 7.4))
    fig.set_facecolor(BG)

    _scatter(axes[0], tm, 'density5', 'volume',
             '전진 상황 수 (조별리그 3경기 합산)  =  "양"',
             '상황당 침투 선택지 · 관측 조건 보정  =  "밀도"',
             'A. 양 x 밀도 - 밀어붙인 팀일수록 채널에 선 선수도 많다',
             draw_fit=True, hline=tm['density5'].median(), vline=tm['volume'].median(),
             quad_labels=True)

    r_raw = np.corrcoef(tm['density5'], tm['advanced'])[0, 1]
    r_vc = np.corrcoef(tm['density5_vc'], tm['advanced'])[0, 1]
    _scatter(axes[1], tm, 'density5_vc', 'volume',
             '전진 상황 수 (점유 볼륨과 r=0.98)',
             '밀도 잔차 (점유 볼륨을 통제한 뒤 남는 채널 침투 선택지)',
             f'B. 점유 볼륨을 걷어낸 뒤 - 진출과의 상관이 {r_raw:+.2f}에서 {r_vc:+.2f}로',
             draw_fit=False, hline=0.0)

    handles = [plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=cc,
                          markeredgecolor='#0c0e11', markersize=9,
                          label=ROUND_NAME[i]) for i, cc in enumerate(ROUND_COLORS)]
    handles.append(plt.Line2D([0], [0], marker='o', color='none', markerfacecolor='none',
                              markeredgecolor=KOR, markeredgewidth=2, markersize=11, label='한국'))
    fig.legend(handles=handles, loc='lower center', ncol=6, frameon=False,
               labelcolor=FG, fontsize=9, bbox_to_anchor=(0.5, 0.005))

    fig.suptitle('2022 카타르 월드컵 조별리그 - 채널 침투 선택지의 양·밀도 분해 (32팀)',
                 color=FG, fontsize=14, fontweight='bold', y=0.99)
    fig.text(0.5, 0.935,
             '밀도는 전진 볼륨(= 영역 우위)과 얽혀 있다. 두 축으로 나누면 지표가 낮은 두 유형도 갈라진다 - '
             '왼쪽 아래는 밀어붙일 일이 없었던 팀, 오른쪽 아래는 밀어붙이는데 못 뚫은 팀.',
             ha='center', color='#9aa0a6', fontsize=9.5)
    fig.tight_layout(rect=[0, 0.06, 1, 0.91])
    fig.savefig(OUT / 'fig_volume_density.png', dpi=140, facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    main()
