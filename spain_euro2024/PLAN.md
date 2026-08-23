# 분석 기획: 2024 유로 스페인의 빌드업 패턴

`ideas/backlog.md`의 "2024 유로 스페인의 빌드업 패턴" 항목을 구체화한 기획 문서입니다. 이 폴더(`spain_euro2024/`)는 해당 분석의 노트북·산출물을 모아두는 전용 공간입니다.

이 주제는 방법론이 두 갈래(패스 네트워크 / 구역 기반 전진 경로)라 방법론별 하위 폴더로 나눠 관리합니다:
- [`pass_network/`](./pass_network/) — 패스 네트워크 노트북·산출물·종합 결과([`pass_network/RESULTS.md`](./pass_network/RESULTS.md))
- [`zone_progression/`](./zone_progression/) — 구역 기반 전진 경로 노트북·산출물·종합 결과([`zone_progression/RESULTS.md`](./zone_progression/RESULTS.md))

두 방법론을 종합한 최종 결론은 [`RESULTS.md`](./RESULTS.md)에 있습니다.

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
  - 데이터 검증(결승전 `match_id=3943043` 기준, 스페인 이벤트 2015건): `position` 결측률 낮음(7건만 `NaN`), 로드리→수비멘디 교체 후에도 같은 포지션 라벨을 이어받아 슬롯 집계가 자연스럽게 이어짐. 7경기 전체로 확대해 다시 확인한 결과도 모든 경기에서 결측률 1% 미만으로 안정적이었다(표는 `pass_network/04_spain_euro2024_buildup.ipynb`의 방법론 셀 참고).
  - **노이즈 노드 필터(`min_node_pass_count`, 기본값 3)**: 후반 막판 몇 분만 뛰고 패스를 거의 못 만진 조커 교체 선수가, 표본이 적어 불안정한 모달 포지션으로 다른 노드와 겹치는 "가짜" 노드를 만드는 문제를 발견 — 프랑스전에서 93분 투입된 수비멘디의 스퓨리어스 RCM 노드가 실제 사례. 패스 시도가 `min_node_pass_count` 미만인 슬롯은 노드/로스터에서 제외하도록 고쳤다. (단, 조지아전 메리노처럼 패스를 3회 이상 만든 조커는 정당한 데이터이므로 필터로 지워지지 않고, 여전히 중앙 포지션끼리 노드가 겹칠 수 있다 — 이건 노이즈가 아니라 "중앙 포지션은 평균 위치가 가깝다"는 별개의 한계.)
  - **"실제 교체" vs "포지션 재태깅" 구분(`*` 표시)**: 로스터 패널에서 `Tactical Shift`로 인한 라벨 변경(이미 뛰던 선수의 포지션이 바뀐 것)과 실제 `Substitution`으로 새로 들어온 선수를 구분하지 못하던 문제를 고쳤다. 각 선수의 "경기 전체 첫 이벤트 시각"과 "그 슬롯에서의 첫 등장 시각"을 비교해, 슬롯 등장이 더 늦으면 `*`를 붙여 "이미 뛰고 있었음"을 표시한다. 프랑스전으로 검증: LW 줄의 `Mikel Merino (93'*)`는 실제로는 76분에 CAM으로 교체 투입된 뒤 93분에 라벨만 LW로 바뀐 것(진짜 LW 신규 투입은 `Martín Zubimendi (93')` 하나뿐)임을 정확히 잡아냈다. 덤으로 RB 줄의 `Nacho (62'*)`도 같은 경기에서 발견됐는데, 이는 57분 나바스 교체 이후 나초가 RCB에서 RB로 재배치된 것으로 보여 — 백4→백3/5 전환 같은 실제 전술 변화를 로스터 패널에서 읽어낼 수 있다는 뜻이기도 하다.
  - 알려진 한계(고쳐지지 않은 부분): `*` 표시는 "재태깅되었다"는 사실만 알려줄 뿐, 정확히 어떤 전술 변화였는지는 여전히 사용자가 원본 이벤트를 봐야 해석할 수 있다. 또한 중앙 포지션(RDM/CAM/CF 등)은 평균 위치가 서로 가까워 피치 위 노드가 여전히 겹치기 쉽다.
  - **7경기 전체로 확대하기 전, 경기마다 `Tactical Shift` 빈도와 `position` 결측률을 다시 확인할 것** (`.claude/rules/statsbomb-data-notes.md`의 `position` 컬럼 노트, `.claude/rules/analysis-workflow.md`의 "데이터 검토" 단계 참고) — 완료, 아래 진행 상황 참고.
- **선발 라인업 스냅샷 (보조 방법론)**: `src/visualizer.py`의 `plot_pass_network()`. 첫 교체 시각 이전(또는 `minute_range`로 지정한 구간)만 사용해 "그 시점 실제 11명"의 이름과 위치를 보고 싶을 때 보조적으로 사용. 구간이 짧으면(예: 6분) 표본 부족으로 품질이 떨어지므로 15분 미만 구간은 참고용으로만 쓴다.
- **구역 기반 전진 경로**(방법론 확정, 승격 전): 피치를 mplsoccer의 `Pitch(positional=True)`가 그리는 표준 Juego de Posición(포지션 플레이) 그리드로 나눈다 — 직접 구간을 정하는 대신 `pitch.dim.positional_x`/`positional_y` 값을 그대로 읽어와 쓴다. StatsBomb 좌표계(120×80) 기준:
    - 가로 6단(`positional_x = [0, 18, 39, 60, 81, 102, 120]`): `Def Box`(0–18, 페널티박스 라인) / `Def Third`(18–39) / `Def-Mid`(39–60, 하프라인까지) / `Att-Mid`(60–81) / `Att Third`(81–102) / `Att Box`(102–120, 상대 페널티박스 라인). 18·102는 박스 라인, 60은 하프라인, 39·81은 그 중점.
    - 세로 5채널(`positional_y = [0, 18, 30, 50, 62, 80]`): `Left Wide` / `Left HS`(하프스페이스) / `Central` / `Right HS` / `Right Wide` — 박스 폭 라인에 맞춰 정의되는 mplsoccer 표준 하프스페이스 채널.
    - 총 30구역(6×5). 처음엔 직접 정한 3등분×5채널(15구역)로 시작했으나, 사용자가 "요즘 축구는 포지션 플레이 기반 전술이 많은데 이를 반영할 수 없냐"고 제안했고 mplsoccer의 `positional=True` 내장 그리드가 정확히 이 이론(spielverlagerung.com에서 정의한 Juego de Posición)을 구현한다는 걸 확인해 하드코딩 대신 라이브러리 값을 그대로 채택했다.
  - **시각화 형식(단일 피치 통합)**: 점유 히트맵과 전진 화살표를 피치 하나 위에 함께 그린다.
    - 배경 음영: 30구역 전부(패스 0회인 구역 포함)를 컬러맵(`YlOrRd`)으로 채우고 각 구역 중앙에 점유 횟수(그 구역에서 시작된 성공 패스 수, 방향 무관)를 텍스트로 표시. 오른쪽에 컬러바.
    - 화살표: 배경 음영 위에 겹쳐, 구역 간 "전진"(더 앞선 가로단으로 넘어가는) 성공 패스만 표시(두께는 빈도 비례, `min_transition_count` 미만 쌍은 생략).
    - 두 레이어 모두 같은 `x_edges`/`y_edges`(`positional_x`/`positional_y`)를 써서 구역 정의가 완전히 동일하다 — 다만 화살표는 30구역 중 전진 조건과 `min_transition_count`를 만족하는 구역 쌍만 그리므로, 히트맵엔 숫자가 있어도 화살표가 안 닿는 구역이 있을 수 있다.
    - 채택 배경: 처음엔 왼쪽 피치(화살표) + 오른쪽 `imshow` 히트맵 패널을 분리해서 그렸으나, 사용자가 "화살표는 가로 방향(피치 좌표), 히트맵은 별도 격자라 축 방향이 안 맞아 보인다"고 지적했다. 두 레이어를 하나의 피치 좌표계로 합쳐 이 문제를 근본적으로 없앴다.
    - 의외로 15구역보다 30구역(더 세밀한 그리드)에서 화살표 겹침이 줄어들었다 — 구역이 세밀해질수록 하나의 구역 쌍에 몰리는 표본이 줄어 `min_transition_count` 문턱을 넘는 쌍 자체가 적어지기 때문.
    - 알려진 한계: 화살표가 지나가는 구역에서는 배경 텍스트(점유 횟수)가 가려질 수 있다(예: 결승전 샘플의 41, 26 구역).
  - **y좌표 방향 검증**: y가 클수록 오른쪽(공격 방향 기준)인지 결승전 라멜 야말(RW) 패스 평균 y=64.7(Right HS/Right Wide 구간)로, 조지아전 니코 윌리엄스(LW) 관련 왼쪽 와이드 구역 점유(86·95, 압도적 1위)로 각각 확인했다.
  - **데이터 검토** (`scripts/review_zone_progression_data.py`, 7경기 전체 스페인 `Pass` 이벤트 기준): `location`/`pass_end_location` 결측 0건, `[x, y]` 형태가 아닌 이상값도 0건 — 전체 4334개 패스 모두 정상.
  - 프로토타입은 `scripts/test_zone_progression.py`(`plot_zone_progression()`)에 있으며, 결승전·조지아전(R16) 두 샘플로 검증했다. 아직 `src/visualizer.py`로 승격하거나 7경기 전체를 실행하지는 않았다.

## 예상 산출물

- 경기별 포지션 기반 전체 경기 패스 네트워크(+로스터 패널) PNG 7장 → [`pass_network/processed/spain_euro2024_pass_networks/`](./pass_network/processed/spain_euro2024_pass_networks/) (완료)
- 경기별 구역 기반 전진 경로 시각화 (단일 피치 위 점유 히트맵 + 전진 화살표, 30구역 Juego de Posición 그리드) PNG 7장 → [`zone_progression/processed/spain_euro2024_zone_progression/`](./zone_progression/processed/spain_euro2024_zone_progression/) (완료)
- 결승전 전반 샘플 분석 문서: [`pass_network/processed/spain_pass_network_euro2024_final_sample.md`](./pass_network/processed/spain_pass_network_euro2024_final_sample.md) (완료, 선발 라인업 스냅샷 기준)
- 결승전 포지션 기반 전체 경기 샘플: [`pass_network/processed/spain_pass_network_euro2024_final_by_position.png`](./pass_network/processed/spain_pass_network_euro2024_final_by_position.png) (완료)
- 패스 네트워크 7경기 종합 결론: [`pass_network/RESULTS.md`](./pass_network/RESULTS.md) (완료)

## 진행 상황

- [x] `plot_pass_network()` 함수 구현 (`src/visualizer.py`)
- [x] 결승전 전반 1경기 샘플로 방법론 검증
- [x] 7경기 루프 스캐폴딩 (`pass_network/04_spain_euro2024_buildup.ipynb`, 패스 네트워크 부분)
- [x] `plot_pass_network_by_position()` 함수 구현 (`src/visualizer.py`) + 결승전 샘플로 검증
- [x] 7경기 전체 실행 및 결과 확인 (경기마다 `position` 결측률·`Tactical Shift` 빈도 재확인 포함, 결과는 노트북 방법론 셀 참고)
- [x] 노이즈 노드 필터(`min_node_pass_count`) + "실제 교체 vs 재태깅" 구분(`*` 표시) 추가, 7경기 재생성으로 검증
- [x] 패스 네트워크 산출물을 `pass_network/` 전용 하위 폴더로 재구성, 7경기 종합 비교 및 결론 정리(`pass_network/RESULTS.md`)
- [x] 구역 기반 전진 경로: 데이터 검토 완료 (`scripts/review_zone_progression_data.py`)
- [x] 구역 그리드 확정: mplsoccer `Pitch(positional=True)` 표준 Juego de Posición 그리드(30구역) 채택
- [x] 시각화 형식 확정(단일 피치 위 점유 히트맵 + 전진 화살표 통합) 및 프로토타입(`scripts/test_zone_progression.py`), 결승전·조지아전 샘플로 검증
- [x] 검증된 함수 `plot_zone_progression()`을 `src/visualizer.py`로 승격, `zone_progression/05_spain_euro2024_zone_progression.ipynb`로 7경기 전체 실행
- [x] 구역 기반 전진 경로 7경기 종합 비교 및 결론 정리 ([`zone_progression/RESULTS.md`](./zone_progression/RESULTS.md))
- [x] 패스 네트워크 + 구역 기반 전진 경로 두 방법론을 종합한 "스페인 빌드업 스타일" 최종 결론 정리 (상위 `PLAN.md`, 분석 질문 4번)

## 종합 결론: 대회 전체를 관통한 스페인 빌드업 스타일 (분석 질문 4)

패스 네트워크와 구역 기반 전진 경로 두 방법론을 종합한 최종 결론은 [`RESULTS.md`](./RESULTS.md)에 정리했습니다. 요약하면: **센터백을 넓게 벌리고 로드리가 축이 되는 중앙 순환 구조로 빌드업을 시작해 풀백을 윙까지 전진시키는 대형(좌우 대칭)이었지만, 실제 전진의 종착점(`Att-Mid/Left Wide`)은 7경기 내내 왼쪽으로 쏠렸습니다.**

## 한계 / 유의사항

- 평균 위치 기반 노드는 이상치(세트피스 등)에 영향받을 수 있다.
- `plot_pass_network()`(선발 라인업 스냅샷)는 첫 교체 이전 구간만 보므로 후반전 전술 변화는 반영되지 않고, 경기당 하나의 스냅샷이라 표본이 작아(경기당 45분 내외) 통계적 일반화보다는 정성적 관찰에 가깝다.
- `plot_pass_network_by_position()`(포지션 기반 전체 경기)는 `Tactical Shift`가 잦은 경기일수록 로스터 패널에 `*`(재태깅) 표시가 많아진다 — 표시 자체는 정확하지만, 그 재태깅이 정확히 어떤 전술 변화였는지는 원본 이벤트를 봐야 해석할 수 있다. 또한 중앙 포지션(RDM/CAM/CF 등) 노드는 평균 위치가 서로 가까워 피치 위에서 여전히 겹치기 쉽다.
