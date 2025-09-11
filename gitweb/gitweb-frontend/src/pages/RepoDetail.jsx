import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
const API_URL = process.env.REACT_APP_API_URL;

const styles = {
  container: {
    fontFamily: "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif",
    maxWidth: 900,
    margin: "20px auto",
    padding: 20,
    backgroundColor: "#f6f8fa",
    borderRadius: 6,
  },
  header: {
    backgroundColor: "white",
    padding: 20,
    borderRadius: 6,
    borderBottom: "1px solid #e1e4e8",
    marginBottom: 20,
  },
  repoName: {
    fontSize: 28,
    fontWeight: "bold",
    color: "#0366d6",
    cursor: "default",
  },
  description: {
    fontSize: 16,
    color: "#586069",
    marginTop: 6,
  },
  navTabs: {
    display: "flex",
    gap: 20,
    borderBottom: "1px solid #e1e4e8",
    paddingBottom: 10,
    marginBottom: 20,
  },
  tab: {
    fontSize: 14,
    color: "#586069",
    cursor: "pointer",
    paddingBottom: 8,
  },
  activeTab: {
    borderBottom: "2px solid #0366d6",
    color: "#0366d6",
    fontWeight: "bold",
  },
  filesSection: {
    backgroundColor: "white",
    padding: 20,
    borderRadius: 6,
    boxShadow: "0 1px 3px rgba(27,31,35,.1)",
  },
  fileItem: {
    padding: "6px 0",
    borderBottom: "1px solid #e1e4e8",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    cursor: "pointer",
  },
  folderChildren: {
    marginLeft: 20,
    marginTop: 4,
  },
  commitItem: {
    padding: "10px 0",
    borderBottom: "1px solid #e1e4e8",
    display: "flex",
    justifyContent: "space-between",
    flexDirection: "column",
    alignItems: "flex-start",
  },
  commitMessage: {
    fontFamily: "monospace",
    fontSize: 14,
    color: "#24292e",
  },
  commitDate: {
    fontSize: 12,
    color: "#6a737d",
  },
  buttonsContainer: {
    marginTop: 20,
    display: "flex",
    gap: 12,
  },
  buttonPrimary: {
    backgroundColor: "#28a745",
    color: "white",
    border: "none",
    padding: "8px 16px",
    borderRadius: 6,
    cursor: "pointer",
    fontWeight: "bold",
  },
  buttonSecondary: {
    backgroundColor: "white",
    color: "#0366d6",
    border: "1px solid #0366d6",
    padding: "8px 16px",
    borderRadius: 6,
    cursor: "pointer",
  },
  textarea: {
    width: "100%",
    padding: 8,
    borderRadius: 6,
    border: "1px solid #ccc",
    marginTop: 10,
    marginBottom: 10,
  },
  commitFiles: {
    marginTop: 8,
    marginLeft: 12,
    paddingLeft: 10,
    borderLeft: "2px solid #e1e4e8",
  },
  fileContentPreview: {
    marginTop: 6,
    backgroundColor: "#f0f0f0",
    padding: 10,
    borderRadius: 6,
    fontFamily: "monospace",
    whiteSpace: "pre-wrap",
  },
  branchBar: {
    display: "flex",
    alignItems: "center",
    gap: 10,
    marginBottom: 20,
  },
};

const RepoDetail = () => {
  const { id } = useParams();
  const [repo, setRepo] = useState(null);
  const [files, setFiles] = useState([]);
  const [fileContent, setFileContent] = useState("");
  const [selectedPath, setSelectedPath] = useState("");
  const [commits, setCommits] = useState([]);
  const [expandedCommit, setExpandedCommit] = useState(null);
  const [expandedFile, setExpandedFile] = useState(null);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [commitMessage, setCommitMessage] = useState("");
  const [activeTab, setActiveTab] = useState("code");
  const [loading, setLoading] = useState(true);
  const [expandedFolders, setExpandedFolders] = useState({});

  // NUEVO: ramas
  const [branches, setBranches] = useState([]);
  const [currentBranch, setCurrentBranch] = useState("main");
  const [newBranch, setNewBranch] = useState("");

  useEffect(() => {
    async function fetchRepo() {
      try {
        const repoRes = await axios.get(`${API_URL}/repos/${id}`);
        setRepo(repoRes.data);

        await fetchBranches();

        await fetchFilesAndCommits(currentBranch);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchRepo();
  }, [id]);

  const fetchBranches = async () => {
    try {
      const res = await axios.get(`${API_URL}/branches/${id}`);
      setBranches(res.data);

      // Guarda solo el nombre de la rama como currentBranch
      if (res.data.length > 0 && currentBranch !== res.data[0].name) {
        setCurrentBranch(res.data[0].name);
      }
    } catch (err) {
      console.error("Error cargando ramas", err);
    }
  };


  const fetchFilesAndCommits = async (branch) => {
    try {
      const filesRes = await axios.get(`${API_URL}/files/${id}?path=&branch=${branch}`);
      setFiles(filesRes.data);

      const commitsRes = await axios.get(`${API_URL}/repos/${id}/commits?branch=${branch}`);
      setCommits(commitsRes.data);
    } catch (err) {
      console.error("Error cargando archivos/commits", err);
    }
  };

  const changeBranch = async (branch) => {
    setCurrentBranch(branch);
    await fetchFilesAndCommits(branch);
  };

const createBranch = async (branchName) => {
  if (!branchName) return alert("Debes poner un nombre de rama");

  try {
    await axios.post(`${API_URL}/branches/create`, {
      repo_id: id,   // id del repo actual
      name: branchName // solo el string
    });
    fetchBranches(); // refrescar la lista
  } catch (err) {
    console.error("Error creando rama", err.response?.data || err);
    alert("Error creando rama: " + (err.response?.data?.error || err.message));
  }
};



  const fetchFolderContent = async (path) => {
    if (expandedFolders[path]) {
      setExpandedFolders((prev) => ({ ...prev, [path]: null }));
      return;
    }
    try {
      const res = await axios.get(`${API_URL}/files/${id}?path=${encodeURIComponent(path)}&branch=${currentBranch}`);
      setExpandedFolders((prev) => ({ ...prev, [path]: res.data }));
    } catch (err) {
      console.error(err);
      alert("No se pudo cargar la carpeta");
    }
  };

  const fetchFileContent = async (path) => {
    setSelectedPath(path);
    try {
      const res = await axios.get(`${API_URL}/files/${id}/file?path=${encodeURIComponent(path)}&branch=${currentBranch}`);
      setFileContent(res.data.content);
    } catch (err) {
      console.error(err);
      alert("No se pudo cargar el archivo");
    }
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const formatted = files.map((f) => ({
      file: f,
      path: f.webkitRelativePath || f.name,
    }));
    setSelectedFiles((prev) => [...prev, ...formatted]);
  };

  const removeSelectedFile = (path) => {
    setSelectedFiles((prev) => prev.filter((f) => f.path !== path));
  };

  const createCommit = async () => {
    if (!commitMessage || selectedFiles.length === 0) {
      alert("Debes poner un mensaje y seleccionar al menos un archivo.");
      return;
    }

    const filesData = await Promise.all(
      selectedFiles.map(async (f) => {
        const content = await f.file.text();
        return { path: f.path, content };
      })
    );

    try {
      await axios.post(`${API_URL}/commits/create`, {
        repo_id: id,
        message: commitMessage,
        files: filesData,
        branch: currentBranch,
      });
      setCommitMessage("");
      setSelectedFiles([]);
      await fetchFilesAndCommits(currentBranch);
      alert("Commit creado correctamente");
    } catch (err) {
      console.error("Error creando commit", err);
      alert("Error al crear commit");
    }
  };

  const toggleCommitExpand = async (commitId) => {
    if (expandedCommit === commitId) {
      setExpandedCommit(null);
      return;
    }
    try {
      const res = await axios.get(`${API_URL}/commits/${commitId}/files?branch=${currentBranch}`);
      setExpandedCommit({ id: commitId, files: res.data });
      setExpandedFile(null);
    } catch (err) {
      console.error("Error cargando archivos del commit", err);
    }
  };

  const toggleFileExpand = async (commitId, path) => {
    if (expandedFile?.path === path) {
      setExpandedFile(null);
      return;
    }
    try {
      const res = await axios.get(
        `${API_URL}/files/${id}/file?path=${encodeURIComponent(path)}&branch=${currentBranch}`
      );
      setExpandedFile({ commitId, path, content: res.data.content });
    } catch (err) {
      console.error("Error cargando contenido del archivo", err);
    }
  };

  const renderFiles = (filesList) => {
    return filesList.map((f) => (
      <div key={f.path}>
        {f.type === "folder" ? (
          <div style={styles.fileItem} onClick={() => fetchFolderContent(f.path)}>
            📁 {f.name}
          </div>
        ) : (
          <div style={styles.fileItem} onClick={() => fetchFileContent(f.path)}>
            📄 {f.name}
          </div>
        )}
        {f.type === "folder" && expandedFolders[f.path] && (
          <div style={styles.folderChildren}>
            {renderFiles(expandedFolders[f.path])}
          </div>
        )}
      </div>
    ));
  };

  if (loading) return <div style={{ padding: 20 }}>Cargando...</div>;
  if (!repo) return <div style={{ padding: 20, color: "red" }}>Repositorio no encontrado</div>;

  return (
    <div style={styles.container}>
      <header style={styles.header}>
        <div style={styles.repoName}>
          {repo.owner_username} / {repo.name}
        </div>
        <div style={styles.description}>{repo.description || "Sin descripción"}</div>
      </header>

      <nav style={styles.navTabs}>
        <div
          onClick={() => setActiveTab("code")}
          style={{ ...styles.tab, ...(activeTab === "code" ? styles.activeTab : {}) }}
        >
          Code
        </div>
        <div
          onClick={() => setActiveTab("commits")}
          style={{ ...styles.tab, ...(activeTab === "commits" ? styles.activeTab : {}) }}
        >
          Commits ({commits.length})
        </div>
      </nav>

      {activeTab === "code" && (
        <div style={styles.filesSection}>
          <div style={styles.branchBar}>
            <label>🌿 Rama actual: </label>
<select value={currentBranch} onChange={(e) => changeBranch(e.target.value)}>
  {branches.map((b) => (
    <option key={b.id} value={b.name}>
      {b.name}
    </option>
  ))}
</select>
            <input
              type="text"
              placeholder="Nueva rama"
              value={newBranch}
              onChange={(e) => setNewBranch(e.target.value)}
            />
            <button
  style={styles.buttonSecondary}
  onClick={() => createBranch(newBranch)}
>
  ➕ Crear rama
</button>

          </div>

          {files.length === 0 ? <p>No hay archivos aún.</p> : renderFiles(files)}

          {selectedPath && (
            <div style={{ marginTop: 20 }}>
              <h4>Contenido de: {selectedPath}</h4>
              <pre style={styles.fileContentPreview}>{fileContent}</pre>
            </div>
          )}
        </div>
      )}

      {activeTab === "commits" && (
        <section style={styles.filesSection}>
          <div style={styles.buttonsContainer}>
            <label style={styles.buttonPrimary}>
              📁 Subir archivos
              <input type="file" multiple style={{ display: "none" }} onChange={handleFileSelect} />
            </label>
            <label style={styles.buttonPrimary}>
              📂 Subir carpeta
              <input
                type="file"
                webkitdirectory="true"
                directory="true"
                multiple
                style={{ display: "none" }}
                onChange={handleFileSelect}
              />
            </label>
          </div>

          {selectedFiles.length > 0 && (
            <div style={{ marginTop: 10 }}>
              {selectedFiles.map((f) => (
                <div key={f.path}>
                  {f.path}{" "}
                  <button onClick={() => removeSelectedFile(f.path)}>❌</button>
                </div>
              ))}
            </div>
          )}

          <textarea
            style={styles.textarea}
            placeholder="Mensaje del commit"
            value={commitMessage}
            onChange={(e) => setCommitMessage(e.target.value)}
          />
          <button style={styles.buttonPrimary} onClick={createCommit}>
            ➕ Crear commit
          </button>

          <h4 style={{ marginTop: 20 }}>Historial de commits:</h4>
          {commits.length === 0 ? (
            <p>No hay commits aún.</p>
          ) : (
            commits.map((commit) => (
              <div key={commit.id} style={styles.commitItem}>
                <div onClick={() => toggleCommitExpand(commit.id)} style={{ cursor: "pointer" }}>
                  <div style={styles.commitMessage}>{commit.message}</div>
                  <div style={styles.commitDate}>
                    {new Date(commit.created_at).toLocaleString()} (#{commit.id})
                  </div>
                </div>
                {expandedCommit?.id === commit.id && (
                  <div style={styles.commitFiles}>
                    {expandedCommit.files.map((f) => (
                      <div
                        key={f.path}
                        style={{ cursor: "pointer", marginTop: 4 }}
                        onClick={() => toggleFileExpand(commit.id, f.path)}
                      >
                        📄 {f.path}
                        {expandedFile?.path === f.path && (
                          <pre style={styles.fileContentPreview}>{expandedFile.content}</pre>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))
          )}
        </section>
      )}
    </div>
  );
};

export default RepoDetail;
