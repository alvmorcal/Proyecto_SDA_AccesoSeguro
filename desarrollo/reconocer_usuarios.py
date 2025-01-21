from picamera2 import Picamera2
import face_recognition
import sqlite3
import numpy as np
import cv2
import requests
from time import sleep
import libcamera

# Configuracion global
BOT_TOKEN = "XXX"
CHAT_ID = "YYY"
RESOLUTION = (640, 480)
TOLERANCE = 0.6
REFRESH_INTERVAL = 30  # Intervalo de tiempo para refrescar usuarios (en segundos)

# --- FUNCIONES DE TELEGRAM ---
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        """
        if response.status_code == 200:
            print("Notificacion enviada por Telegram.")
        else:
            print("Error al enviar la notificacion.")
        """
    except Exception as e:
        print(f"Error en send_telegram_message: {e}")

def send_telegram_photo(frame, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        _, buffer = cv2.imencode('.jpg', frame)
        response = requests.post(url, files={"photo": buffer.tobytes()}, data={"chat_id": CHAT_ID, "caption": caption})
        """
        if response.status_code == 200:
            print("Imagen enviada por Telegram.")
        else:
            print("Error al enviar la imagen.")
        """
    except Exception as e:
        print(f"Error en send_telegram_photo: {e}")

# --- BASE DE DATOS ---
def load_users_from_database():
    users = []
    try:
        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, encoding FROM users")
            rows = cursor.fetchall()
            users = [(row[0], np.frombuffer(row[1], dtype=np.float64)) for row in rows]
    except sqlite3.Error as e:
        print(f"Error en la base de datos: {e}")
    return users

# --- CAMARA ---
def initialize_camera():
    camera = Picamera2()
    config = camera.create_still_configuration(main={"size": RESOLUTION}, lores={"size": (320, 240)}, display="lores")
    #config['transform'] = libcamera.Transform(vflip=True)
    camera.configure(config)
    return camera

# --- PROCESAMIENTO DE IMAGENES ---
def process_frame(frame, users):
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    results = []
    for face_encoding, face_location in zip(face_encodings, face_locations):
        matches = face_recognition.compare_faces([user[1] for user in users], face_encoding, tolerance=TOLERANCE)
        name = "Desconocido"
        if True in matches:
            name = users[matches.index(True)][0]
        results.append((name, face_location))
    return results

def draw_results(frame, results):
    for name, (top, right, bottom, left) in results:
        color = (0, 255, 0) if name != "Desconocido" else (0, 0, 255)
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    return frame

# --- RECONOCIMIENTO PRINCIPAL ---
def recognize_faces(camera):
    print("Iniciando reconocimiento facial. Presiona 'O' para interactuar o 'Q' para salir.")
    sleep(2)
    users = load_users_from_database()
    last_refresh = 0

    while True:
        # Refrescar usuarios cada REFRESH_INTERVAL segundos
        if (sleep(0) or (time := int(cv2.getTickCount() / cv2.getTickFrequency()))) - last_refresh >= REFRESH_INTERVAL:
            users = load_users_from_database()
            last_refresh = time
            print("Usuarios actualizados desde la base de datos.")

        frame = camera.capture_array()
        results = process_frame(frame, users)
        frame = draw_results(frame, results)

        known_user = next((name for name, _ in results if name != "Desconocido"), None)
        cv2.imshow("Reconocimiento Facial", frame)

        key = cv2.waitKey(1) & 0xFF
        if key == ord('o'):
            if known_user:
                # print(f"Acceso permitido para {known_user}.")
                send_telegram_message(f"✅ Acceso permitido: {known_user} ha abierto la caja fuerte.")
            else:
                # print("Alarma activada: Persona desconocida detectada.")
                send_telegram_message("🚨 ALERTA: Un desconocido intentó acceder a la caja fuerte.")
                send_telegram_photo(frame, "Persona no autorizada")
            break
        elif key == ord('q'):
            # print("Reconocimiento detenido por el usuario.")
            break

    cv2.destroyAllWindows()

# --- EJECUCION PRINCIPAL ---
if __name__ == "__main__":
    camera = initialize_camera()
    camera.start()
    try:
        recognize_faces(camera)
    except Exception as e:
        print(f"Error durante el reconocimiento: {e}")
    finally:
        camera.stop()
        camera.close()
