"""브라질전 비교 (분석 질문 5): 한국의 16강 브라질전(4:1 패)은
조별리그 세 경기와 실제로 달랐는가.

주의(PLAN "한계"): 16강 브라질전은 기준선(조별리그) 밖의 단일 사례다. 재현성
근거가 없고, 무엇보다 **가시율이 다르다** - 브라질전은 한국 네 경기 중
유일하게 관측 조건이 32팀 평균을 넘는다. 따라서 원시값 절대 비교는 하지 않고,
가시율을 항상 함께 표기하며, 관측 조건 보정값으로만 방향을 읽는다.

산출물(`korea_qatar2022/processed/`):
- brazil_comparison.csv       - 한국 4경기 지표 표 (가시율 포함)
- fig_brazil_comparison.png   - 원시 vs 보정, 가시율을 함께 표기
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
BRAZIL_MATCH = 3869253
OPP_KR = {'Portugal': '포르투갈', 'Uruguay': '우루과이', 'Ghana': '가나', 'Brazil': '브라질'}


def ols_beta(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    A = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return beta


def main() -> None:
    s = pd.read_pickle(CACHE / 'situations.pkl')

    # 회귀 계수는 조별리그 32팀 오픈플레이로 적합 (질문 1~2와 동일)
    g = s[(s['stage'] == 'Group Stage') & (~s['setpiece'])].copy()
    g['max_vis_x'] = g['def_line'] + g['vis_depth']
    Xg = g[COND_COLS].to_numpy(float)
    betas = {c: ols_beta(Xg, g[c].to_numpy(float))
             for c in ['n_launch5', 'n_launch', 'n_beyond']}

    avg32 = {
        'n_opp_visible': g['n_opp_visible'].mean(),
        'band15': g['band15'].mean(),
        'vis_launch': g['vis_launch'].mean(),
        'def_line': g['def_line'].mean(),
        'n_launch5': g['n_launch5'].mean(),
        'n_launch': g['n_launch'].mean(),
        'n_beyond': g['n_beyond'].mean(),
    }

    # 한국 4경기 (오픈플레이)
    k = s[(s['team'] == 'South Korea') & (~s['setpiece'])].copy()
    k['max_vis_x'] = k['def_line'] + k['vis_depth']
    A = np.column_stack([np.ones(len(k)), k[COND_COLS].to_numpy(float)])
    for src, dst in [('n_launch5', 'adj5'), ('n_launch', 'adj10'), ('n_beyond', 'adjb')]:
        k[dst] = k[src].to_numpy(float) - A @ betas[src]

    k['is_brazil'] = k['match_id'] == BRAZIL_MATCH

    agg = k.groupby(['match_id', 'stage', 'opponent']).agg(
        n=('n_launch5', 'size'),
        n_opp_visible=('n_opp_visible', 'mean'),
        band15=('band15', 'mean'),
        vis_launch=('vis_launch', 'mean'),
        def_line=('def_line', 'mean'),
        raw5=('n_launch5', 'mean'), raw10=('n_launch', 'mean'), rawb=('n_beyond', 'mean'),
        adj5=('adj5', 'mean'), adj10=('adj10', 'mean'), adjb=('adjb', 'mean'),
        pre_goal=('pre_first_goal', 'sum'),
    ).reset_index()
    agg['opp_kr'] = agg['opponent'].map(OPP_KR).fillna(agg['opponent'])
    agg = agg.sort_values('match_id').reset_index(drop=True)

    # 조별 3경기 합산 한 줄
    kg = k[k['stage'] == 'Group Stage']
    kb = k[k['is_brazil']]

    print("=" * 74)
    print("질문 5: 한국의 16강 브라질전은 조별리그 세 경기와 달랐는가")
    print("=" * 74)
    print("\n한국 4경기 (오픈플레이 전진 상황):")
    cols = ['opp_kr', 'n', 'n_opp_visible', 'band15', 'vis_launch', 'def_line',
            'raw5', 'raw10', 'rawb', 'adj5', 'adj10', 'adjb', 'pre_goal']
    print(agg[cols].round(3).to_string(index=False))
    print(f"\n  조별리그 32팀 평균: n_opp_visible {avg32['n_opp_visible']:.2f}  "
          f"band15 {avg32['band15']:.3f}  vis_launch {avg32['vis_launch']:.3f}  "
          f"def_line {avg32['def_line']:.1f}")
    print(f"                     raw5 {avg32['n_launch5']:.3f}  raw10 {avg32['n_launch']:.3f}  "
          f"rawb {avg32['n_beyond']:.3f}")

    print("\n조별 3경기 합산  vs  브라질전:")
    print(f"  관측 상대     : {kg['n_opp_visible'].mean():.2f}명  ->  {kb['n_opp_visible'].mean():.2f}명  "
          f"(브라질전이 한국 유일하게 32팀 평균 초과)")
    print(f"  band15(라인뒤): {kg['band15'].mean():.3f}  ->  {kb['band15'].mean():.3f}")
    print(f"  원시 침투선택지 5m : {kg['n_launch5'].mean():.3f}  ->  {kb['n_launch5'].mean():.3f}  (상승)")
    print(f"  원시 침투선택지 10m: {kg['n_launch'].mean():.3f}  ->  {kb['n_launch'].mean():.3f}  (상승)")
    print(f"  보정 침투선택지 5m : {kg['adj5'].mean():+.3f}  ->  {kb['adj5'].mean():+.3f}  (오히려 하락)")
    print(f"  보정 침투선택지 10m: {kg['adj10'].mean():+.3f}  ->  {kb['adj10'].mean():+.3f}  (비슷)")
    print(f"  보정 오프사이드위치: {kg['adjb'].mean():+.3f}  ->  {kb['adjb'].mean():+.3f}")

    brz_all = k[k['is_brazil']]
    # 브라질 득점: 7분(비니시우스) 13분(네이마르 PK) 29분(히샬리송) 36분(파케타)
    n = len(brz_all)
    print(f"\n  경기 상태: 브라질전 전진 상황 {n}건 중 선제 실점 이전은 "
          f"{int(brz_all['pre_first_goal'].sum())}건뿐 ({100 * brz_all['pre_first_goal'].mean():.0f}%).")
    print(f"             두 골차 이후(13분~) {int((brz_all['minute'] >= 13).sum())}건 "
          f"({100 * (brz_all['minute'] >= 13).mean():.0f}%), "
          f"네 골차 이후(36분~) {int((brz_all['minute'] >= 36).sum())}건 "
          f"({100 * (brz_all['minute'] >= 36).mean():.0f}%) - 표본 대부분이 큰 점수차 추격.")
    per = brz_all.groupby('period')['n_launch5'].agg(['size', 'mean']).round(3)
    print(f"             전/후반 원시 5m: {per.loc[1, 'mean']} ({int(per.loc[1, 'size'])}건) / "
          f"{per.loc[2, 'mean']} ({int(per.loc[2, 'size'])}건) - 큰 차이 없음.")

    print("\n해석:")
    print("  원시값은 브라질전에서 침투 선택지가 늘어난 것처럼 보이지만, 그 상승은")
    print("  브라질전이 한국 네 경기 중 유일하게 카메라가 상대를 충분히 담은 경기라는")
    print("  사실로 대부분 설명된다. 관측 조건을 보정하면 브라질전의 침투 선택지 밀도는")
    print("  조별리그 수준이거나 오히려 약간 낮다. 게다가 표본 대부분이 큰 점수차 추격 상황이다.")
    print("  => 브라질전이 전술적으로 달랐다는 근거는 없다. 단일 경기라 방증으로만 쓴다.")

    out = agg[['opp_kr', 'stage', 'n', 'n_opp_visible', 'band15', 'vis_launch',
               'def_line', 'raw5', 'raw10', 'rawb', 'adj5', 'adj10', 'adjb', 'pre_goal']].copy()
    out.round(4).to_csv(OUT / 'brazil_comparison.csv', index=False, encoding='utf-8-sig')
    print(f"\n저장: {OUT / 'brazil_comparison.csv'}")

    _ensure_korean_font()
    _fig(agg, avg32)
    print("그림 저장 완료")


# ---------------------------------------------------------------------------
BG = '#15181c'
FG = '#e8e8e8'
KOR = '#ff4b4b'
GRP = '#6b7280'
RAW_C = '#5b8def'
ADJ_C = '#00c2a8'


def _fig(agg: pd.DataFrame, avg32: dict) -> None:
    labels = ['vs ' + o for o in agg['opp_kr']]
    x = np.arange(len(agg))
    bar_colors = [KOR if b else GRP for b in (agg['opp_kr'] == '브라질')]

    fig, axes = plt.subplots(1, 3, figsize=(15.5, 5.8))
    fig.set_facecolor(BG)

    # (1) 관측 조건
    ax = axes[0]
    w = 0.38
    ax.bar(x - w / 2, agg['n_opp_visible'], w, color='#8b93a0', label='관측된 상대 (명)')
    ax.axhline(avg32['n_opp_visible'], color='#9aa0a6', lw=1, ls='--')
    ax.text(len(agg) - 0.5, avg32['n_opp_visible'] + 0.15,
            f"32팀 평균 {avg32['n_opp_visible']:.1f}", color='#9aa0a6', fontsize=7.5,
            ha='right', va='bottom')
    ax2 = ax.twinx()
    ax2.plot(x, agg['band15'], 'o-', color='#e0a13c', lw=1.8, ms=7, label='라인 뒤 가시율 (band15)')
    ax2.axhline(avg32['band15'], color='#e0a13c', lw=0.8, ls=':')
    ax2.set_ylim(0, 0.5)
    ax2.tick_params(colors='#e0a13c', labelsize=8)
    ax2.set_ylabel('라인 뒤 가시율', color='#e0a13c', fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=FG, fontsize=8.5)
    ax.set_ylabel('관측된 상대 필드플레이어 (명)', color=FG, fontsize=9)
    ax.set_ylim(0, 10)
    ax.set_title('관측 조건 - 브라질전만 한국 유일하게\n32팀 평균을 넘는다', color=FG, fontsize=10.5, pad=8)
    _style(ax)
    lines1, lab1 = ax.get_legend_handles_labels()
    lines2, lab2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, lab1 + lab2, loc='lower center', frameon=False,
              labelcolor=FG, fontsize=7.5)

    # (2) 원시 침투 선택지
    ax = axes[1]
    ax.bar(x - w / 2, agg['raw5'], w, color=RAW_C, label='5m')
    ax.bar(x + w / 2, agg['raw10'], w, color='#3a5fa0', label='10m')
    ax.axhline(avg32['n_launch5'], color=RAW_C, lw=0.9, ls=':')
    ax.axhline(avg32['n_launch'], color='#3a5fa0', lw=0.9, ls=':')
    ax.text(2.6, avg32['n_launch'], f' 32팀 평균 10m {avg32["n_launch"]:.2f}', color='#8ba3c9',
            fontsize=7, va='bottom')
    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=FG, fontsize=8.5)
    ax.set_ylabel('상황당 침투 선택지 (원시)', color=FG, fontsize=9)
    ax.set_title('원시값 - 브라질전이 높아 보인다\n(관측이 좋았을 뿐)', color=FG, fontsize=10.5, pad=8)
    ax.legend(loc='upper left', frameon=False, labelcolor=FG, fontsize=8)
    _style(ax)

    # (3) 보정 침투 선택지
    ax = axes[2]
    ax.bar(x - w / 2, agg['adj5'], w, color=ADJ_C, label='5m')
    ax.bar(x + w / 2, agg['adj10'], w, color='#0a7d6f', label='10m')
    ax.axhline(0, color='#3a3f46', lw=1)
    ax.set_xticks(x)
    ax.set_xticklabels(labels, color=FG, fontsize=8.5)
    ax.set_ylabel('침투 선택지 · 관측 조건 보정 잔차', color=FG, fontsize=9)
    ax.set_title('보정 후 - 브라질전은 조별리그 수준이거나\n오히려 약간 낮다', color=FG, fontsize=10.5, pad=8)
    ax.legend(loc='lower left', frameon=False, labelcolor=FG, fontsize=8)
    _style(ax)

    fig.suptitle('한국 4경기 - 브라질전(16강)이 조별리그와 달랐는가',
                 color=FG, fontsize=13.5, fontweight='bold', y=0.98)
    fig.text(0.5, 0.9,
             '원시 침투 선택지는 브라질전에서 올라가지만, 관측 조건을 보정하면 그 상승이 사라진다. '
             '표본 대부분이 큰 점수차 추격 상황이라 단일 경기 방증으로만 쓴다.',
             ha='center', color='#9aa0a6', fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.84])
    fig.savefig(OUT / 'fig_brazil_comparison.png', dpi=140, facecolor=BG)
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
