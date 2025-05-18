import React, { useEffect, useState } from "react";
import {
    Radar, RadarChart, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis, Legend, ResponsiveContainer
} from "recharts";

const TEAMS = [
    "UCDavis", "CalPolySLO", "CalStateBakersfield", "CalStateFullerton",
    "CalStateNorthridge", "LongBeachState", "UCIrvine", "UCRiverside",
    "UCSanDiego", "UCSantaBarbara", "UniversityOfHawaii", "Conference Average"
];

const RadarComparisonChart = ({ team1, team2, onTeamChange }) => {
    const [team1Stats, setTeam1Stats] = useState(null);
    const [team2Stats, setTeam2Stats] = useState(null);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                let team1Data, team2Data;
                if (team1 === "Conference Average") {
                    const res = await fetch(`http://localhost:5001/api/radar-chart/conference-average`);
                    team1Data = await res.json();
                } else {
                    const res = await fetch(`http://localhost:5001/api/radar-chart/${team1}`);
                    team1Data = await res.json();
                }
                setTeam1Stats(team1Data.normalized_stats);

                if (team2 === "Conference Average") {
                    const res = await fetch(`http://localhost:5001/api/radar-chart/conference-average`);
                    team2Data = await res.json();
                } else {
                    const res = await fetch(`http://localhost:5001/api/radar-chart/${team2}`);
                    team2Data = await res.json();
                }
                setTeam2Stats(team2Data.normalized_stats);
            } catch (error) {
                console.error("Failed to load stats:", error);
            }
        };

        if (team1 && team2) fetchStats();
    }, [team1, team2]);

    const chartData = team1Stats && team2Stats
        ? Object.keys(team1Stats).map(stat => ({
            stat,
            [team1]: team1Stats[stat],
            [team2]: team2Stats[stat],
        }))
        : [];

    return (
        <div style={{ width: '100%', height: 300, display: 'flex', flexDirection: 'column', alignItems: 'flex-start' }}>
            <h2 style={{ fontSize: '1.1rem', marginTop: 2, marginBottom: 10 }}>Team Comparison</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 4, marginBottom: 10, alignItems: 'flex-start', marginLeft: 0 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <label htmlFor="team1-select" style={{ fontSize: '0.85rem', marginRight: 4, color: '#8884d8', fontWeight: 500 }}>Team 1:</label>
                    <select 
                        id="team1-select"
                        value={team1} 
                        onChange={e => onTeamChange(0, e.target.value)}
                        style={{ fontSize: '0.85rem', padding: '2px 6px', borderRadius: 5, border: '1.1px solid #8884d8', minWidth: 70, marginBottom: 2 }}
                    >
                        {TEAMS.map(team => (
                            <option key={team} value={team}>{team}</option>
                        ))}
                    </select>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <label htmlFor="team2-select" style={{ fontSize: '0.85rem', marginRight: 4, color: '#82ca9d', fontWeight: 500 }}>Team 2:</label>
                    <select 
                        id="team2-select"
                        value={team2} 
                        onChange={e => onTeamChange(1, e.target.value)}
                        style={{ fontSize: '0.85rem', padding: '2px 6px', borderRadius: 5, border: '1.1px solid #82ca9d', minWidth: 70, marginTop: 2 }}
                    >
                        {TEAMS.map(team => (
                            <option key={team} value={team}>{team}</option>
                        ))}
                    </select>
                </div>
            </div>
            {!team1Stats || !team2Stats ? (
                <p>Loading radar chart...</p>
            ) : (
                <ResponsiveContainer width="100%" height={220}>
                    <RadarChart cx="48%" cy="50%" outerRadius="80%" data={chartData}>
                        <PolarGrid />
                        <PolarAngleAxis dataKey="stat" />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} />
                        <Radar name={team1} dataKey={team1} stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} isAnimationActive={true} animationDuration={800} dot={{ r: 4, stroke: '#8884d8', fill: '#fff', strokeWidth: 2 }} />
                        <Radar name={team2} dataKey={team2} stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.4} isAnimationActive={true} animationDuration={800} dot={{ r: 4, stroke: '#82ca9d', fill: '#fff', strokeWidth: 2 }} />
                        <Legend />
                    </RadarChart>
                </ResponsiveContainer>
            )}
        </div>
    );
};

export default RadarComparisonChart;
