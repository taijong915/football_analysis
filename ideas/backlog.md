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

### 2024 유로 스페인의 빌드업 패턴

- **분석 질문**: 2024 유로 스페인이 치른 경기들에서 빌드업 패턴(핵심 선수 중심 패스 네트워크 + 구역 기반 전진 경로)이 상대·경기 상황에 따라 어떻게 달랐는가? 이를 종합해 대회 전체를 관통하는 스페인의 빌드업 스타일은 무엇이었는가?
- **필요 데이터**: StatsBomb `competition_id=55, season_id=282` (UEFA Euro 2024), 스페인이 치른 전 경기(조별리그 3 + 토너먼트 4, 총 7경기) 이벤트 데이터(`location`, `pass_end_location`, `player`, `pass_recipient` 등) + `lineups`(포지션/선발)
- **예상 산출물**:
  - 경기별 패스 네트워크 다이어그램 (평균 위치 + 선수 간 패스 빈도, `mplsoccer`)
  - 경기별 빌드업 구역(zone) 전진 패턴 시각화 (수비 1/3 → 중원 → 공격 1/3 전환 경로/히트맵)
  - 7경기를 관통하는 종합 비교 및 "스페인 빌드업 스타일" 결론 정리 (노트북)
- **진행 상황**: 패스 네트워크 부분 완료 — `plot_pass_network()`/`plot_pass_network_by_position()`(`src/visualizer.py`) 구현, `spain_euro2024/pass_network/04_spain_euro2024_buildup.ipynb`로 7경기 전체 실행, 종합 결과는 [`spain_euro2024/pass_network/RESULTS.md`](../spain_euro2024/pass_network/RESULTS.md). 구역 기반 전진 경로 시각화는 아직 미착수. 상세 기획은 [`spain_euro2024/PLAN.md`](../spain_euro2024/PLAN.md) 참고.

## 완료

## 보류

<!-- 예: ### 주제 제목 — 보류 사유 -->
