"""한국 대조 (분석 질문 4): 채널 침투 선택지 vs 중앙, 그리고 그 값을
관측 조건이 얼마나 밀고 있는가.

2차 확장 정의는 같은 "라인 앞 5m 온사이드" 선수를 레인으로 갈라 센다.
**채널**(사이드·하프스페이스)은 컷백을 올리러 파고드는 자리, **중앙**(골에어리어
폭)은 컷백을 받으러 서는 자리다. 한 팀이 어느 쪽에 사람을 두는지가 이 질문의
축이다. 1차 정의는 둘을 합쳐 세서 이 구분을 볼 수 없었다.

여기서 재는 것은 "한국이 침투가 적은 팀인지"가 아니라 **한국의 침투가 어땠는지**다.
원시 순위를 결론으로 읽지 않고, 관측 조건을 걷어낸 뒤 무엇이 남는지까지 본다.

1. 팀 산점도 - 채널 x 중앙, 원시 vs 보정
2. 한국이 32팀 중 상대가 가장 적게 관측된 팀임을 (경기별로도) 확인
3. 처리 방식별 한국 순위: 원시 / vis_launch 필터 / n_opp_visible 필터 / 회귀 보정
4. 관측 조건이 지표를 미는 방향 (상황 단위 상관)

산출물(`korea_qatar2022/processed/`):
- korea_contrast.csv            - 한국 경기별 표
- korea_contrast_ranks.csv      - 처리 방식별 한국 순위
- korea_contrast_notes.md       - 관찰 메모(스크립트 생성)
- fig_korea_contrast.png        - 채널 x 중앙 (원시 / 보정)
- fig_korea_observation.png     - 관측 조건 메커니즘
- blog_korea_contrast.png       - 블로그용: 채널 x 중앙 최종값 한 패널, 분석 용어 없음
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

COND_COLS = ['n_opp_visible', 'max_vis_x', 'band15',
             'vis_launch_wide', 'vis_launch_half', 'vis_launch_center']

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
    s = pd.read_pickle(CACHE / 'situations_lanes.pkl')
    g = s[(s['stage'] == 'Group Stage') & (~s['setpiece']) & (s['in_scope'])].copy()
    g['max_vis_x'] = g['def_line'] + g['vis_depth']
    g = g.dropna(subset=COND_COLS)

    Xc = g[COND_COLS].to_numpy(float)
    g['adj5'] = ols_residuals(Xc, g['n_channel5'].to_numpy(float))
    g['adjc'] = ols_residuals(Xc, g['n_center5'].to_numpy(float))
    g['adjb'] = ols_residuals(Xc, g['n_beyond'].to_numpy(float))

    tm = g.groupby('team').agg(
        n=('n_channel5', 'size'),
        raw5=('n_channel5', 'mean'), rawc=('n_center5', 'mean'),
        rawb=('n_beyond', 'mean'),
        adj5=('adj5', 'mean'), adjc=('adjc', 'mean'), adjb=('adjb', 'mean'),
        opp_visible=('n_opp_visible', 'mean'),
    )
    tm['advanced'] = [t in ADVANCED for t in tm.index]
    tm['team_kr'] = [TEAM_KR.get(t, t) for t in tm.index]

    # ===== 1. 처리 방식별 한국 순위 =====
    treatments = {}
    treatments['원시'] = (rank_low(tm['raw5']), rank_low(tm['rawc']), rank_low(tm['rawb']))

    # 사이드 가시율 필터는 2차 확장에서 새로 넣었다. 채널 지표가 세는 구역이
    # 사이드라, 전 폭 가시율(vis_launch)보다 이쪽이 겨냥이 맞다.
    for label, col, thr in [('vis_launch>=0.85', 'vis_launch', 0.85),
                            ('사이드 가시율>=0.8', 'vis_launch_wide', 0.8),
                            ('상대 관측>=8', 'n_opp_visible', 8)]:
        sub = g[g[col] >= thr]
        treatments[label] = (rank_low(sub.groupby('team')['n_channel5'].mean()),
                             rank_low(sub.groupby('team')['n_center5'].mean()),
                             rank_low(sub.groupby('team')['n_beyond'].mean()))

    treatments['회귀 보정'] = (rank_low(tm['adj5']), rank_low(tm['adjc']), rank_low(tm['adjb']))

    # ===== 2. 한국 경기별 =====
    kor = g[g['team'] == 'South Korea']
    per_match = (kor.groupby(['match_id', 'opponent'])
                 .agg(n=('n_channel5', 'size'),
                      opp_visible=('n_opp_visible', 'mean'),
                      vis_wide=('vis_launch_wide', 'mean'),
                      def_line=('def_line', 'mean'),
                      raw5=('n_channel5', 'mean'), raw_center=('n_center5', 'mean'),
                      raw_beyond=('n_beyond', 'mean'),
                      adj5=('adj5', 'mean'), adj_center=('adjc', 'mean'),
                      adj_beyond=('adjb', 'mean'))
                 .reset_index())
    per_match['opponent_kr'] = per_match['opponent'].map(OPP_KR).fillna(per_match['opponent'])

    avg32 = dict(opp_visible=g['n_opp_visible'].mean(), vis_wide=g['vis_launch_wide'].mean(),
                 raw5=g['n_channel5'].mean(), raw_center=g['n_center5'].mean(),
                 raw_beyond=g['n_beyond'].mean())

    # ===== 3. 관측 조건이 미는 방향 =====
    corr_all = (g['n_opp_visible'].corr(g['n_channel5']),
                g['n_opp_visible'].corr(g['n_center5']),
                g['n_opp_visible'].corr(g['n_beyond']))
    corr_kor = (kor['n_opp_visible'].corr(kor['n_channel5']),
                kor['n_opp_visible'].corr(kor['n_center5']),
                kor['n_opp_visible'].corr(kor['n_beyond']))
    corr_wide = (g['vis_launch_wide'].corr(g['n_channel5']),
                 g['vis_launch_wide'].corr(g['n_center5']),
                 g['vis_launch_wide'].corr(g['n_beyond']))

    # ===== 출력 =====
    print("=" * 70)
    print("질문 4: 한국의 채널 침투는 어땠나 - 관측 조건을 걷어내면 무엇이 남나")
    print("=" * 70)
    print(f"\n한국 상대 관측 평균: {tm.loc['South Korea', 'opp_visible']:.2f}명  "
          f"(32팀 최저, 순위 {rank_low(tm['opp_visible'])}/32, 32팀 평균 {avg32['opp_visible']:.2f}명)")
    nxt = tm.sort_values('opp_visible').iloc[1]
    print(f"두 번째로 적은 팀: {TEAM_KR.get(nxt.name, nxt.name)} {nxt['opp_visible']:.2f}명 "
          f"(한국과 {nxt['opp_visible'] - tm.loc['South Korea', 'opp_visible']:.2f} 차)")

    print("\n한국 경기별:")
    show = per_match[['opponent_kr', 'n', 'opp_visible', 'vis_wide', 'def_line',
                      'raw5', 'raw_center', 'adj5', 'adj_center']]
    print(show.round(3).to_string(index=False))
    print(f"  32팀 평균:  opp_visible {avg32['opp_visible']:.2f}  "
          f"vis_wide {avg32['vis_wide']:.3f}  raw5(채널) {avg32['raw5']:.3f}  "
          f"raw_center {avg32['raw_center']:.3f}")

    print("\n처리 방식별 한국 순위 (채널 / 중앙 / 오프사이드 위치, 낮을수록 1위):")
    for label, (r5, rc, rb) in treatments.items():
        print(f"  {label:>16s}:  채널 {r5:>2d}위   중앙 {rc:>2d}위   오프사이드 위치 {rb:>2d}위")

    print("\n관측 조건이 지표를 미는 방향 (상황 단위 상관):")
    print(f"  전체 n_opp_visible  vs 채널 {corr_all[0]:+.3f} / 중앙 {corr_all[1]:+.3f} / 오프사이드 {corr_all[2]:+.3f}")
    print(f"  한국 n_opp_visible  vs 채널 {corr_kor[0]:+.3f} / 중앙 {corr_kor[1]:+.3f} / 오프사이드 {corr_kor[2]:+.3f}")
    print(f"  전체 사이드 가시율  vs 채널 {corr_wide[0]:+.3f} / 중앙 {corr_wide[1]:+.3f} / 오프사이드 {corr_wide[2]:+.3f}")
    print("  -> 상대가 적게 보일수록 채널·중앙 카운트는 줄고 오프사이드 위치는 는다.")

    kor_row = tm.loc['South Korea']
    for label, raw_col, adj_col in [('채널', 'raw5', 'adj5'), ('중앙', 'rawc', 'adjc'),
                                    ('오프사이드 위치', 'rawb', 'adjb')]:
        print(f"\n한국 {label}: 원시 {rank_low(tm[raw_col]):>2d}위 (값 {kor_row[raw_col]:.3f}, "
              f"32팀 중앙값 {tm[raw_col].median():.3f})")
        print(f"{'':>{len(label) + 4}s}보정 {rank_low(tm[adj_col]):>2d}위 (값 {kor_row[adj_col]:+.3f}, "
              f"32팀 중앙값 {tm[adj_col].median():+.3f})")

    # ===== CSV =====
    csv = per_match.copy()
    csv['team'] = 'South Korea'
    csv.round(4).to_csv(OUT / 'korea_contrast.csv', index=False, encoding='utf-8-sig')
    treat_df = pd.DataFrame(
        [(k, v[0], v[1], v[2]) for k, v in treatments.items()],
        columns=['treatment', 'rank_channel_5m', 'rank_center_5m', 'rank_offside_position'])
    treat_df.to_csv(OUT / 'korea_contrast_ranks.csv', index=False, encoding='utf-8-sig')
    print(f"\n저장: {OUT / 'korea_contrast.csv'}, {OUT / 'korea_contrast_ranks.csv'}")

    _write_notes(tm, per_match, treatments, avg32, corr_all, corr_kor)
    print(f"저장: {OUT / 'korea_contrast_notes.md'}")

    _ensure_korean_font()
    _fig_contrast(tm)
    _fig_observation(tm, per_match, treatments, avg32)
    _fig_blog_contrast(tm)
    print("그림 2개 저장 완료")


def _write_notes(tm, per_match, treatments, avg32, corr_all, corr_kor) -> None:
    """질문 4 관찰 메모를 계산값으로 생성한다(손으로 고치지 말 것)."""
    kor = tm.loc['South Korea']
    nxt = tm.sort_values('opp_visible').iloc[1]

    lines = [
        "# 채널 vs 중앙 관찰 메모 (질문 4)",
        "",
        "`03_korea_contrast.py`가 실행 때마다 새로 쓰는 파일이다. 손으로 고치지 말 것.",
        "",
        "## 묻는 것",
        "",
        "같은 \"라인 앞 5m 온사이드\" 선수를 레인으로 갈라, 한 팀이 **채널**(컷백을 올리러 "
        "파고드는 자리)과 **중앙**(컷백을 받으러 서는 자리) 중 어디에 사람을 두는지 본다. "
        "재는 것은 \"한국이 침투가 적은 팀인지\"가 아니라 한국의 침투가 어땠는지다.",
        "",
        "## 관측 조건",
        "",
        f"- 한국은 32팀 중 상대가 가장 적게 관측된 팀이다: 상황당 {kor['opp_visible']:.2f}명 "
        f"(32팀 평균 {avg32['opp_visible']:.2f}명). 두 번째로 적은 "
        f"{nxt['team_kr']}({nxt['opp_visible']:.2f}명)와도 "
        f"{nxt['opp_visible'] - kor['opp_visible']:.2f}명 차다.",
        "",
        "### 한국 경기별",
        "",
        "| 상대 | 상황 수 | 관측 상대 | 사이드 가시율 | 추정 라인 x | 채널 원시 | 중앙 원시 | 채널 보정 | 중앙 보정 |",
        "| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for _, r in per_match.iterrows():
        lines.append(
            f"| {r['opponent_kr']} | {int(r['n'])} | {r['opp_visible']:.2f} | "
            f"{r['vis_wide']:.3f} | {r['def_line']:.1f} | {r['raw5']:.3f} | "
            f"{r['raw_center']:.3f} | {r['adj5']:+.3f} | {r['adj_center']:+.3f} |")
    lines += [
        f"| **32팀 평균** | - | {avg32['opp_visible']:.2f} | {avg32['vis_wide']:.3f} | - | "
        f"{avg32['raw5']:.3f} | {avg32['raw_center']:.3f} | - | - |",
        "",
        "## 처리 방식별 한국 순위",
        "",
        "| 처리 | 채널 5m | 중앙 5m | 오프사이드 위치 |",
        "| :--- | ---: | ---: | ---: |",
    ]
    for label, (r5, rc, rb) in treatments.items():
        lines.append(f"| {label} | {r5}위 | {rc}위 | {rb}위 |")
    lines += [
        "",
        "(순위는 낮을수록 지표가 작음, 1-32)",
        "",
        f"- 관측 조건이 지표를 미는 방향(상황 단위 상관): 상대가 적게 보일수록 채널"
        f"({corr_all[0]:+.3f})과 중앙({corr_all[1]:+.3f})은 줄고 오프사이드 위치는 "
        f"는다({corr_all[2]:+.3f}). 한국만 보면 각각 {corr_kor[0]:+.3f} / "
        f"{corr_kor[1]:+.3f} / {corr_kor[2]:+.3f}.",
        "- 필터는 편향을 덜 걷어낸다. `vis_launch` 필터는 *추정된* 라인 주변만 보므로 "
        "추정 자체가 틀린 경우를 통과시킨다.",
        "",
        "## 보정 후 한국",
        "",
    ]
    for label, raw_col, adj_col in [('채널 5m', 'raw5', 'adj5'), ('중앙 5m', 'rawc', 'adjc'),
                                    ('오프사이드 위치', 'rawb', 'adjb')]:
        lines.append(
            f"- {label}: 원시 {rank_low(tm[raw_col])}위(값 {kor[raw_col]:.3f}, "
            f"중앙값 {tm[raw_col].median():.3f}) -> 보정 {rank_low(tm[adj_col])}위"
            f"(값 {kor[adj_col]:+.3f}, 중앙값 {tm[adj_col].median():+.3f})")
    lines += [
        "",
        "## 산출물",
        "",
        "- `korea_contrast.csv` - 한국 경기별 표",
        "- `korea_contrast_ranks.csv` - 처리 방식별 순위",
        "- `fig_korea_contrast.png` - 채널 x 중앙 산점도 (원시 / 보정)",
        "- `fig_korea_observation.png` - 관측 조건 메커니즘 3패널",
        "- `blog_korea_contrast.png` - 블로그용 채널 x 중앙 (최종값만)",
    ]
    (OUT / 'korea_contrast_notes.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


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
    _panel(axes[0], tm, 'raw5', 'rawc',
           '채널 침투 선택지 (사이드+하프스페이스, 원시)', '중앙 (골에어리어 폭, 원시)',
           'A. 원시값 - 오른쪽 아래일수록 컷백을 올리러 가는 팀, 왼쪽 위일수록 받으러 서는 팀')
    _panel(axes[1], tm, 'adj5', 'adjc',
           '채널 침투 선택지 (관측 조건 보정)', '중앙 (관측 조건 보정)',
           'B. 보정 후 - 관측 조건을 걷어내도 두 축이 갈라지는가')
    handles = [
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=KOR, markersize=9, label='한국'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=ADV_C, markersize=9, label='16강 진출'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=OUT_C, markersize=9, label='조별 탈락'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=3, frameon=False,
               labelcolor=FG, fontsize=9, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle('채널 x 중앙 - 같은 라인 앞 5m를 어디에 서서 기다렸나',
                 color=FG, fontsize=13, fontweight='bold', y=0.99)
    fig.text(0.5, 0.935,
             '점선 = 32팀 중앙값. 두 축 모두 "라인 앞 5m, 온사이드, 공보다 앞" 조건은 같고 레인만 다르다.',
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
    nxt = d.iloc[1]
    gap = nxt['opp_visible'] - d.iloc[0]['opp_visible']
    ax1.set_title('한국은 32팀 중 상대가 가장 적게 잡힌 팀\n'
                  f"(다음으로 적은 {nxt['team_kr']}와 {gap:.1f}명 차)",
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
    ax2.set_title('한국 세 경기의 상대 관측 수 (32팀 평균과 비교)',
                  color=FG, fontsize=10.5, pad=8)
    _style(ax2)

    # (3) 처리 방식별 한국 순위 - 그룹 수평 막대
    labels = list(treatments.keys())
    yv = np.arange(len(labels))
    pen = np.array([treatments[l][0] for l in labels])
    off = np.array([treatments[l][1] for l in labels])
    h = 0.36
    ax3.barh(yv + h / 2, pen, height=h, color=ADV_C, label='채널')
    ax3.barh(yv - h / 2, off, height=h, color='#e0a13c', label='중앙')
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
    ax3.set_title('처리 방식에 따라 한국 순위가 어떻게 움직이는가\n'
                  '(vis_launch 필터는 추정된 라인 주변만 봐서 편향을 덜 걷어낸다)',
                  color=FG, fontsize=10, pad=8)
    ax3.legend(loc='upper right', frameon=False, labelcolor=FG, fontsize=8)
    _style(ax3)

    fig.suptitle('질문 4 - 한국의 값을 읽기 전에 관측 조건부터 걷어낸다',
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


def _fig_blog_contrast(tm: pd.DataFrame) -> None:
    """블로그용: 채널 x 중앙 최종값(관측 조건 보정 후) 한 패널.

    블로그 원고는 보정 전후 비교를 쓰지 않으므로(`blog-essay-architect` 스킬)
    원시 패널을 빼고, 축 이름에서 분석 용어를 뺀다. 값은 32팀 평균 대비.
    """
    fig, ax = plt.subplots(figsize=(9.5, 7.6))
    fig.set_facecolor(BG)
    _panel(ax, tm, 'adj5', 'adjc',
           '사이드·하프스페이스에 선 선수 (평균 대비, 오른쪽일수록 많음)',
           '박스 중앙에 선 선수 (평균 대비, 위쪽일수록 많음)', '')
    handles = [
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=KOR, markersize=9, label='한국'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=ADV_C, markersize=9, label='16강 진출'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=OUT_C, markersize=9, label='조별 탈락'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=3, frameon=False,
               labelcolor=FG, fontsize=9, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle('수비 라인 바로 앞, 어디에 서서 기다렸나 (32팀)',
                 color=FG, fontsize=13, fontweight='bold', y=0.985)
    fig.text(0.5, 0.94, '점선 = 32팀 중간값. 2022 카타르 월드컵 조별리그, 패스가 나가는 순간 한 번당 인원',
             ha='center', color='#9aa0a6', fontsize=9.5)
    fig.tight_layout(rect=[0, 0.05, 1, 0.925])
    fig.savefig(OUT / 'blog_korea_contrast.png', dpi=140, facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    main()
