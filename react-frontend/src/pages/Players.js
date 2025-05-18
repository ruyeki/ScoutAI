import React, { useState, useRef, useCallback } from "react";
import Chatbot from "./Chatbot";
import RadarComparisonChart from "./Radar";
import PlayerEfficiencyChart from "./Chart";
import { Typewriter } from "react-simple-typewriter";
import "../Players.css";
import PlayerComparison from "./PlayerComparison";

const API_URL = "http://localhost:5001";

const TEAMS = [
    "UCDavis", "CalPolySLO", "CalStateBakersfield", "CalStateFullerton",
    "CalStateNorthridge", "LongBeachState", "UCIrvine", "UCRiverside",
    "UCSanDiego", "UCSantaBarbara", "UniversityOfHawaii", "Conference Average"
];

const Players = () => {
    const [selectedTeams, setSelectedTeams] = useState(["UCDavis", "Conference Average"]);
    const [selectedTeamForEfficiency, setSelectedTeamForEfficiency] = useState("UCDavis");
    const [dropdownOpen, setDropdownOpen] = useState(false);
    const dropdownRef = useRef(null);

    // Handler for chatbot
    const handleRelevantTeams = useCallback((teams) => {
        if (Array.isArray(teams) && teams.length === 2) {
            setSelectedTeams(teams);
            setSelectedTeamForEfficiency(teams[0]); // Update efficiency chart with first team
        }
    }, []);

    // Handler for manual selection
    const handleTeamChange = (index, value) => {
        setSelectedTeams((prev) => {
            const updated = [...prev];
            updated[index] = value;
            return updated;
        });
        if (index === 0) {
            setSelectedTeamForEfficiency(value); // Update efficiency chart when first team changes
        }
    };

    // Close dropdown when clicking outside
    React.useEffect(() => {
        function handleClickOutside(event) {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setDropdownOpen(false);
            }
        }
        if (dropdownOpen) {
            document.addEventListener("mousedown", handleClickOutside);
        } else {
            document.removeEventListener("mousedown", handleClickOutside);
        }
        return () => {
            document.removeEventListener("mousedown", handleClickOutside);
        };
    }, [dropdownOpen]);

    return (
        <div className="dashboard-container" 
            style={{ 
                alignItems: 'flex-start',
                display: 'flex',
                justifyContent: 'space-between',
                gap: '20px',
                width: '100%',
                margin: 0,
                padding:0,
                maxWidth: 'none',
            }}
        >
            {/* Left Section: Radar Chart and Player Efficiency Chart */}
            <div className="player-stats-section" style={{ flex: 1 }}>
                <div style={{ marginTop: 0, background: '#fff', borderRadius: 10, boxShadow: '0 4px 16px rgba(0,0,0,0.07)', padding: 14, marginBottom: 2, height: 340, display: 'flex', flexDirection: 'row', justifyContent: 'flex-start' }}>
                    <div style={{ flex: 1.5, paddingRight: 5 }}>
                        <RadarComparisonChart
                            team1={selectedTeams[0]}
                            team2={selectedTeams[1]}
                            onTeamChange={handleTeamChange}
                        />
                    </div>
                    <div style={{ flex: 1, borderLeft: '1px solid #eee', paddingLeft: 10 }}>
                        <PlayerComparison />
                    </div>
                </div>
                <div style={{ background: '#fff', borderRadius: 16, boxShadow: '0 4px 16px rgba(0,0,0,0.07)', padding: 12 }}>
                    <PlayerEfficiencyChart selectedTeam={selectedTeamForEfficiency} />
                    <div style={{ marginTop: 16 }}>
                        <label htmlFor="efficiency-team-select" style={{ marginRight: 8, fontWeight: 500 }}>
                            Select a Team:
                        </label>
                        <select
                            id="efficiency-team-select"
                            value={selectedTeamForEfficiency}
                            onChange={e => setSelectedTeamForEfficiency(e.target.value)}
                            style={{
                                borderRadius: 8,
                                padding: '6px 16px',
                                fontSize: '1rem',
                                border: '1.5px solid #4b0082',
                                color: '#4b0082',
                                background: 'white',
                                fontFamily: 'inherit',
                                outline: 'none',
                                marginLeft: 4
                            }}
                        >
                            {TEAMS.filter(team => team !== "Conference Average").map(team => (
                                <option key={team} value={team}>{team}</option>
                            ))}
                        </select>
                    </div>
                </div>
            </div>

            {/* Right Section: Chatbot */}
            <div className="chatbot-section" 
                style={{ 
                    flex: '0 0 600px', 
                    minWidth: 0, 
                    maxHeight: 700, 
                    display: 'flex', 
                    flexDirection: 'column',
                    marginLeft: 'auto'
                }}
            >
                <Chatbot onRelevantTeams={handleRelevantTeams} />
            </div>
        </div>
    );
};

export default Players;
