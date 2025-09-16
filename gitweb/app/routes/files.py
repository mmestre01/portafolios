# app/routes/files.py
from flask import Blueprint, request, jsonify
from app.database import get_db

bp4 = Blueprint('files', __name__, url_prefix='/files')

import os

import os

@bp4.route('/<int:repo_id>', methods=['GET'])
def get_files(repo_id):
    branch_name = request.args.get("branch")
    path = request.args.get("path", "")

    db = get_db()
    cursor = db.cursor()

    # 1. Buscar branch_id
    cursor.execute("SELECT id FROM branches WHERE repo_id=? AND name=?", (repo_id, branch_name))
    branch = cursor.fetchone()
    if not branch:
        return jsonify([])  # rama no encontrada
    branch_id = branch["id"]

    # 2. Buscar todos los commits de esa rama (ordenados por id ascendente = histórico)
    cursor.execute(
        "SELECT id FROM commits WHERE repo_id=? AND branch_id=? ORDER BY id ASC",
        (repo_id, branch_id)
    )
    commits = cursor.fetchall()
    if not commits:
        return jsonify([])

    # 3. Construir snapshot final = última versión de cada archivo
    snapshot = {}
    for c in commits:
        commit_id = c["id"]
        cursor.execute("SELECT path, content FROM files WHERE commit_id=?", (commit_id,))
        files = cursor.fetchall()
        for f in files:
            snapshot[f["path"]] = f["content"]  # sobrescribe versiones anteriores

    # 4. Filtrar por carpeta actual (como GitHub)
    items = {}
    for raw_path, content in snapshot.items():
        # calcular la ruta relativa a `path`
        relative_path = raw_path[len(path):].lstrip("/") if path else raw_path
        if not relative_path:
            continue

        parts = relative_path.split("/", 1)
        name = parts[0]

        if len(parts) > 1:
            # es carpeta
            items[name] = {
                "path": f"{path}/{name}".strip("/"),
                "name": name,
                "type": "folder"
            }
        else:
            # es archivo
            items[name] = {
                "path": raw_path,
                "name": name,
                "type": "file",
                "content": content
            }

    return jsonify(list(items.values()))


import io, zipfile
from flask import send_file

import io, zipfile, sys
from flask import send_file

import io, zipfile
from flask import send_file, Response

import io, zipfile, os
from flask import send_file, jsonify
from app.database import get_db

import io, zipfile, os, tempfile
from flask import send_file, jsonify
from app.database import get_db

@bp4.route('/<int:repo_id>/download', methods=['GET'])
def download_repo(repo_id):
    branch_name = request.args.get("branch")

    db = get_db()
    cursor = db.cursor()

    # Buscar branch_id
    cursor.execute("SELECT id FROM branches WHERE repo_id=? AND name=?", (repo_id, branch_name))
    branch = cursor.fetchone()
    if not branch:
        return jsonify({'error': 'Branch not found'}), 404
    branch_id = branch["id"]

    # Buscar commits de esa rama
    cursor.execute(
        "SELECT id FROM commits WHERE repo_id=? AND branch_id=? ORDER BY id ASC",
        (repo_id, branch_id)
    )
    commits = cursor.fetchall()
    if not commits:
        return jsonify({'error': 'No commits in branch'}), 404

    # Construir snapshot con última versión de cada archivo
    snapshot = {}
    for c in commits:
        commit_id = c["id"]
        cursor.execute("""
            SELECT f.path, f.content
            FROM files f
            JOIN commits c ON f.commit_id = c.id
            WHERE f.commit_id=? AND c.repo_id=?
        """, (commit_id, repo_id))
        for f in cursor.fetchall():
            snapshot[f["path"]] = f["content"]

    if not snapshot:
        return jsonify({'error': 'No files found in branch'}), 404

    # Crear archivo temporal para el ZIP
    tmp_zip = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    zip_path = tmp_zip.name
    tmp_zip.close()

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in snapshot.items():
            if not path:
                continue

            if content is None:
                content = ""
            if isinstance(content, str):
                content = content.encode("utf-8")

            norm_path = path.strip("/")
            print(f"DEBUG: escribiendo en ZIP {norm_path}")
            zf.writestr(norm_path, content)

    return send_file(
        zip_path,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"repo_{repo_id}_{branch_name}.zip"
    )





    


@bp4.route('/files/<int:repo_id>/history', methods=['GET'])
def file_history(repo_id):
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'Path requerido'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT c.id AS commit_id, c.message, c.created_at
        FROM commits c
        JOIN files f ON f.commit_id = c.id
        WHERE f.path = ? AND f.repo_id = ?
        ORDER BY c.created_at DESC
    """, (path, repo_id))
    history = cursor.fetchall()
    
    return jsonify([
        {'commit_id': row['commit_id'], 'message': row['message'], 'created_at': row['created_at']}
        for row in history
    ])

# Ver contenido de un archivo
@bp4.route('/<int:repo_id>/file', methods=['GET'])
def get_file(repo_id):
    path = request.args.get('path')
    if not path:
        return jsonify({'error': 'path requerido'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT f.content FROM files f
        JOIN commits c ON f.commit_id = c.id
        WHERE c.repo_id = ? AND f.path = ?
        ORDER BY c.id DESC LIMIT 1
    """, (repo_id, path))
    file_row = cursor.fetchone()
    if not file_row:
        return jsonify({'error': 'Archivo no encontrado'}), 404
    return jsonify({'path': path, 'content': file_row['content']})

@bp4.route("/<int:repo_id>/history", methods=["GET"], endpoint="file_history_full")
def file_history():
    path = request.args.get("path")
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT f.id AS file_id, f.path, f.content, c.id AS commit_id, c.message, c.created_at
        FROM files f
        JOIN commits c ON f.commit_id = c.id
        WHERE c.repo_id = ? AND f.path = ?
        ORDER BY c.created_at DESC
    """, (repo_id, path))
    files = cursor.fetchall()
    return jsonify([
        {
            "file_id": row["file_id"],
            "path": row["path"],
            "content": row["content"],
            "commit_id": row["commit_id"],
            "message": row["message"],
            "created_at": row["created_at"]
        } for row in files
    ]), 200

@bp4.route("/commits/<int:commit_id>/files", methods=["GET"])
def files_in_commit(commit_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT path, content
        FROM files
        WHERE commit_id = ?
    """, (commit_id,))
    files = cursor.fetchall()
    result = [
        {"path": row["path"], "content": row["content"]}
        for row in files
    ]
    return jsonify(result), 200

# Crear commit con archivos
@bp4.route('/commits/create', methods=['POST'])
def create_commit():
    data = request.json
    repo_id = data.get('repo_id')
    message = data.get('message')
    files = data.get('files', [])

    if not repo_id or not message or not files:
        return jsonify({'error': 'repo_id, message y files son requeridos'}), 400

    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO commits (repo_id, message) VALUES (?, ?)", (repo_id, message))
    commit_id = cursor.lastrowid

    for f in files:
        cursor.execute("INSERT INTO files (commit_id, path, content) VALUES (?, ?, ?)",
                       (commit_id, f['path'], f['content']))
    db.commit()
    return jsonify({'message': 'Commit creado', 'commit_id': commit_id})
