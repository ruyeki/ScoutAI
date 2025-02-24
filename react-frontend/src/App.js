import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Profile from './pages/Profile';
import Chatbot from './pages/Chatbot';

import './index.css';

const App = () => {
  const [currentPage, setCurrentPage] = useState('dashboard'); // Default page is the Dashboard

  const handleNavigate = (page) => {
    setCurrentPage(page);
  };

  let pageContent;
  switch (currentPage) {
    case 'dashboard':
      pageContent = <Dashboard />;
      break;
    case 'profile':
      pageContent = <Profile />;
      break;
    case 'chatbot':
      pageContent = <Chatbot />;
      break;
    default:
      pageContent = <Dashboard />;
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
