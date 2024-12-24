# Script mejorado para controlar el LED blanco con el sensor de puerta
import RPi.GPIO as GPIO
import time

SENSOR_MAGNETICO = 5
LED_BLANCO = 22

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_MAGNETICO, GPIO.IN)
GPIO.setup(LED_BLANCO, GPIO.OUT)

def leer_estado_sensor(sensor_pin, lecturas=5, intervalo=0.02):
    """
    Realiza múltiples lecturas del sensor y retorna el estado estabilizado.
    :param sensor_pin: Pin GPIO del sensor.
    :param lecturas: Número de lecturas a realizar.
    :param intervalo: Tiempo entre lecturas (en segundos).
    :return: Estado estabilizado del sensor.
    """
    estados = []
    for _ in range(lecturas):
        estados.append(GPIO.input(sensor_pin))
        time.sleep(intervalo)
    # Consideramos la mayoría como el estado estable
    return all(estados)

print("Control del LED blanco con sensor de puerta mejorado. Presiona Ctrl+C para salir.")
try:
    while True:
        if leer_estado_sensor(SENSOR_MAGNETICO):  # Puerta abierta
            GPIO.output(LED_BLANCO, True)
            print("Puerta abierta. LED blanco encendido.")
        else:  # Puerta cerrada
            GPIO.output(LED_BLANCO, False)
            print("Puerta cerrada. LED blanco apagado.")
        time.sleep(0.1)
except KeyboardInterrupt:
    print("Deteniendo programa.")
    GPIO.cleanup()
