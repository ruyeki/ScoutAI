import os
import pandas as pd
from flask import Blueprint, request, jsonify

player_bp = Blueprint("player_bp", __name__)

# Load the CSV file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, "ucd_player_stats.csv")

if os.path.exists(CSV_PATH):
    df = pd.read_csv(CSV_PATH)
    df["Player"] = df["Player"].str.strip().str.lower()  # Standardize player names
else:
    df = None

def extract_per_game_stats(player_data):
    def format_percentage(value):
        """ Convert decimal to percentage format (e.g., 0.5 → 50%) """
        return f"{round(value * 100, 1)}%" if isinstance(value, (int, float)) else "N/A"

    return {
        "PPG": player_data.get("AVG", "N/A"),  # Points Per Game
        "APG": round(player_data.get("AST", 0) / player_data.get("GP", 1), 1) if player_data.get("GP", 1) > 0 else "N/A",  # Assists Per Game
        "RPG": player_data.get("AVG.2", "N/A"),  # Rebounds Per Game
        "FG%": format_percentage(player_data.get("FG%", "N/A")),  # Convert FG% from decimal to percentage
        "3P%": format_percentage(player_data.get("3PT%", "N/A"))  # Convert 3P% from decimal to percentage
    }


@player_bp.route("/players", methods=["GET"])
def get_players():
    if df is None:
        return jsonify({"error": "Player stats file not found"}), 500

    # Remove non-player entries like "TM Team", "Total", "Opponents"
    excluded_entries = {"tm team", "total", "opponents"}
    players = [player for player in df["Player"].unique().tolist() if player not in excluded_entries]

    return jsonify(players)

@player_bp.route("/compare", methods=["GET"])
def compare_players():
    try:
        player1 = request.args.get("player1", "").strip().lower()
        player2 = request.args.get("player2", "").strip().lower()

        if not player1 or not player2:
            return jsonify({"error": "Missing player names"}), 400

        p1_stats = df[df["Player"] == player1].to_dict(orient="records")
        p2_stats = df[df["Player"] == player2].to_dict(orient="records")

        if not p1_stats or not p2_stats:
            return jsonify({"error": "Player not found"}), 404

        return jsonify({
            "player1": extract_per_game_stats(p1_stats[0]),
            "player2": extract_per_game_stats(p2_stats[0]),
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
