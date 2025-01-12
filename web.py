from flask import Flask, render_template, request, redirect, url_for, session, flash
# Flask: Framework para crear aplicaciones web fácilmente.
# render_template: Renderiza plantillas HTML.
# request: Maneja solicitudes HTTP.
# redirect, url_for: Facilitan redirecciones.
# session: Permite manejar sesiones de usuario.
# flash: Muestra mensajes temporales (notificaciones).

import sqlite3
# sqlite3: Base de datos ligera integrada en Python, utilizada aquí para almacenar usuarios.

import face_recognition
# face_recognition: Biblioteca para el reconocimiento facial. Permite analizar imágenes y extraer características únicas de rostros.

import numpy as np
# numpy: Biblioteca matemática para manejar matrices y operaciones numéricas.

import os
# os: Proporciona funcionalidades del sistema operativo como manejo de archivos y directorios.

from werkzeug.utils import secure_filename
# secure_filename: Asegura que los nombres de archivos subidos sean seguros.

from flask_bcrypt import Bcrypt
# flask_bcrypt: Biblioteca para el manejo seguro de contraseñas mediante hashing.

import requests
# requests: Realiza solicitudes HTTP, aquí usado para interactuar con la API de Telegram.

import smtplib
from email.mime.text import MIMEText
# smtplib: Protocolo para enviar correos electrónicos.
# MIMEText: Permite crear el contenido del correo electrónico en formato texto.

from dotenv import load_dotenv
# dotenv: Carga variables de entorno desde un archivo .env.

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Configuración sensible como variables de entorno
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')  # Clave secreta para proteger sesiones y cookies.
SMTP_SERVER = os.getenv('SMTP_SERVER')  # Servidor SMTP para enviar correos.
SMTP_PORT = int(os.getenv('SMTP_PORT'))  # Puerto del servidor SMTP.
SMTP_USER = os.getenv('SMTP_USER')  # Usuario para la autenticación del servidor SMTP.
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')  # Contraseña del servidor SMTP.
BOT_TOKEN = os.getenv('BOT_TOKEN')  # Token del bot de Telegram.
CHAT_ID = os.getenv('CHAT_ID')  # ID del chat de Telegram para enviar notificaciones.

bcrypt = Bcrypt(app)  # Inicializamos Bcrypt para manejar contraseñas de forma segura.
UPLOAD_FOLDER = 'uploads'  # Carpeta donde se guardan los archivos subidos.
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}  # Extensiones permitidas para las imágenes.
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Credenciales de administrador
ADMIN_USER = 'admin'  # Nombre de usuario del administrador.
ADMIN_PASSWORD = bcrypt.generate_password_hash('admin').decode('utf-8')  # Contraseña encriptada.

# Función para enviar mensajes a Telegram
def send_telegram_message(message):
    """Envía un mensaje al chat de Telegram configurado."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

# Función para enviar correos electrónicos
def send_email(to_email, subject, body):
    """Envía un correo electrónico utilizando las configuraciones SMTP."""
    try:
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = SMTP_USER
        msg['To'] = to_email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
    except Exception as e:
        print(f"Error al enviar el correo: {e}")

# Conexión a la base de datos SQLite
def connect_db():
    """Establece una conexión con la base de datos SQLite."""
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row  # Devuelve filas como diccionarios.
    return conn

# Verifica si un archivo tiene una extensión permitida
def allowed_file(filename):
    """Comprueba si el archivo tiene una extensión válida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def login():
    """Maneja la autenticación del administrador."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USER and bcrypt.check_password_hash(ADMIN_PASSWORD, password):
            session['logged_in'] = True
            flash('Inicio de sesión exitoso.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    """Muestra la lista de usuarios registrados."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT name, email FROM users")  # Consulta todos los usuarios registrados.
    users = c.fetchall()
    conn.close()
    return render_template('dashboard.html', users=users)

@app.route('/delete_user_confirm', methods=['POST'])
def delete_user_confirm():
    """Elimina un usuario específico de la base de datos."""
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    username = request.form['username']
    admin_password = request.form['admin_password']
    if bcrypt.check_password_hash(ADMIN_PASSWORD, admin_password):
        conn = connect_db()
        c = conn.cursor()
        # Obtener el correo del usuario antes de eliminarlo
        c.execute("SELECT email FROM users WHERE name = ?", (username,))
        user = c.fetchone()
        if not user:
            flash("El usuario no existe.", "danger")
            conn.close()
            return redirect(url_for('dashboard'))
        
        email = user['email']  # Extraer el correo electrónico
        c.execute("DELETE FROM users WHERE name = ?", (username,))  # Eliminar el usuario
        conn.commit()
        conn.close()

        # Enviar notificaciones
        send_telegram_message(f"❌ Usuario eliminado: {username}")
        send_email(email, "Confirmación de Baja", f"Hola {username}, ha sido dado de baja de la base de datos. Ya no podrá acceder al contenido de la caja de seguridad.")
        flash(f"Usuario '{username}' eliminado correctamente.", "success")
    else:
        flash("Clave de administrador incorrecta.", "danger")
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    """Cierra la sesión del administrador."""
    session['logged_in'] = False
    flash("Sesión cerrada correctamente.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    # Configuración inicial para base de datos y directorios
    if not os.path.exists('users.db'):
        conn = connect_db()
        c = conn.cursor()
        c.execute("CREATE TABLE users (name TEXT UNIQUE, email TEXT, encoding BLOB)")  # Crear tabla para usuarios.
        conn.commit()
        conn.close()
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)  # Crear directorio para subir archivos si no existe.
    app.run(debug=True, host='0.0.0.0', port=5000)  # Iniciar la aplicación en modo depuración.
