# CLAUDE.md

이 파일은 이 저장소에서 작업할 때 Claude Code(claude.ai/code)에게 제공되는 가이드입니다. 자주 쓰이지 않는 상세 가이드·도메인 지식은 `.claude/rules/`에 분리해뒀으니, 아래에서 링크하는 시점에 필요할 때 읽으세요.

## 프로젝트 개요

StatsBomb 이벤트/추적 데이터를 불러와 피치 시각화(슛 맵, 패스 맵, 레이더/피자 차트)를 생성하는 Python 축구 분석 환경입니다. GitHub 저장소 `taijong915/football_analysis`의 `main` 브랜치에 연결되어 있습니다.

## 세션 시작 시 필독

**매 세션 시작 시 [`DECISIONS.md`](./DECISIONS.md)를 먼저 읽고 시작하세요.** 이 프로젝트의 주요 의사결정(왜 이렇게 구성했는지, 무엇을 의도적으로 하지 않았는지)이 시간순으로 기록되어 있습니다. 코드나 커밋 이력만으로는 알 수 없는 배경 맥락(예: git 연결 방식, 문서 언어 선택 이유)을 담고 있으므로, 과거 결정을 뒤집거나 재논의하기 전에 반드시 확인하세요. 새로운 의사결정을 내렸다면 `DECISIONS.md`에 같은 형식으로 항목을 추가하세요.

## CLAUDE.md 정기 검토

`DECISIONS.md`를 읽을 때 아래 조건 중 하나라도 해당하면 `CLAUDE.md`와 `.claude/rules/*.md`를 함께 검토하세요. 문서가 실제 프로젝트 구조·관례와 조용히 어긋나는 것을 막기 위함입니다.

- **검토 트리거**: `DECISIONS.md`에서 제목에 "CLAUDE.md 검토"가 포함된 가장 최근 항목의 날짜가 오늘로부터 약 1개월 이상 지났을 때 / 그런 항목이 아직 없을 때 / 사용자가 "claude.md 검토해줘"처럼 명시적으로 요청할 때 / 주제 폴더(`spain_euro2024/` 같은) 착수·완료가 3회 이상 누적돼 아키텍처 서술이 낡았을 가능성이 클 때.
- **검토 절차**:
  1. `CLAUDE.md`와 `.claude/rules/*.md`를 처음부터 다시 읽는다.
  2. 실제 폴더 구조(주제 폴더 목록, `notebooks/`·`scripts/`·`data/` 내용)와 최근 `DECISIONS.md` 항목을 대조해, 문서가 서술하는 관례가 여전히 맞는지 확인한다.
  3. 어긋난 부분을 수정한다. 자주 참조하게 된 `.claude/rules/` 내용은 `CLAUDE.md` 본문으로 끌어올리고, 반대로 `CLAUDE.md`가 다시 길어졌다면 자주 쓰이지 않는 부분을 `.claude/rules/`로 옮긴다.
  4. 바뀐 내용이 있든 없든, 검토했다는 사실 자체를 `DECISIONS.md`에 "YYYY-MM-DD CLAUDE.md 검토" 항목으로 남긴다 (다음 검토 시점을 계산하는 기준점이 된다).

## 분석 워크플로우

새 분석 주제는 항상 3단계를 거칩니다: **아이디어 논의(`ideas/backlog.md`, 질문증강 방식) → 주제별 전용 폴더 생성(`PLAN.md` 포함, 예: `spain_euro2024/`) → 그 폴더 하위 `processed/`에서 산출물 관리**. 재사용 가능한 함수가 필요해지면 주제 폴더 안에서 바로 만들지 말고 `notebooks/`·`scripts/`·`data/`(공용 샌드박스)에서 먼저 프로토타입·테스트한 뒤 검증되면 `src/`로 승격해 커밋합니다.

각 단계의 세부 규칙(질문증강 화법, 폴더 명명, `PLAN.md` 구성, 산출물 경로, 샌드박스 사용법)은 착수 시점에 [`.claude/rules/analysis-workflow.md`](./.claude/rules/analysis-workflow.md)를 읽고 따르세요.

## 명령어

먼저 venv를 활성화하거나(PowerShell), 활성화 없이 `.venv\Scripts\python.exe` / `.venv\Scripts\jupyter.exe`를 직접 호출합니다:

```powershell
.\.venv\Scripts\Activate.ps1
```

예제 분석 전체 파이프라인 실행(StatsBomb에서 2022 월드컵 결승전 데이터를 가져와 `data/processed/`에 PNG로 저장):

```powershell
.\.venv\Scripts\python scripts/example_analysis.py
```

`notebooks/`의 대화형 노트북을 위한 JupyterLab 실행:

```powershell
.\.venv\Scripts\jupyter lab
```

의존성 설치/업데이트:

```powershell
.\.venv\Scripts\pip install -r requirements.txt
```

이 저장소에는 린트 설정, 테스트 스위트, 빌드 단계가 없습니다.

## 아키텍처

- `src/data_loader.py` — `statsbombpy` 래퍼 + pandas 필터 헬퍼(`filter_player_events`, `filter_team_events`). 인증·로컬 데이터 파일 없이 StatsBomb 무료 오픈 데이터 API만 사용합니다.
- `src/visualizer.py` — `mplsoccer` 기반 플로팅 함수들(`create_standard_pitch`, `plot_shot_map`, `plot_pass_map`, `plot_pizza_chart`, `plot_pass_network`). 디스크에 저장하지 않고 `(fig, ax)`를 반환하므로 저장은 호출부에서 `fig.savefig(...)`로 처리합니다.
- `scripts/` — `example_analysis.py`(최초 셋업 예제 파이프라인) + 새 기능을 독립 스크립트로 테스트하는 샌드박스.
- `notebooks/` — 스타터 노트북(`01`~`03`) + 새 함수를 `src/`로 승격하기 전 프로토타입하는 샌드박스. 주제별 분석은 여기가 아니라 전용 폴더에 둡니다.
- `data/processed/` — 스타터 노트북/`example_analysis.py`·샌드박스 테스트의 산출물이 쌓이는 공용 폴더. 주제별 분석의 정식 산출물은 해당 주제 폴더의 `processed/`에 저장합니다. `data/raw/`는 README에 언급된 원본 데이터용 위치이나 아직 존재하지 않습니다.
- `ideas/` — 분석 주제 백로그(`backlog.md`)를 관리하는 브레인스토밍 공간. 새 주제를 제안·착수할 때 상태(대기/구체화/진행중/완료/보류)를 함께 갱신하세요.
- 팀/주제별 전용 폴더(예: `spain_euro2024/`) — `ideas/backlog.md`에서 구체화된 주제에 착수하면 만드는 표준 폴더. `PLAN.md` + 노트북/스크립트 + `processed/`를 함께 둡니다.

`notebooks/`·`scripts/`의 샌드박스 사용법은 [`.claude/rules/analysis-workflow.md`](./.claude/rules/analysis-workflow.md), `data_loader`/`visualizer` 수정 시 필요한 StatsBomb 컬럼 규칙(좌표 언패킹, outcome 의미, 선수 이름/교체 처리)은 [`.claude/rules/statsbomb-data-notes.md`](./.claude/rules/statsbomb-data-notes.md)를 참고하세요.

## 참고 사항

- 소스 코드의 주석, 독스트링, README는 한글로 작성되어 있습니다. `src/`나 `scripts/`를 수정할 때 이 스타일을 따르세요.
- `scripts/example_analysis.py`는 Windows에서 한글을 올바르게 출력하기 위해 stdout을 UTF-8로 재설정합니다(`sys.stdout.reconfigure`). Windows에서 콘솔 출력을 추가할 때 이를 유지하세요.
