from flask import Blueprint, request, jsonify
from app.database import get_db
from werkzeug.security import generate_password_hash, check_password_hash

from flask import Blueprint, request, jsonify

bp = Blueprint('users', __name__, url_prefix='/users')

@bp.route('/', methods=['GET'], strict_slashes=False)
def list_users():
    db = get_db()
    users = db.execute(
        'SELECT id, username, email FROM users'
    ).fetchall()

    return jsonify([
        {
            'id': user['id'],
            'username': user['username'],
            'email': user['email']
        }
        for user in users
    ])

@bp.route('/', methods=['POST'], strict_slashes=False)
def create_user():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not username or not email or not password:
        return jsonify({'error': 'username, email y password son requeridos'}), 400

    hashed_password = generate_password_hash(password)

    db = get_db()
    try:
        db.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, hashed_password)
        )
        db.commit()
    except Exception as e:
        return jsonify({'error': str(e)}), 400

    return jsonify({'message': 'Usuario creado correctamente'}), 201

@bp.route('/login', methods=['POST'], strict_slashes=False)
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'username y password requeridos'}), 400

    db = get_db()
    user = db.execute(
        'SELECT * FROM users WHERE username = ?',
        (username,)
    ).fetchone()

    if user is None:
        return jsonify({'error': 'Usuario no encontrado'}), 404

    if user['password'] != password:
        return jsonify({'error': 'Contraseña incorrecta'}), 401
    
    return jsonify({
    'message': 'Login exitoso',
    'user': {
      'id': user['id'],
      'username': user['username']
    }
    }), 200
@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({'error': 'Faltan datos'}), 400

    db = get_db()
    db.execute(
        "INSERT INTO users (username, password) VALUES (?, ?)",
        (username, password)
    )
    db.commit()
    return jsonify({'message': 'Usuario creado'}), 201