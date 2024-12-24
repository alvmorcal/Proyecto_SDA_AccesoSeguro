# Script para alternar LEDs y mostrar mensajes
import RPi.GPIO as GPIO
import time

LED_ROJO = 17
LED_VERDE = 27
LED_BLANCO = 22

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_ROJO, GPIO.OUT)
GPIO.setup(LED_VERDE, GPIO.OUT)
GPIO.setup(LED_BLANCO, GPIO.OUT)

print("Alternando LEDs. Presiona Ctrl+C para salir.")
try:
    while True:
        GPIO.output(LED_VERDE, True)
        print("Encendiendo LED verde")
        time.sleep(1)
        GPIO.output(LED_VERDE, False)

        GPIO.output(LED_ROJO, True)
        print("Encendiendo LED rojo")
        time.sleep(1)
        GPIO.output(LED_ROJO, False)

        GPIO.output(LED_BLANCO, True)
        print("Encendiendo LED blanco")
        time.sleep(1)
        GPIO.output(LED_BLANCO, False)
except KeyboardInterrupt:
    print("Deteniendo programa.")
    GPIO.cleanup()
