import RPi.GPIO as GPIO
import cv2
import face_recognition
import numpy as np
import time
import sqlite3
import threading
from picamera2 import Picamera2
import requests
import signal
import sys

# Configuración de pines GPIO
SENSOR_PRESENCIA = 23
BUTTON_PIN = 24
BUZZER_PIN = 25
SERVO_PIN = 18
LED_ROJO = 17
LED_VERDE = 27
LED_BLANCO = 22
SENSOR_MAGNETICO = 5

# Configuración global
BOT_TOKEN = "7623844834:AAEh23cpLEIXKFJPcTwh-BCmsqZ6Cze6jew"
CHAT_ID = "1882908107"
TOLERANCE = 0.6
DOOR_UNLOCK_TIME = 10  # Tiempo para mantener la puerta desbloqueada tras pulsación válida (segundos)
DOOR_AUTO_LOCK_TIME = 2  # Tiempo para bloquear automáticamente tras cerrar la puerta (segundos)

# Configuración de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PRESENCIA, GPIO.IN)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(LED_ROJO, GPIO.OUT)
GPIO.setup(LED_VERDE, GPIO.OUT)
GPIO.setup(LED_BLANCO, GPIO.OUT)
GPIO.setup(SENSOR_MAGNETICO, GPIO.IN)

servo = GPIO.PWM(SERVO_PIN, 50)  # Configurar PWM para el servo
servo.start(0)

# Variables globales
threads = []
running = True

# --- Funciones Auxiliares ---
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
    except Exception as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

def send_telegram_photo(frame, caption):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        _, buffer = cv2.imencode('.jpg', frame)
        requests.post(url, files={"photo": buffer.tobytes()}, data={"chat_id": CHAT_ID, "caption": caption})
    except Exception as e:
        print(f"Error al enviar foto a Telegram: {e}")

def set_led(state, pin):
    GPIO.output(pin, state)

def desbloquear_servo():
    servo.ChangeDutyCycle(7)  # Posición de desbloqueo
    time.sleep(1)
    servo.ChangeDutyCycle(0)

def bloquear_servo():
    servo.ChangeDutyCycle(12)  # Posición de bloqueo
    time.sleep(1)
    servo.ChangeDutyCycle(0)

def activate_buzzer():
    GPIO.output(BUZZER_PIN, True)
    time.sleep(10)  # Sonar durante 10 segundos
    GPIO.output(BUZZER_PIN, False)

def detectar_presencia():
    return GPIO.input(SENSOR_PRESENCIA) == GPIO.HIGH

def button_pressed():
    return GPIO.input(BUTTON_PIN) == GPIO.LOW

def sensor_door_open():
    return GPIO.input(SENSOR_MAGNETICO) == GPIO.LOW

def get_users_from_database():
    try:
        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, encoding FROM users")
            rows = cursor.fetchall()
            return [(row[0], np.frombuffer(row[1], dtype=np.float64)) for row in rows]
    except Exception as e:
        print(f"Error al cargar usuarios: {e}")
        return []

def process_camera(camera, users):
    frame = camera.capture_array()
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    face_locations = face_recognition.face_locations(rgb_frame)
    face_encodings = face_recognition.face_encodings(rgb_frame, face_locations)

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces([user[1] for user in users], face_encoding, tolerance=TOLERANCE)
        if True in matches:
            name = users[matches.index(True)][0]
            return name
    return None

def inicializar_estado():
    if sensor_door_open():
        print("Estado inicial: puerta abierta.")
        desbloquear_servo()
        set_led(False, LED_ROJO)
        set_led(True, LED_VERDE)
    else:
        print("Estado inicial: puerta cerrada.")
        bloquear_servo()
        set_led(False, LED_VERDE)
        set_led(True, LED_ROJO)

# --- Funciones de Control en Hilos ---
def reconocimiento_facial(camera):
    global running
    global users
    while running:
        if detectar_presencia():
            known_user = process_camera(camera, users)
            if known_user:
                #print(f"Usuario reconocido: {known_user}")
                set_led(True, LED_BLANCO)
            else:
                #print("Persona desconocida.")
                set_led(False, LED_BLANCO)

def monitoreo_boton():
    global running
    while running:
        if button_pressed():
            if GPIO.input(LED_BLANCO):  # Si el LED blanco está encendido
                #print("Acceso permitido.")
                desbloquear_servo()
                set_led(False, LED_ROJO)
                set_led(True, LED_VERDE)
                send_telegram_message("✅ Acceso permitido.")

                start_time = time.time()
                while time.time() - start_time < DOOR_UNLOCK_TIME:
                    if sensor_door_open():
                        print("Puerta abierta.")
                        while sensor_door_open():
                            time.sleep(0.1)
                        print("Puerta cerrada, bloqueando automáticamente.")
                        time.sleep(DOOR_AUTO_LOCK_TIME)
                        bloquear_servo()
                        set_led(False, LED_VERDE)
                        set_led(True, LED_ROJO)
                        return
                        
                print("Tiempo agotado. Bloqueando nuevamente.")
                bloquear_servo()
                set_led(True, LED_ROJO)
                set_led(False, LED_VERDE)
            else:
                print("Intento no autorizado. Activando alarma.")
                activate_buzzer()
                send_telegram_message("🚨 ALERTA: Persona desconocida detectada.")

def verificar_puerta():
    global running
    while running:
        if sensor_door_open():
            print("Puerta abierta.")
            while sensor_door_open():
                time.sleep(0.1)
            print("Puerta cerrada, bloqueando automáticamente.")
            time.sleep(DOOR_AUTO_LOCK_TIME)
            bloquear_servo()
            set_led(True, LED_ROJO)

def actualizar_usuarios_periodicamente():
    global running
    global users
    while running:
        users = get_users_from_database()
        #print("Base de datos actualizada.")
        time.sleep(10)  # Actualizar cada 10 segundos

# --- Manejo de Señales para Salida Ordenada ---
def cerrar_programa(signal, frame):
    global running
    print("\nCerrando programa...")
    running = False
    for t in threads:
        t.join()
    GPIO.cleanup()
    sys.exit(0)

# --- Programa Principal ---
if __name__ == "__main__":
    signal.signal(signal.SIGINT, cerrar_programa)  # Manejo de Ctrl+C
    inicializar_estado()

    # Configurar cámara
    camera = Picamera2()
    config = camera.create_still_configuration(main={"size": (640, 480)})
    camera.configure(config)
    camera.start()

    # Cargar usuarios inicialmente
    users = get_users_from_database()

    # Crear hilos
    threads = [
        threading.Thread(target=reconocimiento_facial, args=(camera,)),
        threading.Thread(target=monitoreo_boton),
        threading.Thread(target=verificar_puerta),
        threading.Thread(target=actualizar_usuarios_periodicamente),
    ]

    # Iniciar hilos
    for t in threads:
        t.start()

    # Mantener el programa corriendo
    for t in threads:
        t.join()



