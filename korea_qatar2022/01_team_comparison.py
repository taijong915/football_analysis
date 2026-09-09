"""팀 비교 (분석 질문 1~2): 2022 카타르 월드컵 조별리그 32팀의 '침투 선택지'.

`data/raw/wc2022_360/situations.pkl`(2단계 산출물)을 받아, 조별리그 오픈플레이
전진 상황을 팀별로 합산해 침투 선택지 지표를 계산한다.

핵심은 **관측 조건 보정**이다. 프레임에 잡히는 상대 필드플레이어가 적을수록
추정 오프사이드 라인이 얕아지고 침투 선택지도 적게 잡힌다. 한국은 32팀 중
상대가 가장 적게 관측된 팀이라, 원시값을 그대로 순위로 읽으면 안 된다.
상황 단위로 지표를 관측 조건 변수에 회귀한 **잔차**를 팀 평균으로 삼아 보정한다.

산출물(`korea_qatar2022/processed/`):
- team_comparison.csv          - 32팀 지표 표 (원시 / 필터 / 보정 + 순위)
- fig_team_comparison_5m.png   - 보정 전/후 팀 분포, 한국 강조
- fig_rank_slope_5m.png        - 보정 전후 순위 변화(범프 차트)
- fig_advancement.png          - 16강 진출 여부별 지표 분포
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
from scipy import stats

from src.visualizer import _ensure_korean_font

SITUATIONS = Path('data/raw/wc2022_360/situations.pkl')
OUT = Path('korea_qatar2022/processed')
OUT.mkdir(parents=True, exist_ok=True)

# 회귀에 넣는 관측 조건 변수
COND_COLS = ['n_opp_visible', 'vis_launch', 'max_vis_x', 'band15']

# 2022 조별리그 통과(16강 진출) 16팀 - StatsBomb 팀명 기준
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


def ols_residuals(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """상수항을 포함한 최소제곱 회귀의 잔차."""
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta, beta


def avg_pairwise_corr(pivot: pd.DataFrame) -> float:
    """팀 x 경기(0/1/2) 표에서 경기쌍 간 팀 순위 상관의 평균 - 경기 간 재현성."""
    cols = list(pivot.columns)
    vals = [pivot[i].corr(pivot[j]) for a, i in enumerate(cols) for j in cols[a + 1:]]
    return float(np.mean(vals))


def main() -> None:
    s = pd.read_pickle(SITUATIONS)

    # 대상: 조별리그 + 오픈플레이(세트피스 제외). 정의상 '오픈플레이 패스'만 센다.
    g = s[(s['stage'] == 'Group Stage') & (~s['setpiece'])].copy()
    g['max_vis_x'] = g['def_line'] + g['vis_depth']

    print(f"조별리그 오픈플레이 전진 상황: {len(g)}건, {g['team'].nunique()}팀")
    print(f"관측 조건 변수 결측: {g[COND_COLS].isna().any(axis=1).sum()}건\n")

    # ===== 관측 조건 보정: 상황 단위 회귀 잔차 =====
    Xc = g[COND_COLS].to_numpy(float)
    for src_col, res_col in [('n_launch5', 'resid5'), ('n_launch', 'resid10'), ('n_beyond', 'residb')]:
        resid, beta = ols_residuals(Xc, g[src_col].to_numpy(float))
        g[res_col] = resid
        var = np.var(g[src_col])
        r2 = 1 - np.var(resid) / var
        print(f"  {src_col:>10s}  R^2={r2:.3f}  "
              f"beta[const,{','.join(COND_COLS)}]={np.round(beta, 4)}")
    print()

    # ===== 팀별 집계 =====
    tm = g.groupby('team').agg(
        n_situations=('n_launch5', 'size'),
        raw5=('n_launch5', 'mean'),
        raw10=('n_launch', 'mean'),
        rawb=('n_beyond', 'mean'),
        adj5=('resid5', 'mean'),
        adj10=('resid10', 'mean'),
        adjb=('residb', 'mean'),
        opp_visible=('n_opp_visible', 'mean'),
        vis_launch=('vis_launch', 'mean'),
    )

    # 필터 버전: 상대가 8명 이상 관측된 상황만
    gf = g[g['n_opp_visible'] >= 8]
    tm['filt5'] = gf.groupby('team')['n_launch5'].mean()
    tm['filt10'] = gf.groupby('team')['n_launch'].mean()
    tm['n_filtered'] = gf.groupby('team').size()

    tm['advanced'] = [t in ADVANCED for t in tm.index]
    tm['team_kr'] = [TEAM_KR.get(t, t) for t in tm.index]

    # 순위 (1 = 가장 낮음, 침투 선택지가 가장 적은 팀)
    for col in ['raw5', 'raw10', 'rawb', 'adj5', 'adj10', 'adjb', 'filt5', 'filt10']:
        tm[col + '_rank'] = tm[col].rank(method='min').astype(int)

    tm = tm.sort_values('adj5')

    # ===== 진단 수치 =====
    n_teams = len(tm)
    rho_raw_adj = stats.spearmanr(tm['raw5'], tm['adj5']).correlation
    moved5 = (tm['raw5_rank'] - tm['adj5_rank']).abs()
    n_moved5 = int((moved5 >= 5).sum())

    corr = {}
    for col in ['raw5', 'adj5', 'raw10', 'adj10', 'rawb', 'adjb', 'filt5']:
        corr[col] = np.corrcoef(tm[col], tm['advanced'].astype(float))[0, 1]

    # 경기 간 재현성
    per_match = (g.groupby(['team', 'match_id'])
                 .agg(m5=('n_launch5', 'mean'), a5=('resid5', 'mean'))
                 .reset_index())
    per_match['slot'] = per_match.groupby('team').cumcount()
    rep_raw5 = avg_pairwise_corr(per_match.pivot(index='team', columns='slot', values='m5'))
    rep_adj5 = avg_pairwise_corr(per_match.pivot(index='team', columns='slot', values='a5'))

    kor = tm.loc['South Korea']
    print("=" * 70)
    print("진단")
    print("=" * 70)
    print(f"보정 전/후 순위 상관 (Spearman)         : {rho_raw_adj:+.3f}")
    print(f"보정으로 5계단 이상 이동한 팀           : {n_moved5} / {n_teams}")
    print(f"경기 간 재현성  raw5 {rep_raw5:+.3f} -> adj5 {rep_adj5:+.3f}")
    print(f"16강 진출 상관  raw5 {corr['raw5']:+.3f} -> adj5 {corr['adj5']:+.3f}")
    print(f"               raw10 {corr['raw10']:+.3f} -> adj10 {corr['adj10']:+.3f}")
    print(f"               rawb {corr['rawb']:+.3f} -> adjb {corr['adjb']:+.3f}  (오프사이드 위치, 부호 반대)")
    print(f"               filt5(상대>=8) {corr['filt5']:+.3f}")
    print()
    print("한국 순위 (낮은 쪽 = 1, 침투 선택지가 적음):")
    print(f"  침투 선택지 5m : {int(kor['raw5_rank'])}위  ->  보정 {int(kor['adj5_rank'])}위")
    print(f"  침투 선택지 10m: {int(kor['raw10_rank'])}위  ->  보정 {int(kor['adj10_rank'])}위")
    print(f"  오프사이드 위치: {int(kor['rawb_rank'])}위  ->  보정 {int(kor['adjb_rank'])}위")
    print(f"  필터(상대>=8) 5m: {int(kor['filt5_rank'])}위")
    print(f"  상대 관측 평균  : {kor['opp_visible']:.2f}명  (최소. 32팀 평균 "
          f"{tm['opp_visible'].mean():.2f}명[팀 평균의 평균] / {g['n_opp_visible'].mean():.2f}명[상황 단위])")
    print()

    top_adj = tm.sort_values('adj5', ascending=False).head(5)['team_kr'].tolist()
    bot_adj = tm.sort_values('adj5').head(5)['team_kr'].tolist()
    print(f"보정 후 상위 5: {', '.join(top_adj)}")
    print(f"보정 후 하위 5: {', '.join(bot_adj)}")

    # ===== CSV 저장 =====
    cols_out = ['team_kr', 'advanced', 'n_situations', 'n_filtered',
                'raw5', 'filt5', 'adj5', 'raw10', 'filt10', 'adj10', 'rawb', 'adjb',
                'opp_visible', 'vis_launch',
                'raw5_rank', 'filt5_rank', 'adj5_rank',
                'raw10_rank', 'adj10_rank', 'rawb_rank', 'adjb_rank']
    out = tm[cols_out].copy()
    out.insert(0, 'team', out.index)
    out.round(4).to_csv(OUT / 'team_comparison.csv', index=False, encoding='utf-8-sig')
    print(f"\n저장: {OUT / 'team_comparison.csv'}")

    # ===== 그림 =====
    _ensure_korean_font()
    _fig_distribution(tm)
    _fig_rank_slope(tm)
    _fig_advancement(tm)
    print("그림 3개 저장 완료")


# ---------------------------------------------------------------------------
# 그림
# ---------------------------------------------------------------------------
BG = '#15181c'
FG = '#e8e8e8'
KOR = '#ff4b4b'
ADV_C = '#00c2a8'
OUT_C = '#6b7280'


def _style(ax):
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_color('#3a3f46')
    ax.tick_params(colors=FG, labelsize=8)
    ax.xaxis.label.set_color(FG)
    ax.yaxis.label.set_color(FG)


def _fig_distribution(tm: pd.DataFrame) -> None:
    """보정 전(raw5) / 후(adj5) 팀 분포를 나란히. 한국 강조."""
    fig, axes = plt.subplots(1, 2, figsize=(13, 9))
    fig.set_facecolor(BG)

    for ax, col, title, ref in [
        (axes[0], 'raw5', '보정 전: 상황당 침투 선택지 (5m, 원시값)', None),
        (axes[1], 'adj5', '보정 후: 관측 조건 회귀 잔차 (5m)', 0.0),
    ]:
        d = tm.sort_values(col)
        y = np.arange(len(d))
        colors = [KOR if t == 'South Korea'
                  else (ADV_C if adv else OUT_C)
                  for t, adv in zip(d.index, d['advanced'])]
        ax.hlines(y, ref if ref is not None else d[col].min(), d[col], color=colors, lw=2, alpha=0.6)
        ax.scatter(d[col], y, c=colors, s=34, zorder=3)
        ax.set_yticks(y)
        ax.set_yticklabels(d['team_kr'], fontsize=8)
        for tick, t in zip(ax.get_yticklabels(), d.index):
            if t == 'South Korea':
                tick.set_color(KOR)
                tick.set_fontweight('bold')
        if ref is not None:
            ax.axvline(ref, color='#3a3f46', lw=1, ls='--')
        ax.set_title(title, color=FG, fontsize=11, pad=10)
        ax.set_ylim(-1, len(d))
        _style(ax)

    handles = [
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=KOR, markersize=8, label='한국'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=ADV_C, markersize=8, label='16강 진출'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=OUT_C, markersize=8, label='조별 탈락'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=3, frameon=False,
               labelcolor=FG, fontsize=9, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle('2022 카타르 월드컵 조별리그 - 팀별 침투 선택지 (32팀)',
                 color=FG, fontsize=14, fontweight='bold', y=0.98)
    fig.text(0.5, 0.925,
             '원시값에서 하위 3위였던 한국이 관측 조건을 보정하면 중위권으로 이동한다',
             ha='center', color='#9aa0a6', fontsize=9.5)
    fig.tight_layout(rect=[0, 0.05, 1, 0.92])
    fig.savefig(OUT / 'fig_team_comparison_5m.png', dpi=140, facecolor=BG)
    plt.close(fig)


def _fig_rank_slope(tm: pd.DataFrame) -> None:
    """보정 전 순위 -> 보정 후 순위 범프 차트."""
    d = tm.copy()
    n = len(d)
    fig, ax = plt.subplots(figsize=(8, 11))
    fig.set_facecolor(BG)
    ax.set_facecolor(BG)

    for t, row in d.iterrows():
        r0, r1 = row['raw5_rank'], row['adj5_rank']
        move = abs(r0 - r1)
        if t == 'South Korea':
            c, lw, a = KOR, 2.6, 1.0
        elif move >= 5:
            c, lw, a = '#e0a13c', 1.8, 0.9
        else:
            c, lw, a = '#4b5563', 1.0, 0.5
        ax.plot([0, 1], [r0, r1], color=c, lw=lw, alpha=a, zorder=3 if move >= 5 else 1)
        ax.scatter([0, 1], [r0, r1], color=c, s=22, alpha=a, zorder=4)
        label = f"{row['team_kr']}"
        ax.text(-0.03, r0, label, ha='right', va='center', fontsize=7.5,
                color=KOR if t == 'South Korea' else FG,
                fontweight='bold' if t == 'South Korea' else 'normal')
        ax.text(1.03, r1, label, ha='left', va='center', fontsize=7.5,
                color=KOR if t == 'South Korea' else FG,
                fontweight='bold' if t == 'South Korea' else 'normal')

    ax.set_xlim(-0.35, 1.35)
    ax.set_ylim(n + 1, 0)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(['보정 전\n(원시 침투 선택지 5m)', '보정 후\n(관측 조건 잔차)'], color=FG, fontsize=9)
    ax.set_yticks([1, 5, 10, 15, 20, 25, 30, 32])
    ax.tick_params(colors=FG, labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_ylabel('순위 (1 = 침투 선택지 최소)', color=FG, fontsize=9)
    ax.set_title('관측 조건 보정에 따른 팀 순위 변화\n한국(빨강)은 3위 -> 18위, 12개 팀이 5계단 이상 이동',
                 color=FG, fontsize=12, fontweight='bold', pad=16)
    fig.tight_layout()
    fig.savefig(OUT / 'fig_rank_slope_5m.png', dpi=140, facecolor=BG)
    plt.close(fig)


def _fig_advancement(tm: pd.DataFrame) -> None:
    """16강 진출 여부별 지표 분포 - 보정 후에도 관계가 남는지."""
    metrics = [('raw5', '침투 선택지 5m (원시)'), ('adj5', '침투 선택지 5m (보정)'),
               ('raw10', '침투 선택지 10m (원시)'), ('adj10', '침투 선택지 10m (보정)')]
    fig, axes = plt.subplots(1, 4, figsize=(14, 5.5), sharey=False)
    fig.set_facecolor(BG)
    rng = np.random.default_rng(0)

    for ax, (col, title) in zip(axes, metrics):
        for gi, (adv, label, c) in enumerate([(False, '조별 탈락', OUT_C), (True, '16강 진출', ADV_C)]):
            vals = tm.loc[tm['advanced'] == adv, col]
            x = gi + rng.uniform(-0.12, 0.12, len(vals))
            ax.scatter(x, vals, c=c, s=30, alpha=0.8, zorder=3)
            ax.hlines(vals.mean(), gi - 0.25, gi + 0.25, color=c, lw=2.5, zorder=4)
        kv = tm.loc['South Korea', col]
        kx = 1 if tm.loc['South Korea', 'advanced'] else 0
        ax.scatter([kx], [kv], facecolors='none', edgecolors=KOR, s=150, lw=2, zorder=5)
        r = np.corrcoef(tm[col], tm['advanced'].astype(float))[0, 1]
        ax.set_title(f"{title}\n진출상관 r={r:+.2f}", color=FG, fontsize=9.5, pad=8)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['탈락', '진출'], color=FG, fontsize=9)
        _style(ax)

    fig.suptitle('16강 진출 여부별 침투 선택지 분포 (빨간 원 = 한국)',
                 color=FG, fontsize=13, fontweight='bold', y=1.0)
    fig.text(0.5, 0.9, '보정 후에도 진출 팀의 침투 선택지가 더 많다 (상관은 약간 줄어듦)',
             ha='center', color='#9aa0a6', fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(OUT / 'fig_advancement.png', dpi=140, facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    main()
