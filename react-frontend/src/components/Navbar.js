import React from 'react';
import logo from '../assets/ScoutAI_logo_small_transparent.png'; 

const Navbar = ({ onNavigate }) => {
    const navbarStyle = {
        backgroundColor: '#f5f5f5', // Light background
        color: '#4b0082', // Darker purple text
        fontFamily: "'Archivo Black', sans-serif", // Updated font
        padding: '10px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '2px solid #dcdcdc'
    };

    const logoStyle = {
        height: '60px', 
        marginLeft: '10px', // Add spacing between text and logo
        cursor: 'pointer',
    };

    const titleContainerStyle = {
        display: 'flex',
        alignItems: 'center',
        marginLeft: '0px', 
        cursor: 'pointer'
    };

    const titleStyle = {
        fontSize: '24px',
        fontWeight: 'bold',
        color: '#000', // Black text
        fontFamily: "'Archivo Black', sans-serif",
        cursor: 'pointer'
    };

    return (
        <div className="navbar" style={navbarStyle}>
            <div className="navbar-left" style={titleContainerStyle}>
                <span style={titleStyle}>ScoutAI</span>
                <img src={logo} alt="ScoutAI Logo" style={logoStyle} onClick={() => onNavigate('chatbot')}/>
            </div>
            <div className="navbar-right">
                {/* No navigation buttons */}
            </div>
        </div>
    );
};

export default Navbar;