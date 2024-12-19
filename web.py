from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import face_recognition
import numpy as np
import os
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt
import requests
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)
app.secret_key = 'clave_secreta_flask'
bcrypt = Bcrypt(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USER = 'admin'
ADMIN_PASSWORD = bcrypt.generate_password_hash('admin123').decode('utf-8')

# Configuración SMTP
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = 'tu_correo@gmail.com'
SMTP_PASSWORD = 'tu_contraseña'

# Configuración Telegram
BOT_TOKEN = "7623844834:AAEh23cpLEIXKFJPcTwh-BCmsqZ6Cze6jew"
CHAT_ID = "1882908107"

# Enviar mensaje a Telegram
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

# Conectar a la base de datos
def connect_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Verificar archivos permitidos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET', 'POST'])
def login():
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
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT name, email FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('dashboard.html', users=users)

@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        file = request.files['file']

        if not name or not email or not file or not allowed_file(file.filename):
            flash('Debe ingresar un nombre, correo y una imagen válida.', 'danger')
            return redirect(url_for('add_user'))

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        image = face_recognition.load_image_file(filepath)
        face_encodings = face_recognition.face_encodings(image)

        if not face_encodings:
            flash("No se detectó ninguna cara en la imagen.", "danger")
        else:
            encoding = face_encodings[0]
            conn = connect_db()
            c = conn.cursor()

            # Verificar si el correo ya está registrado
            c.execute("SELECT name FROM users WHERE email = ?", (email,))
            if c.fetchone():
                flash("Ya existe un usuario registrado con este correo.", "danger")
                conn.close()
                os.remove(filepath)
                return redirect(url_for('add_user'))

            try:
                c.execute("INSERT INTO users (name, email, encoding) VALUES (?, ?, ?)", (name, email, encoding.tobytes()))
                conn.commit()
                flash(f'Usuario "{name}" agregado correctamente.', 'success')
            except sqlite3.Error as e:
                flash(f'Error al registrar el usuario: {e}', 'danger')
            finally:
                conn.close()

        os.remove(filepath)
        return redirect(url_for('add_user'))

    return render_template('add_user.html')

@app.route('/delete_user_confirm', methods=['POST'])
def delete_user_confirm():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    username = request.form['username']
    admin_password = request.form['admin_password']

    if bcrypt.check_password_hash(ADMIN_PASSWORD, admin_password):
        try:
            conn = connect_db()
            c = conn.cursor()
            c.execute("DELETE FROM users WHERE name = ?", (username,))
            conn.commit()
            conn.close()
            flash(f'Usuario "{username}" eliminado correctamente.', 'success')
        except sqlite3.Error as e:
            flash(f'Error al eliminar al usuario: {e}', 'danger')
    else:
        flash("Clave de administrador incorrecta.", 'danger')

    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))

if __name__ == '__main__':
    if not os.path.exists('users.db'):
        conn = connect_db()
        c = conn.cursor()
        c.execute("CREATE TABLE users (name TEXT UNIQUE, email TEXT, encoding BLOB)")
        conn.commit()
        conn.close()
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, host='0.0.0.0', port=5000)




