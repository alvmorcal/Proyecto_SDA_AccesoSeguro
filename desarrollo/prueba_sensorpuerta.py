import RPi.GPIO as GPIO
import time

# Configura el pin GPIO donde está conectado el reed switch
SENSOR_PIN = 5  # Cambia al GPIO que estás usando

# Configuración de la Raspberry Pi
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

# Configurar el pin como entrada con resistencia pull-up interna
GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Prueba del reed switch con pull-up interno. Presiona Ctrl+C para salir.")
try:
    while True:
        # Leer el estado del reed switch
        if GPIO.input(SENSOR_PIN) == GPIO.HIGH:
            print("Puerta abierta (reed switch desconectado)")
        else:
            print("Puerta cerrada (reed switch conectado)")
        time.sleep(0.5)
except KeyboardInterrupt:
    print("Deteniendo programa.")
    GPIO.cleanup()

