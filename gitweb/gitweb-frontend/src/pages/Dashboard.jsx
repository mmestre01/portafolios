import React, { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
const API_URL = process.env.REACT_APP_API_URL;


const Dashboard = () => {
  
  const { user, logoutUser } = useContext(AuthContext);
  const navigate = useNavigate();
  const [repos, setRepos] = useState([]);
  const [repoName, setRepoName] = useState('');

  const fetchRepos = async () => {
    try {
      const res = await axios.get(`${API_URL}/repos/user/${user.id}`);
      setRepos(res.data);
    } catch (err) {
      console.error("Error cargando repositorios:", err);
    }
  };

  const createRepo = async () => {
  if (!user || !user.id) {
    console.error("No hay usuario logueado");
    return;
  }

  if (!repoName.trim()) return; // evita nombre vacío

  try {
    await axios.post(`${API_URL}/repos/create`, {
      name: repoName,
      owner_id: user.id,
    });
    setRepoName('');
    fetchRepos();
  } catch (error) {
    console.error("Error creando repositorio:", error);
  }
};


  const deleteRepo = async (id) => {
    try {
      await axios.delete(`${API_URL}/repos/delete/${id}`);
      fetchRepos();
    } catch (err) {
      console.error("Error eliminando repositorio:", err);
    }
  };

 useEffect(() => {
  if (user && user.id) {
    fetchRepos();
  }
}, [user])

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <h1>Bienvenido, {user?.username}</h1>
        <button onClick={() => { logoutUser(); navigate('/login'); }} style={styles.logout}>
          Cerrar sesión
        </button>
      </header>

      <section style={styles.section}>
        <h2 style={styles.subtitle}>Tus Repositorios</h2>
        <div style={styles.repoForm}>
          <input
            type="text"
            placeholder="Nombre del repositorio"
            value={repoName}
            onChange={(e) => setRepoName(e.target.value)}
            style={styles.input}
          />
          <button onClick={createRepo} style={styles.createBtn}>Crear</button>
        </div>

        <div style={styles.repoList}>
          {repos.length === 0 && <p>No tienes repositorios aún.</p>}
          {repos.map((repo) => (
            <div key={repo.id} style={styles.repoCard}>
              <h3>{repo.name}</h3>
              <div>
                <button onClick={() => navigate(`/repos/${repo.id}`)} style={styles.viewBtn}>Ver</button>

                <button onClick={() => deleteRepo(repo.id)} style={styles.deleteBtn}>Eliminar</button>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

const styles = {
  container: {
    padding: 40,
    fontFamily: "'Segoe UI', sans-serif",
    background: '#f4f6f8',
    minHeight: '100vh',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 30,
  },
  logout: {
    padding: '8px 16px',
    background: '#e74c3c',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
  },
  section: {
    background: '#fff',
    padding: 30,
    borderRadius: 12,
    boxShadow: '0 0 15px rgba(0,0,0,0.05)',
  },
  subtitle: {
    fontSize: 24,
    marginBottom: 20,
  },
  repoForm: {
    display: 'flex',
    gap: 10,
    marginBottom: 20,
  },
  input: {
    flex: 1,
    padding: 10,
    borderRadius: 8,
    border: '1px solid #ccc',
  },
  createBtn: {
    padding: '10px 16px',
    background: '#3498db',
    color: '#fff',
    border: 'none',
    borderRadius: 8,
    cursor: 'pointer',
  },
  repoList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  repoCard: {
    padding: 20,
    background: '#fafafa',
    border: '1px solid #ddd',
    borderRadius: 10,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  viewBtn: {
    marginRight: 10,
    padding: '6px 12px',
    background: '#2ecc71',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
  },
  deleteBtn: {
    padding: '6px 12px',
    background: '#e74c3c',
    color: '#fff',
    border: 'none',
    borderRadius: 6,
    cursor: 'pointer',
  },
};

export default Dashboard;
