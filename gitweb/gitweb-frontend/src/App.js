import React from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation, BrowserRouter } from 'react-router-dom';

import Navbar from './components/Navbar';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import RepoDetail from './pages/RepoDetail';

// Layout para controlar Navbar
const Layout = ({ children }) => {
  const location = useLocation();
  const noNavbarRoutes = ['/login', '/register'];
  const showNavbar = !noNavbarRoutes.includes(location.pathname);

  return (
    <>
      {showNavbar && <Navbar />}
      {children}
    </>
  );
};

function App() {
  return (
    <BrowserRouter basename="/gitweb/">
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/repos/:id" element={<RepoDetail />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
