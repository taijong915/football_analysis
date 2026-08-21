"""Football Data Loading Utilities (StatsBomb Open Data, FBref, etc.)
"""
import pandas as pd
from statsbombpy import sb
from typing import Optional, List, Dict, Any


def get_available_competitions() -> pd.DataFrame:
    """StatsBomb 오픈 데이터에서 이용 가능한 모든 대회 목록을 조회합니다."""
    comps = sb.competitions()
    return comps[['competition_id', 'season_id', 'country_name', 'competition_name', 'season_name', 'match_available']]


def get_competition_matches(competition_id: int, season_id: int) -> pd.DataFrame:
    """특정 대회의 시즌 경기 목록을 조회합니다."""
    return sb.matches(competition_id=competition_id, season_id=season_id)


def get_match_events(match_id: int, split: bool = False) -> pd.DataFrame:
    """특정 경기의 모든 이벤트 데이터를 가져옵니다.

    Args:
        match_id (int): 경기 ID
        split (bool): 이벤트 타입별로 분리해서 가져올지 여부 (기본값: False)

    Returns:
        pd.DataFrame or dict: 이벤트 데이터프레임
    """
    return sb.events(match_id=match_id, split=split)


def get_match_lineups(match_id: int) -> Dict[str, pd.DataFrame]:
    """특정 경기의 양 팀 라인업 및 선수 정보를 조회합니다."""
    return sb.lineups(match_id=match_id)


def filter_player_events(events_df: pd.DataFrame, player_name: str, event_type: Optional[str] = None) -> pd.DataFrame:
    """특정 선수의 이벤트 데이터를 필터링합니다."""
    df = events_df[events_df['player'] == player_name]
    if event_type:
        df = df[df['type'] == event_type]
    return df


def filter_team_events(events_df: pd.DataFrame, team_name: str, event_type: Optional[str] = None) -> pd.DataFrame:
    """특정 팀의 이벤트 데이터를 필터링합니다."""
    df = events_df[events_df['team'] == team_name]
    if event_type:
        df = df[df['type'] == event_type]
    return df
