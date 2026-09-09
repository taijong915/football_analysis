"""한국 대조 (분석 질문 4): 침투 선택지 vs 오프사이드 위치, 그리고
한국의 원시값 극단이 실제 경기 내용인가 중계 화면 구성의 산물인가.

원시값에서 한국은 "라인 앞에 준비된 선수(침투 선택지)"가 32팀 중 하위 3위,
"라인을 넘어간 선수(오프사이드 위치)"가 상위 2위인 극단적인 팀이다.
이 스크립트는 그 극단이 관측 조건으로 얼마나 설명되는지 네 가지로 확인한다:

1. 팀 산점도 - 침투 선택지 x 오프사이드 위치, 원시 vs 보정
2. 한국이 32팀 중 상대가 가장 적게 관측된 팀임을 (경기별로도) 확인
3. 처리 방식별 한국 순위: 원시 / vis_launch 필터 / n_opp_visible 필터 / 회귀 보정
4. 관측 조건이 지표를 미는 방향이 한국의 원시 패턴과 일치하는지 (상황 단위 상관)

산출물(`korea_qatar2022/processed/`):
- korea_contrast.csv            - 한국 경기별 표 + 처리 방식별 순위
- fig_korea_contrast.png        - 침투 선택지 x 오프사이드 위치 (원시 / 보정)
- fig_korea_observation.png     - 관측 조건 메커니즘
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

from src.visualizer import _ensure_korean_font

CACHE = Path('data/raw/wc2022_360')
OUT = Path('korea_qatar2022/processed')
OUT.mkdir(parents=True, exist_ok=True)

COND_COLS = ['n_opp_visible', 'vis_launch', 'max_vis_x', 'band15']

ADVANCED = {
    'Netherlands', 'United States', 'Argentina', 'Australia', 'Japan', 'Croatia',
    'Brazil', 'South Korea', 'England', 'Senegal', 'France', 'Poland', 'Morocco',
    'Spain', 'Portugal', 'Switzerland',
}
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
OPP_KR = {'Portugal': '포르투갈', 'Uruguay': '우루과이', 'Ghana': '가나'}


def ols_residuals(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def rank_low(series: pd.Series, key: str = 'South Korea') -> int:
    """낮은 값이 1위인 순위에서 key의 등수."""
    return int(series.rank(method='min')[key])


def main() -> None:
    s = pd.read_pickle(CACHE / 'situations.pkl')
    g = s[(s['stage'] == 'Group Stage') & (~s['setpiece'])].copy()
    g['max_vis_x'] = g['def_line'] + g['vis_depth']

    Xc = g[COND_COLS].to_numpy(float)
    g['adj5'] = ols_residuals(Xc, g['n_launch5'].to_numpy(float))
    g['adjb'] = ols_residuals(Xc, g['n_beyond'].to_numpy(float))
    g['adj10'] = ols_residuals(Xc, g['n_launch'].to_numpy(float))

    tm = g.groupby('team').agg(
        n=('n_launch5', 'size'),
        raw5=('n_launch5', 'mean'), rawb=('n_beyond', 'mean'),
        adj5=('adj5', 'mean'), adjb=('adjb', 'mean'),
        opp_visible=('n_opp_visible', 'mean'),
    )
    tm['advanced'] = [t in ADVANCED for t in tm.index]
    tm['team_kr'] = [TEAM_KR.get(t, t) for t in tm.index]

    # ===== 1. 처리 방식별 한국 순위 =====
    treatments = {}
    treatments['원시'] = (rank_low(tm['raw5']), rank_low(tm['rawb']))

    for label, col, thr in [('vis_launch>=0.85', 'vis_launch', 0.85),
                            ('상대 관측>=8', 'n_opp_visible', 8)]:
        sub = g[g[col] >= thr]
        r5 = sub.groupby('team')['n_launch5'].mean()
        rb = sub.groupby('team')['n_beyond'].mean()
        treatments[label] = (rank_low(r5), rank_low(rb))

    treatments['회귀 보정'] = (rank_low(tm['adj5']), rank_low(tm['adjb']))

    # ===== 2. 한국 경기별 =====
    kor = g[g['team'] == 'South Korea']
    per_match = (kor.groupby(['match_id', 'opponent'])
                 .agg(n=('n_launch5', 'size'),
                      opp_visible=('n_opp_visible', 'mean'),
                      def_line=('def_line', 'mean'),
                      raw5=('n_launch5', 'mean'), raw_beyond=('n_beyond', 'mean'),
                      adj5=('adj5', 'mean'), adj_beyond=('adjb', 'mean'))
                 .reset_index())
    per_match['opponent_kr'] = per_match['opponent'].map(OPP_KR).fillna(per_match['opponent'])

    avg32 = dict(opp_visible=g['n_opp_visible'].mean(), raw5=g['n_launch5'].mean(),
                 raw_beyond=g['n_beyond'].mean())

    # ===== 3. 관측 조건이 미는 방향 =====
    corr_all = (g['n_opp_visible'].corr(g['n_launch5']), g['n_opp_visible'].corr(g['n_beyond']))
    corr_kor = (kor['n_opp_visible'].corr(kor['n_launch5']), kor['n_opp_visible'].corr(kor['n_beyond']))

    # ===== 출력 =====
    print("=" * 70)
    print("질문 4: 한국의 원시값 극단은 경기 내용인가 화면 구성인가")
    print("=" * 70)
    print(f"\n한국 상대 관측 평균: {tm.loc['South Korea', 'opp_visible']:.2f}명  "
          f"(32팀 최저, 순위 {rank_low(tm['opp_visible'])}/32, 32팀 평균 {avg32['opp_visible']:.2f}명)")
    nxt = tm.sort_values('opp_visible').iloc[1]
    print(f"두 번째로 적은 팀: {TEAM_KR.get(nxt.name, nxt.name)} {nxt['opp_visible']:.2f}명 "
          f"(한국과 {nxt['opp_visible'] - tm.loc['South Korea', 'opp_visible']:.2f} 차)")

    print("\n한국 경기별:")
    show = per_match[['opponent_kr', 'n', 'opp_visible', 'def_line',
                      'raw5', 'raw_beyond', 'adj5', 'adj_beyond']]
    print(show.round(3).to_string(index=False))
    print(f"  32팀 평균:  opp_visible {avg32['opp_visible']:.2f}  "
          f"raw5 {avg32['raw5']:.3f}  raw_beyond {avg32['raw_beyond']:.3f}")
    print("  -> 세 경기 모두 상대 관측이 32팀 평균 아래이고, 원시값이 같은 방향으로 치우친다.")
    print("     보정값은 세 경기 모두 0 근처 - 극단이 한 경기 탓이 아니라 관측 조건 탓.")

    print("\n처리 방식별 한국 순위 (침투 선택지 / 오프사이드 위치, 낮을수록 1위):")
    for label, (r5, rb) in treatments.items():
        print(f"  {label:>14s}:  침투 선택지 {r5:>2d}위   오프사이드 위치 {rb:>2d}위")
    print("  -> vis_launch 필터는 오히려 더 극단으로 민다(추정된 라인 주변만 보므로 - PLAN 한계 절).")
    print("     상대 관측 수를 직접 겨냥한 필터는 침투 선택지를 3->10위로 끌어올리고,")
    print("     회귀 보정은 두 지표를 모두 중위권으로 옮긴다(침투 18위 / 오프사이드 8위).")

    print(f"\n관측 조건이 지표를 미는 방향 (상황 단위 상관):")
    print(f"  전체:  n_opp_visible vs 침투 선택지 {corr_all[0]:+.3f} / vs 오프사이드 위치 {corr_all[1]:+.3f}")
    print(f"  한국:  n_opp_visible vs 침투 선택지 {corr_kor[0]:+.3f} / vs 오프사이드 위치 {corr_kor[1]:+.3f}")
    print("  -> 상대가 적게 보일수록 침투 선택지는 줄고 오프사이드 위치는 는다.")
    print("     한국의 원시 패턴(침투 선택지 하위 3위 + 오프사이드 위치 상위 2위)이 정확히 이 방향.")

    kor_row = tm.loc['South Korea']
    print(f"\n보정 후 한국:")
    print(f"  침투 선택지 {rank_low(tm['adj5'])}위  (값 {kor_row['adj5']:+.3f}, 중앙값 {tm['adj5'].median():+.3f}) - 사실상 중앙값")
    print(f"  오프사이드 위치 {rank_low(tm['adjb'])}위  (값 {kor_row['adjb']:+.3f}, 중앙값 {tm['adjb'].median():+.3f}) - 평균보다 약간 적은 쪽으로 반전")

    # ===== CSV =====
    csv = per_match.copy()
    csv['team'] = 'South Korea'
    csv.round(4).to_csv(OUT / 'korea_contrast.csv', index=False, encoding='utf-8-sig')
    treat_df = pd.DataFrame(
        [(k, v[0], v[1]) for k, v in treatments.items()],
        columns=['treatment', 'rank_penetration_5m', 'rank_offside_position'])
    treat_df.to_csv(OUT / 'korea_contrast_ranks.csv', index=False, encoding='utf-8-sig')
    print(f"\n저장: {OUT / 'korea_contrast.csv'}, {OUT / 'korea_contrast_ranks.csv'}")

    _ensure_korean_font()
    _fig_contrast(tm)
    _fig_observation(tm, per_match, treatments, avg32)
    print("그림 2개 저장 완료")


# ---------------------------------------------------------------------------
BG = '#15181c'
FG = '#e8e8e8'
KOR = '#ff4b4b'
ADV_C = '#00c2a8'
OUT_C = '#6b7280'


def _panel(ax, tm, xcol, ycol, xlabel, ylabel, title):
    ax.set_facecolor(BG)
    colors = [KOR if t == 'South Korea' else (ADV_C if a else OUT_C)
              for t, a in zip(tm.index, tm['advanced'])]
    ax.axvline(tm[xcol].median(), color='#3a3f46', lw=1, ls=':')
    ax.axhline(tm[ycol].median(), color='#3a3f46', lw=1, ls=':')
    ax.scatter(tm[xcol], tm[ycol], c=colors, s=64, edgecolors='#0c0e11', linewidths=0.6, zorder=3)
    for t, row in tm.iterrows():
        is_k = t == 'South Korea'
        ax.annotate(row['team_kr'], (row[xcol], row[ycol]), xytext=(4, 3),
                    textcoords='offset points', fontsize=6.5 if not is_k else 9,
                    color=KOR if is_k else '#b8bdc2',
                    fontweight='bold' if is_k else 'normal', zorder=4)
        if is_k:
            ax.scatter([row[xcol]], [row[ycol]], facecolors='none', edgecolors=KOR,
                       s=190, lw=2, zorder=5)
    ax.set_xlabel(xlabel, color=FG, fontsize=9.5)
    ax.set_ylabel(ylabel, color=FG, fontsize=9.5)
    ax.set_title(title, color=FG, fontsize=11, pad=10)
    ax.tick_params(colors=FG, labelsize=8)
    for sp in ax.spines.values():
        sp.set_color('#3a3f46')


def _fig_contrast(tm: pd.DataFrame) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14.5, 7.2))
    fig.set_facecolor(BG)
    _panel(axes[0], tm, 'raw5', 'rawb',
           '침투 선택지 (라인 앞 5m, 원시)', '오프사이드 위치 선수 (원시)',
           'A. 원시값 - 한국은 좌상단 극단 (침투 선택지 최소, 오프사이드 위치 최다)')
    _panel(axes[1], tm, 'adj5', 'adjb',
           '침투 선택지 (관측 조건 보정)', '오프사이드 위치 선수 (관측 조건 보정)',
           'B. 보정 후 - 한국은 중앙 근처로 이동, 두 극단 모두 해소')
    handles = [
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=KOR, markersize=9, label='한국'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=ADV_C, markersize=9, label='16강 진출'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=OUT_C, markersize=9, label='조별 탈락'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=3, frameon=False,
               labelcolor=FG, fontsize=9, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle('침투 선택지 x 오프사이드 위치 - 한국의 원시 극단은 보정으로 사라진다',
                 color=FG, fontsize=13, fontweight='bold', y=0.99)
    fig.text(0.5, 0.935, '점선 = 32팀 중앙값. 좌상단 = 준비된 선수는 없고 넘어간 선수만 많은 자리.',
             ha='center', color='#9aa0a6', fontsize=9)
    fig.tight_layout(rect=[0, 0.05, 1, 0.92])
    fig.savefig(OUT / 'fig_korea_contrast.png', dpi=140, facecolor=BG)
    plt.close(fig)


def _fig_observation(tm, per_match, treatments, avg32) -> None:
    fig = plt.figure(figsize=(15.5, 8.4))
    fig.set_facecolor(BG)
    gs = fig.add_gridspec(2, 2, width_ratios=[1.15, 1.6], height_ratios=[1.3, 1],
                          hspace=0.42, wspace=0.28)
    ax1 = fig.add_subplot(gs[:, 0])   # 32팀 관측 (왼쪽 전체 높이)
    ax2 = fig.add_subplot(gs[0, 1])   # 한국 경기별
    ax3 = fig.add_subplot(gs[1, 1])   # 처리 방식별 순위

    # (1) 32팀 상대 관측 평균
    d = tm.sort_values('opp_visible')
    y = np.arange(len(d))
    colors = [KOR if t == 'South Korea' else OUT_C for t in d.index]
    ax1.barh(y, d['opp_visible'], color=colors, height=0.72)
    ax1.axvline(avg32['opp_visible'], color='#9aa0a6', lw=1, ls='--')
    ax1.text(avg32['opp_visible'], -1.4, f"32팀 평균 {avg32['opp_visible']:.1f}명",
             color='#9aa0a6', fontsize=8, ha='center')
    ax1.set_yticks(y)
    ax1.set_yticklabels(d['team_kr'], fontsize=7.5)
    for tick, t in zip(ax1.get_yticklabels(), d.index):
        if t == 'South Korea':
            tick.set_color(KOR)
            tick.set_fontweight('bold')
    ax1.set_xlabel('상황당 관측된 상대 필드플레이어 (명)', color=FG, fontsize=9)
    ax1.set_title('한국은 32팀 중 상대가 가장 적게 잡힌 팀\n(다음으로 적은 에콰도르와 0.9명 차)',
                  color=FG, fontsize=10.5, pad=10)
    ax1.set_ylim(-2, len(d))
    _style(ax1)

    # (2) 한국 경기별 관측
    x = np.arange(len(per_match))
    ax2.bar(x, per_match['opp_visible'], color=KOR, width=0.5, alpha=0.85)
    ax2.axhline(avg32['opp_visible'], color='#9aa0a6', lw=1, ls='--')
    ax2.text(len(per_match) - 0.5, avg32['opp_visible'] + 0.1,
             f"32팀 평균 {avg32['opp_visible']:.1f}", color='#9aa0a6', fontsize=8,
             ha='right', va='bottom')
    ax2.set_xticks(x)
    ax2.set_xticklabels(['vs ' + o for o in per_match['opponent_kr']], color=FG, fontsize=9)
    ax2.set_ylabel('관측된 상대 (명)', color=FG, fontsize=9)
    ax2.set_ylim(0, 9)
    ax2.set_title('한국 세 경기 모두 평균 아래 - 극단은 한 경기 탓이 아니다',
                  color=FG, fontsize=10.5, pad=8)
    _style(ax2)

    # (3) 처리 방식별 한국 순위 - 그룹 수평 막대
    labels = list(treatments.keys())
    yv = np.arange(len(labels))
    pen = np.array([treatments[l][0] for l in labels])
    off = np.array([treatments[l][1] for l in labels])
    h = 0.36
    ax3.barh(yv + h / 2, pen, height=h, color=ADV_C, label='침투 선택지')
    ax3.barh(yv - h / 2, off, height=h, color='#e0a13c', label='오프사이드 위치')
    for v, yy in zip(pen, yv):
        ax3.text(v + 0.4, yy + h / 2, f'{v}위', va='center', color=ADV_C, fontsize=7.5)
    for v, yy in zip(off, yv):
        ax3.text(v + 0.4, yy - h / 2, f'{v}위', va='center', color='#e0a13c', fontsize=7.5)
    ax3.axvline(16.5, color='#6b7280', lw=1, ls=':')
    ax3.text(16.5, -0.75, '중위권', color='#6b7280', fontsize=7.5, ha='center')
    ax3.set_yticks(yv)
    ax3.set_yticklabels(labels, color=FG, fontsize=8.5)
    ax3.set_ylim(-1.1, len(labels) - 0.3)
    ax3.set_xlabel('한국 순위 (1 = 지표 최소, 32 = 최대)', color=FG, fontsize=9)
    ax3.set_xlim(0, 34)
    ax3.set_title('상대 관측 수를 겨냥한 필터·보정에서만 두 극단이 풀린다\n'
                  '(vis_launch 필터는 추정된 라인 주변만 봐서 오히려 더 극단으로)',
                  color=FG, fontsize=10, pad=8)
    ax3.legend(loc='upper right', frameon=False, labelcolor=FG, fontsize=8)
    _style(ax3)

    fig.suptitle('질문 4 - 한국의 침투 선택지 극단은 실제 경기 내용보다 중계 화면 구성에 가깝다',
                 color=FG, fontsize=13.5, fontweight='bold', y=0.985)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUT / 'fig_korea_observation.png', dpi=140, facecolor=BG)
    plt.close(fig)


def _style(ax):
    ax.set_facecolor(BG)
    for sp in ax.spines.values():
        sp.set_color('#3a3f46')
    ax.tick_params(colors=FG, labelsize=8)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)


if __name__ == '__main__':
    main()
