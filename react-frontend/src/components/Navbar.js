import React from 'react';

const Navbar = ({ onNavigate }) => {
    return (
        <div className="navbar">
            <div className="navbar-left">
                <h1>UC Davis Basketball | ASA</h1>
            </div>
            <div className="navbar-right">
                <button className="nav-link" onClick={() => onNavigate('players')}>Chatbot</button>
                <button className="nav-link" onClick={() => onNavigate('radar')}>Radar</button>
            </div>
        </div>
    );
};

export default Navbar;