# Script para comprobar la pulsación del botón y controlar el LED blanco
import RPi.GPIO as GPIO
import time

BUTTON_PIN = 24
LED_BLANCO = 22

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(LED_BLANCO, GPIO.OUT)

print("Control del LED blanco con el botón. Presiona Ctrl+C para salir.")
try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # Botón presionado
            GPIO.output(LED_BLANCO, True)
            print("Botón presionado. LED blanco encendido.")
        else:  # Botón no presionado
            GPIO.output(LED_BLANCO, False)
            print("Botón no presionado. LED blanco apagado.")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Deteniendo programa.")
    GPIO.cleanup()
