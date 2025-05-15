import React, { useEffect, useState } from 'react';
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Label } from 'recharts';

const API_URL = "http://localhost:5001";

export const PlayerEfficiencyChart = () => {
    const [data, setData] = useState([]);

    useEffect(() => {
        fetch(`${API_URL}/api/player-efficiency`)
            .then(res => res.json())
            .then(json => setData(json));
    }, []);

    return (
        <div>
            <h2 style={{ fontSize: '1.1rem', marginBottom: 10 }}>Player Efficiency Chart</h2>
            <ResponsiveContainer width="90%" height={200}>
                <ScatterChart>
                    <CartesianGrid />
                    <XAxis type="number" dataKey="mpg" name="Minutes Per Game" stroke="#4b0082">
                        <Label value="Minutes Per Game" position="insideBottom" offset={-5} style={{ fill: '#4b0082', fontSize: 13 }} />
                    </XAxis>
                    <YAxis type="number" dataKey="ppg" name="Points Per Game" stroke="#4b0082">
                        <Label value="Points Per Game" angle={-90} position="insideLeft" offset={10} dy={50} style={{ fill: '#4b0082', fontSize: 13 }} />
                    </YAxis>
                    <Tooltip />
                    <Scatter name="Players" data={data} fill="#4b0082" />
                </ScatterChart>
            </ResponsiveContainer>
        </div>
    );
};

const Chart = PlayerEfficiencyChart;

export default Chart;
