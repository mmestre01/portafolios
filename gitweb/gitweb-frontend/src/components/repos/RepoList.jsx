import React, { useEffect, useState } from 'react';
import api from '../../services/api';

function RepoList() {
  const [repos, setRepos] = useState([]);

  useEffect(() => {
    api.get('/repos/')
      .then(res => setRepos(res.data))
      .catch(console.error);
  }, []);

  return (
    <div>
      <h2>Repositorios</h2>
      <ul>
        {repos.map(r => (
          <li key={r.id}>{r.name} - {r.description}</li>
        ))}
      </ul>
    </div>
  );
}

export default RepoList;
