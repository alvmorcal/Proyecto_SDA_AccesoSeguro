import multiprocessing
import os

# Función para ejecutar el servidor Flask
def run_web():
    os.system("python3 web.py")

# Función para ejecutar el reconocimiento facial
def run_caja():
    os.system("python3 caja.py")

if __name__ == "__main__":
    # Crear procesos
    web = multiprocessing.Process(target=run_web)
    caja = multiprocessing.Process(target=run_caja)

    # Iniciar procesos
    web.start()
    caja.start()

    # Esperar a que terminen los procesos
    web.join()
    caja.join()
