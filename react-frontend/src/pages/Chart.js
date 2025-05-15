import React, { useEffect, useState } from 'react';

import {
    ScatterChart,
    Scatter,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Label
} from 'recharts';

const API_URL = "http://localhost:5001";

const CustomTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
        const player = payload[0].payload;
        return (
            <div
                style={{
                    backgroundColor: 'rgba(255, 255, 255, 0.95)',
                    border: '1px solid #ccc',
                    borderRadius: '8px',
                    padding: '12px',
                    boxShadow: '0 4px 8px rgba(0, 0, 0, 0.1)',
                    minWidth: '160px'
                }}
            >
                <p style={{ fontWeight: 'bold', marginBottom: '8px' }}>{player.player}</p>
                {player.image && (
                    <img
                        src={player.image}
                        alt={player.player}
                        style={{
                            width: '60px',
                            height: '90px',
                            borderRadius: '0%',
                            objectFit: 'cover',
                            marginBottom: '8px'
                        }}
                    />
                )}
                <p style={{ margin: 0 }}>MPG: {player.mpg}</p>
                <p style={{ margin: 0 }}>PPG: {player.ppg}</p>
            </div>
        );
    }
    return null;
};

export default function PlayerEfficiencyChart() {
    const [data, setData] = useState([]);

    useEffect(() => {
        fetch(`${API_URL}/api/player-efficiency`)
            .then((res) => res.json())
            .then((json) => setData(json))
            .catch((err) => console.error("API error:", err));
    }, []);

    return (
        <div className="p-4">
            <h2 className="text-2xl font-bold mb-4">UC Davis Player Efficiency</h2>
            <ResponsiveContainer width="100%" height={250}>
                <ScatterChart>
                    <CartesianGrid />
                    <XAxis
                        type="number"
                        dataKey="mpg"
                        name="Minutes Per Game"
                        stroke="#4b0082"
                        label={{ value: 'Minutes Per Game', position: 'insideBottomRight', offset: -10 }}
                    />
                    <YAxis
                        type="number"
                        dataKey="ppg"
                        name="Points Per Game"
                        stroke="#4b0082"
                        label={{ value: 'Points Per Game', angle: -90, position: 'insideLeft' }}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Scatter name="Players" data={data} fill="#4b0082" />
                </ScatterChart>
            </ResponsiveContainer>
        </div>
    );
}
