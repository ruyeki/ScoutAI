import React, { useState } from "react";
import axios from "axios";
import ReactMarkdown from "react-markdown";

function Chatbot({ onRelevantTeams }) {
    const [input, setInput] = useState("");
    const [messages, setMessages] = useState([]);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        const userMessage = input;
        setInput("");

        setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
        setLoading(true);

        try {
            const response = await axios.post("http://127.0.0.1:5001/chat", {
                message: userMessage,
            });

            // Pass relevant_teams up if available
            if (onRelevantTeams && response.data.relevant_teams) {
                onRelevantTeams(response.data.relevant_teams);
            }

            setMessages((prev) => [
                ...prev,
                { role: "assistant", content: response.data.response },
            ]);
        } catch (error) {
            console.error("Error:", error);
            setMessages((prev) => [
                ...prev,
                {
                    role: "assistant",
                    content: "Error: Could not get response from server",
                },
            ]);
        } finally {
            setLoading(false);
        }
    };

    const TypingIndicator = () => {
        const [dots, setDots] = useState("");
        React.useEffect(() => {
            if (!loading) return;
            const interval = setInterval(() => {
                setDots((prev) => (prev.length < 3 ? prev + "." : ""));
            }, 500);
            return () => clearInterval(interval);
        }, [loading]);
        return <span>Assistant is typing{dots}</span>;
    };

    // Group messages into user/assistant pairs for display
    const groupedMessages = [];
    for (let i = 0; i < messages.length; i++) {
        if (messages[i].role === "user") {
            // If next message is assistant, group them
            if (messages[i + 1] && messages[i + 1].role === "assistant") {
                groupedMessages.push([messages[i], messages[i + 1]]);
                i++; // Skip next
            } else {
                groupedMessages.push([messages[i]]);
            }
        } else if (messages[i].role === "assistant") {
            // If assistant message comes first (shouldn't happen), show alone
            groupedMessages.push([messages[i]]);
        }
    }

    return (
        <div style={{ display: "flex", flexDirection: "column-reverse", height: "100vh" }}>
            {/* Input Bar */}
            <form
                onSubmit={handleSubmit}
                style={{
                    display: "flex",
                    padding: "10px",
                    // backgroundColor: "#f5f5f5",
                }}
            >
                <div style={{ position: "relative", flex: 1, display: "flex" }}>
                    <input
                        type="text"
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder="Type your message..."
                        style={{
                            flex: 1,
                            padding: "10px 48px 10px 16px", // extra right padding for button
                            fontSize: "16px",
                            border: "2px solid #800000",
                            borderRadius: "30px",
                            outline: "none",
                            boxSizing: "border-box",
                        }}
                    />
                    <button
                        type="submit"
                        style={{
                            position: "absolute",
                            right: 4,
                            top: "50%",
                            transform: "translateY(-50%)",
                            height: 36,
                            width: 36,
                            backgroundColor: "rgba(128,0,0,0.5)",
                            color: "white",
                            border: "none",
                            borderRadius: "50%",
                            cursor: "pointer",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontSize: "32px",
                            padding: 0,
                        }}
                        disabled={loading}
                    >
                        <span style={{ display: 'block', marginTop: '14px', fontWeight: 'bold' }}>^</span>
                    </button>
                </div>
            </form>

            {/* Chat Display */}
            <div
                style={{
                    flex: 1,
                    maxHeight: 450,
                    overflowY: "auto",
                    padding: "10px",
                    backgroundColor: "#ffffff",
                    display: "flex",
                    flexDirection: "column",
                }}
            >
                {groupedMessages.map((pair, idx) => (
                    <div key={idx}>
                        {pair.map((message, index) => (
                            <div
                                key={index}
                                style={{
                                    margin: "10px 0",
                                    ...(message.role === "user"
                                        ? {
                                              alignSelf: "flex-start",
                                              backgroundColor: "#e3f2fd",
                                              padding: "10px",
                                              borderRadius: "10px",
                                              maxWidth: "60%",
                                          }
                                        : {
                                              alignSelf: "flex-start",
                                              color: "#333",
                                          }),
                                }}
                            >
                                {message.role === "user" && (
                                    <strong style={{ display: "block", marginBottom: "5px" }}>
                                        You:
                                    </strong>
                                )}
                                {message.role === "assistant" ? (
                                    <ReactMarkdown>{message.content}</ReactMarkdown>
                                ) : (
                                    message.content
                                )}
                            </div>
                        ))}
                    </div>
                ))}
                {loading && (
                    <div
                        style={{
                            margin: "10px 0",
                            alignSelf: "flex-start",
                            color: "#888",
                            fontStyle: "italic",
                        }}
                    >
                        <TypingIndicator />
                    </div>
                )}
            </div>
        </div>
    );
}

export default Chatbot;
