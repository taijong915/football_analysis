"""구역 기반 전진 경로(zone progression) 프로토타입

피치를 mplsoccer의 Juego de Posición(포지션 플레이) 그리드로 나눈다 —
`Pitch(positional=True)`가 그리는 표준 그리드를 그대로 쓴다(참고:
https://spielverlagerung.com/2014/11/26/juego-de-posicion-a-short-explanation/).
30구역별 패스 시작 위치 점유를 배경 음영으로, 구역 간 전진 패스 전환을 화살표로
피치 하나 위에 함께 표시한다. 처음엔 화살표 피치 + 별도 imshow 히트맵 패널로
분리했으나, 두 좌표계가 어긋나 보인다는 지적을 받아 하나의 피치 좌표계로 통합했다.

검증을 마치고 src/visualizer.py의 plot_zone_progression()으로 승격했다.
이 스크립트는 그 승격 과정을 추적할 수 있도록 남겨둔 것으로, 이제는 승격된 함수를
그대로 가져다 써서 결승전 샘플을 재생성한다.
spain_euro2024/PLAN.md "구역 기반 전진 경로" 항목 참고.
산출물은 zone_progression/ 하위 폴더에 저장한다.
"""
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')

from src.data_loader import get_match_events
from src.visualizer import plot_zone_progression

if __name__ == '__main__':
    match_id = 3943043  # 2024 유로 결승 Spain vs England
    events = get_match_events(match_id=match_id)

    fig, ax = plot_zone_progression(
        events_df=events, team_name='Spain',
        title='Spain Zone Progression - Final vs England',
    )

    out_dir = os.path.join('spain_euro2024', 'zone_progression', 'processed')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'spain_zone_progression_euro2024_final_prototype.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
    print('saved', out_path)
