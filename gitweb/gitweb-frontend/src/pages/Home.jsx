import React from 'react';
import { Link } from 'react-router-dom';
const API_URL = process.env.REACT_APP_API_URL;

const Home = () => {
  return (
    <div style={{
      fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
      color: '#24292e',
      backgroundColor: '#f6f8fa',
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: '60px 20px',
    }}>
      {/* Header principal */}
      <header style={{ maxWidth: 700, textAlign: 'center', marginBottom: 40 }}>
        <h1 style={{ fontSize: '3.5rem', fontWeight: '700', marginBottom: 20 }}>
          GitWeb: tu GitHub personalizado
        </h1>
        <p style={{ fontSize: '1.25rem', color: '#57606a', marginBottom: 30 }}>
          Gestiona tus repositorios, colabora con tus proyectos y controla tu código en un solo lugar, a tu manera.
        </p>
        <div>
          <Link
            to="/login"
            style={{
              backgroundColor: '#2ea44f',
              color: 'white',
              fontWeight: '600',
              padding: '12px 28px',
              borderRadius: 6,
              textDecoration: 'none',
              marginRight: 15,
              boxShadow: '0 4px 14px rgb(46 164 79 / 39%)',
              transition: 'background-color 0.3s',
            }}
            onMouseOver={e => e.currentTarget.style.backgroundColor = '#279644'}
            onMouseOut={e => e.currentTarget.style.backgroundColor = '#2ea44f'}
          >
            Iniciar sesión
          </Link>
          <Link
            to="/register"
            style={{
              backgroundColor: '#0366d6',
              color: 'white',
              fontWeight: '600',
              padding: '12px 28px',
              borderRadius: 6,
              textDecoration: 'none',
              boxShadow: '0 4px 14px rgb(3 102 214 / 39%)',
              transition: 'background-color 0.3s',
            }}
            onMouseOver={e => e.currentTarget.style.backgroundColor = '#0356b6'}
            onMouseOut={e => e.currentTarget.style.backgroundColor = '#0366d6'}
          >
            Crear cuenta
          </Link>
        </div>
      </header>

      {/* Sección características */}
      <section style={{
        display: 'flex',
        justifyContent: 'center',
        gap: '40px',
        maxWidth: 900,
        flexWrap: 'wrap',
      }}>
        {[
          {
            title: 'Repositorios ilimitados',
            desc: 'Crea, almacena y administra todos tus proyectos sin límite.',
            icon: '📁',
          },
          {
            title: 'Control total de versiones',
            desc: 'Haz commit, push y merge con facilidad desde tu web personalizada.',
            icon: '🔧',
          },
          {
            title: 'Colaboración en equipo',
            desc: 'Invita a compañeros y trabaja en equipo con acceso controlado.',
            icon: '🤝',
          },
        ].map(({ title, desc, icon }) => (
          <div key={title} style={{
            backgroundColor: 'white',
            padding: 20,
            borderRadius: 12,
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            width: 260,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 48, marginBottom: 10 }}>{icon}</div>
            <h3 style={{ marginBottom: 10, color: '#24292e' }}>{title}</h3>
            <p style={{ color: '#57606a', fontSize: '0.95rem' }}>{desc}</p>
          </div>
        ))}
      </section>

      {/* Pie de página simple */}
      <footer style={{ marginTop: 60, color: '#57606a' }}>
        <p>© 2025 GitWeb, creado por ti.</p>
      </footer>
    </div>
  );
};

export default Home;
