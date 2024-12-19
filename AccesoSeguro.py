import multiprocessing
import os

# Función para ejecutar el servidor Flask
def run_web():
    os.system("python3 web.py")

# Función para ejecutar el reconocimiento facial
def run_face_recognition():
    os.system("python3 face_recognition.py")

if __name__ == "__main__":
    # Crear procesos
    web = multiprocessing.Process(target=run_web)
    face_recognition = multiprocessing.Process(target=run_face_recognition)

    # Iniciar procesos
    web.start()
    face_recognition.start()

    # Esperar a que terminen los procesos
    web.join()
    face_recognition.join()
