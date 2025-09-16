import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
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
    flexWrap: "wrap",
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
  branchCard: {
    marginTop: 20,
    background: "white",
    padding: 20,
    borderRadius: 8,
    boxShadow: "0 1px 3px rgba(27,31,35,.1)",
    display: "flex",
    alignItems: "center",
    gap: 12,
    flexWrap: "wrap",
  },
  conflictBox: {
    marginTop: 20,
    padding: 12,
    border: "1px solid #d73a49",
    backgroundColor: "#ffeef0",
    borderRadius: 6,
    color: "#86181d",
  },
};

const RepoDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
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
  const [branches, setBranches] = useState([]);
  const [currentBranch, setCurrentBranch] = useState("");
  const [newBranch, setNewBranch] = useState("");
  const [mergeTarget, setMergeTarget] = useState("");
  const [conflicts, setConflicts] = useState([]);

  // colaboradores
  const [collaborators, setCollaborators] = useState([]);
  const [newCollaborator, setNewCollaborator] = useState("");

  // editar descripción
  const [editingDesc, setEditingDesc] = useState(false);
  const [descValue, setDescValue] = useState("");

  useEffect(() => {
    async function fetchRepo() {
      try {
        const repoRes = await axios.get(`${API_URL}/repos/${id}`);
        setRepo(repoRes.data);
        setDescValue(repoRes.data.description || "");
        await fetchBranches();
        await fetchCollaborators();
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    }
    fetchRepo();
  }, [id]);

  useEffect(() => {
    if (currentBranch) {
      fetchFilesAndCommits(currentBranch);
      setSelectedPath("");
      setFileContent("");
      setExpandedFolders({});
    }
  }, [currentBranch]);

  const fetchBranches = async () => {
    try {
      const res = await axios.get(`${API_URL}/branches/${id}`);
      setBranches(res.data);
      if (!currentBranch && res.data.length > 0) {
        setCurrentBranch(res.data[0].name);
      }
    } catch (err) {
      console.error("Error cargando ramas", err);
    }
  };

  const fetchCollaborators = async () => {
    try {
      const res = await axios.get(`${API_URL}/repos/${id}/collaborators`);
      setCollaborators(res.data);
    } catch (err) {
      console.error("Error cargando colaboradores", err);
    }
  };

  const addCollaborator = async () => {
    if (!newCollaborator) return;
    try {
      await axios.post(`${API_URL}/repos/${id}/collaborators`, { username: newCollaborator });
      setNewCollaborator("");
      fetchCollaborators();
    } catch {
      alert("Error añadiendo colaborador");
    }
  };

  const removeCollaborator = async (userId) => {
    try {
      await axios.delete(`${API_URL}/repos/${id}/collaborators/${userId}`);
      fetchCollaborators();
    } catch {
      alert("Error eliminando colaborador");
    }
  };

  const updateDescription = async () => {
    try {
      await axios.put(`${API_URL}/repos/${id}`, { description: descValue });
      setRepo((prev) => ({ ...prev, description: descValue }));
      setEditingDesc(false);
    } catch {
      alert("Error actualizando descripción");
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

  const changeBranch = (branch) => setCurrentBranch(branch);

  const createBranch = async (branchName) => {
    if (!branchName) return alert("Debes poner un nombre de rama");
    try {
      await axios.post(`${API_URL}/branches/create`, { repo_id: id, name: branchName });
      setNewBranch("");
      fetchBranches();
    } catch {
      alert("Error creando rama");
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
    } catch {
      alert("No se pudo cargar la carpeta");
    }
  };

  const fetchFileContent = async (path) => {
    setSelectedPath(path);
    try {
      const res = await axios.get(`${API_URL}/files/${id}/file?path=${encodeURIComponent(path)}&branch=${currentBranch}`);
      setFileContent(res.data.content);
    } catch {
      alert("No se pudo cargar el archivo");
    }
  };

  const downloadFile = (filename, content) => {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleFileSelect = (e) => {
    const files = Array.from(e.target.files);
    const formatted = files.map((f) => ({ file: f, path: f.webkitRelativePath || f.name }));
    setSelectedFiles((prev) => [...prev, ...formatted]);
  };

  const removeSelectedFile = (path) => {
    setSelectedFiles((prev) => prev.filter((f) => f.path !== path));
  };

  const createCommit = async () => {
    if (!commitMessage || selectedFiles.length === 0) {
      return alert("Debes poner un mensaje y seleccionar al menos un archivo.");
    }
    const filesData = await Promise.all(
      selectedFiles.map(async (f) => ({ path: f.path, content: await f.file.text() }))
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
      fetchFilesAndCommits(currentBranch);
    } catch {
      alert("Error al crear commit");
    }
  };

  const mergeBranches = async () => {
    if (!mergeTarget) return alert("Debes seleccionar la rama destino");
    try {
      const res = await axios.post(`${API_URL}/commits/merge`, {
        repo_id: id,
        source_branch: currentBranch,
        target_branch: mergeTarget,
      });
      setConflicts(res.data.conflicts || []);
      alert("Merge completado");
      await fetchFilesAndCommits(currentBranch);
    } catch (err) {
      alert("Error en merge: " + (err.response?.data?.error || err.message));
    }
  };

  const toggleCommitExpand = async (commitId) => {
    if (expandedCommit === commitId) return setExpandedCommit(null);
    try {
      const res = await axios.get(`${API_URL}/commits/${commitId}/files?branch=${currentBranch}`);
      setExpandedCommit({ id: commitId, files: res.data });
      setExpandedFile(null);
    } catch {}
  };

  const toggleFileExpand = async (commitId, path) => {
    if (expandedFile?.path === path) return setExpandedFile(null);
    try {
      const res = await axios.get(
        `${API_URL}/files/${id}/file?path=${encodeURIComponent(path)}&branch=${currentBranch}`
      );
      setExpandedFile({ commitId, path, content: res.data.content });
    } catch {}
  };

  const renderFiles = (filesList) =>
    filesList.map((f) => (
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
          <div style={styles.folderChildren}>{renderFiles(expandedFolders[f.path])}</div>
        )}
      </div>
    ));

  if (loading) return <div style={{ padding: 20 }}>Cargando...</div>;
  if (!repo) return <div style={{ padding: 20, color: "red" }}>Repositorio no encontrado</div>;

  return (
    <div style={styles.container}>
      {/* 🔙 Volver */}
      <button
        style={{ ...styles.buttonSecondary, marginBottom: 15 }}
        onClick={() => navigate("/repos")}
      >
        ⬅️ Volver al listado
      </button>

      <header style={styles.header}>
        <div style={styles.repoName}>
          {repo.owner_username} / {repo.name}
        </div>

        {/* ✏️ Editable descripción */}
        {!editingDesc ? (
          <div style={styles.description}>
            {repo.description || "Sin descripción"}{" "}
            <button
              style={{
                border: "none",
                background: "transparent",
                cursor: "pointer",
                color: "#0366d6",
              }}
              onClick={() => setEditingDesc(true)}
            >
              ✏️
            </button>
          </div>
        ) : (
          <div style={{ marginTop: 10 }}>
            <textarea
              style={styles.textarea}
              value={descValue}
              onChange={(e) => setDescValue(e.target.value)}
            />
            <div style={{ marginTop: 6, display: "flex", gap: 10 }}>
              <button style={styles.buttonPrimary} onClick={updateDescription}>
                💾 Guardar
              </button>
              <button
                style={styles.buttonSecondary}
                onClick={() => {
                  setEditingDesc(false);
                  setDescValue(repo.description || "");
                }}
              >
                ❌ Cancelar
              </button>
            </div>
          </div>
        )}

        {/* 👥 Colaboradores */}
        <div
          style={{
            marginTop: 20,
            background: "white",
            padding: 20,
            borderRadius: 8,
            boxShadow: "0 1px 3px rgba(27,31,35,.1)",
          }}
        >
          <h4 style={{ marginBottom: 12 }}>👥 Colaboradores</h4>
          {collaborators.length === 0 ? (
            <p style={{ color: "#586069" }}>No hay colaboradores.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0 }}>
              {collaborators.map((c) => (
                <li
                  key={c.id}
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "6px 0",
                    borderBottom: "1px solid #e1e4e8",
                  }}
                >
                  <span>
                    <b>{c.username}</b>{" "}
                    <span style={{ color: "#6a737d" }}>({c.role})</span>
                  </span>
                  <button
                    style={{
                      background: "transparent",
                      border: "none",
                      color: "#d73a49",
                      cursor: "pointer",
                      fontSize: 14,
                    }}
                    onClick={() => removeCollaborator(c.id)}
                  >
                    ❌
                  </button>
                </li>
              ))}
            </ul>
          )}
          <div style={{ marginTop: 12, display: "flex", gap: 8 }}>
            <input
              type="text"
              placeholder="Usuario a invitar..."
              value={newCollaborator}
              onChange={(e) => setNewCollaborator(e.target.value)}
              style={{
                flex: 1,
                padding: "8px 10px",
                borderRadius: 6,
                border: "1px solid #ccc",
              }}
            />
            <button style={styles.buttonPrimary} onClick={addCollaborator}>
              ➕ Añadir
            </button>
          </div>
        </div>
      </header>

      {/* Tabs */}
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

      {/* Code tab */}
      {activeTab === "code" && (
        <div style={styles.filesSection}>
          {/* 🌿 Branch selector más chulo */}
          <div style={styles.branchCard}>
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
            <button style={styles.buttonSecondary} onClick={() => createBranch(newBranch)}>
              ➕ Crear rama
            </button>
            <button
              style={styles.buttonPrimary}
              onClick={() =>
                window.open(`${API_URL}/files/${id}/download?branch=${currentBranch}`, "_blank")
              }
            >
              ⬇️ Descargar repositorio
            </button>
          </div>

          {files.length === 0 ? <p>No hay archivos aún.</p> : renderFiles(files)}

          {selectedPath && (
            <div style={{ marginTop: 20 }}>
              <div
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
              >
                <h4 style={{ margin: 0 }}>Contenido de: {selectedPath}</h4>
                <button
                  style={styles.buttonSecondary}
                  onClick={() => downloadFile(selectedPath, fileContent)}
                >
                  ⬇️ Descargar este archivo
                </button>
              </div>
              <pre style={styles.fileContentPreview}>{fileContent}</pre>
            </div>
          )}
        </div>
      )}

      {/* Commits tab */}
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
                  {f.path} <button onClick={() => removeSelectedFile(f.path)}>❌</button>
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

          {/* 🔀 Merge bonito */}
          <div
            style={{
              marginTop: 30,
              padding: 20,
              background: "#f1f8ff",
              border: "1px solid #c8e1ff",
              borderRadius: 8,
            }}
          >
            <h4 style={{ marginTop: 0 }}>🔀 Merge de ramas</h4>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
              <label>Destino:</label>
              <select
                value={mergeTarget}
                onChange={(e) => setMergeTarget(e.target.value)}
                style={{ padding: "6px 10px", borderRadius: 6, border: "1px solid #ccc" }}
              >
                <option value="">-- Selecciona rama --</option>
                {branches
                  .filter((b) => b.name !== currentBranch)
                  .map((b) => (
                    <option key={b.id} value={b.name}>
                      {b.name}
                    </option>
                  ))}
              </select>
              <button style={styles.buttonSecondary} onClick={mergeBranches}>
                🔀 Mergear {currentBranch} → {mergeTarget || "?"}
              </button>
            </div>
            {conflicts.length > 0 && (
              <div style={styles.conflictBox}>
                ⚠️ Conflictos detectados en los siguientes archivos:
                <ul>
                  {conflicts.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
                Revisa el contenido en la rama destino para resolverlos.
              </div>
            )}
          </div>

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
