from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
import face_recognition
import numpy as np
import os
from werkzeug.utils import secure_filename
from flask_bcrypt import Bcrypt

app = Flask(__name__)
app.secret_key = 'clave_secreta_flask'
bcrypt = Bcrypt(app)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USER = 'admin'
ADMIN_PASSWORD = bcrypt.generate_password_hash('admin123').decode('utf-8')

# Conectar a la base de datos
def connect_db():
    conn = sqlite3.connect('users.db')
    conn.row_factory = sqlite3.Row
    return conn

# Verificar archivos permitidos
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# --- Login ---
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username == ADMIN_USER and bcrypt.check_password_hash(ADMIN_PASSWORD, password):
            session['logged_in'] = True
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

# --- Dashboard ---
@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = connect_db()
    c = conn.cursor()
    c.execute("SELECT name FROM users")
    users = c.fetchall()
    conn.close()
    return render_template('dashboard.html', users=users)

# --- Agregar Usuario ---
@app.route('/add_user', methods=['GET', 'POST'])
def add_user():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        name = request.form['name']
        file = request.files['file']
        if not name or not file or not allowed_file(file.filename):
            flash('Debe ingresar un nombre y una imagen válida.', 'danger')
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
            try:
                c.execute("INSERT INTO users (name, encoding) VALUES (?, ?)", (name, encoding.tobytes()))
                conn.commit()
                flash(f'Usuario "{name}" agregado correctamente.', 'success')
            except sqlite3.IntegrityError:
                flash(f'El usuario "{name}" ya existe.', 'danger')
            conn.close()
        os.remove(filepath)
        return redirect(url_for('dashboard'))
    return render_template('add_user.html')

# --- Eliminar Usuario ---
@app.route('/delete_user/<name>')
def delete_user(name):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    conn = connect_db()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    flash(f'Usuario "{name}" eliminado correctamente.', 'success')
    return redirect(url_for('dashboard'))

# --- Logout ---
@app.route('/logout')
def logout():
    session['logged_in'] = False
    return redirect(url_for('login'))

# Inicializar base de datos
if __name__ == '__main__':
    if not os.path.exists('users.db'):
        conn = connect_db()
        c = conn.cursor()
        c.execute("CREATE TABLE users (name TEXT UNIQUE, encoding BLOB)")
        conn.commit()
        conn.close()
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True, host='0.0.0.0', port=5000)
