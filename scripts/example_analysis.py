"""Example Football Analysis Script
- 2022 카타르 월드컵 결승전 (아르헨티나 vs 프랑스) 데이터 분석 및 시각화 예제
"""
import os
import sys

# Windows 콘솔 인코딩 대응
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader import get_competition_matches, get_match_events
from src.visualizer import plot_shot_map, plot_pass_map, plot_pizza_chart
import matplotlib.pyplot as plt


def main():
    print("[1/4] StatsBomb에서 2022 카타르 월드컵 결승전 데이터 조회 중...")
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "processed")
    os.makedirs(output_dir, exist_ok=True)

    # 2022 FIFA World Cup (Competition ID: 43, Season ID: 106)
    matches = get_competition_matches(competition_id=43, season_id=106)
    final_match = matches[matches['competition_stage'] == 'Final'].iloc[0]
    
    match_id = final_match['match_id']
    print(f">> 경기 확인: {final_match['home_team']} {final_match['home_score']} : {final_match['away_score']} {final_match['away_team']} (Match ID: {match_id})")

    # 경기 이벤트 데이터 다운로드
    print("[2/4] 이벤트 데이터 로드 중...")
    events = get_match_events(match_id=match_id)
    print(f">> 총 {len(events)}개의 이벤트 데이터 로드 완료.")

    # 1. 아르헨티나 슈팅 맵 (xG 분석)
    print("[3/4] 시각화 생성 중: 슛 맵 & 패스 맵...")
    fig_shot, ax_shot = plot_shot_map(
        events_df=events,
        team_name="Argentina",
        title="2022 World Cup Final: Argentina Shot & xG Map"
    )
    shot_output_path = os.path.join(output_dir, "argentina_shot_map.png")
    fig_shot.savefig(shot_output_path, dpi=300, bbox_inches='tight')
    plt.close(fig_shot)
    print(f"  -> 슈팅 맵 저장 완료: {shot_output_path}")

    # 2. 리오넬 메시 패스 맵
    fig_pass, ax_pass = plot_pass_map(
        events_df=events,
        player_name="Lionel Andrés Messi Cuccittini",
        title="Lionel Messi - Pass Map (2022 WC Final vs France)"
    )
    pass_output_path = os.path.join(output_dir, "messi_pass_map.png")
    fig_pass.savefig(pass_output_path, dpi=300, bbox_inches='tight')
    plt.close(fig_pass)
    print(f"  -> 메시 패스 맵 저장 완료: {pass_output_path}")

    # 3. 레이더 피자 차트 예시
    print("[4/4] 시각화 생성 중: 선수 피자(레이더) 차트...")
    params = [
        "Non-Penalty Goals", "xG (Expected Goals)", "Shots Total",
        "Key Passes", "Passes into Penalty Area", "Progressive Passes",
        "Successful Dribbles", "Tackles Won"
    ]
    values = [92, 88, 94, 98, 96, 95, 89, 45]
    fig_pizza, ax_pizza = plot_pizza_chart(
        params=params,
        values=values,
        player_name="Lionel Messi",
        sub_title="2022 World Cup Percentile Rank vs Attacking Midfielders / Wingers"
    )
    pizza_output_path = os.path.join(output_dir, "messi_radar_pizza.png")
    fig_pizza.savefig(pizza_output_path, dpi=300, bbox_inches='tight')
    plt.close(fig_pizza)
    print(f"  -> 피자 차트 저장 완료: {pizza_output_path}")

    print("\n[SUCCESS] 모든 분석 및 시각화 생성이 성공적으로 완료되었습니다!")


if __name__ == "__main__":
    main()
