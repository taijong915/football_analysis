# ⚽ 축구 데이터 분석 환경 (Football Analytics Lab)

축구 이벤트 데이터, 추적(Tracking) 데이터, 선수 및 팀 스탯 분석과 시각화를 위한 Python 기반 올인원 축구 데이터 분석 환경입니다.

---

## 📁 프로젝트 구조

```text
Football/
├── .venv/                         # 파이썬 가상환경 (football_analytics 커널 등록됨)
├── data/
│   ├── raw/                       # 원본 데이터 저장소
│   └── processed/                 # 전처리 데이터 및 생성된 시각화 이미지 (.png)
├── notebooks/                     # 대화형 주피터 노트북
│   ├── 01_statsbomb_starter.ipynb      # StatsBomb 오픈 데이터 기초 및 xG 분석
│   ├── 02_pitch_visualizations.ipynb   # 패스 맵, 슈팅 맵, 히트맵 시각화 가이드
│   └── 03_player_radar_chart.ipynb     # 선수 스탯 피자(레이더) 차트
├── src/                           # 재사용 가능한 모듈
│   ├── data_loader.py             # 데이터 로더 유틸리티 (StatsBomb 등)
│   └── visualizer.py              # mplsoccer 기반 경기장 & 차트 시각화 함수
├── scripts/
│   └── example_analysis.py        # 2022 카타르 월드컵 결승전 분석 및 이미지 생성 스크립트
├── requirements.txt               # 패키지 의존성 목록
└── README.md
```

---

## 🚀 시작하기

### 1. 가상환경 활성화

터미널(PowerShell)에서 아래 명령어로 가상환경을 활성화할 수 있습니다:
```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. JupyterLab 실행

브라우저에서 대화형 분석 환경을 실행하려면:
```powershell
.\.venv\Scripts\jupyter lab
```
> **VS Code / Cursor / Antigravity 사용 시**: 노트북(`.ipynb`) 파일을 열고 우측 상단 커널 선택에서 **`Python (Football Analytics)`** 또는 **`.venv`**를 선택하시면 바로 실행 가능합니다.

### 3. 예제 스크립트 실행

2022 카타르 월드컵 결승전(아르헨티나 vs 프랑스) 데이터 분석 및 시각화 이미지를 생성합니다:
```powershell
.\.venv\Scripts\python scripts/example_analysis.py
```
실행 결과물은 `data/processed/` 폴더에 이미지 파일로 저장됩니다:
- `argentina_shot_map.png` (슈팅 맵 & xG 분석)
- `messi_pass_map.png` (메시 패스 성공/실패 맵)
- `messi_radar_pizza.png` (선수 스탯 백분위수 피자 차트)

---

## 📚 주요 라이브러리 및 데이터 소스

| 라이브러리 / 소스 | 설명 | 주요 용도 |
| :--- | :--- | :--- |
| **`mplsoccer`** | 축구 전문 시각화 라이브러리 | 피치 렌더링, 패스 맵, 슛 맵, 히트맵, 피자 차트, 패스 소나 |
| **`statsbombpy`** | StatsBomb Open Data 공식 API | 월드컵, 챔피언스리그, 메시 커리어 전 경기 무료 고품질 이벤트 데이터 |
| **`soccerdata`** | 웹 데이터 스크래핑 래퍼 | FBref, Understat, ClubElo, MatchHistory, WhoScored 등 데이터 수집 |
| **`pandas` / `numpy`** | 데이터 처리 및 수치 계산 | 경기 이벤트 필터링, 선수별/팀별 집계 |
| **`scikit-learn`** | 머신러닝 라이브러리 | xG(기대 득점) 모델링, xT(기대 위협) 분석 등 |

---

## 💡 추천 다음 단계

1. `notebooks/01_statsbomb_starter.ipynb`를 열어 원하는 경기나 선수의 이벤트 데이터를 탐색해보세요.
2. `src/visualizer.py`에 원하는 커스텀 축구 시각화(패스 네트워크, 수비 액션 등) 함수를 추가해보세요.
3. 관심 있는 리그(프리미어리그, K리그, 라리가 등)의 데이터를 수집하여 팀별 전술 비교 리포트를 작성해보세요.
