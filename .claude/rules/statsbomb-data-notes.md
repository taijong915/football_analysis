# StatsBomb 이벤트 데이터 규칙

`src/data_loader.py`나 `src/visualizer.py`를 수정하거나, 노트북/스크립트에서 StatsBomb 이벤트 데이터를 직접 다룰 때 참고하세요.

- **좌표 컬럼**: `location`, `pass_end_location` 등은 `[x, y]` 리스트 형태로 들어옵니다. 바로 산술 연산에 쓸 수 없으므로 언패킹이 필요합니다:
  ```python
  df['x'] = df['location'].apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)
  df['y'] = df['location'].apply(lambda loc: loc[1] if isinstance(loc, list) else np.nan)
  ```
- **결과(outcome) 컬럼**: `pass_outcome` 등은 성공 시 `NaN`, 실패/기타 결과일 때 문자열(`Incomplete`, `Out` 등)입니다. 성공 여부를 필터링할 때는 `.isna()` / `.notna()`를 사용하세요.
- **선수 이름**: `player` 필드는 StatsBomb의 전체 법적 이름입니다. 성이 두 개인 국가(스페인 등)의 선수는 마지막 단어만 잘라 쓰면 실제 통용되는 이름과 달라질 수 있습니다 (예: `Daniel Carvajal Ramos`를 마지막 단어로 자르면 "Ramos"가 되어 다른 선수와 혼동). 표시용 이름이 필요하면 `get_match_lineups(...)[team_name]`의 `player_nickname`을 우선 사용하세요.
- **선수 교체 이후 데이터**: `Substitution` 이벤트 이후에는 선발 라인업 조합이 깨지므로, 대형/패스 네트워크처럼 "고정된 11명"을 전제로 하는 분석은 해당 팀의 첫 `Substitution` 이벤트 `minute` 이전으로 구간을 제한해야 합니다. `plot_pass_network()`(`src/visualizer.py`)는 이 로직을 기본 내장하고 있습니다.
