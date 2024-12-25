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
BOT_TOKEN = "7623844834:AAEh23cpLEIXKFJPcTwh-BCmsqZ6Cze6jew"
CHAT_ID = "1882908107"
TOLERANCE = 0.6
DOOR_UNLOCK_TIME = 5
DOOR_AUTO_LOCK_TIME = 2

door_locked = False

# Locks para protección de recursos
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
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar mensaje a Telegram: {e}")

def send_telegram_photo(frame, caption):
    """Envía una foto a Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN o CHAT_ID no configurados.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        _, buffer = cv2.imencode('.jpg', frame)
        response = requests.post(url, files={"photo": buffer.tobytes()}, data={"chat_id": CHAT_ID, "caption": caption})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
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
    global unlock_time
    unlock_time = time.time()
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
    """Detecta presencia con estabilidad de múltiples lecturas."""
    return any(GPIO.input(SENSOR_PRESENCIA) for _ in range(5))

def button_pressed():
    """Detecta si el botón ha sido pulsado."""
    return GPIO.input(BUTTON_PIN) == GPIO.LOW

def sensor_door_open():
    """Detecta si la puerta está abierta con múltiples lecturas estables."""
    return all(GPIO.input(SENSOR_MAGNETICO) for _ in range(5))

def get_users_from_database():
    """Carga los usuarios desde la base de datos."""
    try:
        with sqlite3.connect("users.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name, encoding FROM users")
            rows = cursor.fetchall()
            return [(row[0], np.frombuffer(row[1], dtype=np.float64)) for row in rows]
    except sqlite3.Error as e:
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
        set_led_state(False, True, None)
    else:
        set_led_state(True, False, None)

def hilo_seguro(func, *args, **kwargs):
    """Ejecuta una función dentro de un hilo y captura errores."""
    try:
        func(*args, **kwargs)
    except Exception as e:
        print(f"Error en el hilo {func.__name__}: {e}")

def reconocimiento_facial(camera):
    """Hilo que realiza reconocimiento facial continuamente."""
    global users
    while True:
        if detectar_presencia():
            name, frame = process_camera(camera, users)
            set_led_state(None, None, name is not None)
        else:
            set_led_state(None, None, False)
        time.sleep(0.1)

def monitoreo_boton():
    """Hilo que monitorea las acciones del botón."""
    global door_locked
    last_pressed_time = 0
    debounce_time = 0.2
    while True:
        if button_pressed():
            current_time = time.time()
            if current_time - last_pressed_time > debounce_time:
                last_pressed_time = current_time
                if GPIO.input(LED_BLANCO):
                    desbloquear_servo()
                    set_led_state(False, True, None)
                    name, frame = process_camera(camera, users)
                    send_telegram_message(f"✅ Acceso permitido: {name} desbloqueó la caja.")
                else:
                    activate_buzzer()
                    with camera_lock:
                        frame = camera.capture_array()
                    send_telegram_message("🚨 Intento no autorizado detectado.")
                    send_telegram_photo(frame, "🚨 Foto del intento no autorizado")

def verificar_puerta():
    """Hilo que verifica continuamente el estado de la puerta."""
    global door_locked
    last_close_time = None
    unlock_time = None

    while True:
        door_is_open = sensor_door_open()

        if door_is_open:
            with door_lock:
                door_locked = False
            last_close_time = None
            unlock_time = None
        else:
            current_time = time.time()

            if last_close_time is None:
                last_close_time = current_time

            if unlock_time is not None and not door_locked and current_time - unlock_time >= 5:
                with door_lock:
                    bloquear_servo()
                    set_led_state(True, False, None)
                    send_telegram_message("🔒 Caja bloqueada automáticamente tras desbloqueo sin apertura.")
                    door_locked = True
                unlock_time = None

            if last_close_time is not None and not door_locked and current_time - last_close_time >= 5:
                with door_lock:
                    bloquear_servo()
                    set_led_state(True, False, None)
                    send_telegram_message("🔒 Caja bloqueada automáticamente al cerrar.")
                    door_locked = True
                last_close_time = None

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

    threading.Thread(target=hilo_seguro, args=(reconocimiento_facial, camera), daemon=True).start()
    threading.Thread(target=hilo_seguro, args=(monitoreo_boton,), daemon=True).start()
    threading.Thread(target=hilo_seguro, args=(verificar_puerta,), daemon=True).start()
    threading.Thread(target=hilo_seguro, args=(actualizar_usuarios_periodicamente,), daemon=True).start()

    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("Finalizando programa.")
        GPIO.cleanup()



















