from flask import Blueprint, request, jsonify
from app.database import get_db

bp2 = Blueprint('repos', __name__, url_prefix='/repos')
@bp2.route("/<int:repo_id>/branches", methods=["GET"])
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
@bp2.route('/<int:repo_id>', methods=['PUT'])
def update_repo(repo_id):
    data = request.json
    description = data.get("description")

    db = get_db()
    cursor = db.cursor()

    # Comprobar que existe
    cursor.execute("SELECT id FROM repositories WHERE id = ?", (repo_id,))
    repo = cursor.fetchone()
    if not repo:
        return jsonify({"error": "Repositorio no encontrado"}), 404

    # Actualizar descripción
    cursor.execute(
        "UPDATE repositories SET description = ? WHERE id = ?",
        (description, repo_id)
    )
    db.commit()

    return jsonify({"message": "Descripción actualizada correctamente"})
@bp2.route('/user/<int:user_id>', methods=['GET'])
def get_user_repos(user_id):
    db = get_db()
    cursor = db.cursor()

    # Repos propios
    cursor.execute(
        "SELECT id, name, description, 'owner' as role FROM repositories WHERE owner_id = ?",
        (user_id,)
    )
    own_repos = cursor.fetchall()

    # Repos compartidos
    cursor.execute("""
        SELECT r.id, r.name, r.description, 'collaborator' as role
        FROM repo_collaborators rc
        JOIN repositories r ON rc.repo_id = r.id
        WHERE rc.user_id = ?
    """, (user_id,))
    shared_repos = cursor.fetchall()

    # Unimos
    repos = own_repos + shared_repos

    return jsonify([
        {
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'role': row['role']  # 👈 así sabes si es dueño o colaborador
        }
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
from flask import Blueprint, request, jsonify
from app.database import get_db


# Listar colaboradores
@bp2.route("/<int:repo_id>/collaborators", methods=["GET"])
def list_collaborators(repo_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT u.id, u.username, rc.role
        FROM repo_collaborators rc
        JOIN users u ON rc.user_id = u.id
        WHERE rc.repo_id = ?
    """, (repo_id,))
    rows = cursor.fetchall()
    return jsonify([{"id": r["id"], "username": r["username"], "role": r["role"]} for r in rows])


# Añadir colaborador
@bp2.route("/<int:repo_id>/collaborators", methods=["POST"])
def add_collaborator(repo_id):
    data = request.json
    username = data.get("username")
    role = data.get("role", "collaborator")

    db = get_db()
    cursor = db.cursor()

    # buscar user_id
    cursor.execute("SELECT id FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404

    user_id = user["id"]

    # evitar duplicados
    cursor.execute("SELECT id FROM repo_collaborators WHERE repo_id=? AND user_id=?", (repo_id, user_id))
    if cursor.fetchone():
        return jsonify({"error": "Ya es colaborador"}), 400

    cursor.execute(
        "INSERT INTO repo_collaborators (repo_id, user_id, role) VALUES (?, ?, ?)",
        (repo_id, user_id, role)
    )
    db.commit()
    return jsonify({"message": "Colaborador añadido"}), 201


# Eliminar colaborador
@bp2.route("/<int:repo_id>/collaborators/<int:user_id>", methods=["DELETE"])
def remove_collaborator(repo_id, user_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM repo_collaborators WHERE repo_id=? AND user_id=?", (repo_id, user_id))
    db.commit()
    return jsonify({"message": "Colaborador eliminado"}), 200


@bp2.route('/delete/<int:repo_id>', methods=['DELETE'])
def delete_repo(repo_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM repositories WHERE id = ?", (repo_id,))
    db.commit()
    return jsonify({'message': 'Repositorio eliminado correctamente'})

@bp2.route("/<int:repo_id>/branches", methods=["POST"])
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
    branch_name = request.args.get("branch")  # nombre de rama
    db = get_db()
    cursor = db.cursor()

    # Buscar branch_id según el nombre
    if branch_name:
        cursor.execute("SELECT id FROM branches WHERE repo_id=? AND name=?", (repo_id, branch_name))
        branch = cursor.fetchone()
        if not branch:
            return jsonify({'error': 'Branch not found'}), 404
        branch_id = branch['id']
        cursor.execute(
            "SELECT id, message, created_at FROM commits WHERE repo_id=? AND branch_id=? ORDER BY id DESC",
            (repo_id, branch_id)
        )
    else:
        # Si no pasan branch, usar todas (o la default)
        cursor.execute(
            "SELECT id, message, created_at FROM commits WHERE repo_id=? ORDER BY id DESC",
            (repo_id,)
        )

    commits = cursor.fetchall()

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