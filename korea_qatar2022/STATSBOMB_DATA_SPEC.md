# StatsBomb 오픈 데이터 명세 (침투 분석 방향 결정용)

2026-09-14, `korea_qatar2022` 침투 분석의 방법론(360 계속 쓸지, 이벤트 전용으로 갈지)을 정하기 위해
실제 캐시 데이터(`data/raw/wc2022_360/`)와 `statsbombpy` API를 직접 열어 확인한 결과입니다.
일반적인 StatsBomb 데이터 특성 중 재사용 가치가 있는 항목은 [`.claude/rules/statsbomb-data-notes.md`](../.claude/rules/statsbomb-data-notes.md)에도 반영돼 있습니다.

## 1. 이벤트 데이터 (모든 경기 공통)

`sb.events()`가 반환하는 데이터는 패스/슛/캐리/듀얼 등 이벤트 타입마다 채워지는 컬럼이 다른 롱 포맷입니다.
WC2022 샘플 10경기 기준 컬럼 합집합은 **104개**입니다. 크게 네 갈래로 묶입니다.

- **좌표류**: `location`(이벤트 발생 지점), `pass_end_location`, `carry_end_location`, `shot_end_location`, `goalkeeper_end_location`.
  이벤트의 시작/끝 지점만 있고, 그 사이의 움직임은 기록되지 않습니다.
- **결과/속성류**: `pass_outcome`, `shot_outcome`, `duel_outcome`, `dribble_outcome`, `shot_statsbomb_xg`, `pass_height`, `pass_body_part` 등.
- **문맥류**: `possession`, `possession_team`, `play_pattern`, `position`, `tactics`(포메이션), `under_pressure`, `counterpress`, `related_events`.
- **`shot_freeze_frame`**: 슛 이벤트에만 붙는 별도 스냅샷(`{location, player, position, teammate}` 리스트).
  360 데이터가 있는 대회에서만 채워지며, WC2022 확인 결과 슛 24건 전부 100% 채워져 있었습니다.
  `sb.frames()`의 슛 프레임과 사실상 같은 정보를 다른 포맷으로 중복 제공하는 것입니다.

## 2. 360 프리즈프레임 (`sb.frames`)

### 2-1. 대회 범위가 제한적

`sb.competitions()` 기준 오픈 데이터 80개 대회-시즌 중 **12개**만 360이 있습니다.

| 대회 | 시즌 |
|---|---|
| FIFA World Cup | 2022 |
| UEFA Euro | 2024, 2020 |
| UEFA Women's Euro | 2025, 2022 |
| Women's World Cup | 2023 |
| 1. Bundesliga | 2023/2024 |
| La Liga | 2020/2021 |
| Ligue 1 | 2022/2023, 2021/2022 |
| Major League Soccer | 2023 |
| African Cup of Nations | 2023 |

WC2022는 전체 **64경기 중 49경기**만 캐시돼 있습니다(조별리그 48 + 한국 16강전 1). 16강 이후 경기는 대부분 API 자체에서 제공하지 않습니다.

### 2-2. 스키마

`id`(이벤트 uuid), `visible_area`(카메라가 잡은 다각형, x·y가 번갈아 나오는 평평한 리스트), `match_id`, `teammate`, `actor`, `keeper`, `location`.
프레임 x 선수 롱 포맷이라 한 이벤트가 여러 행을 차지합니다(한 경기 약 3천 프레임 = 약 3.8만 행).

### 2-3. 이벤트 타입별 커버리지 (1경기 실측, `match_id=3857254`)

| 이벤트 타입 | 커버리지 |
|---|---|
| Shot | 100.0% |
| Block | 95.3% |
| Ball Recovery | 92.6% |
| Dispossessed | 92.0% |
| Duel | 92.1% |
| Interception | 90.9% |
| Carry | 90.0% |
| Ball Receipt* | 88.4% |
| Foul Committed | 87.0% |
| Pressure | 87.0% |
| Clearance | 86.8% |
| Foul Won | 86.4% |
| Miscontrol | 85.2% |
| Pass | 82.1% |
| Dribble | 80.0% |
| Dribbled Past | 71.4% |
| Goal Keeper | 37.9% |
| 전체 평균 | 85.9% |

Substitution, Half Start/End, Tactical Shift, Starting XI 등 "경기 진행 메타" 이벤트는 360이 붙지 않습니다(0%).

### 2-4. 가시 영역(`visible_area`)의 한계

기록된 선수 좌표의 98.2%가 그 프레임의 `visible_area` 안에 있습니다. 다각형 밖 선수는 "없는 것"이 아니라 "관측 안 된 것"이며 데이터만으로 구분 불가합니다.
공이 전진 상황(x 30~80)일 때, 추정 수비라인 **앞**(공-수비라인 사이) 가시율은 평균 0.80(96%가 0.5 이상)인 반면, 라인 **뒤** 15m 밴드는 평균 0.33(0.5 이상이 24%뿐)로 크게 떨어집니다.
이 가시율은 팀마다 체계적으로 다릅니다 - 32팀 평균의 표준편차가 노이즈 기대치의 6.4배이고, 상대 최종 수비라인 깊이와 r=+0.665로 얽혀 있습니다("상대가 깊이 내려설수록 잘 보인다"). 즉 "모든 팀이 똑같이 못 보니 편향이 상쇄된다"는 가정이 성립하지 않습니다.

## 3. 연속 추적(tracking) 데이터 - 존재하지 않음, 직접 재검증함

`location`과 360 프레임을 시간순으로 이어 붙여도 경기 전체에 대한 연속 위치 정보가 되지 않는다는 걸 실측으로 확인했습니다.

- **이벤트가 가장 많은 선수(경기당 254개 이벤트, 크리스티안 에릭센)를 시간순 정렬**해도 `location`은 그 선수가 공을 만지거나 압박하는 등 **행동을 한 순간에만** 찍힙니다. 공을 안 만지는 구간은 좌표가 아예 없습니다.
- 같은 선수의 연속 `location` 샘플 사이 시간 간격은 **중앙값 1초, 75%가 11초**입니다. 실제 tracking data(25fps = 0.04초 간격)라면 나올 수 없는 간격이며, "고정 주기 샘플링"이 아니라 "사건이 일어날 때만" 기록된다는 증거입니다.
- **360 프레임도 마찬가지**입니다. 프레임 하나(`id` 하나)는 그 순간의 정지 스냅샷이고, 경기 전체로 봐도 프레임 간 간격이 중앙값 1초, 75%가 2초, **최대 153초(2분 반)**입니다. 그 사이 구간은 데이터가 아예 없어 보간할 근거도 없습니다.

**결론**: StatsBomb 오픈 데이터는 이벤트/360 모두 이산적(discrete) 사건 기반 스냅샷입니다. 22명 전원의 프레임 단위 실시간 좌표(진짜 tracking data, 예: Second Spectrum·Tracab)는 오픈 데이터에 없고, 있다 해도 비공개·유료라 이 프로젝트가 쓰는 무료 오픈 API 범위 밖입니다.

## 4. 침투 분석에 대한 함의 (결정 전 참고용, 아직 미확정)

- **360 계속 쓰되 범위 제한**: 라인 뒤 대신 라인 앞(공-수비라인 사이, 가시율 0.80·96%가 0.5 이상) 구간만 세는 기존 완화책 유지. WC2022 47경기 재현성 테스트에서 이 정의가 +0.28~0.33으로 회복된 전례 있음(`statsbomb-data-notes.md` 참고).
- **이벤트 데이터 전용 지표로 전환**: 360 없이 패스 성공 후 전진 거리/방향, possession chain의 필드 진입 속도 등으로 대체. 12개 대회 전체로 확장 가능하지만 "공간 창출"이라는 원래 개념과는 거리가 생김.
- **두 정의를 나란히 계산해 비교**: 같은 경기에 대해 360 기반 지표와 이벤트 전용 지표를 함께 내서 상관관계·불일치 패턴을 먼저 살펴본 뒤 결정.
