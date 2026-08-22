# CLAUDE.md

이 파일은 이 저장소에서 작업할 때 Claude Code(claude.ai/code)에게 제공되는 가이드입니다.

## 프로젝트 개요

StatsBomb 이벤트/추적 데이터를 불러와 피치 시각화(슛 맵, 패스 맵, 레이더/피자 차트)를 생성하는 Python 축구 분석 환경입니다. GitHub 저장소 `taijong915/football_analysis`의 `main` 브랜치에 연결되어 있습니다.

## 세션 시작 시 필독

**매 세션 시작 시 [`DECISIONS.md`](./DECISIONS.md)를 먼저 읽고 시작하세요.** 이 프로젝트의 주요 의사결정(왜 이렇게 구성했는지, 무엇을 의도적으로 하지 않았는지)이 시간순으로 기록되어 있습니다. 코드나 커밋 이력만으로는 알 수 없는 배경 맥락(예: git 연결 방식, 문서 언어 선택 이유)을 담고 있으므로, 과거 결정을 뒤집거나 재논의하기 전에 반드시 확인하세요. 새로운 의사결정을 내렸다면 `DECISIONS.md`에 같은 형식으로 항목을 추가하세요.

## 분석 워크플로우

이 프로젝트에서 새 분석 주제는 항상 다음 3단계를 거칩니다: **아이디어 논의(`ideas/backlog.md`) → 분석 주제 폴더 및 파일 구성 → 해당 폴더 안에서 산출물 관리**. 아래 각 단계를 순서대로 따르세요.

### 1단계 — 아이디어 논의 (`ideas/backlog.md`)

`ideas/`(분석 주제 브레인스토밍)와 관련된 대화에서는 답을 바로 나열하는 대신 **질문증강(question augmentation) 방식**으로 소통하세요. 즉, 사용자가 던진 주제나 관심사를 곧장 완성된 아이디어 목록으로 바꾸지 말고, 되묻는 질문을 통해 사용자 스스로 생각을 구체화하도록 돕는 역할을 합니다.

- 사용자가 막연한 관심사(예: "메시 관련해서 뭔가 해보고 싶어")를 던지면, 바로 아이디어를 제안하기보다 관점을 넓히거나 좁히는 질문을 먼저 던지세요 — 어떤 대회/시즌에 관심 있는지, 개인 기록 중심인지 팀 전술 맥락인지, 이미 본 적 없는 새로운 인사이트를 원하는지 등.
- 여러 질문을 한 번에 쏟아내지 말고, 답변에 따라 다음 질문을 이어가며 대화로 좁혀가세요.
- 사용자가 충분히 구체화됐다고 판단되면 정리한 내용을 `ideas/backlog.md`의 형식(분석 질문/필요 데이터/예상 산출물)으로 요약해 제안하고, 사용자 확인 후 `구체화` 상태로 기록하세요.
- 사용자가 명시적으로 "그냥 아이디어를 던져줘/브레인스토밍해줘"라고 요청하면 질문 없이 바로 아이디어 목록을 제시해도 됩니다 — 이 방식은 기본값이지 강제 규칙이 아닙니다.

### 2단계 — 분석 주제 폴더 및 파일 구성

`구체화` 상태의 아이디어에 실제로 착수할 때는 프로젝트 루트에 주제별 전용 폴더를 새로 만듭니다(예: `spain_euro2024/`). 이 폴더가 해당 주제의 노트북·스크립트·산출물을 모두 담는 단위가 됩니다.

- 폴더 이름은 팀/주제 + 대회·시즌처럼 짧고 식별 가능하게 짓습니다(예: `spain_euro2024`, `messi_barcelona_career`).
- 폴더 안에 `PLAN.md`(분석 기획 문서)를 먼저 작성합니다. 배경, 분석 질문, 데이터 범위, 방법론 요약, 예상 산출물, 진행 상황 체크리스트, 한계를 담습니다. `spain_euro2024/PLAN.md`를 템플릿으로 참고하세요.
- 노트북/스크립트는 폴더 최상위에 둡니다.
- `ideas/backlog.md`의 해당 항목 상태를 `진행중`으로 바꾸고, 새로 만든 `PLAN.md`로 링크를 겁니다. 착수 시점의 폴더 구조 결정은 필요하다면 `DECISIONS.md`에도 기록하세요.

### 3단계 — 해당 분석 폴더 안에서 산출물 관리

착수 이후의 모든 산출물(이미지, 표, 중간 결과 문서)은 해당 주제 폴더 하위 `processed/`에 저장합니다. `data/processed/`처럼 프로젝트 공용 폴더에 흩어 놓지 않습니다.

- 노트북에서 저장 경로를 잡을 때는 프로젝트 루트가 아니라 해당 주제 폴더를 기준으로 상대 경로를 구성하세요(`spain_euro2024/04_spain_euro2024_buildup.ipynb`의 `output_dir` 셀 참고).
- 분석이 진행되며 얻은 관찰/결론은 `PLAN.md`의 진행 상황 체크리스트를 갱신하거나, 필요하면 `processed/` 안에 별도 요약 문서를 추가해 기록합니다.
- 분석이 마무리되면 `ideas/backlog.md`의 상태를 `완료`로 갱신하세요.

이 워크플로우는 `ideas/backlog.md`에서 출발하는 주제별 분석에 적용됩니다. `notebooks/01~03`과 `scripts/example_analysis.py`는 프로젝트 최초 셋업 시 만들어진 스타터/예제 자료이므로 이 흐름과 무관하게 그대로 둡니다.

### 기능 개발/테스트 샌드박스 (`notebooks/`, `scripts/`, `data/`)

`notebooks/`, `scripts/`, `data/`는 특정 주제 폴더에 속하지 않는 공용 샌드박스입니다. 재사용 가능한 함수를 만들고 버전 관리(`src/`로 승격 후 커밋)하거나, 주제 분석 중 필요해진 새 기능을 주제 폴더에 넣기 전에 실험/테스트하는 용도로 씁니다.

- 주제 분석(2~3단계) 도중 `src/`에 넣을 만한 새 함수(예: 새로운 시각화 유형, 데이터 로더 헬퍼)가 필요해지면, 주제 폴더 안에서 바로 만들지 말고 먼저 `notebooks/`(대화형 프로토타입) 또는 `scripts/`(독립 실행 스크립트)에서 구현·테스트하세요. 여러 주제에서 재사용할 코드를 특정 주제 폴더에 묶어두면 나중에 다른 분석에서 찾기 어렵습니다.
- 테스트 과정에서 필요한 중간 데이터나 예제 출력은 `data/`에 둡니다. 주제별 정식 산출물이 아니라 검증 과정의 부산물이라는 점에서 주제 폴더의 `processed/`와 구분됩니다.
- 함수가 검증되면 `src/data_loader.py` 또는 `src/visualizer.py`로 옮겨 정식 커밋합니다 — 이 시점부터 다른 주제 폴더에서도 재사용 가능한 정식 함수가 됩니다. 프로토타입이었던 노트북/스크립트는 지우지 말고 남겨, 그 함수가 어떤 실험을 거쳐 만들어졌는지 추적할 수 있게 하세요.
- 새 프로토타입 파일은 무엇을 테스트하는지 알 수 있는 이름으로 만드세요(예: `notebooks/test_zone_heatmap.ipynb`). 기존 스타터 노트북(`01`~`03`)·`scripts/example_analysis.py`와 섞이지 않도록 구분되는 이름을 씁니다.

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

- `src/data_loader.py` — `statsbombpy`(`sb.competitions`, `sb.matches`, `sb.events`, `sb.lineups`)를 감싼 얇은 래퍼와 pandas 필터 헬퍼(`filter_player_events`, `filter_team_events`)로 구성됩니다. 모든 데이터 접근은 StatsBomb의 무료 오픈 데이터 API를 통하며, 로컬 데이터 파일이나 인증이 필요 없습니다.
- `src/visualizer.py` — `mplsoccer` 기반 플로팅 함수들(`create_standard_pitch`, `plot_shot_map`, `plot_pass_map`, `plot_pizza_chart`). 각 함수는 디스크에 저장하지 않고 `(fig, ax)`(또는 `create_standard_pitch`의 경우 `(Pitch, fig, ax)`)를 반환하므로, 저장은 호출부에서 `fig.savefig(...)`로 처리해야 합니다.
- `scripts/` — `example_analysis.py`는 노트북이 아닌 실행 가능한 스크립트로, 의도된 파이프라인을 보여줍니다: `data_loader`로 데이터 조회 → `visualizer`로 플롯 생성 → `data/processed/`에 PNG 저장. 프로젝트가 `pip install -e`로 설치되어 있지 않으므로 `sys.path.append`를 사용해 `src`를 패키지로 임포트합니다. 최초 셋업 시 만들어진 예제 자료입니다. 이 폴더는 동시에 새 기능을 독립 스크립트 형태로 테스트하는 샌드박스이기도 합니다(위 "기능 개발/테스트 샌드박스" 참고).
- `notebooks/` — 두 종류가 섞여 있습니다: ① 대화형 탐색용 스타터 노트북(`01`~`03`, StatsBomb 기초/xG, 피치 시각화, 레이더/피자 차트), ② 새 함수를 `src/`로 승격하기 전 프로토타입·테스트하는 샌드박스(위 "기능 개발/테스트 샌드박스" 참고). 둘 다 자동 실행 대상이 아닙니다. `ideas/backlog.md`에서 출발한 주제별 분석은 여기가 아니라 전용 폴더에 둡니다.
- `data_loader`/`visualizer` 코드를 수정할 때 알아야 할 StatsBomb 이벤트 데이터 규칙: 좌표는 `location`(및 `pass_end_location` 등) 컬럼에 `[x, y]` 리스트 형태로 들어오며 `.apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)`로 언패킹해야 합니다. 결과(outcome) 컬럼(예: `pass_outcome`)은 성공 시 `NaN`, 실패/기타 결과일 때 문자열입니다.
- `data/processed/` — 스타터 노트북/`scripts/example_analysis.py`가 만드는 시각화 이미지, 그리고 함수 테스트 과정에서 나오는 중간 산출물이 쌓이는 공용 폴더입니다. 주제별 분석의 정식 산출물은 여기가 아니라 해당 주제 폴더의 `processed/` 하위에 저장합니다(위 "분석 워크플로우" 참고). `data/raw/`는 다운로드한 원본 데이터를 위한 위치로 README에 언급되어 있으나 아직 존재하지 않습니다.
- `ideas/` — 분석 주제 아이디어를 백로그(`backlog.md`)로 관리하는 브레인스토밍 공간입니다. 코드가 아니라 문서만 있습니다. 새 분석 주제를 제안하거나 착수할 때는 이곳의 상태(대기/구체화/진행중/완료/보류)를 함께 갱신하세요.
- 팀/주제별 전용 폴더(예: `spain_euro2024/`) — `ideas/backlog.md`에서 구체화된 주제에 착수하면 만드는 표준 폴더입니다. 절차는 위 "분석 워크플로우" 2~3단계를 따르세요: 폴더 안에 기획 문서(`PLAN.md`), 노트북/스크립트, 산출물(`processed/`)을 함께 둡니다.

## 참고 사항

- 소스 코드의 주석, 독스트링, README는 한글로 작성되어 있습니다. `src/`나 `scripts/`를 수정할 때 이 스타일을 따르세요.
- `scripts/example_analysis.py`는 Windows에서 한글을 올바르게 출력하기 위해 stdout을 UTF-8로 재설정합니다(`sys.stdout.reconfigure`). Windows에서 콘솔 출력을 추가할 때 이를 유지하세요.
