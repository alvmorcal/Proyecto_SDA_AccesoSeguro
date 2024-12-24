import RPi.GPIO as GPIO
import cv2
import face_recognition
import numpy as np
import time
import sqlite3
import threading
from picamera2 import Picamera2
import requests

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
DOOR_UNLOCK_TIME = 5  # Tiempo para mantener la puerta desbloqueada tras pulsación válida (segundos)
DOOR_AUTO_LOCK_TIME = 2  # Tiempo para bloquear automáticamente tras cerrar la puerta (segundos)

# Protección de LEDs
led_lock = threading.Lock()

GPIO.setwarnings(False)  # Desactivar advertencias de GPIO
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

def set_led_state(led_rojo, led_verde, led_blanco):
    with led_lock:
        GPIO.output(LED_ROJO, led_rojo)
        GPIO.output(LED_VERDE, led_verde)
        GPIO.output(LED_BLANCO, led_blanco)

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
    time.sleep(1)  # Sonar durante 1 segundos
    GPIO.output(BUZZER_PIN, False)

def detectar_presencia():
    readings = []
    for _ in range(5):  # Toma 5 lecturas rápidas
        readings.append(GPIO.input(SENSOR_PRESENCIA))
        time.sleep(0.01)  # 10ms entre lecturas
    return any(readings)  # Devuelve True si alguna lectura indica presencia

def button_pressed():
    return GPIO.input(BUTTON_PIN) == GPIO.LOW

def sensor_door_open():
    stable_readings = []
    for _ in range(5):  # Toma 5 lecturas rápidas
        stable_readings.append(GPIO.input(SENSOR_MAGNETICO))
        time.sleep(0.02)  # Espera 20ms entre lecturas
    return all(stable_readings)  # Devuelve True solo si todas las lecturas coinciden

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
            return name, frame
    return None, frame

def inicializar_estado():
    set_led_state(False, False, False)  # Asegurar que todos los LEDs están apagados inicialmente
    if sensor_door_open():
        set_led_state(False, True, False)  # Verde encendido
    else:
        set_led_state(True, False, False)  # Rojo encendido

# --- Funciones de Control en Hilos ---
door_locked = False

def reconocimiento_facial(camera):
    global users
    while True:
        if detectar_presencia():  # Solo si hay presencia estabilizada
            name, frame = process_camera(camera, users)
            if name:
                set_led_state(False, GPIO.input(LED_VERDE), True)  # Blanco encendido si se reconoce a una persona conocida
            else:
                set_led_state(GPIO.input(LED_ROJO), GPIO.input(LED_VERDE), False)  # Mantener el estado actual de rojo y verde, apagar blanco
        else:
            set_led_state(GPIO.input(LED_ROJO), GPIO.input(LED_VERDE), False)  # Mantener rojo y verde, apagar blanco si no hay presencia
        time.sleep(0.1)

def monitoreo_boton():
    global door_locked
    last_pressed_time = 0
    debounce_time = 0.2  # Tiempo de debounce (200ms)
    while True:
        if button_pressed():
            current_time = time.time()
            if current_time - last_pressed_time > debounce_time:  # Verificar debounce
                last_pressed_time = current_time
                if GPIO.input(LED_BLANCO):  # Si el LED blanco está encendido
                    desbloquear_servo()
                    set_led_state(False, True, GPIO.input(LED_BLANCO))  # Verde encendido, rojo apagado
                    name, _ = process_camera(camera, users)
                    send_telegram_message(f"✅ Acceso permitido: {name} desbloqueó la caja.")

                    start_time = time.time()
                    while time.time() - start_time < DOOR_UNLOCK_TIME:
                        if sensor_door_open():
                            send_telegram_message("✅ Caja abierta.")
                            while sensor_door_open():
                                time.sleep(0.1)
                            time.sleep(DOOR_AUTO_LOCK_TIME)
                            bloquear_servo()
                            set_led_state(True, False, GPIO.input(LED_BLANCO))  # Rojo encendido, verde apagado
                            send_telegram_message("🔒 Caja bloqueada automáticamente.")
                            door_locked = True
                            return

                    bloquear_servo()
                    set_led_state(True, False, GPIO.input(LED_BLANCO))  # Rojo encendido, verde apagado
                    send_telegram_message("🔒 Caja bloqueada automáticamente por tiempo.")
                    door_locked = True
                else:
                    activate_buzzer()
                    send_telegram_message("🚨 Intento no autorizado: Persona desconocida intentó abrir la caja.")
                    camera = Picamera2()
                    frame = camera.capture_array()
                    send_telegram_photo(frame, "Intento no autorizado detectado.")

def verificar_puerta():
    global door_locked
    while True:
        if sensor_door_open():
            door_locked = False  # Resetear el estado
        else:
            if not door_locked:  # Solo bloquear si aún no está bloqueada
                time.sleep(DOOR_AUTO_LOCK_TIME)
                bloquear_servo()
                set_led_state(True, False, False)  # Rojo encendido, verde apagado
                send_telegram_message("🔒 Caja bloqueada automáticamente al cerrar.")
                door_locked = True
        time.sleep(0.1)  # Reducir uso de CPU

def actualizar_usuarios_periodicamente():
    global users
    while True:
        users = get_users_from_database()
        time.sleep(10)  # Actualizar cada 10 segundos

# --- Programa Principal ---
if __name__ == "__main__":
    inicializar_estado()

    # Configurar cámara
    camera = Picamera2()
    config = camera.create_still_configuration(main={"size": (640, 480)})
    camera.configure(config)
    camera.start()

    # Cargar usuarios inicialmente
    users = get_users_from_database()

    # Crear hilos
    hilo_reconocimiento = threading.Thread(target=reconocimiento_facial, args=(camera,))
    hilo_boton = threading.Thread(target=monitoreo_boton)
    hilo_puerta = threading.Thread(target=verificar_puerta)
    hilo_actualizacion = threading.Thread(target=actualizar_usuarios_periodicamente)

    # Iniciar hilos
    hilo_reconocimiento.start()
    hilo_boton.start()
    hilo_puerta.start()
    hilo_actualizacion.start()

    # Mantener el programa corriendo
    hilo_reconocimiento.join()
    hilo_boton.join()
    hilo_puerta.join()
    hilo_actualizacion.join()













