from flask import Blueprint, jsonify
import pandas as pd
import sqlite3
import os

radar_chart_bp = Blueprint("radar_chart_bp", __name__)

def normalize_stats(row):
    max_values = {
        "Points": 90,
        "FG%": 100,
        "3PT": 12,
        "Rebounds": 45,
        "Assists": 25,
        "Steals": 12,
        "Blocks": 10
    }
    return {
        "Points": 100 * row["PTS/gm"] / max_values["Points"],
        "FG%": row["FG%"],  # Already a percentage
        "3PT": 100 * row["3PT/gm"] / max_values["3PT"],
        "Rebounds": 100 * row["REB/gm"] / max_values["Rebounds"],
        "Assists": 100 * row["Assists/gm"] / max_values["Assists"],
        "Steals": 100 * row["STL/gm"] / max_values["Steals"],
        "Blocks": 100 * row["BLK/gm"] / max_values["Blocks"],
    }

@radar_chart_bp.route('/api/radar-chart/<team_name>')
def radar_chart(team_name):
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ucd-basketball.db"))
    conn = sqlite3.connect(db_path)
    team_df = pd.read_sql_query("SELECT * FROM TeamStats WHERE team = ?", conn, params=(team_name,))
    conn.close()

    if team_df.empty:
        return jsonify({"error": "Team not found"}), 404

    normalized = normalize_stats(team_df.iloc[0])
    return jsonify({"team": team_name, "normalized_stats": normalized})

@radar_chart_bp.route('/api/raw-team-stats/<team_name>')
def raw_team_stats(team_name):
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ucd-basketball.db"))
    conn = sqlite3.connect(db_path)
    team_df = pd.read_sql_query("SELECT * FROM TeamStats WHERE team = ?", conn, params=(team_name,))
    conn.close()

    if team_df.empty:
        return jsonify({"error": "Team not found"}), 404

    raw_data = team_df.iloc[0].to_dict()
    return jsonify({"team": team_name, "raw_stats": raw_data})
  

@radar_chart_bp.route('/api/radar-chart/conference-average')
def radar_chart_conference_average():
    db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ucd-basketball.db"))
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM TeamStats", conn)
    conn.close()

    if df.empty:
        return jsonify({"error": "No data available"}), 404

    max_values = {
        "Points": 90,
        "FG%": 100,
        "3PT": 12,
        "Rebounds": 45,
        "Assists": 25,
        "Steals": 12,
        "Blocks": 10
    }

    # Calculate averages for each stat (no extra *100)
    avg_stats = {
        "Points": df["PTS/gm"].mean(),
        "FG%": df["FG%"].mean(),  # Already a percentage
        "3PT": df["3PT/gm"].mean(),
        "Rebounds": df["REB/gm"].mean(),
        "Assists": df["Assists/gm"].mean(),
        "Steals": df["STL/gm"].mean(),
        "Blocks": df["BLK/gm"].mean(),
    }

    # Normalize relative to max values
    normalized = {
        "Points": 100 * avg_stats["Points"] / max_values["Points"],
        "FG%": avg_stats["FG%"],  # already scaled
        "3PT": 100 * avg_stats["3PT"] / max_values["3PT"],
        "Rebounds": 100 * avg_stats["Rebounds"] / max_values["Rebounds"],
        "Assists": 100 * avg_stats["Assists"] / max_values["Assists"],
        "Steals": 100 * avg_stats["Steals"] / max_values["Steals"],
        "Blocks": 100 * avg_stats["Blocks"] / max_values["Blocks"]
    }

    return jsonify({
        "normalized_stats": normalized,
        "comparison": "conference_average"
    })

