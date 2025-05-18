import os
import pandas as pd
import sqlite3
from flask import Blueprint, request, jsonify

player_bp = Blueprint("player_bp", __name__)

# Database path (root directory)
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "ucd-basketball.db"))

# Helper to fetch player stats from the correct table
# Assumes all player stats are in a table called 'AllPlayers' with columns matching the new schema
# If you have separate tables per team, adjust accordingly

def fetch_player_row(player_name):
    conn = sqlite3.connect(DB_PATH)
    try:
        # Find which table contains the player
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_player_stats'")
        tables = [row[0] for row in cursor.fetchall()]
        
        # Try to find the player in any team table
        for table in tables:
            try:
                # Try new schema first
                try:
                    df = pd.read_sql_query(
                        f'SELECT * FROM "{table}" WHERE "Player Name" = ? COLLATE NOCASE', 
                        conn, 
                        params=(player_name,)
                    )
                except:
                    # Fall back to original schema
                    df = pd.read_sql_query(
                        f"SELECT * FROM {table} WHERE field2 = ? COLLATE NOCASE", 
                        conn, 
                        params=(player_name,)
                    )
                    
                if not df.empty:
                    print(f"Found {player_name} in {table}")
                    return df.iloc[0].to_dict()
            except Exception as e:
                print(f"Error searching for {player_name} in {table}: {e}")
    finally:
        conn.close()
    return None

def extract_per_game_stats(player_data):
    def format_percentage(value):
        """ Convert decimal to percentage format (e.g., 0.5 → 50%) """
        return f"{round(value * 100, 1)}%" if isinstance(value, (int, float)) else "N/A"
    
    # Debug the keys in player_data
    print(f"Player data keys: {list(player_data.keys())}")
    
    # Try to handle both old and new schema
    result = {}
    
    # Points per game
    if "PTS/gm" in player_data:
        result["PPG"] = player_data["PTS/gm"]
    elif "AVG.1" in player_data:
        result["PPG"] = player_data["AVG.1"]
    elif "field17" in player_data:
        result["PPG"] = player_data["field17"]
    else:
        result["PPG"] = "N/A"
    
    # Assists per game
    if "Assists/gm" in player_data:
        result["APG"] = player_data["Assists/gm"]
    else:
        # Try to calculate from total assists and games played
        try:
            assists = player_data.get("AST", player_data.get("field15", 0))
            games = player_data.get("GP", player_data.get("field3", 0))
            if games and assists:
                result["APG"] = round(float(assists) / float(games), 1)
            else:
                result["APG"] = "N/A"
        except:
            result["APG"] = "N/A"
    
    # Rebounds per game
    if "REB/gm" in player_data:
        result["RPG"] = player_data["REB/gm"]
    elif "AVG.2" in player_data:
        result["RPG"] = player_data["AVG.2"]
    elif "field19" in player_data:
        result["RPG"] = player_data["field19"]
    else:
        result["RPG"] = "N/A"
    
    # Field goal percentage
    if "FG%" in player_data:
        result["FG%"] = format_percentage(player_data["FG%"])
    elif "field9" in player_data:
        result["FG%"] = format_percentage(player_data["field9"])
    else:
        result["FG%"] = "N/A"
    
    # 3-point percentage
    if "3PT%" in player_data:
        result["3P%"] = format_percentage(player_data["3PT%"])
    elif "field12" in player_data:
        result["3P%"] = format_percentage(player_data["field12"])
    else:
        result["3P%"] = "N/A"
    
    return result

def extract_comparison_stats(player_data):
    # Debug the keys
    print(f"Player data keys for comparison: {list(player_data.keys())}")
    
    result = {}
    
    # Points per game
    if "PTS/gm" in player_data:
        result["PPG"] = player_data["PTS/gm"]
    elif "AVG.1" in player_data:
        result["PPG"] = player_data["AVG.1"]
    elif "field17" in player_data:
        result["PPG"] = player_data["field17"]
    else:
        result["PPG"] = "N/A"
    
    # Player image URL
    if 'Image URL' in player_data:
        result["imageUrl"] = player_data["Image URL"]
    elif "image_url" in player_data:
        result["imageUrl"] = player_data["image_url"]
    elif "field30" in player_data:  # Adjust field number as needed
        result["imageUrl"] = player_data["field30"]
    else:
        result["imageUrl"] = None
    
    # Minutes per game
    if "Minutes/gm" in player_data:
        result["MPG"] = player_data["Minutes/gm"]
    elif "AVG" in player_data:
        result["MPG"] = player_data["AVG"]
    elif "field6" in player_data:
        result["MPG"] = player_data["field6"]
    else:
        result["MPG"] = "N/A"
    
    # Rebounds per game
    if "REB/gm" in player_data:
        result["RPG"] = player_data["REB/gm"]
    elif "AVG.2" in player_data:
        result["RPG"] = player_data["AVG.2"]
    elif "field19" in player_data:
        result["RPG"] = player_data["field19"]
    else:
        result["RPG"] = "N/A"
    
    # Assists per game
    if "Assists/gm" in player_data:
        result["APG"] = player_data["Assists/gm"]
    else:
        # Try to calculate from total assists and games played
        try:
            assists = player_data.get("AST", player_data.get("field15", 0))
            games = player_data.get("GP", player_data.get("field3", 0))
            if games and assists:
                result["APG"] = round(float(assists) / float(games), 1)
            else:
                result["APG"] = "N/A"
        except:
            result["APG"] = "N/A"
    
    # Steals per game
    if "STL/gm" in player_data:
        result["SPG"] = player_data["STL/gm"]
    else:
        # Try to calculate from total steals and games played
        try:
            steals = player_data.get("STL", player_data.get("field23", 0))
            games = player_data.get("GP", player_data.get("field3", 0))
            if games and steals:
                result["SPG"] = round(float(steals) / float(games), 1)
            else:
                result["SPG"] = "N/A"
        except:
            result["SPG"] = "N/A"
    
    # Blocks per game
    if "BLK/gm" in player_data:
        result["BPG"] = player_data["BLK/gm"]
    else:
        # Try to calculate from total blocks and games played
        try:
            blocks = player_data.get("BLK", player_data.get("field24", 0))
            games = player_data.get("GP", player_data.get("field3", 0))
            if games and blocks:
                result["BPG"] = round(float(blocks) / float(games), 1)
            else:
                result["BPG"] = "N/A"
        except:
            result["BPG"] = "N/A"
    
    # Turnovers per game
    if "Turnovers/gm" in player_data:
        result["TOPG"] = player_data["Turnovers/gm"]
    else:
        # Try to calculate from total turnovers and games played
        try:
            turnovers = player_data.get("TO", player_data.get("field22", 0))
            games = player_data.get("GP", player_data.get("field3", 0))
            if games and turnovers:
                result["TOPG"] = round(float(turnovers) / float(games), 1)
            else:
                result["TOPG"] = "N/A"
        except:
            result["TOPG"] = "N/A"
    
    return result

@player_bp.route("/players", methods=["GET"])
def get_players():
    conn = sqlite3.connect(DB_PATH)
    try:
        # Get a list of all tables that end with _player_stats
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%_player_stats'")
        tables = [row[0] for row in cursor.fetchall()]
        
        all_players = []
        # For each team table, extract players
        for table in tables:
            # Different column name based on your schema (adjust as needed)
            try:
                # Try both "Player Name" and "field2" (original schema)
                try:
                    df = pd.read_sql_query(f'SELECT DISTINCT "Player Name" as player FROM "{table}"', conn)
                    players = df["player"].dropna().tolist()
                except:
                    # Fall back to the original schema
                    df = pd.read_sql_query(f"SELECT DISTINCT field2 as player FROM {table} WHERE field2 NOT IN ('Player', 'Total', 'Opponents', 'TM', '')", conn)
                    players = df["player"].dropna().tolist()
                
                all_players.extend(players)
            except Exception as e:
                print(f"Error getting players from {table}: {e}")
        
        # Remove duplicates and sort
        all_players = sorted(list(set(all_players)))
        return jsonify(all_players)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@player_bp.route("/compare", methods=["GET"])
def compare_players():
    try:
        player1 = request.args.get("player1", "").strip()
        player2 = request.args.get("player2", "").strip()
        if not player1 or not player2:
            return jsonify({"error": "Missing player names"}), 400
        p1_stats = fetch_player_row(player1)
        p2_stats = fetch_player_row(player2)
        if not p1_stats or not p2_stats:
            return jsonify({"error": "Player not found"}), 404
        return jsonify({
            "player1": extract_per_game_stats(p1_stats),
            "player2": extract_per_game_stats(p2_stats),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@player_bp.route("/compare_stats", methods=["GET"])
def compare_players_stats():
    try:
        player1 = request.args.get("player1", "").strip()
        player2 = request.args.get("player2", "").strip()
        if not player1 or not player2:
            return jsonify({"error": "Missing player names"}), 400
        p1_stats = fetch_player_row(player1)
        p2_stats = fetch_player_row(player2)
        if not p1_stats or not p2_stats:
            return jsonify({"error": "Player not found"}), 404
        return jsonify({
            "player1": extract_comparison_stats(p1_stats),
            "player2": extract_comparison_stats(p2_stats),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@player_bp.route("/player_image/<player_name>", methods=["GET"])
def get_player_image(player_name):
    """
    Endpoint to fetch a player's image URL directly.
    The frontend will use this to get an image for a specific player.
    """
    try:
        # Replace hyphens with spaces in the player name
        player_name = player_name.replace("-", " ")
        
        # Fetch the player data
        player_data = fetch_player_row(player_name)
        
        if not player_data:
            return jsonify({"error": "Player not found"}), 404
            
        # Look for image URL in different possible field names
        image_url = None
        if "Image" in player_data:
            image_url = player_data["Image"]
        elif "image_url" in player_data:
            image_url = player_data["image_url"]
        elif "field30" in player_data:  # Adjust field number as needed
            image_url = player_data["field30"]
        
        if image_url:
            # Redirect to the actual image URL
            return jsonify({"imageUrl": image_url})
        else:
            return jsonify({"error": "No image found for player"}), 404
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500
