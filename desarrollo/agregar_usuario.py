from picamera2 import Picamera2
import face_recognition
import sqlite3
import numpy as np
import cv2
from time import sleep
import libcamera
import requests

# CONFIGURACION TELEGRAM
BOT_TOKEN = "XXX"  # Reemplaza con tu TOKEN
CHAT_ID = "YYY"  # Reemplaza con tu Chat ID

# Funcion para enviar notificaciones por Telegram
def send_telegram_message(message):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        requests.post(url, data=data)
        print("Notificacion enviada por Telegram.")
    except Exception as e:
        print(f"Error al enviar notificacion: {e}")



# Verificar si el nombre existe en la base de datos
def is_name_taken(name):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (name TEXT UNIQUE, encoding BLOB)")
    c.execute("SELECT name FROM users WHERE name = ?", (name,))
    exists = c.fetchone() is not None
    conn.close()
    return exists

# Configuración de la cámara
def initialize_camera():
    camera = Picamera2()
    camera_config = camera.create_still_configuration(
        main={"size": (640, 480)},  # Resolución reducida para rendimiento
        lores={"size": (320, 240)},
        display="lores"
    )
    camera_config['transform'] = libcamera.Transform(vflip=True)
    camera.configure(camera_config)
    return camera

# Captura una sola imagen si hay una cara detectada
def capture_face_image(camera):
    print("Por favor, mira de frente a la cámara. La captura se hará cuando se detecte una cara.")
    while True:
        # Capturar el fotograma actual
        frame = camera.capture_array()
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)  # Convertir a formato BGR

        # Detectar caras en el fotograma
        face_locations = face_recognition.face_locations(frame_bgr)

        # Dibujar un recuadro azul si hay caras detectadas
        if face_locations:
            for (top, right, bottom, left) in face_locations:
                cv2.rectangle(frame_bgr, (left, top), (right, bottom), (255, 0, 0), 2)  # Recuadro azul
            cv2.putText(frame_bgr, "Cara detectada - Presiona Enter", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Mostrar la vista previa
            cv2.imshow("Vista Previa - Captura de Imagen", frame_bgr)

            # Permitir captura solo si hay una cara
            if cv2.waitKey(1) & 0xFF == 13:  # Tecla Enter
                print("Imagen capturada correctamente.")
                return frame_bgr  # Devuelve el fotograma capturado
        else:
            # Mostrar mensaje si no se detecta ninguna cara
            cv2.putText(frame_bgr, "No se detecta cara. Intenta nuevamente.", (20, 50),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            cv2.imshow("Vista Previa - Captura de Imagen", frame_bgr)

        # Salir si se presiona 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            print("Captura cancelada por el usuario.")
            return None

# Procesar la imagen y guardar el encoding en la base de datos
def add_user_to_database(name, frame):
    # Procesar la imagen en memoria
    face_encodings = face_recognition.face_encodings(frame)

    if not face_encodings:
        print("No se detectó ninguna cara en la imagen capturada. Registro fallido.")
        return False

    encoding = face_encodings[0]  # Obtener el primer encoding

    # Guardar el encoding en la base de datos
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (name TEXT UNIQUE, encoding BLOB)")

    try:
        c.execute("INSERT INTO users (name, encoding) VALUES (?, ?)", (name, encoding.tobytes()))
        conn.commit()
        print(f"Usuario '{name}' agregado correctamente a la base de datos.")

        # Enviar mensaje a Telegram
        send_telegram_message(f"✅ Nuevo usuario agregado: {name}")
    except sqlite3.IntegrityError:
        print(f"Error: El usuario '{name}' ya existe.")
        send_telegram_message(f"⚠️ Intento de agregar usuario duplicado: {name}")
    finally:
        conn.close()

    return True


# Función principal
if __name__ == "__main__":
    while True:
        name = input("Ingresa el nombre del usuario: ")

        if is_name_taken(name):
            print(f"El nombre '{name}' ya existe en la base de datos. Intenta con otro nombre.")
        else:
            break  # Nombre válido, continuar con la captura

    camera = initialize_camera()
    camera.start()
    sleep(1)  # Dar tiempo para estabilizar la cámara

    try:
        frame = capture_face_image(camera)
        if frame is not None:
            add_user_to_database(name, frame)
        else:
            print("No se completó la captura.")
    except Exception as e:
        print(f"Error durante el registro: {e}")
    finally:
        camera.stop()
        camera.close()
        cv2.destroyAllWindows()
        print("Cámara apagada.")
