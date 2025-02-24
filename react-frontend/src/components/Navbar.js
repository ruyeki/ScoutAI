import React from 'react';

const Navbar = ({ onNavigate }) => {
    return (
        <div className="navbar">
            <div className="navbar-left">
                <h1>UC Davis Basketball | ASA</h1>
            </div>
            <div className="navbar-center">
                <a href="#" onClick={() => onNavigate('dashboard')}>Dashboard</a>
                <a href="#" onClick={() => onNavigate('profile')}>Profile</a>
                <a href="#" onClick={() => onNavigate('chatbot')}>Chatbot</a>
            </div>
        </div>
    );
};

export default Navbar;
