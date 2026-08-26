"""possession 체인 추적(possession_chains) 프로토타입

같은 possession 안에서 팀의 성공 패스가 2회 이상 이어진 진짜 빌드업 체인만
걸러 구역 점유/전진 화살표를 그린다 - plot_zone_progression()과 달리 possession
구분 없이 매치 전체를 집계하지 않는다. 오른쪽에는 왼쪽/오른쪽으로 끝난 가장 긴
체인 1개씩을 실제 좌표 그대로 이은 미니 패널을 별도로 붙여, "왼쪽 진출 루트가
몇 번의 패스를 거치는지"(분석 질문 6)를 구체적 사례로 보여준다. 대표 체인을
메인 히트맵 위에 겹쳐 그려봤으나 왔다갔다하는 패스가 많은 체인은 선이 기존
화살표와 뒤섞여 못 알아볼 정도로 지저분해져, 겹치지 않는 별도 미니 패널로
분리하는 형태로 확정했다.

검증을 마치고 src/visualizer.py의 plot_possession_chain_progression()으로
승격했다. 이 스크립트는 그 승격 과정을 추적할 수 있도록 남겨둔 것으로, 이제는
승격된 함수를 그대로 가져다 써서 결승전 샘플을 재생성한다.
spain_euro2024/PLAN.md "possession 체인 추적" 항목 참고.
"""
import os
import sys

if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib
matplotlib.use('Agg')

from src.data_loader import get_match_events
from src.visualizer import plot_possession_chain_progression

if __name__ == '__main__':
    match_id = 3943043  # 2024 유로 결승 Spain vs England
    events = get_match_events(match_id=match_id)

    fig, axd, summary = plot_possession_chain_progression(
        events_df=events, team_name='Spain',
        title='Spain Possession Chain Progression - Final vs England',
    )

    print('체인 길이(패스 수) 분포 - 마지막 패스 도착 구역의 좌/중/우 채널별:')
    print(summary.groupby('final_side')['n_passes'].agg(['count', 'mean', 'median', 'max']))

    out_dir = os.path.join('data', 'possession_chains_prototype')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'spain_possession_chains_euro2024_final_prototype.png')
    fig.savefig(out_path, dpi=150, bbox_inches='tight', facecolor='#1e1e1e')
    print('saved', out_path)
