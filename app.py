from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
import requests
import os
import random
import string
from urllib.parse import quote

# Configuración de la aplicación
app = Flask(__name__)
app.config.from_object('config.ProductionConfig' if 'DATABASE_URL' in os.environ else 'config.Config')

# Inicialización de la base de datos y bcrypt
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
mail = Mail(app)

class User(db.Model):
    __tablename__ = 'tb_usuario'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    summoner_name = db.Column(db.String(150), unique=True, nullable=True)
    tagline = db.Column(db.String(10), nullable=True)
    profile_picture = db.Column(db.String(255), nullable=True)  # Ruta de la foto de perfil
    verification_code = db.Column(db.String(6), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    partida_en_curso = db.Column(db.Boolean, default=False)  # Nuevo campo para marcar si hay partida en curso
    puntos = db.relationship('PuntosPersona', back_populates='usuario', uselist=False)
    apuestas = db.relationship('Apuesta', back_populates='usuario')



# Modelo de puntos de usuario
class PuntosPersona(db.Model):
    __tablename__ = 'tb_puntos_persona'
    id_usuario = db.Column(db.Integer, db.ForeignKey('tb_usuario.id'), primary_key=True)
    puntos = db.Column(db.Integer, default=0)
    usuario = db.relationship('User', back_populates='puntos')

class Apuesta(db.Model):
    __tablename__ = 'tb_apuestas'
    id_apuesta = db.Column(db.Integer, primary_key=True, autoincrement=True)
    id_usuario = db.Column(db.Integer, db.ForeignKey('tb_usuario.id'), nullable=False)
    id_partida = db.Column(db.String, nullable=False)
    apuesta_tipo = db.Column(db.String, nullable=False)
    puntos_apostados = db.Column(db.Integer, nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)
    resultado = db.Column(db.Boolean, default=None)
    procesada = db.Column(db.Boolean, default=False)
    partida_en_curso = db.Column(db.Boolean, default=False)  # Nuevo campo
    usuario = db.relationship('User', back_populates='apuestas')



class Joke(db.Model):
    __tablename__ = 'tb_chiste'
    id = db.Column(db.Integer, primary_key=True)
    titulo = db.Column(db.String(500), nullable=False)
    chiste = db.Column(db.String(500), nullable=False)

class ChatMessage(db.Model):
    __tablename__ = 'tb_chat'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('tb_usuario.id'), nullable=False)
    message = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())
    user = db.relationship('User', backref='messages')



from flask import Markup
def verificar_resultado_apuesta(apuesta):
    game_info = obtener_estado_partida(apuesta.id_partida)
    
    if game_info and game_info.get('gameEndTime'):
        # Determina si el usuario ganó o perdió
        resultado_apuesta = evaluar_ganador(apuesta.usuario.summoner_name, game_info)
        
        # Asigna los puntos al usuario si la apuesta fue correcta
        if (apuesta.apuesta_tipo == 'ganar' and resultado_apuesta == 'ganar') or \
           (apuesta.apuesta_tipo == 'perder' and resultado_apuesta == 'perder'):
            puntos = calcular_puntos(apuesta.puntos_apostados, resultado_apuesta)
            apuesta.usuario.puntos.puntos += puntos
            apuesta.resultado = True
        else:
            apuesta.resultado = False
            
        apuesta.procesada = True
        db.session.commit()
@app.template_filter('nl2br')
def nl2br(text):
    return Markup(text.replace('\n', '<br>'))
# Generar código de verificación aleatorio
def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

import hashlib
import os
from werkzeug.utils import secure_filename
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])

    if request.method == 'POST':
        # Obtén los valores del formulario
        username = request.form.get('username', '').strip() or user.username
        email = request.form.get('email', '').strip() or user.email
        summoner_name = request.form.get('summoner_name', '').strip() or user.summoner_name
        tagline = request.form.get('tagline', '').strip() or user.tagline

        # Actualiza el usuario con los nuevos datos (solo si no están vacíos)
        user.username = username if username else user.username
        user.email = email if email else user.email
        user.summoner_name = summoner_name if summoner_name else user.summoner_name
        user.tagline = tagline if tagline else user.tagline

        # Si se subió una nueva imagen de perfil
        if 'profile_picture' in request.files:
            profile_picture = request.files['profile_picture']
            if profile_picture and profile_picture.filename != '':
                filename = secure_filename(profile_picture.filename)
                picture_path = os.path.join('static/uploads', filename)
                profile_picture.save(picture_path)
                user.profile_picture = picture_path  # Actualiza la ruta de la imagen en el usuario

        # Guarda todos los cambios en la base de datos
        db.session.commit()

        flash("Ajustes guardados exitosamente.")
        return redirect(url_for('settings'))

    return render_template('settings.html', user=user)

# Carpeta de almacenamiento de imágenes
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Modificar la función para guardar la imagen
def save_profile_picture(file, user_id):
    # Generar un nombre único en hexadecimal usando el ID del usuario y el nombre del archivo original
    original_filename = secure_filename(file.filename)
    unique_name = f"{user_id}_{original_filename}"
    hex_name = hashlib.md5(unique_name.encode()).hexdigest()  # Convierte el nombre en hexadecimal
    extension = os.path.splitext(original_filename)[1]  # Obtener la extensión del archivo

    # Ruta final de la imagen en hexadecimal
    filename = f"{hex_name}{extension}"
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(file_path)

    # Actualizar la ruta en la base de datos
    user = User.query.get(user_id)
    user.profile_picture = f"{app.config['UPLOAD_FOLDER']}/{filename}"
    db.session.commit()

    return filename


from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_mail import Mail, Message



# Función para generar el código de verificación
import random
import string

def generate_verification_code():
    return ''.join(random.choices(string.digits, k=6))

# Función para enviar el correo de verificación
def send_verification_email(user):
    verification_code = generate_verification_code()
    user.verification_code = verification_code
    db.session.commit()  # Guarda el código en la base de datos

    subject = 'Confirma tu cuenta'
    recipients = [user.email]
    body = f"Hola {user.username},\n\nTu código de verificación es: {verification_code}."

    try:
        msg = Message(subject=subject, sender=app.config['MAIL_DEFAULT_SENDER'], recipients=recipients)
        msg.body = body
        mail.send(msg)
        print("Correo enviado con éxito.")
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

# Ruta para enviar el correo de verificación
@app.route('/send_verification/<int:user_id>')
def send_verification(user_id):
    user = User.query.get(user_id)
    if user:
        send_verification_email(user)
        flash("Correo de verificación enviado.")
        return redirect(url_for('verify', email=user.email))
    else:
        flash("Usuario no encontrado.")
        return redirect(url_for('register'))
# Ruta principal
@app.route('/')
def index():
    return redirect(url_for('login'))
@app.route('/jokes')
def jokes():
    jokes_list = Joke.query.all()
    
    for joke in jokes_list:
        original_chiste = joke.chiste  # Texto original
        # Reemplazar `\n` sin cambiar la codificación
        joke.chiste = joke.chiste.replace('\\n', '<br>')
        print(f"Original chiste: {original_chiste}")  # Log del texto original
        print(f"Processed chiste: {joke.chiste}")      # Log del texto después del reemplazo
    
    return render_template('jokes.html', jokes=jokes_list)

# Ruta de registro de usuario
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = bcrypt.generate_password_hash(request.form['password']).decode('utf-8')

        # Verifica si ya existe un usuario con el mismo email o nombre de usuario
        existing_user = User.query.filter((User.email == email) | (User.username == username)).first()
        if existing_user:
            flash('El correo o nombre de usuario ya está en uso.')
            return redirect(url_for('register'))

        # Crear el usuario con un código de verificación
        verification_code = generate_verification_code()
        user = User(username=username, email=email, password=password, verification_code=verification_code)
        
        db.session.add(user)
        db.session.commit()

        # Crear el registro de puntos para el usuario
        puntos_persona = PuntosPersona(id_usuario=user.id, puntos=100)
        db.session.add(puntos_persona)
        db.session.commit()
        
        flash('Registro exitoso, verifica tu correo.')
        return redirect(url_for('verify', email=email))  # Redirigir a la verificación con el email del usuario

    return render_template('register.html')





@app.route('/verify/<email>', methods=['GET', 'POST'])
def verify(email=None):
    if request.method == 'POST':
        entered_code = request.form.get('verification_code')
        user = User.query.filter_by(email=email).first()

        if user and user.verification_code == entered_code:
            user.is_verified = True
            db.session.commit()
            flash('Cuenta verificada con éxito.')
            return redirect(url_for('dashboard'))
        else:
            flash('Código de verificación incorrecto.')

    return render_template('verify.html', email=email)


from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, request

# Proteger rutas para usuarios no verificados
@app.before_request
def restrict_unverified_users():
    restricted_routes = ['dashboard', 'simulations', 'game', 'chaos_game', 'solar_system', 'solar_system_3d', 'ranking', 'chat']
    
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        # Verificar si el usuario existe y está en el sistema
        if user and not user.is_verified and request.endpoint in restricted_routes:
            flash('Debes verificar tu cuenta para acceder a esta página.')
            return redirect(url_for('verify', email=user.email))



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()

        if user and bcrypt.check_password_hash(user.password, password):
            if not user.is_verified:
                # Enviar correo de verificación si el usuario no está verificado
                send_verification_email(user)
                flash('Tu cuenta no está verificada. Te hemos enviado un correo con el código de verificación.')
                return redirect(url_for('verify', email=user.email))  # Redirige a la página de verificación
                
            # Si el usuario está verificado, inicia sesión normalmente
            session['user_id'] = user.id
            flash('Inicio de sesión exitoso.')
            return redirect(url_for('dashboard'))
        else:
            flash('Correo o contraseña incorrectos.')

    return render_template('login.html')





@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('Has cerrado sesión.')
    return redirect(url_for('login'))

# Rutas principales del dashboard y simulaciones
@app.route('/dashboard')
def dashboard():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        return render_template('dashboard.html', user=user)
    return redirect(url_for('login'))

@app.route('/simulations')
def simulations():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('simulations.html')

@app.route('/game')
def game():
    return render_template('game.html')

@app.route('/chaos_game')
def chaos_game():
    return render_template('chaos_game.html')

@app.route('/solar_system')
def solar_system():
    return render_template('solar_system.html')

@app.route('/solar_system_3d')
def solar_system_3d():
    return render_template('solar_system_3d.html')
# Ruta para obtener el puuid a partir del nombre de invocador y tagline
def get_puuid(summoner_name, tagline):
    region = 'europe'
    url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{summoner_name}/{tagline}"
    headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json().get("puuid")
    else:
        print(f"Error al obtener el PUUID ({response.status_code}):", response.json())
        return None

import requests
def calcular_puntos(puntos_apostados, resultado):
    # Por ejemplo, multiplica los puntos apostados por 2 si gana; de lo contrario, pierdes puntos apostados
    if resultado == 'ganar':
        return puntos_apostados * 2
    else:
        return -puntos_apostados  # Si pierde, resta los puntos apostados

def evaluar_ganador(summoner_name, game_info):
    # Encuentra al participante según su nombre
    participante = next((p for p in game_info['participants'] if p['summonerName'] == summoner_name), None)
    
    if participante:
        # Identificar el equipo ganador
        team_id = participante['teamId']
        equipo_ganador = game_info['teams'][0]['win'] if game_info['teams'][0]['teamId'] == team_id else game_info['teams'][1]['win']
        
        if equipo_ganador == 'Win':
            return 'ganar'
        else:
            return 'perder'
    else:
        print("No se encontró al participante en la partida.")
        return None

def obtener_estado_partida(partida_id):
    url = f"https://europe.api.riotgames.com/lol/match/v5/matches/{partida_id}"
    headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    elif response.status_code == 404:
        print("La partida aún no ha finalizado o no se encontró.")
        return None
    else:
        print("Error al obtener estado de la partida:", response.json())
        return None

# Ruta para verificar si el jugador está en una partida activa usando el puuid
def check_active_game(puuid):
    url = f"https://euw1.api.riotgames.com/lol/spectator/v5/active-games/by-summoner/{puuid}"
    headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        return response.json()  # Retorna los detalles de la partida activa
    elif response.status_code == 404:
        print("No se encontró partida activa para este invocador.")
        return None
    else:
        print("Error al verificar partida activa:", response.json())
        return None
@app.route('/check_game_status')
def check_game_status():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        
        if user and user.summoner_name:
            # Si el usuario ya está en partida, devuelve `already_in_game`
            if user.partida_en_curso:
                return jsonify({
                    "is_in_champion_select": False,
                    "is_game_in_progress": True,
                    "already_in_game": True
                })
            
            puuid = get_puuid(user.summoner_name, user.tagline)
            if puuid:
                game_info = check_active_game(puuid)
                if game_info:
                    game_id = game_info.get("gameId")
                    if game_id:
                        # Marca `partida_en_curso` en `User` para que no vuelva a llamar
                        user.partida_en_curso = True
                        user.current_game_id = game_id  # Guardar el ID de la partida actual en el usuario
                        db.session.commit()
                        
                        return jsonify({
                            "is_in_champion_select": True,
                            "is_game_in_progress": True,
                            "game_id": game_id,
                            "already_in_game": False  # Solo redirige si es una partida nueva
                        })
    
    return jsonify({
        "is_in_champion_select": False,
        "is_game_in_progress": False,
        "already_in_game": False
    })

@app.route('/realizar_apuesta', methods=['POST'])
def realizar_apuesta():
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            apuesta_tipo = request.form.get('apuesta_tipo')
            puntos_apostados = int(request.form.get('puntos_apostados'))
            game_id = request.form.get('game_id')  # Obtén el `game_id` desde el formulario

            print(f"Game ID en realizar_apuesta: {game_id}")  # Verificación de depuración

            if not game_id:
                flash("Error: no se recibió el ID de la partida.")
                return redirect(url_for('apuestas'))

            # Verifica si el usuario tiene suficientes puntos
            if user.puntos and puntos_apostados <= user.puntos.puntos:
                # Deduce los puntos apostados del usuario
                user.puntos.puntos -= puntos_apostados

                # Crea o actualiza la apuesta con `game_id`
                apuesta = Apuesta.query.filter_by(id_usuario=user.id, id_partida=game_id).first()
                if apuesta:
                    apuesta.apuesta_tipo = apuesta_tipo
                    apuesta.puntos_apostados = puntos_apostados
                else:
                    apuesta = Apuesta(
                        id_usuario=user.id,
                        id_partida=game_id,
                        apuesta_tipo=apuesta_tipo,
                        puntos_apostados=puntos_apostados
                    )
                    db.session.add(apuesta)

                db.session.commit()
                flash("Apuesta realizada con éxito.")
                return redirect(url_for('ranking_apuestas'))
            else:
                flash("No tienes suficientes puntos para esta apuesta.")
                return redirect(url_for('apuestas'))

    flash("Debes iniciar sesión para realizar una apuesta.")
    return redirect(url_for('login'))


@app.route('/ranking_apuestas')
def ranking_apuestas():
    # Asumiendo que estás obteniendo el usuario actual de la sesión
    user = User.query.get(session.get('user_id'))
    
    apuestas_no_procesadas = Apuesta.query.filter_by(procesada=False).all()
    
    for apuesta in apuestas_no_procesadas:
        verificar_resultado_apuesta(apuesta)

    usuarios_con_puntos = (
        db.session.query(User, PuntosPersona.puntos)
        .join(PuntosPersona, User.id == PuntosPersona.id_usuario)
        .order_by(PuntosPersona.puntos.desc())
        .all()
    )
    return render_template('ranking_apuestas.html', usuarios_con_puntos=usuarios_con_puntos, user=user)


@app.route('/apuestas')
def apuestas():
    # Comprueba si hay un usuario en sesión
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
        if user:
            # Obtiene los puntos disponibles o asigna 0 si no existen
            puntos_disponibles = user.puntos.puntos if user.puntos else 0

            # Obtiene el estado del juego y `game_id` si está en partida
            game_status = check_game_status().json
            game_id = game_status.get("game_id") if game_status["is_game_in_progress"] else None

            return render_template('apuestas.html', user=user, puntos_disponibles=puntos_disponibles, game_id=game_id)
    
    # Redirige al login si no hay usuario en sesión
    return redirect(url_for('login'))


@app.route('/stats', methods=['GET', 'POST'])
def stats():
    if 'user_id' not in session:
        print("Usuario no autenticado, redirigiendo a login.")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    print(f"Usuario encontrado en sesión: {user.username}")

    if request.method == 'POST':
        summoner_name = request.form.get('summoner_name')
        match_count = int(request.form.get('match_count', 10))
        tagline = user.tagline if user and user.tagline else request.form.get('tagline', 'EUW')
        
        print(f"Nombre de invocador: {summoner_name}, Tagline: {tagline}, Número de partidas: {match_count}")

        if not summoner_name or not tagline:
            flash('Por favor, proporciona un nombre de invocador y un tagline.', 'error')
            print("Faltan el nombre de invocador o el tagline.")
            return redirect(url_for('stats'))

        region = 'europe'
        headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}
        encoded_summoner_name = quote(summoner_name)

        # Llamada a la API para obtener el puuid del invocador
        url_summoner = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_summoner_name}/{tagline}"
        print(f"URL para obtener PUUID: {url_summoner}")
        response_summoner = requests.get(url_summoner, headers=headers)
        
        if response_summoner.status_code == 200:
            summoner_data = response_summoner.json()
            puuid = summoner_data['puuid']
            print(f"PUUID obtenido: {puuid}")

            # Obtener los últimos N IDs de partidas del invocador
            url_matches = f"https://{region}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?start=0&count={match_count}"
            print(f"URL para obtener IDs de partidas: {url_matches}")
            response_matches = requests.get(url_matches, headers=headers)

            if response_matches.status_code == 200:
                match_ids = response_matches.json()
                match_details = []
                print(f"IDs de partidas obtenidos: {match_ids}")

                # Obtener detalles para cada partida
                for match_id in match_ids:
                    url_match_details = f"https://{region}.api.riotgames.com/lol/match/v5/matches/{match_id}"
                    print(f"URL para obtener detalles de la partida {match_id}: {url_match_details}")
                    response_match_details = requests.get(url_match_details, headers=headers)
                    
                    if response_match_details.status_code == 200:
                        match_data = response_match_details.json()
                        participant_data = next((p for p in match_data['info']['participants'] if p['puuid'] == puuid), None)
                        
                        if participant_data:
                            print(f"Datos del participante en la partida {match_id}: {participant_data}")
                            match_details.append({
                                'result': 'Victoria' if participant_data['win'] else 'Derrota',
                                'champion': participant_data['championName'],
                                'kda': f"{participant_data['kills']}/{participant_data['deaths']}/{participant_data['assists']}",
                                'damage': participant_data['totalDamageDealtToChampions'],
                                'date': datetime.fromtimestamp(match_data['info']['gameStartTimestamp'] / 1000).strftime('%d/%m/%Y')
                            })
                    else:
                        print(f"No se pudieron obtener los detalles de la partida {match_id}. Código de estado: {response_match_details.status_code}")

                return render_template('stats.html', summoner_data=summoner_data, match_details=match_details)
            else:
                flash('No se pudieron obtener las partidas recientes.', 'error')
                print("Error al obtener IDs de partidas:", response_matches.status_code, response_matches.json())
                return redirect(url_for('stats'))
        else:
            flash('No se pudo encontrar el invocador. Verifica el nombre y el tagline.', 'error')
            print("Error al obtener PUUID:", response_summoner.status_code, response_summoner.json())
            return redirect(url_for('stats'))

    return render_template('stats.html', user=user)

from flask import g

@app.before_request
def load_user():
    user_id = session.get('user_id')
    if user_id:
        g.user = User.query.get(user_id)
    else:
        g.user = None
@app.context_processor
def inject_user():
    user_id = session.get('user_id')
    user = User.query.get(user_id) if user_id else None
    return {'user': user}
@app.route('/ranking', methods=['GET', 'POST'])
def ranking():
    if 'user_id' not in session:
        print("No user in session")
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user:
        print("User not found in the database")
        return redirect(url_for('login'))

    print(f"User ID: {user.id}, Username: {user.username}")
    
    region = 'europe'
    headers = {"X-Riot-Token": app.config['RIOT_API_KEY']}

    # Pedir nombre de invocador y tagline si el usuario no los tiene
    if not user.summoner_name or not user.tagline:
        if request.method == 'POST':
            summoner_name = request.form.get('summoner_name')
            tagline = request.form.get('tagline')
            print(f"Received summoner_name: {summoner_name}, tagline: {tagline}")
            
            # Verificar que ambos valores estén presentes
            if summoner_name and tagline:
                # Llamada a la API de Riot para confirmar el nombre y tagline
                encoded_summoner_name = quote(summoner_name)
                url_summoner = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_summoner_name}/{tagline}"
                response_summoner = requests.get(url_summoner, headers=headers)
                print(f"API Request URL: {url_summoner}, Status Code: {response_summoner.status_code}")

                if response_summoner.status_code == 200:
                    user.summoner_name = summoner_name
                    user.tagline = tagline
                    db.session.commit()
                    db.session.refresh(user)
                    print("Summoner name and tagline updated in the database")
                    flash('Nombre de invocador y tagline actualizados.')
                    return redirect(url_for('ranking'))
                else:
                    print(f"Failed to find summoner in Riot API, response: {response_summoner.json()}")
                    flash('No se pudo encontrar el invocador en Riot Games.')

        return render_template('ranking.html', user=user, user_ranks=[])

    # Obtener el ranking si ya tiene `summoner_name` y `tagline`
    users = User.query.filter(User.summoner_name.isnot(None)).all()
    user_ranks = []

    for u in users:
        encoded_summoner_name = quote(u.summoner_name)
        url_summoner = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{encoded_summoner_name}/{u.tagline}"
        response_summoner = requests.get(url_summoner, headers=headers)
        print(f"Checking summoner for user {u.username} with API URL: {url_summoner}")

        if response_summoner.status_code == 200:
            summoner_data = response_summoner.json()
            puuid = summoner_data.get('puuid')
            print(f"Found PUUID for {u.summoner_name}: {puuid}")

            if puuid:
                url_summoner_id = f"https://euw1.api.riotgames.com/lol/summoner/v4/summoners/by-puuid/{puuid}"
                response_summoner_id = requests.get(url_summoner_id, headers=headers)
                print(f"Getting summoner ID for PUUID {puuid} with URL: {url_summoner_id}")

                if response_summoner_id.status_code == 200:
                    summoner_info = response_summoner_id.json()
                    summoner_id = summoner_info['id']
                    summoner_level = summoner_info['summonerLevel']
                    print(f"Summoner ID: {summoner_id}, Level: {summoner_level}")

                    url_rank = f"https://euw1.api.riotgames.com/lol/league/v4/entries/by-summoner/{summoner_id}"
                    response_rank = requests.get(url_rank, headers=headers)
                    print(f"Getting rank info with URL: {url_rank}")

                    if response_rank.status_code == 200 and response_rank.json():
                        rank_data = response_rank.json()[0]
                        wins = rank_data['wins']
                        losses = rank_data['losses']
                        winrate = (wins / (wins + losses)) * 100 if (wins + losses) > 0 else 0  # Evitar división por cero
                        print(f"Rank data for {u.username}: {rank_data}")

                        user_ranks.append({
                            'username': u.username,
                            'summoner_name': u.summoner_name,
                            'tagline': u.tagline,
                            'tier': rank_data['tier'],
                            'rank': rank_data['rank'],
                            'league_points': rank_data['leaguePoints'],
                            'wins': wins,
                            'losses': losses,
                            'winrate': f"{int(winrate)}%",  
                            'summoner_level': summoner_level
                        })
                    else:
                        print(f"User {u.username} is unranked or rank data not found")
                        user_ranks.append({
                            'username': u.username,
                            'summoner_name': u.summoner_name,
                            'tagline': u.tagline,
                            'tier': 'Unranked',
                            'rank': '',
                            'league_points': '-',
                            'wins': '-',
                            'losses': '-',
                            'winrate': '-',
                            'summoner_level': summoner_level
                        })
                else:
                    print(f"Error getting summoner ID for {u.summoner_name}")
            else:
                print(f"No PUUID found for {u.summoner_name}")
        else:
            print(f"Error fetching data for {u.summoner_name} with status code {response_summoner.status_code}")

    # Ordenar el ranking por `tier` y `rank`
    tier_priority = {
        'CHALLENGER': 1, 'GRANDMASTER': 2, 'MASTER': 3,
        'DIAMOND': 4, 'PLATINUM': 5, 'GOLD': 6, 'SILVER': 7, 'BRONZE': 8, 'IRON': 9, 'Unranked': 10
    }
    rank_priority = {'I': 1, 'II': 2, 'III': 3, 'IV': 4}

    user_ranks.sort(key=lambda x: (
        tier_priority.get(x['tier'], 10),
        rank_priority.get(x['rank'], 5) if x['rank'] else 5
    ))

    print("User ranks calculated:", user_ranks)
    return render_template('ranking.html', user=user, user_ranks=user_ranks)



# Ruta del chat
@app.route('/chat')
def chat():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('chat.html')

@app.route('/get_messages', methods=['GET'])
def get_messages():
    messages = ChatMessage.query.order_by(ChatMessage.timestamp).all()
    messages_data = [{
        'username': msg.user.username,
        'message': msg.message,
        'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
    } for msg in messages]
    return jsonify(messages_data)

@app.route('/send_message', methods=['POST'])
def send_message():
    if 'user_id' not in session:
        return jsonify({'success': False}), 401

    message_text = request.form.get('message')
    user_id = session['user_id']
    chat_message = ChatMessage(user_id=user_id, message=message_text)
    db.session.add(chat_message)
    db.session.commit()

    return jsonify({'success': True})

# Crear tablas si no existen
@app.before_first_request
def initialize_database():
    #db.drop_all()
    db.create_all()
    
    print('Revisor de tablas ejecutado')

# Ejecuta la aplicación
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=True)
