import React, { useEffect, useState } from "react";
import {
    Radar, RadarChart, PolarGrid,
    PolarAngleAxis, PolarRadiusAxis, Legend, ResponsiveContainer
} from "recharts";

const TEAMS = [
    "UCDavis", "CalPolySLO", "CalStateBakersfield", "CalStateFullerton",
    "CalStateNorthridge", "LongBeachState", "UCIrvine", "UCRiverside",
    "UCSanDiego", "UCSantaBarbara", "UniversityOfHawaii"
];

const RadarComparisonChart = () => {
    const [teamName, setTeamName] = useState("UCDavis");
    const [teamStats, setTeamStats] = useState(null);
    const [conferenceStats, setConferenceStats] = useState(null);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const teamRes = await fetch(`http://localhost:5001/api/radar-chart/${teamName}`);
                const teamData = await teamRes.json();

                const confRes = await fetch(`http://localhost:5001/api/radar-chart/conference-average`);
                const confData = await confRes.json();

                setTeamStats(teamData.normalized_stats);
                setConferenceStats(confData.normalized_stats);
            } catch (error) {
                console.error("Failed to load stats:", error);
            }
        };

        if (teamName) fetchStats();
    }, [teamName]);


    const chartData = teamStats && conferenceStats
        ? Object.keys(teamStats).map(stat => ({
            stat,
            [teamName]: teamStats[stat],
            "Conference Average": conferenceStats[stat],
        }))
        : [];

    return (
        <div style={{ width: '100%', height: 500 }}>
            <h2>Radar Chart Comparison</h2>
            <select value={teamName} onChange={e => setTeamName(e.target.value)}>
                {TEAMS.map(team => (
                    <option key={team} value={team}>{team}</option>
                ))}
            </select>

            {!teamStats || !conferenceStats ? (
                <p>Loading radar chart...</p>
            ) : (
                <ResponsiveContainer width="100%" height={400}>
                    <RadarChart cx="50%" cy="50%" outerRadius="80%" data={chartData}>
                        <PolarGrid />
                        <PolarAngleAxis dataKey="stat" />
                        <PolarRadiusAxis angle={30} domain={[0, 100]} />
                        <Radar name={teamName} dataKey={teamName} stroke="#8884d8" fill="#8884d8" fillOpacity={0.6} />
                        <Radar name="Conference Average" dataKey="Conference Average" stroke="#82ca9d" fill="#82ca9d" fillOpacity={0.4} />
                        <Legend />
                    </RadarChart>
                </ResponsiveContainer>
            )}
        </div>
    );
};

export default RadarComparisonChart;
