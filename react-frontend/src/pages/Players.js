import React, { useState, useEffect } from "react";
import Chatbot from "./Chatbot";
import "../Players.css";

const API_URL = "http://localhost:5001";

const Players = () => {
    const [players, setPlayers] = useState([]);
    const [player1, setPlayer1] = useState("");
    const [player2, setPlayer2] = useState("");
    const [comparisonData, setComparisonData] = useState(null);

    useEffect(() => {
        async function loadPlayers() {
            try {
                let response = await fetch(`${API_URL}/players`);
                if (!response.ok) {
                    throw new Error(`HTTP error! Status: ${response.status}`);
                }
                let players = await response.json();
                if (Array.isArray(players) && players.length > 0) {
                    setPlayers(players);
                }
            } catch (error) {
                console.error("Error fetching players:", error);
            }
        }
        loadPlayers();
    }, []);

    async function comparePlayers() {
        if (!player1 || !player2) {
            alert("Please select two players.");
            return;
        }

        const url = `${API_URL}/compare?player1=${encodeURIComponent(player1)}&player2=${encodeURIComponent(player2)}`;

        try {
            let response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! Status: ${response.status}`);
            }
            let data = await response.json();
            if (!data.error) {
                setComparisonData(data);
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error("Error fetching player comparison:", error);
        }
    }

    return (
        <div className="players-container">
            {/* Left Side: Player Comparison */}
            <div className="player-comparison">
                <h2>Compare Players</h2>

                {/* <label>Player 1: </label> */}
                <select value={player1} onChange={(e) => setPlayer1(e.target.value)}>
                    <option value="">-- Select --</option>
                    {players.map((player, index) => (
                        <option key={index} value={player}>{player}</option>
                    ))}
                </select>

                {/* <label>Player 2: </label> */}
                <select value={player2} onChange={(e) => setPlayer2(e.target.value)}>
                    <option value="">-- Select --</option>
                    {players.map((player, index) => (
                        <option key={index} value={player}>{player}</option>
                    ))}
                </select>

                <button onClick={comparePlayers}>Compare</button>

                {comparisonData && (
                    <div>
                        <h3>Comparison</h3>
                        <table border="1">
                            <thead>
                                <tr>
                                    <th>Stat</th>
                                    <th>{player1}</th>
                                    <th>{player2}</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr><td>Points Per Game (PPG)</td><td>{comparisonData.player1?.PPG ?? "N/A"}</td><td>{comparisonData.player2?.PPG ?? "N/A"}</td></tr>
                                <tr><td>Assists Per Game (APG)</td><td>{comparisonData.player1?.APG ?? "N/A"}</td><td>{comparisonData.player2?.APG ?? "N/A"}</td></tr>
                                <tr><td>Rebounds Per Game (RPG)</td><td>{comparisonData.player1?.RPG ?? "N/A"}</td><td>{comparisonData.player2?.RPG ?? "N/A"}</td></tr>
                                <tr><td>Field Goal % (FG%)</td><td>{comparisonData.player1?.["FG%"] ?? "N/A"}</td><td>{comparisonData.player2?.["FG%"] ?? "N/A"}</td></tr>
                                <tr><td>3-Point % (3P%)</td><td>{comparisonData.player1?.["3P%"] ?? "N/A"}</td><td>{comparisonData.player2?.["3P%"] ?? "N/A"}</td></tr>
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Right Side: Chatbot */}
            <div className="chatbot">
                <Chatbot />
            </div>
        </div>
    );
};

export default Players;
