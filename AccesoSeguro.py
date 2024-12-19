import multiprocessing
import os

# Función para ejecutar el servidor Flask
def run_web():
    os.system("python3 web.py")

# Función para ejecutar el reconocimiento facial
def run_reconocer_usuarios():
    os.system("python3 reconocer_usuarios.py")

if __name__ == "__main__":
    # Crear procesos
    web = multiprocessing.Process(target=run_web)
    reconocer_usuarios = multiprocessing.Process(target=run_reconocer_usuarios)

    # Iniciar procesos
    web.start()
   reconocer_usuarios.start()

    # Esperar a que terminen los procesos
    web.join()
    reconocer_usuarios.join()
