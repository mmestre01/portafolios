# app/routes/files.py
from flask import Blueprint, request, jsonify
from app.database import get_db

bp4 = Blueprint('files', __name__, url_prefix='/files')

@bp4.route('/<int:repo_id>', methods=['GET'])
def list_files(repo_id):
    path = request.args.get('path', '')

    db = get_db()
    cursor = db.cursor()

    # Traemos la última versión de cada archivo del repo
    cursor.execute("""
        SELECT f.path, f.content FROM files f
        JOIN commits c ON f.commit_id = c.id
        WHERE c.repo_id = ?
        AND f.id IN (
            SELECT MAX(f2.id)
            FROM files f2
            JOIN commits c2 ON f2.commit_id = c2.id
            WHERE c2.repo_id = ?
            GROUP BY f2.path
        )
    """, (repo_id, repo_id))

    all_files = cursor.fetchall()
    result = []
    paths_seen = set()

    for f in all_files:
        file_path = f['path']
        if not file_path.startswith(path):
            continue
        relative_path = file_path[len(path):].strip('/')
        if '/' in relative_path:
            folder = relative_path.split('/')[0]
            if folder not in paths_seen:
                result.append({"name": folder, "path": f"{path}/{folder}".strip('/'), "type": "folder"})
                paths_seen.add(folder)
        else:
            result.append({"name": relative_path, "path": file_path, "type": "file"})

    return jsonify(result)

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
