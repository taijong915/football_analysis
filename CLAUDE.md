# CLAUDE.md

이 파일은 이 저장소에서 작업할 때 Claude Code(claude.ai/code)에게 제공되는 가이드입니다.

## 프로젝트 개요

StatsBomb 이벤트/추적 데이터를 불러와 피치 시각화(슛 맵, 패스 맵, 레이더/피자 차트)를 생성하는 Python 축구 분석 환경입니다. GitHub 저장소 `taijong915/football_analysis`의 `main` 브랜치에 연결되어 있습니다.

## 세션 시작 시 필독

**매 세션 시작 시 [`DECISIONS.md`](./DECISIONS.md)를 먼저 읽고 시작하세요.** 이 프로젝트의 주요 의사결정(왜 이렇게 구성했는지, 무엇을 의도적으로 하지 않았는지)이 시간순으로 기록되어 있습니다. 코드나 커밋 이력만으로는 알 수 없는 배경 맥락(예: git 연결 방식, 문서 언어 선택 이유)을 담고 있으므로, 과거 결정을 뒤집거나 재논의하기 전에 반드시 확인하세요. 새로운 의사결정을 내렸다면 `DECISIONS.md`에 같은 형식으로 항목을 추가하세요.

## 아이디어 도출 시 역할

`ideas/`(분석 주제 브레인스토밍)와 관련된 대화에서는 답을 바로 나열하는 대신 **질문증강(question augmentation) 방식**으로 소통하세요. 즉, 사용자가 던진 주제나 관심사를 곧장 완성된 아이디어 목록으로 바꾸지 말고, 되묻는 질문을 통해 사용자 스스로 생각을 구체화하도록 돕는 역할을 합니다.

- 사용자가 막연한 관심사(예: "메시 관련해서 뭔가 해보고 싶어")를 던지면, 바로 아이디어를 제안하기보다 관점을 넓히거나 좁히는 질문을 먼저 던지세요 — 어떤 대회/시즌에 관심 있는지, 개인 기록 중심인지 팀 전술 맥락인지, 이미 본 적 없는 새로운 인사이트를 원하는지 등.
- 여러 질문을 한 번에 쏟아내지 말고, 답변에 따라 다음 질문을 이어가며 대화로 좁혀가세요.
- 사용자가 충분히 구체화됐다고 판단되면 정리한 내용을 `ideas/backlog.md`의 형식(분석 질문/필요 데이터/예상 산출물)으로 요약해 제안하고, 사용자 확인 후 `구체화` 상태로 기록하세요.
- 사용자가 명시적으로 "그냥 아이디어를 던져줘/브레인스토밍해줘"라고 요청하면 질문 없이 바로 아이디어 목록을 제시해도 됩니다 — 이 방식은 기본값이지 강제 규칙이 아닙니다.

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
- `scripts/example_analysis.py` — 노트북이 아닌 실행 가능한 스크립트로, 의도된 파이프라인을 보여줍니다: `data_loader`로 데이터 조회 → `visualizer`로 플롯 생성 → `data/processed/`에 PNG 저장. 프로젝트가 `pip install -e`로 설치되어 있지 않으므로 `sys.path.append`를 사용해 `src`를 패키지로 임포트합니다.
- `notebooks/` — 동일한 파이프라인 단계(StatsBomb 기초/xG, 피치 시각화, 레이더/피자 차트)를 대화형으로 다루는 탐색용 노트북입니다. 자동 실행 대상이 아니라 대화형 탐색용입니다.
- `data_loader`/`visualizer` 코드를 수정할 때 알아야 할 StatsBomb 이벤트 데이터 규칙: 좌표는 `location`(및 `pass_end_location` 등) 컬럼에 `[x, y]` 리스트 형태로 들어오며 `.apply(lambda loc: loc[0] if isinstance(loc, list) else np.nan)`로 언패킹해야 합니다. 결과(outcome) 컬럼(예: `pass_outcome`)은 성공 시 `NaN`, 실패/기타 결과일 때 문자열입니다.
- 생성된 시각화 이미지는 `data/processed/`에 커밋되어 있습니다. `data/raw/`는 다운로드한 원본 데이터를 위한 위치로 README에 언급되어 있으나 아직 존재하지 않습니다.
- `ideas/` — 분석 주제 아이디어를 백로그(`backlog.md`)로 관리하는 브레인스토밍 공간입니다. 코드가 아니라 문서만 있습니다. 새 분석 주제를 제안하거나 착수할 때는 이곳의 상태(대기/구체화/진행중/완료/보류)를 함께 갱신하세요.

## 참고 사항

- 소스 코드의 주석, 독스트링, README는 한글로 작성되어 있습니다. `src/`나 `scripts/`를 수정할 때 이 스타일을 따르세요.
- `scripts/example_analysis.py`는 Windows에서 한글을 올바르게 출력하기 위해 stdout을 UTF-8로 재설정합니다(`sys.stdout.reconfigure`). Windows에서 콘솔 출력을 추가할 때 이를 유지하세요.
