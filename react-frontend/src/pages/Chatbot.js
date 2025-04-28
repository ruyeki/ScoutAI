import React, { useState, useEffect } from "react";
import axios from "axios";
import { styles } from "../styles/ChatStyles";

// TypingDots component for animated "Typing..." effect
function TypingDots() {
    const [dots, setDots] = useState("");

    useEffect(() => {
        const interval = setInterval(() => {
            setDots(prev => (prev.length >= 3 ? "" : prev + "."));
        }, 500);
        return () => clearInterval(interval);
    }, []);

    return <span>Typing{dots}</span>;
}

function App() {
    const [input, setInput] = useState(""); // Stores current input text
    const [messages, setMessages] = useState([]); // Stores chat history
    const [isLoading, setIsLoading] = useState(false); // Tracks loading state

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!input.trim()) return;

        setIsLoading(true);
        const userMessage = input;
        setInput("");

        // Add user message to chat
        setMessages(prev => [...prev, { role: 'user', content: userMessage }]);

        try {
            const response = await axios.post("http://127.0.0.1:5001/chat", {
                message: userMessage
            });

            // Add assistant's response to chat
            setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);
        } catch (error) {
            console.error("Error:", error);
            setMessages(prev => [...prev, {
                role: 'system',
                content: 'Error: Could not get response from server'
            }]);
        }

        setIsLoading(false);
    };

    return (
        <div className="App">
            <div className="chat-container" style={styles.chatContainer}>
                {messages.map((message, index) => (
                    <div
                        key={index}
                        style={{
                            ...styles.message,
                            ...(message.role === 'user' ? styles.userMessage : styles.assistantMessage)
                        }}
                    >
                        <strong>{message.role === 'user' ? 'You: ' : 'AI: '}</strong>
                        {message.content}
                    </div>
                ))}

                {/* Show typing animation when loading */}
                {isLoading && (
                    <div style={{
                        ...styles.message,
                        ...styles.assistantMessage,
                        fontStyle: 'italic',
                        opacity: 0.7
                    }}>
                        <strong>AI: </strong> <TypingDots />
                    </div>
                )}
            </div>

            <form onSubmit={handleSubmit} style={styles.form}>
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message..."
                    style={styles.input}
                    disabled={isLoading}
                />
                <button type="submit" disabled={isLoading} style={styles.button}>
                    ↑
                </button>
            </form>
        </div>
    );
}

export default App;
