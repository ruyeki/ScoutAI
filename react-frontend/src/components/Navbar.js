import React from 'react';

const Navbar = ({ onNavigate }) => {
    return (
        <div className="navbar">
            <div className="navbar-left">
                <h1>UC Davis Basketball | ASA</h1>
            </div>
            <div className="navbar-right">
                <a href="#" onClick={() => onNavigate('players')}>Chatbot</a>
            </div>
        </div>
    );
};

export default Navbar;
