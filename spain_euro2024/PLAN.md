# 분석 기획: 2024 유로 스페인의 빌드업 패턴

`ideas/backlog.md`의 "2024 유로 스페인의 빌드업 패턴" 항목을 구체화한 기획 문서입니다. 이 폴더(`spain_euro2024/`)는 해당 분석의 노트북·산출물을 모아두는 전용 공간입니다.

## 배경

2024 유로에서 스페인은 우승을 차지하며 대회 내내 뚜렷한 빌드업 스타일(센터백을 넓게 벌리고, 풀백이 윙 포지션까지 전진하며, 로드리가 후방 전개를 전담하는 구조)을 보였다는 평가를 받았다. 이를 StatsBomb 이벤트 데이터로 정량적으로 확인하고, 상대·경기 상황에 따라 이 패턴이 얼마나 일관되게 유지됐는지 살펴본다.

## 분석 질문

1. 스페인이 치른 7경기 각각에서 빌드업 패스 네트워크(핵심 선수, 대형)는 어떤 모습이었는가?
2. 상대 팀이나 경기 상황(조별리그 vs 토너먼트, 스코어 열세/우세 등)에 따라 이 네트워크가 달라졌는가, 아니면 대체로 일관됐는가?
3. 패스 네트워크만으로 보이지 않는 "전진 경로"(수비 1/3 → 중원 → 공격 1/3로 볼이 어떤 구역을 거쳐 나아가는지)는 어떤 모습인가?
4. 위 결과를 종합했을 때, 대회 전체를 관통하는 스페인의 빌드업 스타일을 한두 문장으로 어떻게 요약할 수 있는가?

## 데이터 범위

- StatsBomb 오픈 데이터: `competition_id=55` (UEFA Euro), `season_id=282` (2024)
- 스페인이 치른 전 경기 7경기 (조별리그 3 + 16강·8강·4강·결승 4)
- 경기당 사용 컬럼: `events`의 `location`, `pass_end_location`, `player`, `pass_recipient`, `pass_outcome`, `type`(Substitution 포함) / `lineups`의 `player_nickname`, 포지션

## 방법론 요약

- **경기 전체 패스 네트워크 (채택된 주 방법론)**: `src/visualizer.py`의 `plot_pass_network_by_position()`. 노드를 선수 이름이 아니라 포지션 슬롯(`position` 컬럼, 예: `Right Defensive Midfield`)으로 잡아 교체와 무관하게 90분 전체 패스를 합산한다. 오른쪽 패널에 포지션별 로스터(어떤 선수가 그 슬롯을 맡았는지)와 교체 시각(첫 등장 시각의 근사치)을 함께 표시해, 노드만으로는 안 보이는 "누가 언제 바뀌었는지"를 보완한다.
  - 채택 배경: `plot_pass_network()`(아래)로 첫 교체 이전 구간만 보면 후반전 전술 변화가 전혀 반영되지 않고, 교체 이후 구간을 잘게 쪼개보면(예: 82-88분 6분 구간) 표본 부족으로 네트워크 품질이 급격히 떨어졌다. 포지션 슬롯 기준 합산은 이 두 문제를 동시에 해결한다.
  - 데이터 검증(결승전 `match_id=3943043` 기준, 스페인 이벤트 2015건): `position` 결측률 낮음(7건만 `NaN`), 로드리→수비멘디 교체 후에도 같은 포지션 라벨을 이어받아 슬롯 집계가 자연스럽게 이어짐.
  - 알려진 한계: `Tactical Shift`(포메이션 변경) 이벤트가 발생하면(결승전에선 89분 1회) 로스터 상 교체 쌍이 실제 `Substitution` 이벤트의 OUT/IN과 정확히 일치하지 않을 수 있다 — 결승전 88~92분 구간에서 실제로 관찰됨(야말→올모, 올모→메리노로 표시되지만 실제 교체는 야말→메리노 1건이었고 나머지는 포지션 재배치). 또한 중앙 포지션(RDM/CAM/CF 등)은 평균 위치가 서로 가까워 피치 위 노드가 겹치기 쉽다.
  - **7경기 전체로 확대하기 전, 경기마다 `Tactical Shift` 빈도와 `position` 결측률을 다시 확인할 것** (`.claude/rules/statsbomb-data-notes.md`의 `position` 컬럼 노트, `.claude/rules/analysis-workflow.md`의 "데이터 검토" 단계 참고).
- **선발 라인업 스냅샷 (보조 방법론)**: `src/visualizer.py`의 `plot_pass_network()`. 첫 교체 시각 이전(또는 `minute_range`로 지정한 구간)만 사용해 "그 시점 실제 11명"의 이름과 위치를 보고 싶을 때 보조적으로 사용. 구간이 짧으면(예: 6분) 표본 부족으로 품질이 떨어지므로 15분 미만 구간은 참고용으로만 쓴다.
- **구역 기반 전진 경로**(미착수): 피치를 수비/중원/공격 1/3로 나누고, 각 구역 간 패스 전환 빈도 또는 히트맵으로 시각화 예정. 구체적 방법은 착수 시 여기에 갱신.

## 예상 산출물

- 경기별 포지션 기반 전체 경기 패스 네트워크(+로스터 패널) PNG 7장 → `processed/spain_euro2024_pass_networks/`
- 경기별 구역 기반 전진 경로 시각화 (형식 미정)
- 결승전 전반 샘플 분석 문서: [`processed/spain_pass_network_euro2024_final_sample.md`](./processed/spain_pass_network_euro2024_final_sample.md) (완료, 선발 라인업 스냅샷 기준)
- 결승전 포지션 기반 전체 경기 샘플: [`processed/spain_pass_network_euro2024_final_by_position.png`](./processed/spain_pass_network_euro2024_final_by_position.png) (완료)
- 7경기를 종합한 결론(노트북 "관찰 기록" 셀 또는 별도 요약 문서)

## 진행 상황

- [x] `plot_pass_network()` 함수 구현 (`src/visualizer.py`)
- [x] 결승전 전반 1경기 샘플로 방법론 검증
- [x] 7경기 루프 스캐폴딩 (`04_spain_euro2024_buildup.ipynb`, 패스 네트워크 부분 — `plot_pass_network_by_position()`로 갱신 필요)
- [x] `plot_pass_network_by_position()` 함수 구현 (`src/visualizer.py`) + 결승전 샘플로 검증
- [ ] 7경기 전체 실행 및 결과 확인 (경기마다 `position` 결측률·`Tactical Shift` 빈도 재확인 포함)
- [ ] 구역 기반 전진 경로 시각화
- [ ] 7경기 종합 비교 및 결론 정리

## 한계 / 유의사항

- 평균 위치 기반 노드는 이상치(세트피스 등)에 영향받을 수 있다.
- `plot_pass_network()`(선발 라인업 스냅샷)는 첫 교체 이전 구간만 보므로 후반전 전술 변화는 반영되지 않고, 경기당 하나의 스냅샷이라 표본이 작아(경기당 45분 내외) 통계적 일반화보다는 정성적 관찰에 가깝다.
- `plot_pass_network_by_position()`(포지션 기반 전체 경기)는 `Tactical Shift`가 잦은 경기일수록 로스터 패널의 교체 쌍이 실제 `Substitution` 이벤트와 어긋날 수 있고, 중앙 포지션(RDM/CAM/CF 등) 노드가 서로 가까워 피치 위에서 겹치기 쉽다.
