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

## 완료

### 2024 유로 스페인의 빌드업 패턴

- **분석 질문**: 2024 유로 스페인이 치른 경기들에서 빌드업 패턴(핵심 선수 중심 패스 네트워크 + 구역 기반 전진 경로)이 상대·경기 상황에 따라 어떻게 달랐는가? 이를 종합해 대회 전체를 관통하는 스페인의 빌드업 스타일은 무엇이었는가?
- **필요 데이터**: StatsBomb `competition_id=55, season_id=282` (UEFA Euro 2024), 스페인이 치른 전 경기(조별리그 3 + 토너먼트 4, 총 7경기) 이벤트 데이터(`location`, `pass_end_location`, `player`, `pass_recipient` 등) + `lineups`(포지션/선발)
- **산출물**:
  - 패스 네트워크: `plot_pass_network()`/`plot_pass_network_by_position()`(`src/visualizer.py`), `spain_euro2024/pass_network/04_spain_euro2024_buildup.ipynb`로 7경기 실행, 종합 결과는 [`spain_euro2024/pass_network/RESULTS.md`](../spain_euro2024/pass_network/RESULTS.md).
  - 구역 기반 전진 경로: `plot_zone_progression()`(`src/visualizer.py`, mplsoccer `positional=True` 표준 Juego de Posición 30구역 그리드), `spain_euro2024/zone_progression/05_spain_euro2024_zone_progression.ipynb`로 7경기 실행, 종합 결과는 [`spain_euro2024/zone_progression/RESULTS.md`](../spain_euro2024/zone_progression/RESULTS.md).
  - 두 방법론을 종합한 "스페인 빌드업 스타일" 최종 결론: [`spain_euro2024/RESULTS.md`](../spain_euro2024/RESULTS.md) — 구조는 좌우 대칭(센터백 넓게 벌림 + 로드리 축 + 양쪽 풀백 전진)이지만 실제 전진 방향은 왼쪽으로 일관되게 쏠림.

## 보류

<!-- 예: ### 주제 제목 — 보류 사유 -->
