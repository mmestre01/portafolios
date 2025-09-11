// src/components/Navbar.jsx
import React from 'react';
import { NavLink } from 'react-router-dom';

const Navbar = () => {
  const linkStyle = {
    color: '#ccc',
    textDecoration: 'none',
    fontWeight: '600',
    padding: '10px 18px',
    borderRadius: '8px',
    transition: 'background-color 0.3s, color 0.3s',
  };

  const activeStyle = {
    color: '#fff',
    backgroundColor: '#6b8dd6',
    boxShadow: '0 4px 12px rgba(107,141,214,0.6)',
  };

  return (
    <nav
      style={{
        background:
          'linear-gradient(90deg, rgba(24,24,38,1) 0%, rgba(36,36,58,1) 100%)',
        padding: '12px 30px',
        display: 'flex',
        justifyContent: 'center',
        gap: '30px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.7)',
      }}
    >
      
      <NavLink
        to="/login"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Login
      </NavLink>
      <NavLink
        to="/"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Home
      </NavLink>
      <NavLink
        to="/register"
        style={({ isActive }) =>
          isActive ? { ...linkStyle, ...activeStyle } : linkStyle
        }
      >
        Register
      </NavLink>
    </nav>
  );
};

export default Navbar;
