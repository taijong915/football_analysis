# StatsBomb 이벤트 데이터 규칙

`src/data_loader.py`나 `src/visualizer.py`를 수정하거나, 노트북/스크립트에서 StatsBomb 이벤트 데이터를 직접 다룰 때 참고하세요.

- **좌표 컬럼**: `location`, `pass_end_location` 등은 `[x, y]` 리스트 형태로 들어옵니다. 바로 산술 연산에 쓸 수 없으므로 언패킹이 필요합니다:
  ```python
  df['x'] = df['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
  df['y'] = df['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)
  ```
- **결과(outcome) 컬럼**: `pass_outcome` 등은 성공 시 `NaN`, 실패/기타 결과일 때 문자열(`Incomplete`, `Out` 등)입니다. 성공 여부를 필터링할 때는 `.isna()` / `.notna()`를 사용하세요.
- **선수 이름**: `player` 필드는 StatsBomb의 전체 법적 이름입니다. 성이 두 개인 국가(스페인 등)의 선수는 마지막 단어만 잘라 쓰면 실제 통용되는 이름과 달라질 수 있습니다 (예: `Daniel Carvajal Ramos`를 마지막 단어로 자르면 "Ramos"가 되어 다른 선수와 혼동). 표시용 이름이 필요하면 `get_match_lineups(...)[team_name]`의 `player_nickname`을 우선 사용하세요.
- **선수 교체 이후 데이터**: `Substitution` 이벤트 이후에는 선발 라인업 조합이 깨지므로, 대형/패스 네트워크처럼 "고정된 11명"을 전제로 하는 분석은 해당 팀의 첫 `Substitution` 이벤트 `minute` 이전으로 구간을 제한해야 합니다. `plot_pass_network()`(`src/visualizer.py`)는 `minute_range` 인자로 이 구간을 지정합니다(기본값은 `(0, 첫 교체 시각)`). 다만 교체 이후 구간을 별도로 잘라 보면 표본(패스 수)이 급격히 줄어 네트워크 품질이 떨어질 수 있으니, 아래 `position` 컬럼 기반 접근도 고려하세요.
- **`position` 컬럼(선수의 포지션/역할)**: 각 이벤트에 그 시점 선수가 뛰던 포지션명(예: `Right Center Back`, `Left Defensive Midfield`)이 기록됩니다. 2024 유로 결승(`match_id=3943043`) 스페인 데이터로 확인한 결과 결측률이 낮았고(2015개 중 7개만 `NaN`), 로드리 → 수비멘디처럼 교체된 선수도 같은 포지션 라벨(`Right Defensive Midfield`)을 그대로 이어받았다 - 즉 "선수 이름" 대신 "포지션 슬롯"을 노드로 삼으면 교체와 무관하게 경기 전체 표본을 합산할 수 있다는 뜻이다. 단, `Tactical Shift` 이벤트(포메이션 변경, 이 경기에선 89분에 1회 발생)가 일어나면 같은 선수도 포지션 라벨이 바뀔 수 있으므로(이 경기에선 다니 올모가 2개 라벨을 가짐) 대회/경기가 바뀔 때마다 재확인이 필요하다 - 이 컬럼을 분석에 쓰기로 확정하기 전, 대상 경기들에서 `Tactical Shift` 빈도와 `position` 결측률을 반드시 다시 확인할 것 ([`analysis-workflow.md`](./analysis-workflow.md)의 "데이터 검토" 단계 참고).
- **`possession`/`possession_team` 컬럼(소유권 구간 ID)**: 각 이벤트에 그 시점이 속한 소유권 구간의 정수 ID(`possession`)와 그 구간을 소유한 팀(`possession_team`)이 기록됩니다. 2024 유로 스페인 7경기 전체로 확인한 결과(`scripts/review_possession_chains_data.py`) `possession` 결측은 0건이었고, 경기당 소유권 구간은 144~215개, 그중 특정 팀의 성공 패스가 1개 이상 포함된 구간의 패스 수는 평균 5.7~11.4개(중앙값 4~8개)로 연속 패스 시퀀스("빌드업 체인")를 추적하기에 표본이 충분했다. **주의**: `possession` 번호는 팀 구분 없이 부여되므로 같은 번호 안에 상대 팀 이벤트도 섞여 있다 - 특정 팀의 소유 구간만 뽑으려면 `team`뿐 아니라 `possession_team`도 함께 걸러야 한다. 최솟값 체인 길이는 1(패스 없이 소유권만 짧게 가진 구간)이므로, 시퀀스 분석 시 "길이 2 미만" 구간은 제외하거나 별도 표기가 필요하다.
