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
LED_ROJO = 27
LED_VERDE = 17
LED_BLANCO = 22
SENSOR_MAGNETICO = 5

# Configuración global
BOT_TOKEN = "7623844834:AAEh23cpLEIXKFJPcTwh-BCmsqZ6jew"
CHAT_ID = "1882908107"
TOLERANCE = 0.6
DOOR_UNLOCK_TIME = 5  # Tiempo en segundos
DOOR_AUTO_LOCK_TIME = 2  # Tiempo en segundos

# Estado inicial de la puerta
door_locked = False

# Locks para sincronización
led_lock = threading.Lock()
door_lock = threading.Lock()
camera_lock = threading.Lock()
buzzer_lock = threading.Lock()

# Configuración de GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PRESENCIA, GPIO.IN)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(LED_ROJO, GPIO.OUT)
GPIO.setup(LED_VERDE, GPIO.OUT)
GPIO.setup(LED_BLANCO, GPIO.OUT)
GPIO.setup(SENSOR_MAGNETICO, GPIO.IN)

# Configurar PWM para el servo
servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(0)

def send_telegram_message(message):
    """Envía un mensaje de texto a Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN o CHAT_ID no configurados.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, data={"chat_id": CHAT_ID, "text": message})
        if response.status_code != 200:
            print(f"Error al enviar mensaje: {response.status_code} {response.text}")
    except requests.RequestException as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

def send_telegram_photo(frame, caption):
    """Envía una foto a Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN o CHAT_ID no configurados.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        success, buffer = cv2.imencode('.jpg', frame)
        if not success:
            print("Error al codificar la imagen.")
            return

        response = requests.post(
            url, 
            files={"photo": buffer.tobytes()}, 
            data={"chat_id": CHAT_ID, "caption": caption}
        )
        if response.status_code != 200:
            print(f"Error al enviar foto: {response.status_code} {response.text}")
    except requests.RequestException as e:
        print(f"Error al enviar foto a Telegram: {e}")

def set_led_state(led_rojo=None, led_verde=None, led_blanco=None):
    """Configura el estado de los LEDs de manera segura."""
    with led_lock:
        if led_rojo is not None:
            GPIO.output(LED_ROJO, led_rojo)
        if led_verde is not None:
            GPIO.output(LED_VERDE, led_verde)
        if led_blanco is not None:
            GPIO.output(LED_BLANCO, led_blanco)

def desbloquear_servo():
    """Desbloquea el servo motor."""
    servo.ChangeDutyCycle(12)
    time.sleep(1)
    servo.ChangeDutyCycle(0)

def bloquear_servo():
    """Bloquea el servo motor."""
    servo.ChangeDutyCycle(7)
    time.sleep(1)
    servo.ChangeDutyCycle(0)

def activate_buzzer(duration=1):
    """Activa el buzzer por un tiempo específico."""
    with buzzer_lock:
        GPIO.output(BUZZER_PIN, True)
        time.sleep(duration)
        GPIO.output(BUZZER_PIN, False)

def detectar_presencia():
    """Detecta presencia con múltiples lecturas estables."""
    return any(GPIO.input(SENSOR_PRESENCIA) for _ in range(5))

def button_pressed():
    """Detecta si el botón ha sido pulsado."""
    return GPIO.input(BUTTON_PIN) == GPIO.LOW

def sensor_door_open():
    """Detecta si la puerta está abierta."""
    return all(GPIO.input(SENSOR_MAGNETICO) for _ in range(5))

def get_users_from_database():
    """Carga los usuarios desde la base de datos."""
    try:
        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, encoding FROM users")
            rows = cursor.fetchall()
            return [(row[0], np.frombuffer(row[1], dtype=np.float64)) for row in rows]
    except sqlite3.DatabaseError as e:
        print(f"Error al cargar usuarios: {e}")
        return []

def process_camera(camera, users):
    """Procesa la imagen de la cámara y realiza el reconocimiento facial."""
    try:
        with camera_lock:
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
    except Exception as e:
        print(f"Error en process_camera: {e}")
        return None, None

def inicializar_estado():
    """Inicializa el estado del sistema al iniciar."""
    set_led_state(False, False, False)
    if sensor_door_open():
        set_led_state(False, True, None)  # Verde encendido
    else:
        set_led_state(True, False, None)  # Rojo encendido

def reconocimiento_facial(camera, users):
    """Hilo que realiza reconocimiento facial continuamente."""
    while True:
        if detectar_presencia():
            name, frame = process_camera(camera, users)
            if name:
                set_led_state(None, None, True)  # Blanco encendido
                send_telegram_message(f"✅ Acceso permitido: {name}")
            else:
                set_led_state(None, None, False)
        time.sleep(0.1)

def monitoreo_boton(camera, users):
    """Hilo que monitorea las acciones del botón."""
    while True:
        if button_pressed():
            if GPIO.input(LED_BLANCO):
                desbloquear_servo()
                send_telegram_message("✅ Acceso permitido: Caja desbloqueada.")
            else:
                activate_buzzer()
                send_telegram_message("🚨 Intento no autorizado detectado.")
        time.sleep(0.1)

def verificar_puerta():
    """Hilo que verifica continuamente el estado de la puerta."""
    global door_locked
    while True:
        if sensor_door_open():
            with door_lock:
                door_locked = False
        else:
            with door_lock:
                if not door_locked:
                    time.sleep(DOOR_AUTO_LOCK_TIME)
                    bloquear_servo()
                    set_led_state(True, False, None)
                    send_telegram_message("🔒 Caja bloqueada automáticamente al cerrar.")
                    door_locked = True
        time.sleep(0.1)

def actualizar_usuarios_periodicamente():
    """Hilo que actualiza periódicamente la lista de usuarios."""
    global users
    while True:
        users = get_users_from_database()
        time.sleep(10)

if __name__ == "__main__":
    inicializar_estado()

    camera = Picamera2()
    config = camera.create_still_configuration(main={"size": (640, 480)})
    camera.configure(config)
    camera.start()

    users = get_users_from_database()

    threading.Thread(target=reconocimiento_facial, args=(camera, users), daemon=True).start()
    threading.Thread(target=monitoreo_boton, args=(camera, users), daemon=True).start()
    threading.Thread(target=verificar_puerta, daemon=True).start()
    threading.Thread(target=actualizar_usuarios_periodicamente, daemon=True).start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Finalizando programa.")
        GPIO.cleanup()


















