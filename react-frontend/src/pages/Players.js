import React, { useState } from "react";
import Chatbot from "./Chatbot";
import RadarComparisonChart from "./Radar";
import { PlayerEfficiencyChart } from "./Chart";
import "../Players.css";

const API_URL = "http://localhost:5001";

const Players = () => {
    const [selectedTeams, setSelectedTeams] = useState(["UCDavis", "Conference Average"]);

    // Handler for chatbot
    const handleRelevantTeams = (teams) => {
        if (Array.isArray(teams) && teams.length === 2) {
            setSelectedTeams(teams);
        }
    };

    // Handler for manual selection
    const handleTeamChange = (index, value) => {
        setSelectedTeams((prev) => {
            const updated = [...prev];
            updated[index] = value;
            return updated;
        });
    };

    return (
        <div className="dashboard-container" style={{ alignItems: 'flex-start' }}>
            {/* Left Section: Radar Chart and Player Efficiency Chart */}
            <div className="player-stats-section">
                <div style={{ marginTop: 0 }}>
                    <RadarComparisonChart
                        team1={selectedTeams[0]}
                        team2={selectedTeams[1]}
                        onTeamChange={handleTeamChange}
                    />
                </div>
                <div style={{ marginTop: 30 }}>
                    <PlayerEfficiencyChart />
                </div>
            </div>

            {/* Right Section: Chatbot */}
            <div className="chatbot-section" style={{ flex: 1, minWidth: 0, marginLeft: '40px', maxHeight: 540, display: 'flex', flexDirection: 'column' }}>
                <Chatbot onRelevantTeams={handleRelevantTeams} />
            </div>
        </div>
    );
};

export default Players;
