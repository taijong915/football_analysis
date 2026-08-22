"""포지션(역할) 기반 패스 네트워크 프로토타입

선수 이름 대신 포지션 슬롯(예: Right Defensive Midfield)을 노드로 삼아
교체와 무관하게 경기 전체 패스를 합산하는 방식을 검증했다. 결과 이미지 옆에는
실제 교체가 어떻게 이루어졌는지(포지션별 로스터 + 교체 시각)도 함께 표시한다.

검증을 마치고 src/visualizer.py의 plot_pass_network_by_position()으로 승격했다.
이 스크립트는 그 승격 과정을 추적할 수 있도록 남겨둔 것으로, 이제는 승격된 함수를
그대로 가져다 써서 2024 유로 결승 샘플을 재생성한다.
spain_euro2024/PLAN.md "position 컬럼 기반 대안" 항목 참고.
산출물은 pass_network/ 하위 폴더에 저장한다 (spain_euro2024/PLAN.md, .claude/rules/analysis-workflow.md 참고).
"""
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')

from src.data_loader import get_match_events, get_match_lineups
from src.visualizer import plot_pass_network_by_position

if __name__ == '__main__':
    match_id = 3943043  # 2024 유로 결승 Spain vs England
    events = get_match_events(match_id=match_id)
    lineup = get_match_lineups(match_id=match_id)['Spain']

    fig, axes = plot_pass_network_by_position(
        events_df=events, team_name='Spain', lineup_df=lineup,
        title='Spain Pass Network by Position - Final vs England (Full Match)',
    )

    out_dir = os.path.join('spain_euro2024', 'pass_network', 'processed')
    out_path = os.path.join(out_dir, 'spain_pass_network_euro2024_final_by_position.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
    print('saved', out_path)
