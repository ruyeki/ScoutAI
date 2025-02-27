import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Players from './pages/Players';

import './index.css';

const App = () => {
  const [currentPage, setCurrentPage] = useState('dashboard'); // Default page is the Dashboard

  const handleNavigate = (page) => {
    setCurrentPage(page);
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
