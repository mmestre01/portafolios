// src/pages/Register.jsx
import React, { useState } from 'react';
import axios from 'axios';
import Navbar from '../components/Navbar';
const API_URL = process.env.REACT_APP_API_URL;

const Register = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [mensaje, setMensaje] = useState({ text: '', success: false });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await axios.post(`${API_URL}/users/register`, { username, password });
      setMensaje({ text: "✅ Usuario registrado correctamente.", success: true });
      setUsername('');
      setPassword('');
    } catch (err) {
      setMensaje({ text: "❌ Error al registrar.", success: false });
    }
  };

  return (
    <>
      <Navbar />
      <div style={styles.page}>
        <div style={styles.card}>
          <h1 style={styles.title}>Crear Cuenta</h1>
          <form onSubmit={handleSubmit} style={styles.form}>
            <input
              type="text"
              placeholder="Usuario"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={styles.input}
              required
            />
            <input
              type="password"
              placeholder="Contraseña"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              style={styles.input}
              required
            />
            <button type="submit" style={styles.button}>Registrarse</button>
          </form>
          {mensaje.text && (
            <p style={mensaje.success ? styles.msgSuccess : styles.msgError}>
              {mensaje.text}
            </p>
          )}
        </div>
      </div>
    </>
  );
};

const styles = {
  page: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #6b8dd6 100%)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
  },
  card: {
    backgroundColor: 'rgba(20, 20, 30, 0.85)',
    padding: 40,
    borderRadius: 16,
    boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
    maxWidth: 400,
    width: '100%',
    textAlign: 'center',
    color: '#eee',
  },
  title: {
    marginBottom: 24,
    fontWeight: '700',
    fontSize: 30,
    color: '#f0f0f5',
    textShadow: '0 2px 5px rgba(0,0,0,0.4)',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
  },
  input: {
    backgroundColor: 'rgba(255,255,255,0.1)',
    border: 'none',
    color: '#eee',
    padding: '14px 16px',
    margin: '10px 0',
    borderRadius: 12,
    fontSize: 16,
    outline: 'none',
    boxShadow: 'inset 0 0 5px rgba(255,255,255,0.15)',
    transition: 'background-color 0.3s',
  },
  button: {
    marginTop: 20,
    padding: '14px',
    borderRadius: 12,
    backgroundColor: '#6b8dd6',
    color: 'white',
    fontWeight: '700',
    fontSize: 18,
    border: 'none',
    cursor: 'pointer',
    boxShadow: '0 4px 15px rgba(107,141,214,0.6)',
    transition: 'background-color 0.3s ease',
  },
  msgSuccess: {
    marginTop: 20,
    color: '#7fff7f',
    fontWeight: '700',
  },
  msgError: {
    marginTop: 20,
    color: '#ff6f6f',
    fontWeight: '700',
  },
};

export default Register;
