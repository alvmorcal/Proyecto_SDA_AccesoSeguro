from picamera2 import Picamera2
import face_recognition
import sqlite3
import numpy as np
import cv2
import requests
from time import sleep
import libcamera
import os

# CONFIGURACION TELEGRAM
BOT_TOKEN = "7623844834:AAEh23cpLEIXKFJPcTwh-BCmsqZ6Cze6jew"  # Reemplaza con tu TOKEN
CHAT_ID = "1882908107"  # Reemplaza con tu Chat ID

# Funcion para enviar notificaciones por Telegram
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data)
        print("Notificacion enviada por Telegram.")
    except Exception as e:
        print(f"Error al enviar notificacion: {e}")

# Funcion para enviar una imagen a Telegram
def send_telegram_photo(photo_path, caption):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
        with open(photo_path, "rb") as photo:
            data = {"chat_id": CHAT_ID, "caption": caption}
            files = {"photo": photo}
            requests.post(url, data=data, files=files)
            print("Imagen enviada por Telegram.")
    except Exception as e:
        print(f"Error al enviar imagen: {e}")

# Funcion para cargar los usuarios desde la base de datos
def load_users_from_database():
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT name, encoding FROM users")
    rows = c.fetchall()
    conn.close()

    users = []
    for row in rows:
        name = row[0]
        encoding = np.frombuffer(row[1], dtype=np.float64)
        users.append((name, encoding))
    return users

# Configuracion de la camara
def initialize_camera():
    camera = Picamera2()
    camera_config = camera.create_still_configuration(
        main={"size": (640, 480)},  # Resolucion reducida
        lores={"size": (320, 240)},
        display="lores"
    )
    camera_config['transform'] = libcamera.Transform(vflip=True)
    camera.configure(camera_config)
    return camera

# Reconocimiento facial con apertura de puerta o alarma
def recognize_faces(camera, users):
    print("Iniciando reconocimiento facial. Presiona 'O' para interactuar o 'Q' para salir.")
    sleep(2)

    while True:
        # Capturar el fotograma actual
        frame = camera.capture_array()
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convertir a formato RGB

        # Detectar ubicaciones y encodings de caras
        face_locations = face_recognition.face_locations(rgb_frame)
        face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

        known_user_detected = False
        user_name = None
        photo_path = "unknown_person.jpg"  # Imagen temporal para desconocidos

        for face_encoding, face_location in zip(face_encodings, face_locations):
            # Comparar con los usuarios en la base de datos
            matches = face_recognition.compare_faces([user[1] for user in users], face_encoding, tolerance=0.6)
            name = "Desconocido"

            if True in matches:
                match_index = matches.index(True)
                name = users[match_index][0]
                known_user_detected = True
                user_name = name

            # Dibujar rectangulos y nombres
            top, right, bottom, left = face_location
            color = (0, 255, 0) if name != "Desconocido" else (0, 0, 255)
            cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
            cv2.putText(frame, name, (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Mostrar el cuadro con OpenCV
        cv2.imshow("Reconocimiento Facial", frame)

        # Esperar a que se presione una tecla
        key = cv2.waitKey(1) & 0xFF

        if key == ord('o') or key == ord('O'):  # Tecla 'O'
            if known_user_detected:
                print(f"Puerta abierta: Acceso permitido para {user_name}.")
                message = f"✅ Acceso permitido: {user_name} ha abierto la puerta."
                send_telegram_message(message)
            else:
                print("ALERTA: Alarma activada. Persona desconocida detectada.")
                message = f"🚨 ALERTA: Intento de acceso por persona desconocida."
                # Guardar la imagen y enviarla por Telegram
                cv2.imwrite(photo_path, frame)
                send_telegram_photo(photo_path, message)
                os.remove(photo_path)  # Eliminar la imagen temporal
            break

        if key == ord('q') or key == ord('Q'):  # Tecla 'Q' para salir
            print("Reconocimiento detenido por el usuario.")
            break

    cv2.destroyAllWindows()

# Funcion principal
if __name__ == "__main__":
    users = load_users_from_database()
    if not users:
        print("No hay usuarios registrados en la base de datos.")
        exit()

    camera = initialize_camera()
    camera.start()

    try:
        recognize_faces(camera, users)
    except Exception as e:
        print(f"Error durante el reconocimiento: {e}")
    finally:
        camera.stop()
        camera.close()
        print("Camara apagada.")
