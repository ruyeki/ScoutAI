from flask import Blueprint, jsonify
import pandas as pd
import sqlite3

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
        "Points": 100 * row["AVG_PTS"] / max_values["Points"],
        "FG%": 100 * row["FG_PCT"],
        "3PT": 100 * (row["TOT_3PT"] / row["TOT_GP"]) / max_values["3PT"],
        "Rebounds": 100 * row["AVG_REBS"] / max_values["Rebounds"],
        "Assists": 100 * (row["TOT_AST"] / row["TOT_GP"]) / max_values["Assists"],
        "Steals": 100 * (row["TOT_STL"] / row["TOT_GP"]) / max_values["Steals"],
        "Blocks": 100 * (row["TOT_BLK"] / row["TOT_GP"]) / max_values["Blocks"],
    }

@radar_chart_bp.route('/api/radar-chart/<team_name>')
def radar_chart(team_name):
    conn = sqlite3.connect("ucd-basketball.db")
    team_df = pd.read_sql_query("SELECT * FROM TeamStats WHERE team = ?", conn, params=(team_name,))
    conn.close()

    if team_df.empty:
        return jsonify({"error": "Team not found"}), 404

    normalized = normalize_stats(team_df.iloc[0])
    return jsonify({"team": team_name, "normalized_stats": normalized})

@radar_chart_bp.route('/api/raw-team-stats/<team_name>')
def raw_team_stats(team_name):
    conn = sqlite3.connect("ucd-basketball.db")
    team_df = pd.read_sql_query("SELECT * FROM TeamStats WHERE team = ?", conn, params=(team_name,))
    conn.close()

    if team_df.empty:
        return jsonify({"error": "Team not found"}), 404

    raw_data = team_df.iloc[0].to_dict()
    return jsonify({"team": team_name, "raw_stats": raw_data})
  

@radar_chart_bp.route('/api/radar-chart/conference-average')
def radar_chart_conference_average():
    conn = sqlite3.connect("ucd-basketball.db")
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

    # Calculate averages for each stat
    avg_stats = {
        "Points": df["AVG_PTS"].mean(),
        "FG%": df["FG_PCT"].mean() * 100,
        "3PT": ((df["TOT_3PT"] / df["TOT_GP"]).mean()) * 100,
        "Rebounds": df["AVG_REBS"].mean(),
        "Assists": ((df["TOT_AST"] / df["TOT_GP"]).mean()) * 100,
        "Steals": ((df["TOT_STL"] / df["TOT_GP"]).mean()) * 100,
        "Blocks": ((df["TOT_BLK"] / df["TOT_GP"]).mean()) * 100,
    }

    # Normalize relative to max values
    normalized = {
        "Points": 100 * avg_stats["Points"] / max_values["Points"],
        "FG%": avg_stats["FG%"],  # already scaled
        "3PT": avg_stats["3PT"] / max_values["3PT"],
        "Rebounds": 100 * avg_stats["Rebounds"] / max_values["Rebounds"],
        "Assists": avg_stats["Assists"] / max_values["Assists"],
        "Steals": avg_stats["Steals"] / max_values["Steals"],
        "Blocks": avg_stats["Blocks"] / max_values["Blocks"]
    }

    return jsonify({
        "normalized_stats": normalized,
        "comparison": "conference_average"
    })

