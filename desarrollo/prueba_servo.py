# Script para controlar el servo con teclas
import RPi.GPIO as GPIO
import time

SERVO_PIN = 18

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(SERVO_PIN, GPIO.OUT)

servo = GPIO.PWM(SERVO_PIN, 50)
servo.start(0)

POSICION_ABIERTA = 12  # Duty cycle para abrir
POSICION_CERRADA = 7  # Duty cycle para cerrar

estado_actual = "cerrada"

print("Control del servo: Presiona 'O' para abrir y 'C' para cerrar. Presiona Ctrl+C para salir.")
try:
    while True:
        comando = input("Ingresa comando (O para abrir, C para cerrar): ").strip().upper()
        if comando == "O" and estado_actual != "abierta":
            servo.ChangeDutyCycle(POSICION_ABIERTA)
            time.sleep(1)
            servo.ChangeDutyCycle(0)
            estado_actual = "abierta"
            print("Servo en posición abierta.")
        elif comando == "C" and estado_actual != "cerrada":
            servo.ChangeDutyCycle(POSICION_CERRADA)
            time.sleep(1)
            servo.ChangeDutyCycle(0)
            estado_actual = "cerrada"
            print("Servo en posición cerrada.")
        else:
            print("El servo ya está en la posición deseada.")
except KeyboardInterrupt:
    print("Deteniendo programa.")
    servo.stop()
    GPIO.cleanup()

