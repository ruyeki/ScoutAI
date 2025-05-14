import os
import sqlite3
import pandas as pd
from flask import Blueprint, jsonify

chart_bp = Blueprint("chart_bp", __name__)

# Database path (one level up from backend folder)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "ucd-basketball.db")

# Connect to the database
conn = sqlite3.connect(DB_PATH)

# Query the actual fields by position
query = """
SELECT field2 AS Player, field6 AS AVG, field17 AS "AVG.1", field29 AS "Image URL"
FROM UCDavis_player_stats
WHERE field2 NOT IN ('Player', 'Total', 'Opponents', 'TM', '')
"""

# Load into DataFrame and clean columns
player_stats = pd.read_sql_query(query, conn)
player_stats.columns = player_stats.columns.str.strip()
player_stats['Image URL'] = player_stats['Image URL'].fillna('')
conn.close()

@chart_bp.route('/api/player-efficiency')
def player_efficiency():
    data = []
    for _, row in player_stats.iterrows():
        try:
            data.append({
                "player": row['Player'],
                "mpg": float(row['AVG']),
                "ppg": float(row['AVG.1']),
                "image": row['Image URL']
            })
        except Exception as e:
            print("Skipped row due to error:", e)
    return jsonify(data)
