from flask import Blueprint, request, jsonify
from app.database import get_db

bp_branches = Blueprint("branches", __name__, url_prefix="/branches")

# Listar ramas de un repositorio
@bp_branches.route('/<int:repo_id>', methods=['GET'])
def get_branches(repo_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, name FROM branches WHERE repo_id = ?", (repo_id,))
    branches = cursor.fetchall()
    if branches is None:
        return jsonify([]), 200
    # Convertir cada fila a diccionario
    branches_list = [{"id": b[0], "name": b[1]} for b in branches]
    return jsonify(branches_list), 200

# Crear una nueva rama
@bp_branches.route('/create', methods=['POST'])
def create_branch():
    data = request.json
    repo_id = data.get("repo_id")
    name = data.get("name")

    if not repo_id or not name:
        return jsonify({"error": "repo_id y name son requeridos"}), 400

    db = get_db()
    cursor = db.cursor()

    # Verificar que no exista ya la rama con ese nombre
    cursor.execute("SELECT id FROM branches WHERE repo_id = ? AND name = ?", (repo_id, name))
    if cursor.fetchone():
        return jsonify({"error": "La rama ya existe"}), 400

    cursor.execute(
        "INSERT INTO branches (repo_id, name) VALUES (?, ?)",
        (repo_id, name)
    )
    db.commit()
    return jsonify({"message": "Rama creada correctamente"}), 201

# Función auxiliar: crear rama master por defecto al crear repositorio
def create_master_branch(repo_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute("INSERT INTO branches (repo_id, name) VALUES (?, ?)", (repo_id, "master"))
    db.commit()
