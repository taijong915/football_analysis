"""팀 비교 (분석 질문 1~2): 2022 카타르 월드컵 조별리그 32팀의 '채널 침투 선택지'.

`data/raw/wc2022_360/situations_lanes.pkl`(2단계 산출물)을 받아, 조별리그
오픈플레이 전진 상황(x 30-110)을 팀별로 합산해 지표를 계산한다.

지표는 **채널 침투 선택지**다 - 패스 시점에 온사이드이면서 상대 최종 수비 라인
앞 5m 안이고, 공보다 앞이며, **사이드(y<18, y>62) 또는 하프스페이스(18~30,
50~62)** 에 있는 아군 수. 중앙(30~50)은 버리지 않고 대조군으로 함께 센다.
컷백을 올리러 채널로 파고드는 움직임과 컷백을 받으러 중앙에 서는 움직임은
다르기 때문이다(`PLAN.md`의 "2차 확장" 절).

핵심은 **관측 조건 보정**이다. 프레임에 잡히는 상대 필드플레이어가 적을수록
추정 오프사이드 라인이 얕아지고 침투 선택지도 적게 잡힌다. 한국은 32팀 중
상대가 가장 적게 관측된 팀이라, 원시값을 그대로 순위로 읽으면 안 된다.
상황 단위로 지표를 관측 조건 변수에 회귀한 **잔차**를 팀 평균으로 삼아 보정한다.
공변량에는 레인별 가시율을 쓴다 - 채널이 세는 사이드는 가시율 0.690으로 중앙
0.931보다 훨씬 낮아, 전 폭 가시율 하나로는 이 차이가 가려진다.

산출물(`korea_qatar2022/processed/`):
- team_comparison.csv          - 32팀 지표 표 (원시 / 필터 / 보정 + 순위)
- fig_team_comparison_5m.png   - 보정 전/후 팀 분포, 한국 강조
- fig_rank_slope_5m.png        - 보정 전후 순위 변화(범프 차트)
- fig_advancement.png          - 16강 진출 여부별 지표 분포 (채널 vs 중앙)
- blog_team_comparison.png     - 블로그용: 최종값(보정 후)만 그린 팀 분포, 분석 용어 없음
- blog_advancement.png         - 블로그용: 최종값만 그린 16강 진출별 분포 (채널 vs 중앙)
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

SITUATIONS = Path('data/raw/wc2022_360/situations_lanes.pkl')
OUT = Path('korea_qatar2022/processed')
OUT.mkdir(parents=True, exist_ok=True)

# 회귀에 넣는 관측 조건 변수. 전 폭 `vis_launch` 대신 레인별 가시율 3개를 쓴다 -
# 셋을 넣은 세트들끼리는 팀 순위 상관이 1.0000이라 결과가 같고, `vis_launch`와
# `vis_launch_wide`/`_half`의 상관이 0.898/0.934라 같은 것을 두 번 넣게 된다.
# 가시율끼리 상관이 높아 개별 회귀계수는 해석하지 않는다 - 쓰는 것은 잔차뿐이다.
COND_COLS = ['n_opp_visible', 'max_vis_x', 'band15',
             'vis_launch_wide', 'vis_launch_half', 'vis_launch_center']

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

    # 대상: 조별리그 + 오픈플레이(세트피스 제외) + 채택 범위(x 30-110).
    # 정의상 '오픈플레이 패스'만 센다.
    g = s[(s['stage'] == 'Group Stage') & (~s['setpiece']) & (s['in_scope'])].copy()
    g['max_vis_x'] = g['def_line'] + g['vis_depth']

    print(f"조별리그 오픈플레이 전진 상황: {len(g)}건, {g['team'].nunique()}팀")
    # 추정 라인이 골라인에 닿은 상황(def_line >= 119.6)에서는 라인 뒤 밴드가
    # 성립하지 않아 band15가 비는데, x 상한을 110으로 넓히며 처음 생겼다.
    n_na = int(g[COND_COLS].isna().any(axis=1).sum())
    g = g.dropna(subset=COND_COLS)
    print(f"관측 조건 변수 결측 제외: {n_na}건 -> {len(g)}건\n")

    # ===== 관측 조건 보정: 상황 단위 회귀 잔차 =====
    Xc = g[COND_COLS].to_numpy(float)
    r2_by_metric = {}
    for src_col, res_col in [('n_channel5', 'resid5'), ('n_channel10', 'resid10'),
                             ('n_center5', 'residc'), ('n_beyond', 'residb')]:
        resid, beta = ols_residuals(Xc, g[src_col].to_numpy(float))
        g[res_col] = resid
        var = np.var(g[src_col])
        r2 = 1 - np.var(resid) / var
        r2_by_metric[src_col] = r2
        print(f"  {src_col:>10s}  R^2={r2:.3f}  "
              f"beta[const,{','.join(COND_COLS)}]={np.round(beta, 4)}")
    print()

    # ===== 팀별 집계 =====
    tm = g.groupby('team').agg(
        n_situations=('n_channel5', 'size'),
        raw5=('n_channel5', 'mean'),
        raw10=('n_channel10', 'mean'),
        rawc=('n_center5', 'mean'),
        rawb=('n_beyond', 'mean'),
        adj5=('resid5', 'mean'),
        adj10=('resid10', 'mean'),
        adjc=('residc', 'mean'),
        adjb=('residb', 'mean'),
        opp_visible=('n_opp_visible', 'mean'),
        vis_launch=('vis_launch', 'mean'),
        vis_wide=('vis_launch_wide', 'mean'),
        vis_center=('vis_launch_center', 'mean'),
    )

    # 필터 버전: 상대가 8명 이상 관측된 상황만
    gf = g[g['n_opp_visible'] >= 8]
    tm['filt5'] = gf.groupby('team')['n_channel5'].mean()
    tm['filt10'] = gf.groupby('team')['n_channel10'].mean()
    tm['n_filtered'] = gf.groupby('team').size()

    tm['advanced'] = [t in ADVANCED for t in tm.index]
    tm['team_kr'] = [TEAM_KR.get(t, t) for t in tm.index]

    # 순위 (1 = 가장 낮음, 침투 선택지가 가장 적은 팀)
    for col in ['raw5', 'raw10', 'rawc', 'rawb', 'adj5', 'adj10', 'adjc', 'adjb',
                'filt5', 'filt10']:
        tm[col + '_rank'] = tm[col].rank(method='min').astype(int)

    tm = tm.sort_values('adj5')

    # ===== 진단 수치 =====
    n_teams = len(tm)
    rho_raw_adj = stats.spearmanr(tm['raw5'], tm['adj5']).correlation
    moved5 = (tm['raw5_rank'] - tm['adj5_rank']).abs()
    n_moved5 = int((moved5 >= 5).sum())

    corr = {}
    for col in ['raw5', 'adj5', 'raw10', 'adj10', 'rawc', 'adjc', 'rawb', 'adjb', 'filt5']:
        corr[col] = np.corrcoef(tm[col], tm['advanced'].astype(float))[0, 1]

    # 경기 간 재현성
    per_match = (g.groupby(['team', 'match_id'])
                 .agg(m5=('n_channel5', 'mean'), a5=('resid5', 'mean'))
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
    print(f"               rawc {corr['rawc']:+.3f} -> adjc {corr['adjc']:+.3f}  (중앙 대조군, 보정하면 부호가 뒤집힌다)")
    print(f"               rawb {corr['rawb']:+.3f} -> adjb {corr['adjb']:+.3f}  (오프사이드 위치, 부호 반대)")
    print(f"               filt5(상대>=8) {corr['filt5']:+.3f}")
    print()
    print("한국 순위 (낮은 쪽 = 1, 침투 선택지가 적음):")
    print(f"  채널 침투 선택지 5m : {int(kor['raw5_rank'])}위  ->  보정 {int(kor['adj5_rank'])}위")
    print(f"  채널 침투 선택지 10m: {int(kor['raw10_rank'])}위  ->  보정 {int(kor['adj10_rank'])}위")
    print(f"  중앙 (대조군) 5m    : {int(kor['rawc_rank'])}위  ->  보정 {int(kor['adjc_rank'])}위")
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
                'raw5', 'filt5', 'adj5', 'raw10', 'filt10', 'adj10',
                'rawc', 'adjc', 'rawb', 'adjb',
                'opp_visible', 'vis_launch', 'vis_wide', 'vis_center',
                'raw5_rank', 'filt5_rank', 'adj5_rank',
                'raw10_rank', 'adj10_rank', 'rawc_rank', 'adjc_rank',
                'rawb_rank', 'adjb_rank']
    out = tm[cols_out].copy()
    out.insert(0, 'team', out.index)
    out.round(4).to_csv(OUT / 'team_comparison.csv', index=False, encoding='utf-8-sig')
    print(f"\n저장: {OUT / 'team_comparison.csv'}")

    # ===== 관찰 메모 =====
    # 손으로 쓰면 재실행 때 조용히 낡는다(2026-09-15 재실행에서 실제로 1차 정의
    # 수치가 남아 있었다). 스크립트가 계산값으로 다시 쓴다.
    _write_notes(g, tm, dict(r2=r2_by_metric, rho=rho_raw_adj, n_moved=n_moved5,
                             rep_raw=rep_raw5, rep_adj=rep_adj5, corr=corr,
                             n_filtered=len(gf)))
    print(f"저장: {OUT / 'team_comparison_notes.md'}")

    # ===== 그림 =====
    _ensure_korean_font()
    _fig_distribution(tm)
    _fig_rank_slope(tm)
    _fig_advancement(tm)
    _fig_blog_team(tm)
    _fig_blog_advancement(tm)
    print("그림 3개 저장 완료")


def _write_notes(g: pd.DataFrame, tm: pd.DataFrame, d: dict) -> None:
    """질문 1~2 관찰 메모를 계산값으로 생성한다."""
    n = g.groupby('team').size()
    kor = tm.loc['South Korea']
    top5 = tm.sort_values('adj5', ascending=False).head(5)['team_kr'].tolist()
    bot5 = tm.sort_values('adj5').head(5)['team_kr'].tolist()
    # 진출/탈락 그룹 평균과 진출 팀 안에서의 한국 위치 (보정 채널 5m)
    grp = tm.groupby('advanced')['adj5'].mean()
    adv = tm[tm['advanced']]
    kor_rank_adv = int((adv['adj5'] < kor['adj5']).sum()) + 1

    lines = [
        "# 팀 비교 관찰 메모 (질문 1~2)",
        "",
        "`01_team_comparison.py`가 실행 때마다 새로 쓰는 파일이다. 손으로 고치지 말 것 - "
        "종합 결론은 `RESULTS.md`에 있다.",
        "",
        "## 대상",
        "",
        f"- 2022 카타르 월드컵 조별리그 32팀, 오픈플레이 전진 상황(패스 시작 x 30-110, "
        f"세트피스 제외) {len(g):,}건",
        f"- 팀당 {n.min():,}-{n.max():,}건(중앙값 {int(n.median()):,}건)",
        "- 지표: 채널 침투 선택지 5m(`n_channel5`) 기준. 중앙 5m(`n_center5`)를 대조군으로, "
        "채널 10m(`n_channel10`)와 오프사이드 위치(`n_beyond`)를 함께 계산",
        "",
        "## 관측 조건 보정",
        "",
        f"상황 단위로 지표를 {', '.join('`' + c + '`' for c in COND_COLS)}에 회귀한 잔차를 "
        "팀 평균으로 삼았다. 전 폭 가시율 대신 레인별 가시율을 쓰는 이유는 채널이 세는 "
        "사이드가 세 레인 중 가장 안 보이기 때문이다(`PLAN.md`의 재적합 결과 절).",
        "",
        f"- 회귀 설명력은 크지 않다: R^2 = "
        + " / ".join(f"{v:.3f}({k})" for k, v in d['r2'].items()) + ".",
        f"- 필터(`n_opp_visible >= 8`)는 표본을 {len(g):,} -> {d['n_filtered']:,}건으로 "
        f"줄이면서도 진출 상관이 {d['corr']['raw5']:+.2f} -> {d['corr']['filt5']:+.2f}로 "
        "약해진다. 편향의 기울기를 없애지 못하므로 결론에는 쓰지 않는다.",
        "",
        "## 핵심 수치",
        "",
        "| | 보정 전 | 보정 후 |",
        "| :--- | ---: | ---: |",
        f"| 보정 전/후 팀 순위 상관 (Spearman) | | {d['rho']:+.2f} |",
        f"| 5계단 이상 이동한 팀 | | {d['n_moved']} / {len(tm)} |",
        f"| 경기 간 재현성 (경기쌍 평균 상관) | {d['rep_raw']:+.2f} | {d['rep_adj']:+.2f} |",
        f"| 16강 진출 상관 (채널 5m) | {d['corr']['raw5']:+.2f} | {d['corr']['adj5']:+.2f} |",
        f"| 16강 진출 상관 (채널 10m) | {d['corr']['raw10']:+.2f} | {d['corr']['adj10']:+.2f} |",
        f"| 16강 진출 상관 (중앙 5m, 대조군) | {d['corr']['rawc']:+.2f} | {d['corr']['adjc']:+.2f} |",
        f"| 오프사이드 위치 vs 진출 상관 | {d['corr']['rawb']:+.2f} | {d['corr']['adjb']:+.2f} |",
        "",
        f"- 보정 후 상위 5: {', '.join(top5)}",
        f"- 보정 후 하위 5: {', '.join(bot5)}",
        "- **중앙 대조군은 보정하면 진출과의 관계가 뒤집힌다.** 채널은 양의 상관을 유지하는데 "
        "중앙은 음으로 돌아선다 - 컷백을 받으러 중앙에 서 있는 인원이 많은 것은 좋은 신호가 아니다.",
        "",
        "## 한국",
        "",
        "| 지표 | 원시 순위 | 보정 순위 |",
        "| :--- | ---: | ---: |",
        f"| 채널 침투 선택지 5m | {int(kor['raw5_rank'])}위 | {int(kor['adj5_rank'])}위 |",
        f"| 채널 침투 선택지 10m | {int(kor['raw10_rank'])}위 | {int(kor['adj10_rank'])}위 |",
        f"| 중앙 5m (대조군) | {int(kor['rawc_rank'])}위 | {int(kor['adjc_rank'])}위 |",
        f"| 오프사이드 위치 (최초 정의) | {int(kor['rawb_rank'])}위 | {int(kor['adjb_rank'])}위 |",
        f"| 필터(상대 >= 8) 채널 5m | {int(kor['filt5_rank'])}위 | - |",
        "",
        "(순위는 낮을수록 지표가 작음. 1위 = 최소)",
        "",
        f"- 한국은 32팀 중 상대 필드플레이어가 가장 적게 관측된 팀이다: 상황당 평균 "
        f"{kor['opp_visible']:.2f}명(32팀 평균 {g['n_opp_visible'].mean():.2f}명, 상황 단위).",
        f"- 사이드 레인 가시율도 {kor['vis_wide']:.3f}로 32팀 중 최저다"
        f"(32팀 평균 {g['vis_launch_wide'].mean():.3f}). 채널 지표가 세는 구역이라 "
        "보정 폭이 큰 팀에 속한다.",
        f"- 보정 채널 5m에서 한국({kor['adj5']:+.3f})은 16강 진출 {len(adv)}팀 평균"
        f"({grp[True]:+.3f})보다 낮고 탈락 {len(tm) - len(adv)}팀 평균({grp[False]:+.3f})보다 "
        f"높다. 진출 팀 안에서는 아래에서 {kor_rank_adv}번째다.",
        "",
        "## 해석 시 유의 (PLAN \"한계\" 재확인)",
        "",
        "- 채널 침투 선택지는 상대 수비 라인 깊이·점유 볼륨과 얽혀 있어 \"침투 의지\"만 잰 값이 "
        "아니다. 질문 3의 2차원 표현에서 이 얽힘을 드러낸다.",
        f"- 3경기 팀 평균의 재현성이 높지 않다(보정 후 {d['rep_adj']:+.2f}). 개별 팀의 \"몇 위\"가 "
        "아니라 분포에서의 대략적 위치로만 서술한다.",
        "- 회귀 보정은 관측 조건과 지표의 관계가 선형이라고 가정한다. 잔차 자체가 팀 스타일 + "
        "남은 관측 잡음의 혼합이다.",
        "",
        "## 산출물",
        "",
        "- `team_comparison.csv` - 32팀 지표 표 (원시 / 필터 / 보정 + 순위 + 진출 여부)",
        "- `fig_team_comparison_5m.png` - 보정 전/후 팀 분포, 한국 강조",
        "- `fig_rank_slope_5m.png` - 보정 전후 순위 변화 범프 차트",
        "- `fig_advancement.png` - 16강 진출 여부별 분포 (채널 vs 중앙 x 원시/보정)",
        "- `blog_team_comparison.png` - 블로그용 팀 분포 (최종값만)",
        "- `blog_advancement.png` - 블로그용 16강 진출별 분포 (최종값만)",
    ]
    (OUT / 'team_comparison_notes.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')


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
        (axes[0], 'raw5', '보정 전: 상황당 채널 침투 선택지 (5m, 원시값)', None),
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
    fig.suptitle('2022 카타르 월드컵 조별리그 - 팀별 채널 침투 선택지 (32팀)',
                 color=FG, fontsize=14, fontweight='bold', y=0.98)
    kr_raw = int(tm.loc['South Korea', 'raw5_rank'])
    kr_adj = int(tm.loc['South Korea', 'adj5_rank'])
    fig.text(0.5, 0.925,
             f'사이드·하프스페이스만 센 값. 한국은 원시 {kr_raw}위에서 보정하면 {kr_adj}위가 된다',
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
    ax.set_xticklabels(['보정 전\n(원시 채널 침투 선택지 5m)', '보정 후\n(관측 조건 잔차)'], color=FG, fontsize=9)
    ax.set_yticks([1, 5, 10, 15, 20, 25, 30, 32])
    ax.tick_params(colors=FG, labelsize=8)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_ylabel('순위 (1 = 채널 침투 선택지 최소)', color=FG, fontsize=9)
    kr_raw = int(d.loc['South Korea', 'raw5_rank'])
    kr_adj = int(d.loc['South Korea', 'adj5_rank'])
    n_moved = int(((d['raw5_rank'] - d['adj5_rank']).abs() >= 5).sum())
    ax.set_title('관측 조건 보정에 따른 팀 순위 변화\n'
                 f'한국(빨강)은 {kr_raw}위 -> {kr_adj}위, {n_moved}개 팀이 5계단 이상 이동',
                 color=FG, fontsize=12, fontweight='bold', pad=16)
    fig.tight_layout()
    fig.savefig(OUT / 'fig_rank_slope_5m.png', dpi=140, facecolor=BG)
    plt.close(fig)


def _fig_advancement(tm: pd.DataFrame) -> None:
    """16강 진출 여부별 지표 분포 - 보정 후에도 관계가 남는지."""
    metrics = [('raw5', '채널 5m (원시)'), ('adj5', '채널 5m (보정)'),
               ('rawc', '중앙 5m (원시)'), ('adjc', '중앙 5m (보정)')]
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

    fig.suptitle('16강 진출 여부별 분포 - 채널 vs 중앙 (빨간 원 = 한국)',
                 color=FG, fontsize=13, fontweight='bold', y=1.0)
    fig.text(0.5, 0.9,
             '채널은 보정 후에도 진출 팀이 더 많지만, 중앙은 보정하면 관계의 방향이 뒤집힌다',
             ha='center', color='#9aa0a6', fontsize=9)
    fig.tight_layout(rect=[0, 0, 1, 0.88])
    fig.savefig(OUT / 'fig_advancement.png', dpi=140, facecolor=BG)
    plt.close(fig)


# --- 블로그용 그림 -----------------------------------------------------------
# 블로그 원고는 분석 과정(보정 전후 비교)을 쓰지 않으므로(`blog-essay-architect`
# 스킬), 최종값(관측 조건 보정 후)만 한 패널로 그리고 "원시/보정/잔차" 같은
# 분석 용어를 쓰지 않는다. 값은 32팀 평균 대비라 0이 평균이다.

def _fig_blog_team(tm: pd.DataFrame) -> None:
    """블로그용: 팀별 채널 침투 선택지(최종값) 한 패널, 한국 강조."""
    d = tm.sort_values('adj5')
    y = np.arange(len(d))
    colors = [KOR if t == 'South Korea' else (ADV_C if adv else OUT_C)
              for t, adv in zip(d.index, d['advanced'])]
    fig, ax = plt.subplots(figsize=(8, 10))
    fig.set_facecolor(BG)
    ax.hlines(y, 0.0, d['adj5'], color=colors, lw=2, alpha=0.6)
    ax.scatter(d['adj5'], y, c=colors, s=38, zorder=3)
    ax.axvline(0.0, color='#3a3f46', lw=1, ls='--')
    ax.set_yticks(y)
    ax.set_yticklabels(d['team_kr'], fontsize=8.5)
    for tick, t in zip(ax.get_yticklabels(), d.index):
        if t == 'South Korea':
            tick.set_color(KOR)
            tick.set_fontweight('bold')
    ax.set_ylim(-1, len(d))
    ax.set_xlabel('32팀 평균과의 차이 (0 = 평균, 오른쪽일수록 많음)', color=FG, fontsize=9.5)
    _style(ax)
    handles = [
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=KOR, markersize=8, label='한국'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=ADV_C, markersize=8, label='16강 진출'),
        plt.Line2D([0], [0], marker='o', color='none', markerfacecolor=OUT_C, markersize=8, label='조별 탈락'),
    ]
    fig.legend(handles=handles, loc='lower center', ncol=3, frameon=False,
               labelcolor=FG, fontsize=9, bbox_to_anchor=(0.5, 0.01))
    fig.suptitle('사이드·하프스페이스로 파고들 준비가 된 선수 (32팀)',
                 color=FG, fontsize=13, fontweight='bold', y=0.985)
    fig.text(0.5, 0.945, '2022 카타르 월드컵 조별리그, 패스가 나가는 순간 한 번당 인원',
             ha='center', color='#9aa0a6', fontsize=9.5)
    fig.tight_layout(rect=[0, 0.04, 1, 0.935])
    fig.savefig(OUT / 'blog_team_comparison.png', dpi=140, facecolor=BG)
    plt.close(fig)


def _fig_blog_advancement(tm: pd.DataFrame) -> None:
    """블로그용: 16강 진출 여부별 분포(최종값), 채널 vs 중앙 두 패널."""
    metrics = [('adj5', '사이드·하프스페이스'), ('adjc', '박스 중앙')]
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 5.8))
    fig.set_facecolor(BG)
    rng = np.random.default_rng(0)
    for ax, (col, title) in zip(axes, metrics):
        for gi, (adv, c) in enumerate([(False, OUT_C), (True, ADV_C)]):
            vals = tm.loc[tm['advanced'] == adv, col]
            x = gi + rng.uniform(-0.12, 0.12, len(vals))
            ax.scatter(x, vals, c=c, s=34, alpha=0.8, zorder=3)
            ax.hlines(vals.mean(), gi - 0.25, gi + 0.25, color=c, lw=2.5, zorder=4)
        kx = 1 if tm.loc['South Korea', 'advanced'] else 0
        ax.scatter([kx], [tm.loc['South Korea', col]], facecolors='none',
                   edgecolors=KOR, s=160, lw=2, zorder=5)
        ax.axhline(0.0, color='#3a3f46', lw=1, ls=':')
        r = np.corrcoef(tm[col], tm['advanced'].astype(float))[0, 1]
        ax.set_title(f"{title}\n16강 진출과 함께 움직이는 정도 {r:+.2f}",
                     color=FG, fontsize=10.5, pad=8)
        ax.set_xticks([0, 1])
        ax.set_xticklabels(['조별 탈락', '16강 진출'], color=FG, fontsize=9.5)
        ax.set_xlim(-0.6, 1.6)
        _style(ax)
    axes[0].set_ylabel('32팀 평균과의 차이 (0 = 평균)', color=FG, fontsize=9.5)
    fig.suptitle('16강에 오른 팀은 어디에 섰나 (가로 막대 = 그룹 평균, 빨간 원 = 한국)',
                 color=FG, fontsize=12, fontweight='bold', y=0.99)
    fig.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(OUT / 'blog_advancement.png', dpi=140, facecolor=BG)
    plt.close(fig)


if __name__ == '__main__':
    main()
