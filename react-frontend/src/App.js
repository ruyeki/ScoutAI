import React, { useState } from 'react';
import axios from "axios";
import Navbar from './components/Navbar';
import Players from './pages/Players';

import './index.css';

const App = () => {
  // Navigation state
  const [currentPage, setCurrentPage] = useState('dashboard');
  // Chat states
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [threadId, setThreadId] = useState(null);

  const handleNavigate = (page) => {
    setCurrentPage(page);
  };

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
        message: userMessage,
        thread_id: threadId
      });

      // Save thread ID from response
      if (response.data.thread_id) {
        setThreadId(response.data.thread_id);
      }

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

  let pageContent;
  switch (currentPage) {
    case 'players':
      pageContent = <Players />;
      break;
    default:
      pageContent = <Players />;
  }

  return (
    <div>
      <Navbar onNavigate={handleNavigate} />
      <div className="container mx-auto mt-8">
        {pageContent}
      </div>
    </div>
  );
};

export default App;
