# Librerías Importadas y su propósito
import RPi.GPIO as GPIO  # Manejo de pines GPIO para sensores, LEDs y actuadores.
import cv2  # Captura y procesamiento de imágenes para reconocimiento facial.
import face_recognition  # Biblioteca para reconocimiento facial.
import numpy as np  # Manejo eficiente de matrices y operaciones numéricas.
import time  # Manejo de tiempos y retrasos.
import sqlite3  # Conexión y manejo de la base de datos SQLite.
import threading  # Manejo de tareas concurrentes usando hilos.
from picamera2 import Picamera2  # Manejo de la cámara en Raspberry Pi.
import requests  # Realizar solicitudes HTTP, utilizado para enviar mensajes y fotos a Telegram.
from dotenv import load_dotenv  # Para cargar variables de entorno desde un archivo .env.
import os  # Para manejar variables de entorno.

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# Configuración de pines GPIO
SENSOR_PRESENCIA = 23  # Sensor de movimiento.
BUTTON_PIN = 24  # Botón físico.
BUZZER_PIN = 25  # Buzzer (alarma).
SERVO_PIN = 18  # Servo motor para bloqueo/desbloqueo.
LED_ROJO = 27  # LED indicador de bloqueo.
LED_VERDE = 17  # LED indicador de desbloqueo.
LED_BLANCO = 22  # LED indicador de actividad.
SENSOR_MAGNETICO = 5  # Sensor magnético para detectar apertura/cierre de puerta.

# Configuración global
BOT_TOKEN = os.getenv("BOT_TOKEN")  # Token del bot de Telegram (de variable de entorno).
CHAT_ID = os.getenv("CHAT_ID")  # ID del chat de Telegram (de variable de entorno).
TOLERANCE = 0.6  # Tolerancia para reconocimiento facial.
DOOR_UNLOCK_TIME = 5  # Tiempo en segundos antes de bloquear automáticamente tras desbloqueo.

door_locked = False  # Estado de la puerta (bloqueada/desbloqueada).
servo_unlocked = False  # Estado del servo (posición de desbloqueo).

# Locks para sincronización de hilos
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

# Inicialización del servo motor
servo = GPIO.PWM(SERVO_PIN, 50)  # PWM en 50 Hz.
servo.start(0)  # Inicia con el servo apagado.

# Funciones auxiliares
def send_telegram_message(message):
    """Envía un mensaje de texto a Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN o CHAT_ID no configurados.")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message})
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
        requests.post(url, files={"photo": buffer.tobytes()}, data={"chat_id": CHAT_ID, "caption": caption})
    except requests.exceptions.RequestException as e:
        print(f"Error al enviar foto a Telegram: {e}")

def set_led_state(led_rojo=None, led_verde=None, led_blanco=None):
    """Configura el estado de los LEDs."""
    with led_lock:
        if led_rojo is not None:
            GPIO.output(LED_ROJO, led_rojo)
        if led_verde is not None:
            GPIO.output(LED_VERDE, led_verde)
        if led_blanco is not None:
            GPIO.output(LED_BLANCO, led_blanco)

def desbloquear_servo():
    """Desbloquea la puerta moviendo el servo a la posición de desbloqueo."""
    global servo_unlocked
    servo_unlocked = True
    servo.ChangeDutyCycle(12)  # Posición de desbloqueo.
    time.sleep(1)
    servo.ChangeDutyCycle(0)

def bloquear_servo():
    """Bloquea la puerta moviendo el servo a la posición de bloqueo."""
    global servo_unlocked
    servo.ChangeDutyCycle(7)  # Posición de bloqueo.
    time.sleep(1)
    servo.ChangeDutyCycle(0)
    servo_unlocked = False

def sensor_door_open():
    """Verifica si la puerta está abierta."""
    return GPIO.input(SENSOR_MAGNETICO) == GPIO.HIGH

def inicializar_estado():
    """Inicializa el estado de la puerta y LEDs al inicio."""
    if sensor_door_open():
        desbloquear_servo()
        set_led_state(led_rojo=False, led_verde=True)
    else:
        bloquear_servo()
        set_led_state(led_rojo=True, led_verde=False)

# Hilos
def verificar_puerta():
    """Hilo para verificar el estado de la puerta y bloquear automáticamente si no se abre."""
    global servo_unlocked
    while True:
        if not servo_unlocked:  # Si la puerta ya está bloqueada, no hace nada.
            continue

        time.sleep(DOOR_UNLOCK_TIME)  # Espera tiempo para comprobar si se abrió.
        if not sensor_door_open():  # Si la puerta sigue cerrada.
            bloquear_servo()
            set_led_state(led_rojo=True, led_verde=False)
            send_telegram_message("🔒 Puerta bloqueada automáticamente tras inactividad.")

# Código principal
if __name__ == "__main__":
    if not BOT_TOKEN or not CHAT_ID:
        print("Error: BOT_TOKEN o CHAT_ID no configurados. Asegúrate de configurar las variables en el archivo .env.")
        exit(1)

    inicializar_estado()  # Inicializa el sistema.

    # Configuración de la cámara.
    camera = Picamera2()
    config = camera.create_still_configuration(main={"size": (640, 480)})
    camera.configure(config)
    camera.start()

    # Iniciar hilos.
    threading.Thread(target=verificar_puerta, daemon=True).start()

    try:
        while True:
            time.sleep(0.1)  # Mantén el programa en ejecución.
    except KeyboardInterrupt:
        print("Finalizando programa.")
        GPIO.cleanup()  # Limpia la configuración GPIO al finalizar.






