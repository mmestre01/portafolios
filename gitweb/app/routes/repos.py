from flask import Blueprint, request, jsonify
from app.database import get_db

bp2 = Blueprint('repos', __name__, url_prefix='/repos')
@bp2.route("/repos/<int:repo_id>/branches", methods=["GET"])
def get_branches(repo_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM branches WHERE repo_id=?", (repo_id,))
    rows = cursor.fetchall()
    return jsonify([{"name": r[0]} for r in rows])
@bp2.route('/create', methods=['POST'])
def create_repo():
    data = request.json
    name = data.get('name')
    description = data.get('description')
    owner_id = data.get('owner_id')
    
    if not name or not owner_id:
        return jsonify({'error': 'Nombre y owner_id son requeridos'}), 400

    db = get_db()
    cursor = db.cursor()

    # Crear repositorio
    cursor.execute(
        "INSERT INTO repositories (name, description, owner_id, default_branch) VALUES (?, ?, ?, ?)",
        (name, description, owner_id, "master")
    )
    repo_id = cursor.lastrowid

    # Crear rama master asociada al repo
    cursor.execute(
        "INSERT INTO branches (repo_id, name) VALUES (?, ?)",
        (repo_id, "master")
    )

    db.commit()
    return jsonify({
        'message': 'Repositorio creado correctamente',
        'repo_id': repo_id,
        'default_branch': 'master'
    }), 201


@bp2.route('/user/<int:user_id>', methods=['GET'])
def get_user_repos(user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        "SELECT id, name, description FROM repositories WHERE owner_id = ?",
        (user_id,)
    )
    repos = cursor.fetchall()
    return jsonify([
        {'id': row['id'], 'name': row['name'], 'description': row['description']}
        for row in repos
    ])
@bp2.route('/<int:repo_id>', methods=['GET'])
def get_repo(repo_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name, description FROM repositories WHERE id = ?", (repo_id,))
    repo = cursor.fetchone()
    if repo is None:
        return jsonify({'error': 'Repositorio no encontrado'}), 404
    return jsonify({'id': repo['id'], 'name': repo['name'], 'description': repo['description']})


@bp2.route('/delete/<int:repo_id>', methods=['DELETE'])
def delete_repo(repo_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
    db.commit()
    return jsonify({'message': 'Repositorio eliminado correctamente'})

@bp2.route("/repos/<int:repo_id>/branches", methods=["POST"])
def create_branch(repo_id):
    data = request.json
    name = data.get("name")
    conn = get_db()
    c = conn.cursor()
    c.execute("INSERT INTO branches (repo_id, name) VALUES (?, ?)", (repo_id, name))
    conn.commit()
    return jsonify({"message": "Rama creada", "name": name})

@bp2.route('/<int:repo_id>/commits', methods=['GET'])
def get_commits(repo_id):
    db = get_db()
    cursor = db.cursor()
    
    # Obtener todos los commits del repositorio
    cursor.execute(
        "SELECT id, message, created_at FROM commits WHERE repo_id = ? ORDER BY id DESC",
        (repo_id,)
    )
    commits = cursor.fetchall()
    
    # Añadir los archivos de cada commit
    result = []
    for c in commits:
        cursor.execute("SELECT path, content FROM files WHERE commit_id = ?", (c['id'],))
        files = cursor.fetchall()
        result.append({
            'id': c['id'],
            'message': c['message'],
            'created_at': c['created_at'],
            'files': [{'path': f['path'], 'content': f['content']} for f in files]
        })
    
    return jsonify(result)