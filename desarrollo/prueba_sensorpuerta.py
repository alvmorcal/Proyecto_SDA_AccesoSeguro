# Script para comprobar el sensor de puerta y controlar el LED blanco
import RPi.GPIO as GPIO
import time

SENSOR_MAGNETICO = 5
LED_BLANCO = 22

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_MAGNETICO, GPIO.IN)
GPIO.setup(LED_BLANCO, GPIO.OUT)

print("Control del LED blanco con el sensor de puerta. Presiona Ctrl+C para salir.")
try:
    while True:
        if GPIO.input(SENSOR_MAGNETICO):  # Puerta abierta
            GPIO.output(LED_BLANCO, True)
            print("Puerta abierta. LED blanco encendido.")
        else:  # Puerta cerrada
            GPIO.output(LED_BLANCO, False)
            print("Puerta cerrada. LED blanco apagado.")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Deteniendo programa.")
    GPIO.cleanup()
