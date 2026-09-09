# 분석 주제 백로그

상태 값과 사용법은 [`README.md`](./README.md) 참고.

## 대기

| 주제 | 메모 |
| :--- | :--- |
| | |

## 구체화

<!-- 아이디어가 구체화되면 아래 형식으로 항목을 추가하세요.

### 주제 제목

- **분석 질문**: 무엇을 알아내고 싶은가
- **필요 데이터**: StatsBomb 대회/시즌/선수 등
- **예상 산출물**: 어떤 노트북/시각화로 표현할 것인가
-->

## 진행중

<!-- 없음 -->

## 완료

### "침투!" - 2022 카타르 월드컵, 전방에는 얼마나 있었나

- **분석 질문**: (1) 팀이 전진하려는 순간 상대 수비 라인 바로 앞에서 온사이드로 뛰어들 준비가 된 자기 팀 선수(= "침투 선택지")는 몇 명이고, 32팀 중 한국은 어디에 위치하는가? (2) 이 지표가 대회 성적과 관계가 있는가("뛰어 들어가야 한다"는 해설에 데이터 근거가 있는가)? (3) 전진 상황의 양과 상황당 밀도를 두 축으로 놓으면 팀들이 어떻게 갈리는가(지표가 영역 우위와 얽혀 있으므로 그 교란을 드러내는 장치)? (4) 한국의 원시값 극단은 실제 경기 내용인가 중계 화면 구성의 산물인가? (5) 한국의 16강 브라질전(4:1 패)은 조별리그 세 경기와 달랐는가?
- **필요 데이터**: StatsBomb `competition_id=43, season_id=106` (FIFA World Cup 2022). 조별리그 48경기 이벤트 + **360 프리즈프레임** + 한국 16강 브라질전 `3869253`. 캐시는 `data/raw/wc2022_360/`(약 280 MB, git 제외).
- **조작적 정의 (2단계에서 한 번 뒤집힘)**: 처음에는 "패스 시점에 수비 라인보다 앞에 있는 아군 수"로 잡았으나 규칙상 그건 오프사이드 위치였다. "온사이드(라인 이하)이면서 라인에서 5m 이내이고 공보다 앞에 있는 아군 수"로 바꾸자 가시율(0.33 → 0.80), 재현성(-0.14 → +0.33), 진출 상관(-0.32 → +0.31)이 함께 회복됐다. 경위는 `DECISIONS.md` 2026-09-08 "침투 조작적 정의 오류".
- **산출물**: 기획은 [`korea_qatar2022/PLAN.md`](../korea_qatar2022/PLAN.md), 종합 결론은 [`korea_qatar2022/RESULTS.md`](../korea_qatar2022/RESULTS.md). 질문별 스크립트·메모·그림은 `korea_qatar2022/01_team_comparison.py` ~ `04_brazil_comparison.py`와 `korea_qatar2022/processed/`(각 `*_notes.md` + CSV + 그림 7개). 프리즈프레임 시각화 `plot_freeze_frame()`은 `src/visualizer.py`로 승격(커밋 `123000c`).
- **결론**: 침투 준비가 잘 된 팀일수록 대회를 더 오래 남았다(16강 진출 상관 보정 후 +0.27). 단 이 지표는 점유 볼륨과 크게 얽혀 있어(r=+0.54, 점유 통제 시 진출 상관 +0.33 → +0.19) 순수한 "침투 의지"는 아니다. **한국의 원시값 극단("전방에 아무도 없었다")은 실제 경기 내용보다 중계 화면 구성의 산물** - 한국은 32팀 중 상대가 가장 적게 잡힌 팀이고, 관측 조건을 보정하면 침투 선택지는 정확히 중위권(3위 → 18위), 오프사이드 위치는 반전(31위 → 8위)한다. 브라질전도 보정하면 조별리그와 다르지 않다.
- **한계**: 관측 완전성이 지표를 직접 밀어 올린다(보이는 상대 1명 시 침투 선택지 0.42명, 9명 시 1.44명 - 보정 필수). 영역 우위와 얽혀 있어 "침투 의지"만 잰 값이 아니다. 3경기 팀 평균 신뢰도가 약 0.59라 특정 팀 등수가 아니라 분포상 위치로만 서술. 라인 앞 가시율도 0.80이지 1.0이 아니라 절대 개수는 과소 집계. 2026 북중미 월드컵은 오픈 데이터에 없어 직접 답할 수 없다.
- **미착수(선택)**: 프리즈프레임 대비 스냅샷(중앙값 근접 상황 선정), 블로그 발행.

### 2024 유로 스페인의 빌드업 패턴

- **분석 질문**: 2024 유로 스페인이 치른 경기들에서 빌드업 패턴(핵심 선수 중심 패스 네트워크 + 구역 기반 전진 경로)이 상대·경기 상황에 따라 어떻게 달랐는가? 이를 종합해 대회 전체를 관통하는 스페인의 빌드업 스타일은 무엇이었는가? (심화) 패스 네트워크의 "구조 유지" 판단과 구역 기반 전진 경로의 "왼쪽 쏠림"을 수치·통계적으로 검증하면 어떤 결과가 나오는가? 개별 성공 패스 단위가 아니라 `possession` 단위로 연속된 빌드업 시퀀스를 추적하면, 스페인의 "왼쪽 진출 루트"가 실제로 몇 번의 패스·어떤 구역들을 거쳐 이루어지는가? 그 왼쪽 쏠림의 원인은 무엇인가 - 득점 효율인가, 선수 조합인가, 크로스/어시스트 위치인가?
- **필요 데이터**: StatsBomb `competition_id=55, season_id=282` (UEFA Euro 2024), 스페인이 치른 전 경기(조별리그 3 + 토너먼트 4, 총 7경기) 이벤트 데이터(`location`, `pass_end_location`, `player`, `pass_recipient`, `possession`/`possession_team` 등) + `lineups`(포지션/선발)
- **산출물**:
  - 패스 네트워크: `plot_pass_network()`/`plot_pass_network_by_position()`(`src/visualizer.py`), `spain_euro2024/pass_network/04_spain_euro2024_buildup.ipynb`로 7경기 실행, 종합 결과는 [`spain_euro2024/pass_network/RESULTS.md`](../spain_euro2024/pass_network/RESULTS.md).
  - 구역 기반 전진 경로: `plot_zone_progression()`(`src/visualizer.py`, mplsoccer `positional=True` 표준 Juego de Posición 30구역 그리드), `spain_euro2024/zone_progression/05_spain_euro2024_zone_progression.ipynb`로 7경기 실행, 종합 결과는 [`spain_euro2024/zone_progression/RESULTS.md`](../spain_euro2024/zone_progression/RESULTS.md).
  - 좌우 비대칭 통계 검증: 매치별 좌/우 비율(구역 점유 전체/Att-Mid + 패스 네트워크 4개 역할군)을 paired t-test로 검정, `spain_euro2024/asymmetry_stats/07_spain_euro2024_asymmetry_stats.ipynb`로 7경기 실행, 종합 결과는 [`spain_euro2024/asymmetry_stats/RESULTS.md`](../spain_euro2024/asymmetry_stats/RESULTS.md) - 세 지표 모두 통계적으로 유의(p<0.05)하게 왼쪽 쏠림, 선수 관여도(53.5%)보다 목적지 구역(56.9~59.7%)에서 쏠림이 더 크게 증폭됨.
  - possession 체인 추적: `plot_possession_chain_progression()`(`src/visualizer.py`), `spain_euro2024/possession_chains/06_spain_euro2024_possession_chains.ipynb`로 7경기 실행, 종합 결과는 [`spain_euro2024/possession_chains/RESULTS.md`](../spain_euro2024/possession_chains/RESULTS.md) - 7경기 중 6경기에서 왼쪽으로 끝난 체인의 중앙값 패스 수가 오른쪽보다 많음.
  - 왼쪽 쏠림의 이유(득점 효율 + 선수 조합 밀도 + 크로스/어시스트 위치): `spain_euro2024/chain_outcomes/08_spain_euro2024_chain_outcomes.ipynb`로 7경기 실행, 종합 결과는 [`spain_euro2024/chain_outcomes/RESULTS.md`](../spain_euro2024/chain_outcomes/RESULTS.md) - 득점 효율은 원인이 아니었음(중앙 체인이 압도적으로 효율적, 골/슈팅 어시스트 좌우 비율도 유의미하지 않음), 선수 조합 밀도(왼쪽 포지션끼리 패스 연결 57.2%, p=0.008)와 크로스 빈도(왼쪽 60.5%, p=0.011)가 통계적으로 뒷받침되는 원인.
  - 다섯 방법론을 종합한 "스페인 빌드업 스타일" 최종 결론: [`spain_euro2024/RESULTS.md`](../spain_euro2024/RESULTS.md) - 구조는 거의 좌우 대칭(센터백 넓게 벌림 + 로드리 축 + 양쪽 풀백 전진)이지만 실제 전진 방향은 통계적으로 유의미하게 왼쪽으로 쏠렸고, 그 쏠림은 선수 관여도보다 최종 목적지에서 더 크게 증폭되며, 왼쪽 진출 빌드업은 더 많은 패스를 거쳐 조립됨 - 원인은 득점 효율이 아니라 왼쪽 포지션 조합·크로스의 잦은 활용.
  - 블로그 발행용 종합 문서: [`blog/spain_euro2024/BLOG_POST.md`](../blog/spain_euro2024/BLOG_POST.md). 2026-09-01 티스토리 공개 발행 완료 → https://tj-archive.tistory.com/2 (기존 #1은 삭제 후 재발행, `DECISIONS.md` 2026-09-01 항목 참고)

## 보류

<!-- 예: ### 주제 제목 - 보류 사유 -->
