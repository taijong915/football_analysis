# 분석 기획: 2024 유로 스페인의 빌드업 패턴

`ideas/backlog.md`의 "2024 유로 스페인의 빌드업 패턴" 항목을 구체화한 기획 문서입니다. 이 폴더(`spain_euro2024/`)는 해당 분석의 노트북·산출물을 모아두는 전용 공간입니다.

이 주제는 방법론이 여러 갈래라 방법론별 하위 폴더로 나눠 관리합니다:
- [`pass_network/`](./pass_network/) — 패스 네트워크 노트북·산출물·종합 결과([`pass_network/RESULTS.md`](./pass_network/RESULTS.md)) (완료)
- [`zone_progression/`](./zone_progression/) — 구역 기반 전진 경로 노트북·산출물·종합 결과([`zone_progression/RESULTS.md`](./zone_progression/RESULTS.md)) (완료)
- [`asymmetry_stats/`](./asymmetry_stats/) — 좌우 비대칭 통계 검증 노트북·산출물·종합 결과([`asymmetry_stats/RESULTS.md`](./asymmetry_stats/RESULTS.md)) (완료)
- [`possession_chains/`](./possession_chains/) — possession 체인 추적 노트북·산출물·종합 결과([`possession_chains/RESULTS.md`](./possession_chains/RESULTS.md)) (완료)
- [`chain_outcomes/`](./chain_outcomes/) — 왼쪽 쏠림의 이유(득점 효율 + 선수 조합 밀도) 노트북·산출물·종합 결과([`chain_outcomes/RESULTS.md`](./chain_outcomes/RESULTS.md)) (완료)

패스 네트워크·구역 기반 전진 경로 두 방법론을 종합한 최초 결론은 [`RESULTS.md`](./RESULTS.md)에 있습니다. 이 결론을 수치·통계로 검증하고(`asymmetry_stats/`), 시퀀스 단위로 더 깊게 파고(`possession_chains/`), 쏠림의 원인까지 확인하는(`chain_outcomes/`) 심화 작업까지 모두 완료했습니다 — 심화 결론을 반영한 종합 정리는 아래 "종합 결론" 절 참고.

## 배경

2024 유로에서 스페인은 우승을 차지하며 대회 내내 뚜렷한 빌드업 스타일(센터백을 넓게 벌리고, 풀백이 윙 포지션까지 전진하며, 로드리가 후방 전개를 전담하는 구조)을 보였다는 평가를 받았다. 이를 StatsBomb 이벤트 데이터로 정량적으로 확인하고, 상대·경기 상황에 따라 이 패턴이 얼마나 일관되게 유지됐는지 살펴본다.

## 분석 질문

1. 스페인이 치른 7경기 각각에서 빌드업 패스 네트워크(핵심 선수, 대형)는 어떤 모습이었는가?
2. 상대 팀이나 경기 상황(조별리그 vs 토너먼트, 스코어 열세/우세 등)에 따라 이 네트워크가 달라졌는가, 아니면 대체로 일관됐는가?
3. 패스 네트워크만으로 보이지 않는 "전진 경로"(수비 1/3 → 중원 → 공격 1/3로 볼이 어떤 구역을 거쳐 나아가는지)는 어떤 모습인가?
4. 위 결과를 종합했을 때, 대회 전체를 관통하는 스페인의 빌드업 스타일을 한두 문장으로 어떻게 요약할 수 있는가?
5. (심화) 패스 네트워크의 "구조 유지" 판단과 구역 기반 전진 경로의 "왼쪽 쏠림"을 수치·통계적으로 검증하면 어떤 결과가 나오는가? 좌우 비대칭이 실제로 통계적으로 유의미한가, 경기별 편차는 얼마나 되는가?
6. (심화) 개별 성공 패스 단위가 아니라 `possession` 단위로 연속된 빌드업 시퀀스를 추적하면, 스페인의 "왼쪽 진출 루트"가 실제로 몇 번의 패스·어떤 구역들을 거쳐 이루어지는가?
7. (심화) 왼쪽 쏠림의 원인은 무엇인가 — 왼쪽으로 끝난 빌드업이 득점에 더 효율적이었기 때문인가, 왼쪽 포지션 조합이 더 자주 활용됐기 때문인가, 아니면 왼쪽에서 크로스/어시스트가 더 자주 나왔기 때문인가?

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
- **좌우 비대칭 통계 검증**(분석 질문 5, 완료): 기존 두 방법론의 "구조 유지"·"왼쪽 쏠림" 판단이 7장 이미지 정성 비교에 그쳤던 한계를 수치로 보완한다. 패스 네트워크는 노드별 패스 수·연결 밀도를 수치화해 경기 간 비교, 구역 기반 전진 경로는 좌/우 진출 비율 차이를 통계적으로 검정(예: t-test 또는 부트스트랩)한다.
  - **데이터 검토** (`scripts/review_asymmetry_stats_data.py`, 7경기 전체): `location`/`pass_end_location` 결측률은 `zone_progression` 데이터 검토(동일 7경기)에서 이미 0건으로 확인했으므로 재검증하지 않았다.
    - **구역 기반 좌/우 표본 수**: 성공 패스의 시작 위치를 왼쪽 채널(Left Wide/HS)·중앙·오른쪽 채널(Right HS/Wide)로 나눠 집계한 결과, **전체 구역 기준으로 7경기 전부에서 왼쪽 패스 수가 오른쪽보다 많았다**(예: 결승전 208 vs 187, 조지아전 370 vs 255, 프랑스전 225 vs 132). 경기당 좌/우 각각 최소 132개(가장 적은 경기 기준) 표본이 있어 통계 검정에 충분하다. `Att-Mid` 가로단(기존 `zone_progression/RESULTS.md`에서 "왼쪽 쏠림"의 근거가 된 `Att-Mid/Left Wide` 구역이 속한 대) 하나로 좁혀도 마찬가지로 7경기 전부 왼쪽이 우세했고(예: 프랑스전 97 vs 26, 독일전 65 vs 39), 경기당 표본은 26~142개로 전체 구역 기준보다는 작지만 여전히 검정 가능한 수준이다. **표본 크기(全구역 기준 132~370, Att-Mid 기준 26~142)는 경기마다 최대 2~3배 차이 나므로(구역 기반 전진 경로 결과와 동일한 이유 — 전체 성공 패스 수 자체가 경기마다 다름), 매치별 원시 개수를 직접 비교하기보다 매치별 "왼쪽 비율"(left / (left+right))로 정규화해 검정하는 편이 안전하다.
    - **position 라벨 좌/우 대칭성**: 각 경기의 Left/Right 접두 포지션 라벨이 7경기 전부에서 완벽히 대응 쌍을 이뤘다(Left Back ↔ Right Back 등, 불일치 0건). 다만 경기마다 등장하는 라벨 집합 크기가 다르다 — 대부분 4쌍(백/DM/윙)이지만 조지아전·프랑스전은 5쌍(Center Midfield 추가), 연장까지 간 독일전은 7쌍(Center Forward·Midfield 추가)까지 늘어난다. **이는 포메이션이 매 경기 동일하지 않다는 뜻이므로, 노드별 패스 수를 경기 간 비교할 때는 StatsBomb 원본 라벨(예: "Left Wing")을 그대로 매칭하기보다 역할군 단위(백/미드필드/윙 등)로 묶어 항상 존재하는 라벨끼리만 비교해야 한다.**
  - **통계 검정 방법 확정**: 매치별 "왼쪽 비율"(왼쪽 / (왼쪽+오른쪽))을 계산해 완전 대칭(0.5)과의 차이를 paired t-test(`scipy.stats.ttest_1samp`, mu=0.5, n=7)로 검정한다. 지표 3개 — ① 구역 점유(전체 구역), ② 구역 점유(Att-Mid만), ③ 패스 네트워크(7경기 공통 4개 역할군 Back/Center Back/Defensive Midfield/Wing의 슬롯별 패스 수) — 를 모두 계산해 비교한다.
  - **결과**: 세 지표 모두 유의수준 0.05에서 통계적으로 유의미하게 왼쪽으로 치우쳤다(구역 전체 p=0.0059, Att-Mid만 p=0.0370, 패스 네트워크 p=0.0315). 다만 효과 크기는 다르다 — 패스 네트워크(선수 관여도)는 평균 0.535로 대칭에 가깝고, 구역 점유(목적지)는 0.569~0.597로 더 크게 쏠렸다. 즉 기존 "패스 네트워크는 완전 대칭"이라는 정성적 결론은 엄밀히는 틀렸다(미세하지만 유의미하게 왼쪽으로 기움) — 작은 구조적 쏠림이 최종 전진 구역에서 크게 증폭되는 구조다. 상세는 [`asymmetry_stats/RESULTS.md`](./asymmetry_stats/RESULTS.md) 참고.
  - 프로토타입은 `scripts/test_asymmetry_stats.py`에 있으며, 검증 후 `asymmetry_stats/07_spain_euro2024_asymmetry_stats.ipynb`로 7경기 전체를 실행했다(재사용 가능한 시각화 함수가 아니라 이 분석 전용 통계 계산이라 `src/visualizer.py`로 승격하지 않았다).
- **possession 체인 추적**(분석 질문 6, 완료): 구역 기반 전진 경로가 개별 성공 패스 단위로 화살표를 그려 "연속된 빌드업 시퀀스"를 못 잡는 한계를 보완한다. StatsBomb 이벤트의 `possession` id로 같은 소유권 내 연속 패스를 체인으로 묶어, 왼쪽 진출 루트가 실제로 몇 번의 패스·어떤 구역을 거치는지 추적한다.
  - **데이터 검토** (`scripts/review_possession_chains_data.py`, 7경기 전체): `possession` 결측 0건(전 경기). 경기당 possession 개수는 144~215개, 그중 스페인의 성공 패스가 1개 이상 포함된 possession은 64~88개. possession당 스페인 성공 패스 수는 평균 5.7~11.4개, 중앙값 4~8개(최댓값은 조지아전 51개) — 시퀀스로 다루기에 충분한 길이다. 다만 최솟값은 모든 경기에서 1(패스 없이 소유권만 짧게 가진 possession도 다수 포함)이라, 체인 분석 시 "길이 2 미만"은 별도 처리(제외 또는 표기)가 필요하다.
  - **주의**: `possession` 컬럼은 팀 구분 없이 부여되므로(같은 possession 번호 안에 상대 팀 이벤트도 섞임), 스페인의 소유 구간만 뽑으려면 `team`뿐 아니라 `possession_team`도 함께 걸러야 한다 (`scripts/review_possession_chains_data.py`에서 검증).
  - **시각화 형식 확정**: `src/visualizer.py`의 `plot_possession_chain_progression()`. `team`과 `possession_team`이 모두 스페인이고 성공 패스가 `min_chain_length`(기본 2)회 이상 이어진 possession만 "체인"으로 걸러, 메인 패널에는 `plot_zone_progression()`과 동일한 30구역 점유 히트맵 + 전진 화살표를 그린다. 오른쪽에는 왼쪽/오른쪽으로 끝난 체인 중 가장 긴 것을 하나씩 뽑아 실제 좌표 그대로 이은 미니 패널 2개를 추가했다.
  - **설계 변경**: 처음엔 대표 체인을 메인 히트맵 위에 그대로 겹쳐 그렸으나, 왔다갔다하는 패스가 많은 체인은 선이 피치를 가로질러 기존 화살표와 뒤섞여 못 알아볼 정도로 지저분해졌다(결승전 32패스짜리 왼쪽 체인 사례). 겹치지 않는 별도 미니 피치 2개(오른쪽 열)로 분리해 해결했다.
  - 프로토타입은 `scripts/test_possession_chains.py`에 있으며, 검증 후 `plot_possession_chain_progression()`을 `src/visualizer.py`로 승격해 `possession_chains/06_spain_euro2024_possession_chains.ipynb`로 7경기 전체를 실행했다. 결과는 [`possession_chains/RESULTS.md`](./possession_chains/RESULTS.md) 참고 — 7경기 중 6경기에서 왼쪽으로 끝난 체인의 중앙값 패스 수가 오른쪽보다 많았다(예외: R16 조지아전, 51패스짜리 특이 체인 하나의 영향).
- **왼쪽 쏠림의 이유**(분석 질문 7, 완료): 블로그 초안이 "왼쪽으로 쏠렸다"는 결과만 보여주고 원인은 다루지 않는다는 사용자 피드백으로 착수했다. 세 갈래로 원인을 검증한다 — ① 왼쪽 체인이 오른쪽보다 득점에 더 효율적이었는가, ② 왼쪽 포지션 조합이 더 자주 활용됐는가, ③(후속 피드백으로 추가) 왼쪽에서 크로스/어시스트가 더 자주 나왔는가.
  - **데이터 검토** (`scripts/review_chain_outcomes_data.py`, 7경기 전체): Shot 이벤트의 `location`/`shot_statsbomb_xg`/`shot_outcome` 결측 0건. 전체 슈팅 123개 중 111개(90%)가 `possession_chains`에서 정의한 체인(같은 possession 안 성공 패스 2회 이상)과 같은 possession으로 연결되어, 체인-슈팅 연결 분석에 충분한 표본을 확인했다. `pass_goal_assist`/`pass_shot_assist`/`pass_cross` 플래그는 7경기 합산 각각 12/96/89건 — 크로스·슈팅 어시스트는 검정에 쓸 만하지만 골 어시스트는 표본이 작다.
  - **방법 확정**: ① 체인의 마지막 패스 도착 구역(Left/Central/Right, `possession_chains`와 동일한 `_chain_length_by_final_side` 재사용)별로 같은 possession 안의 Shot 이벤트를 연결해 슈팅 전환율·xG·골을 집계. ② 포지션 슬롯을 좌(L)/우(R)/중앙(C)으로 나눠 성공 패스의 (패서, 리시버) 슬롯 쌍이 L-L인지 R-R인지 매치별로 집계, "L-L 비율"을 `asymmetry_stats`와 동일한 paired t-test(mu=0.5)로 검정. ③ `pass_goal_assist`/`pass_shot_assist`/`pass_cross` 플래그가 참인 패스의 시작 위치를 왼쪽/중앙/오른쪽으로 분류해 같은 방식으로 검정(골 어시스트는 표본이 작아 검정 없이 원시 개수만 보고).
  - **결과 (예상과 다름)**: ① 득점 효율은 왼쪽 쏠림의 원인이 아니었다 — 왼쪽 체인 슈팅 전환율 18.8%(체인당 0.0104 xG, 골 2개)와 오른쪽 17.2%(0.0100 xG, 골 2개)는 비슷했고, 오히려 **중앙**으로 끝난 체인이 압도적으로 효율적이었다(전환율 46.5%, 체인당 0.0617 xG, 골 10개 — 7경기 골 14개 중 대부분). ② 선수 조합 밀도는 원인으로 뒷받침됐다 — 왼쪽 포지션 슬롯끼리의 연결(L-L, 7경기 합산 840회)이 오른쪽끼리(R-R, 621회)보다 7경기 전부에서 많았고, 매치별 L-L 비율 평균 57.2%는 통계적으로 유의미했다(t(6)=3.898, p=0.0080) — `asymmetry_stats`에서 확인한 구역 점유 쏠림(56.9%)과 거의 같은 크기다. ③ 크로스도 왼쪽에서 통계적으로 유의미하게 더 많이 올라왔다(평균 60.5%, p=0.0114) — 조합 밀도 결과와 맥락이 통한다. 다만 골 어시스트(오른쪽이 근소 우세, 5 vs 4)와 슈팅 어시스트(53.9%, p=0.6458)의 좌우 비율은 유의미하지 않았다 — **왼쪽에서 크로스는 더 많이 올라왔지만 그게 실제 득점 기여로 유의미하게 더 잘 이어지진 않았다.** 종합하면 "왼쪽이 더 위력적이어서"가 아니라 "왼쪽 조합을 더 자주 활용했기 때문에(그 결과 크로스도 더 많이 나왔지만)" 구역 점유가 쌓였다는 설명이 데이터와 더 부합한다.
  - 프로토타입은 `scripts/test_chain_outcomes.py`에 있으며, 검증 후 `chain_outcomes/08_spain_euro2024_chain_outcomes.ipynb`로 7경기 전체를 실행했다(통계 계산 위주라 `src/visualizer.py`로 승격하지 않고, `_prepare_chain_passes`/`_chain_length_by_final_side`를 재사용했다). 상세는 [`chain_outcomes/RESULTS.md`](./chain_outcomes/RESULTS.md) 참고.

## 예상 산출물

- 경기별 포지션 기반 전체 경기 패스 네트워크(+로스터 패널) PNG 7장 → [`pass_network/processed/spain_euro2024_pass_networks/`](./pass_network/processed/spain_euro2024_pass_networks/) (완료)
- 경기별 구역 기반 전진 경로 시각화 (단일 피치 위 점유 히트맵 + 전진 화살표, 30구역 Juego de Posición 그리드) PNG 7장 → [`zone_progression/processed/spain_euro2024_zone_progression/`](./zone_progression/processed/spain_euro2024_zone_progression/) (완료)
- 결승전 전반 샘플 분석 문서: [`pass_network/processed/spain_pass_network_euro2024_final_sample.md`](./pass_network/processed/spain_pass_network_euro2024_final_sample.md) (완료, 선발 라인업 스냅샷 기준)
- 결승전 포지션 기반 전체 경기 샘플: [`pass_network/processed/spain_pass_network_euro2024_final_by_position.png`](./pass_network/processed/spain_pass_network_euro2024_final_by_position.png) (완료)
- 패스 네트워크 7경기 종합 결론: [`pass_network/RESULTS.md`](./pass_network/RESULTS.md) (완료)
- 매치별 좌/우 비율 산점도(구역 점유 전체/Att-Mid + 패스 네트워크 3개 지표) → [`asymmetry_stats/processed/spain_euro2024_asymmetry_stats.png`](./asymmetry_stats/processed/spain_euro2024_asymmetry_stats.png) (완료)
- 좌우 비대칭 통계 검증 결과: [`asymmetry_stats/RESULTS.md`](./asymmetry_stats/RESULTS.md) (완료)
- 경기별 possession 체인 진행 시각화(구역 히트맵+화살표 메인 패널 + 왼쪽/오른쪽 대표 체인 미니 패널) PNG 7장 → [`possession_chains/processed/spain_euro2024_possession_chains/`](./possession_chains/processed/spain_euro2024_possession_chains/) (완료)
- possession 체인 추적 7경기 종합 결론: [`possession_chains/RESULTS.md`](./possession_chains/RESULTS.md) (완료)
- 체인 효율(side별 xG/슈팅 전환율) + 선수 조합 밀도(L-L vs R-R) 비교 차트 → [`chain_outcomes/processed/spain_euro2024_chain_outcomes.png`](./chain_outcomes/processed/spain_euro2024_chain_outcomes.png) (완료)
- 왼쪽 쏠림의 이유 종합 결론: [`chain_outcomes/RESULTS.md`](./chain_outcomes/RESULTS.md) (완료)
- 종합 결과를 재구성한 블로그 발행용 문서: [`blog/spain_euro2024/BLOG_POST.md`](../blog/spain_euro2024/BLOG_POST.md) (진행 중, 티스토리 HTML 모드용 [`BLOG_POST.html`](../blog/spain_euro2024/BLOG_POST.html) 포함)

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
- [x] 좌우 비대칭 통계 검증: 데이터 검토 (`scripts/review_asymmetry_stats_data.py`, 7경기 전체 — 구역 기반 좌/우 표본 7경기 전부 왼쪽 우세 확인, position 라벨 좌우 대칭 확인)
- [x] 좌우 비대칭 통계 검증: 통계 검정 방법 확정(매치별 왼쪽 비율 paired t-test) 및 프로토타입(`scripts/test_asymmetry_stats.py`), 7경기 전체로 검증
- [x] 좌우 비대칭 통계 검증: `asymmetry_stats/07_spain_euro2024_asymmetry_stats.ipynb`로 7경기 전체 실행, 결과 정리 ([`asymmetry_stats/RESULTS.md`](./asymmetry_stats/RESULTS.md)) — 세 지표 모두 유의(p<0.05)하게 왼쪽 쏠림, 단 패스 네트워크(관여도)는 효과 크기가 작고 구역 점유(목적지)에서 증폭됨
- [x] possession 체인 추적: 데이터 검토 (`scripts/review_possession_chains_data.py`, 7경기 전체 — `possession` 결측 0건, 체인 길이 충분함 확인)
- [x] possession 체인 추적: 시각화 형식 확정(체인 필터링 + 구역 점유/전진 화살표 메인 패널 + 왼쪽/오른쪽 대표 체인 미니 패널) 및 프로토타입(`scripts/test_possession_chains.py`), 결승전 샘플로 검증
- [x] 검증된 함수 `plot_possession_chain_progression()`을 `src/visualizer.py`로 승격, `possession_chains/06_spain_euro2024_possession_chains.ipynb`로 7경기 전체 실행
- [x] possession 체인 추적 7경기 종합 비교 및 결론 정리 ([`possession_chains/RESULTS.md`](./possession_chains/RESULTS.md))
- [x] 왼쪽 쏠림의 이유: 데이터 검토 (`scripts/review_chain_outcomes_data.py`, 7경기 전체 — Shot 이벤트 결측 0건, 슈팅 90%가 기존 체인 정의와 연결 확인)
- [x] 왼쪽 쏠림의 이유: 방법 확정(체인-슈팅 연결 + 포지션 슬롯 L-L/R-R 밀도) 및 프로토타입(`scripts/test_chain_outcomes.py`), 7경기 전체로 검증
- [x] 왼쪽 쏠림의 이유: `chain_outcomes/08_spain_euro2024_chain_outcomes.ipynb`로 7경기 전체 실행, 결과 정리 ([`chain_outcomes/RESULTS.md`](./chain_outcomes/RESULTS.md)) — 득점 효율은 원인이 아님(중앙이 압도적으로 효율적), 선수 조합 밀도(L-L 비율 57.2%, p=0.008)와 크로스 빈도(왼쪽 60.5%, p=0.011)가 원인으로 통계적 뒷받침됨
- [x] 왼쪽 쏠림의 이유(후속): "크로스/어시스트도 왼쪽이었는지" 사용자 후속 질문으로 `pass_goal_assist`/`pass_shot_assist`/`pass_cross` 분석 추가 — 크로스는 유의미하게 왼쪽 우세, 골/슈팅 어시스트는 유의미한 차이 없음
- [x] `BLOG_POST.md`에 "왼쪽 쏠림의 이유" 섹션 반영, 결론부/종합/한계 갱신

## 종합 결론: 대회 전체를 관통한 스페인 빌드업 스타일 (분석 질문 4)

다섯 방법론(패스 네트워크·구역 기반 전진 경로·좌우 비대칭 통계 검증·possession 체인 추적·왼쪽 쏠림의 이유)을 종합한 최종 결론은 [`RESULTS.md`](./RESULTS.md)에 정리했습니다. 요약하면: **센터백을 넓게 벌리고 로드리가 축이 되는 중앙 순환 구조로 빌드업을 시작해 풀백을 윙까지 전진시키는 대형(구조는 거의 좌우 대칭)이었지만, 실제 전진의 종착점(`Att-Mid/Left Wide`)은 통계적으로 유의미하게(paired t-test, p<0.05) 7경기 내내 왼쪽으로 쏠렸습니다 — 그 쏠림은 선수 관여도 수준(53.5%)보다 최종 목적지 수준(56.9~59.7%)에서 훨씬 크게 증폭됐고, 왼쪽 진출 빌드업은 오른쪽보다 더 많은 패스를 거쳐 조립됐습니다. 이 쏠림의 원인은 득점 효율이 아니었습니다(왼쪽·오른쪽 체인의 슈팅 전환율은 비슷했고, 실제로는 중앙으로 끝난 체인이 압도적으로 효율적이었으며, 골/슈팅 어시스트의 좌우 비율도 유의미한 차이가 없었습니다) — 대신 왼쪽 포지션 조합끼리의 패스 연결(57.2%, p=0.008)과 왼쪽에서 나온 크로스(60.5%, p=0.011)가 통계적으로 유의미하게 더 잦았다는 "활용 빈도"가 더 설득력 있는 설명이었습니다.**

## 한계 / 유의사항

- 평균 위치 기반 노드는 이상치(세트피스 등)에 영향받을 수 있다.
- `plot_pass_network()`(선발 라인업 스냅샷)는 첫 교체 이전 구간만 보므로 후반전 전술 변화는 반영되지 않고, 경기당 하나의 스냅샷이라 표본이 작아(경기당 45분 내외) 통계적 일반화보다는 정성적 관찰에 가깝다.
- `plot_pass_network_by_position()`(포지션 기반 전체 경기)는 `Tactical Shift`가 잦은 경기일수록 로스터 패널에 `*`(재태깅) 표시가 많아진다 — 표시 자체는 정확하지만, 그 재태깅이 정확히 어떤 전술 변화였는지는 원본 이벤트를 봐야 해석할 수 있다. 또한 중앙 포지션(RDM/CAM/CF 등) 노드는 평균 위치가 서로 가까워 피치 위에서 여전히 겹치기 쉽다.
