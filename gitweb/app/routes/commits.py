from flask import Blueprint, request, jsonify
from app.database import get_db

bp3 = Blueprint('commits', __name__, url_prefix='/commits')

# Crear un commit con archivos
@bp3.route('/create', methods=['POST'])
def create_commit():
    data = request.json
    repo_id = data.get('repo_id')
    message = data.get('message')
    files = data.get('files')  # lista de {path, content}

    if not repo_id or not message or not files or len(files) == 0:
        return jsonify({'error': 'repo_id, message y al menos un archivo son requeridos'}), 400

    db = get_db()
    cursor = db.cursor()
    
    cursor.execute("INSERT INTO commits (repo_id, message) VALUES (?, ?)", (repo_id, message))
    commit_id = cursor.lastrowid

    for f in files:
        cursor.execute(
            "INSERT INTO files (commit_id, path, content) VALUES (?, ?, ?)",
            (commit_id, f['path'], f['content'])
        )

    db.commit()
    return jsonify({'message': 'Commit creado', 'commit_id': commit_id}), 201

# Obtener commits de un repositorio
@bp3.route('/repo/<int:repo_id>', methods=['GET'])
def get_commits(repo_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM commits WHERE repo_id = ? ORDER BY created_at DESC", (repo_id,))
    commits = cursor.fetchall()
    return jsonify([
        {'id': c['id'], 'message': c['message'], 'created_at': c['created_at']}
        for c in commits
    ])

# Obtener archivos de un commit
@bp3.route('/<int:commit_id>/files', methods=['GET'])
def get_commit_files(commit_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM files WHERE commit_id = ?", (commit_id,))
    files = cursor.fetchall()
    return jsonify([
        {'id': f['id'], 'path': f['path'], 'content': f['content']}
        for f in files
    ])
