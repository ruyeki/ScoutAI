import React, { useState, useEffect } from "react";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    ResponsiveContainer,
    ReferenceLine,
    Label,
    LabelList
} from "recharts";

const API_URL = "http://localhost:5001";

const PlayerComparison = () => {
    const [player1, setPlayer1] = useState("");
    const [player2, setPlayer2] = useState("");
    const [allPlayers, setAllPlayers] = useState([]);
    const [comparison, setComparison] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [chartData, setChartData] = useState([]);

    // Fetch all players on component mount
    useEffect(() => {
        const fetchPlayers = async () => {
            try {
                const response = await fetch(`${API_URL}/players`);
                if (!response.ok) throw new Error("Failed to fetch players");
                const data = await response.json();
                setAllPlayers(data);
                
                // Set specific default players if they exist in the list
                if (data.length > 0) {
                    // Look for TY Johnson and Sevilla, Connor in the player list
                    const player1Default = "TY Johnson";
                    const player2Default = "Sevilla, Connor";
                    
                    // Check if our preferred defaults exist in the list
                    const hasPlayer1 = data.includes(player1Default);
                    const hasPlayer2 = data.includes(player2Default);
                    
                    // Set defaults with fallbacks if needed
                    setPlayer1(hasPlayer1 ? player1Default : data[0]);
                    setPlayer2(hasPlayer2 ? player2Default : (data.length > 1 ? data[1] : data[0]));
                }
            } catch (err) {
                console.error("Error fetching players:", err);
                setError("Failed to load players");
            }
        };
        
        fetchPlayers();
    }, []);

    // Fetch comparison when players change
    useEffect(() => {
        if (player1 && player2) {
            fetchComparison();
        }
    }, [player1, player2]);

    // Transform comparison data into chart format
    useEffect(() => {
        if (comparison) {
            const data = [
                { 
                    name: "PPG", 
                    player1: -parseFloat(comparison.player1.PPG) || 0, 
                    player2: parseFloat(comparison.player2.PPG) || 0,
                    player1Value: parseFloat(comparison.player1.PPG) || 0,
                    player2Value: parseFloat(comparison.player2.PPG) || 0
                },
                { 
                    name: "RPG", 
                    player1: -parseFloat(comparison.player1.RPG) || 0, 
                    player2: parseFloat(comparison.player2.RPG) || 0,
                    player1Value: parseFloat(comparison.player1.RPG) || 0,
                    player2Value: parseFloat(comparison.player2.RPG) || 0
                },
                { 
                    name: "APG", 
                    player1: -parseFloat(comparison.player1.APG) || 0, 
                    player2: parseFloat(comparison.player2.APG) || 0,
                    player1Value: parseFloat(comparison.player1.APG) || 0,
                    player2Value: parseFloat(comparison.player2.APG) || 0
                },
                { 
                    name: "SPG", 
                    player1: -parseFloat(comparison.player1.SPG) || 0, 
                    player2: parseFloat(comparison.player2.SPG) || 0,
                    player1Value: parseFloat(comparison.player1.SPG) || 0,
                    player2Value: parseFloat(comparison.player2.SPG) || 0
                },
                { 
                    name: "BPG", 
                    player1: -parseFloat(comparison.player1.BPG) || 0, 
                    player2: parseFloat(comparison.player2.BPG) || 0,
                    player1Value: parseFloat(comparison.player1.BPG) || 0,
                    player2Value: parseFloat(comparison.player2.BPG) || 0
                },
                { 
                    name: "TOPG", 
                    player1: -parseFloat(comparison.player1.TOPG) || 0, 
                    player2: parseFloat(comparison.player2.TOPG) || 0,
                    player1Value: parseFloat(comparison.player1.TOPG) || 0,
                    player2Value: parseFloat(comparison.player2.TOPG) || 0
                }
            ];
            setChartData(data);
        }
    }, [comparison]);

    const fetchComparison = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await fetch(
                `${API_URL}/compare_stats?player1=${encodeURIComponent(player1)}&player2=${encodeURIComponent(player2)}`
            );
            if (!response.ok) throw new Error("Failed to fetch comparison");
            const data = await response.json();
            setComparison(data);
        } catch (err) {
            console.error("Error fetching comparison:", err);
            setError("Failed to load comparison");
        } finally {
            setLoading(false);
        }
    };

    const handlePlayerChange = (playerNumber, value) => {
        if (playerNumber === 1) {
            setPlayer1(value);
        } else {
            setPlayer2(value);
        }
    };

    return (
        <div>
            <h2 style={{ fontSize: '1.1rem', marginBottom: 10 }}>Player Comparison</h2>
            
            {/* Player selectors */}
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 15 }}>
                <div>
                    <select 
                        value={player1}
                        onChange={(e) => handlePlayerChange(1, e.target.value)}
                        style={{ 
                            fontSize: '0.85rem', 
                            padding: '4px 8px', 
                            borderRadius: 5, 
                            border: '1.1px solid #8884d8' 
                        }}
                    >
                        <option value="">Select Player 1</option>
                        {allPlayers.map(player => (
                            <option key={`p1-${player}`} value={player}>
                                {player}
                            </option>
                        ))}
                    </select>
                </div>
                <div>
                    <select 
                        value={player2}
                        onChange={(e) => handlePlayerChange(2, e.target.value)}
                        style={{ 
                            fontSize: '0.85rem', 
                            padding: '4px 8px', 
                            borderRadius: 5, 
                            border: '1.1px solid #82ca9d' 
                        }}
                    >
                        <option value="">Select Player 2</option>
                        {allPlayers.map(player => (
                            <option key={`p2-${player}`} value={player}>
                                {player}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {/* Comparison Chart */}
            {loading ? (
                <p>Loading comparison...</p>
            ) : error ? (
                <p style={{ color: 'red' }}>{error}</p>
            ) : comparison ? (
                <div style={{ width: '100%', height: 200, marginTop: 20 }}>
                    <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginBottom: 8,
                        fontWeight: 'bold',
                        alignItems: 'center'
                    }}>
                        <div style={{ color: '#8884d8', display: 'flex', alignItems: 'center' }}>
                            <div style={{ 
                                width: 40, 
                                height: 40, 
                                borderRadius: '50%', 
                                overflow: 'hidden',
                                marginRight: 8,
                                border: '2px solid #8884d8',
                                background: '#f0f0f0'
                            }}>
                                <img 
                                    src={comparison.player1.imageUrl || 'https://via.placeholder.com/40?text=NBA'} 
                                    alt={player1}
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    onError={(e) => {
                                        e.target.src = 'https://via.placeholder.com/40?text=NBA';
                                    }}
                                />
                            </div>
                            {player1}
                        </div>
                        <div style={{ color: '#82ca9d', display: 'flex', alignItems: 'center' }}>
                            {player2}
                            <div style={{ 
                                width: 40, 
                                height: 40, 
                                borderRadius: '50%', 
                                overflow: 'hidden',
                                marginLeft: 8,
                                border: '2px solid #82ca9d',
                                background: '#f0f0f0'
                            }}>
                                <img 
                                    src={comparison.player2.imageUrl || 'https://via.placeholder.com/40?text=NBA'} 
                                    alt={player2}
                                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                                    onError={(e) => {
                                        e.target.src = 'https://via.placeholder.com/40?text=NBA';
                                    }}
                                />
                            </div>
                        </div>
                    </div>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart
                            layout="vertical"
                            data={chartData}
                            margin={{ top: 0, right: 30, left: 30, bottom: 5 }}
                            barGap={0}
                            barCategoryGap={8}
                        >
                            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                            <XAxis 
                                type="number" 
                                domain={[
                                    (dataMin) => Math.floor(Math.min(dataMin, -Math.abs(dataMin * 0.2))), 
                                    (dataMax) => Math.ceil(Math.max(dataMax, Math.abs(dataMax * 0.2)))
                                ]}
                                tick={false}
                                axisLine={{ stroke: '#666' }}
                            />
                            <YAxis 
                                dataKey="name" 
                                type="category" 
                                axisLine={false}
                                tickLine={false}
                                width={40}
                            />
                            <ReferenceLine x={0} stroke="#666" strokeWidth={2} />
                            <Bar 
                                dataKey="player1" 
                                fill="#8884d8" 
                                name={player1}
                                barSize={12}
                            >
                                <LabelList 
                                    dataKey="player1Value" 
                                    position="inside" 
                                    formatter={(value) => value.toFixed(1)}
                                    style={{ fill: 'white', fontSize: 10, fontWeight: 600 }} 
                                />
                            </Bar>
                            <Bar 
                                dataKey="player2" 
                                fill="#82ca9d" 
                                name={player2}
                                barSize={12}
                            >
                                <LabelList 
                                    dataKey="player2Value" 
                                    position="inside" 
                                    formatter={(value) => value.toFixed(1)}
                                    style={{ fill: 'white', fontSize: 10, fontWeight: 600 }} 
                                />
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            ) : (
                <p>Select two players to compare.</p>
            )}
        </div>
    );
};

export default PlayerComparison; 