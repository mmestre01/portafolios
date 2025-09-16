from flask import Blueprint, request, jsonify
from app.database import get_db

bp3 = Blueprint('commits', __name__, url_prefix='/commits')
@bp3.route('/merge', methods=['POST'])
def merge_branches():
    data = request.json
    repo_id = data.get('repo_id')
    source_branch = data.get('source_branch')
    target_branch = data.get('target_branch')
    message = data.get('message', f"Merge {source_branch} into {target_branch}")

    db = get_db()
    cursor = db.cursor()

    # IDs de ramas
    cursor.execute("SELECT id FROM branches WHERE repo_id=? AND name=?", (repo_id, source_branch))
    src = cursor.fetchone()
    cursor.execute("SELECT id FROM branches WHERE repo_id=? AND name=?", (repo_id, target_branch))
    tgt = cursor.fetchone()
    if not src or not tgt:
        return jsonify({'error': 'Rama no encontrada'}), 404

    src_id, tgt_id = src['id'], tgt['id']

    # Snapshot de origen y destino
    def snapshot(branch_id):
        cursor.execute("SELECT id FROM commits WHERE repo_id=? AND branch_id=? ORDER BY id ASC", (repo_id, branch_id))
        commits = cursor.fetchall()
        snap = {}
        for c in commits:
            cursor.execute("SELECT path, content FROM files WHERE commit_id=?", (c['id'],))
            for f in cursor.fetchall():
                snap[f['path']] = f['content']
        return snap

    src_snap = snapshot(src_id)
    tgt_snap = snapshot(tgt_id)

    # Merge simple
    merged = dict(tgt_snap)  # empezar desde destino
    conflicts = []
    for path, content in src_snap.items():
        if path not in tgt_snap:
            merged[path] = content
        elif tgt_snap[path] != content:
            conflicts.append(path)
            merged[path] = f"<<<<<<< {source_branch}\n{content}\n=======\n{tgt_snap[path]}\n>>>>>>> {target_branch}"

    # Crear commit en destino
    cursor.execute(
        "INSERT INTO commits (repo_id, branch_id, message, created_at) VALUES (?, ?, ?, datetime('now'))",
        (repo_id, tgt_id, message)
    )
    commit_id = cursor.lastrowid
    for path, content in merged.items():
        cursor.execute("INSERT INTO files (commit_id, path, content) VALUES (?, ?, ?)", (commit_id, path, content))

    db.commit()

    return jsonify({'message': 'Merge completado', 'commit_id': commit_id, 'conflicts': conflicts})

# Crear un commit con archivos
@bp3.route('/create', methods=['POST'])
def create_commit():
    data = request.json
    

    repo_id = data.get('repo_id')
    message = data.get('message')
    files = data.get('files', [])
    branch_name = data.get('branch')

    db = get_db()
    cursor = db.cursor()

    # Buscar branch_id
    cursor.execute("SELECT id FROM branches WHERE repo_id=? AND name=?", (repo_id, branch_name))
    branch = cursor.fetchone()
    print("DEBUG branch found:", branch)  # 👀

    if not branch:
        return jsonify({'error': 'Branch not found'}), 404
    branch_id = branch['id']

    # Insertar commit
    cursor.execute(
        "INSERT INTO commits (repo_id, branch_id, message, created_at) VALUES (?, ?, ?, datetime('now'))",
        (repo_id, branch_id, message)
    )
    commit_id = cursor.lastrowid

    # Insertar archivos del commit
    for f in files:
        print("DEBUG inserting file:", f)  # 👀
        cursor.execute(
            "INSERT INTO files ( commit_id, path, content) VALUES (?, ?, ?)",
            ( commit_id, f.get('path'), f.get('content'))
        )

    db.commit()
    return jsonify({'message': 'Commit creado', 'commit_id': commit_id})


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
