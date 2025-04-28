import React, { useState } from 'react';
import Navbar from './components/Navbar';
import Players from './pages/Players';
import Chart from './pages/Chart'; // ✅ Import new page

import './index.css';

const App = () => {
  const [currentPage, setCurrentPage] = useState('dashboard');

  const handleNavigate = (page) => {
    setCurrentPage(page);
  };

  let pageContent;
  switch (currentPage) {
    case 'players':
      pageContent = <Players />;
      break;
    case 'chart':
      pageContent = <Chart />;
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
