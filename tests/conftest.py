import os
import sys

# Permite importar el paquete "mesa" al ejecutar pytest desde la carpeta del proyecto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
