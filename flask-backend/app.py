from flask import Flask
from flask_cors import CORS
from chatbot_routes2 import chatbot_bp 
from player_comparison_routes import player_bp

app = Flask(__name__)

CORS(app, resources={
    r"/*": {
        "origins": ["http://localhost:3000"],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

app.register_blueprint(chatbot_bp)
app.register_blueprint(player_bp)

if __name__ == "__main__":
    app.run(debug=True, port=5001)