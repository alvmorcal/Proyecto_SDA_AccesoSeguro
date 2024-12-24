# Script para detectar presencia y controlar el LED blanco
import RPi.GPIO as GPIO
import time

SENSOR_PRESENCIA = 23
LED_BLANCO = 22

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PRESENCIA, GPIO.IN)
GPIO.setup(LED_BLANCO, GPIO.OUT)

print("Detectando presencia. Presiona Ctrl+C para salir.")
try:
    while True:
        if GPIO.input(SENSOR_PRESENCIA):
            GPIO.output(LED_BLANCO, True)
            print("Presencia detectada. LED blanco encendido.")
        else:
            GPIO.output(LED_BLANCO, False)
            print("Sin presencia. LED blanco apagado.")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Deteniendo programa.")
    GPIO.cleanup()
