// src/context/AuthContext.jsx
import React, { createContext, useState, useEffect } from 'react';
import axios from 'axios';

// Crear el contexto
export const AuthContext = createContext();

// Proveedor del contexto
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);  // usuario logueado o null
  const [loading, setLoading] = useState(true); // para saber si carga sesión

  // Si quieres mantener sesión persistente, puedes cargarla aquí con useEffect
  useEffect(() => {
    const fetchUser = async () => {
      try {
        // Por ejemplo, si tienes un endpoint que devuelve el usuario logueado actual
        const res = await axios.get('http://localhost:5000/users/session', { withCredentials: true });
        setUser(res.data.user); 
      } catch {
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    fetchUser();
  }, []);

  // Función para hacer login
const loginUser = (data) => {
  // data es la respuesta completa del backend
  setUser(data.user);  // aquí sacamos el user
};




  // Función para hacer logout
  const logoutUser = async () => {
    try {
      await axios.post('http://localhost:5000/users/logout', {}, { withCredentials: true });
      setUser(null);
    } catch {
      // manejar error si quieres
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginUser, logoutUser }}>
      {children}
    </AuthContext.Provider>
  );
};
