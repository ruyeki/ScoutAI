# charts.py
from flask import Blueprint, jsonify
import pandas as pd

chart_bp = Blueprint("chart_bp", __name__)

# Load CSV once
player_stats = pd.read_csv("ucd_player_stats.csv")
# print(player_stats[['Player', 'GP', 'PTS', 'AVG.1']].head())


@chart_bp.route('/api/player-efficiency')
def player_efficiency():
    filtered = player_stats[~player_stats['Player'].isin(['Total', 'Opponents'])]

    data = []
    for _, row in filtered.iterrows():
        data.append({
            "player": row['Player'],
            "mpg": row['AVG'],        # Minutes Per Game
            "ppg": row['AVG.1']       # Points Per Game
        })
    return jsonify(data)
