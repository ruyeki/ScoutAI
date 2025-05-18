import os
import sqlite3
import pandas as pd
from flask import Blueprint, jsonify

chart_bp = Blueprint("chart_bp", __name__)

# Database path (in the same folder as the backend folder)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ucd-basketball.db"))

def get_player_stats_for_team(team):
    try:
        conn = sqlite3.connect(DB_PATH)
        query = f"""
        SELECT 
            "Player Name", "Minutes/gm", "PTS/gm", "Assists/gm", "Turnovers/gm", "STL/gm", "BLK/gm", "Image URL"
        FROM "{team}_player_stats"
        """
        player_stats = pd.read_sql_query(query, conn)
        player_stats = player_stats.fillna('')
        data = []
        for _, row in player_stats.iterrows():
            try:
                data.append({
                    "player": row['Player Name'],
                    "mpg": float(row['Minutes/gm']),
                    "ppg": float(row['PTS/gm']),
                    "apg": float(row['Assists/gm']),
                    "topg": float(row['Turnovers/gm']),
                    "spg": float(row['STL/gm']),
                    "bpg": float(row['BLK/gm']),
                    "image": row['Image URL']
                })
            except Exception as e:
                print("Skipped row due to error:", e)
        conn.close()
        return data
    except Exception as e:
        print(f"Error fetching data for team {team}:", e)
        return []

@chart_bp.route('/api/player-efficiency/<team>')
def player_efficiency_by_team(team):
    data = get_player_stats_for_team(team)
    return jsonify(data)

@chart_bp.route('/api/player-efficiency')
def player_efficiency():
    data = get_player_stats_for_team('UCDavis')
    return jsonify(data)
