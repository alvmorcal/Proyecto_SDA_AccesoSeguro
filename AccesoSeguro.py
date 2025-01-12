import multiprocessing  # Biblioteca para crear y manejar procesos independientes
import os  # Biblioteca para interactuar con el sistema operativo

# Función para ejecutar el servidor Flask
def run_web():
    # Usa un comando del sistema operativo para ejecutar el archivo "web.py"
    os.system("python3 web.py")

# Función para ejecutar el reconocimiento facial
def run_caja():
    # Usa un comando del sistema operativo para ejecutar el archivo "caja.py"
    os.system("python3 caja.py")

if __name__ == "__main__":
    # Bloque principal del script, asegura que el código dentro de este bloque
    # solo se ejecute cuando el archivo se ejecuta directamente, no cuando es importado.

    # Crear un proceso independiente para el servidor web
    web = multiprocessing.Process(target=run_web)

    # Crear un proceso independiente para el sistema de reconocimiento facial
    caja = multiprocessing.Process(target=run_caja)

    # Iniciar el proceso que ejecuta "web.py"
    web.start()

    # Iniciar el proceso que ejecuta "caja.py"
    caja.start()

    # Esperar a que el proceso "web" termine antes de continuar
    web.join()

    # Esperar a que el proceso "caja" termine antes de continuar
    caja.join()

