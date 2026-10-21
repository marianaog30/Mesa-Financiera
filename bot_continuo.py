"""Bot que responde al instante mientras este programa esté corriendo.

Úsalo en clase desde tu computadora, Colab o GitHub Codespaces. Detenlo con Ctrl + C.
Para que funcione con la computadora apagada usa GitHub Actions (revisar_telegram.py).
"""
import time
import sys

import requests

from mesa import config
from mesa.comandos import atender
from mesa.telegram_io import obtener_mensajes, preparar_polling, verificar_bot


def main():
    print("Configuración:", config.resumen())
    if not config.TELEGRAM_CHAT_ID:
        sys.exit("🔒 Falta TELEGRAM_CHAT_ID: el bot se bloqueó para impedir acceso público.")
    print(f"✅ Bot @{verificar_bot()} escuchando. Escríbele /analiza AAPL. Ctrl + C para detener.")
    preparar_polling()
    offset = None
    while True:
        try:
            for actualizacion in obtener_mensajes(offset=offset, espera=30):
                offset = actualizacion["update_id"] + 1
                if "message" in actualizacion:
                    try:
                        atender(actualizacion["message"])
                    except Exception as error:
                        print(f"⚠️ No se completó el mensaje: {type(error).__name__}")
        except (requests.RequestException, RuntimeError):
            print("Conexión inestable con Telegram; reintento en 5 s.")
            time.sleep(5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot detenido.")
