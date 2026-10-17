"""Revisión única de mensajes pendientes. Lo ejecuta GitHub Actions cada 10 minutos.

No necesita tu computadora encendida: lee los /analiza que escribiste en Telegram,
corre la cadena de agentes para cada uno, responde y termina.
"""
import sys

from mesa import config
from mesa.comandos import atender
from mesa.telegram_io import confirmar_leidos, obtener_mensajes, preparar_polling, verificar_bot


def main():
    print("Configuración:", config.resumen())
    if not config.TELEGRAM_BOT_TOKEN:
        # Copia de la plantilla sin Secrets: terminar en verde, sin correos de error cada 10 minutos.
        print("ℹ️ Sin TELEGRAM_BOT_TOKEN: nada que revisar. Agrega tus Secrets para activar el bot.")
        return
    try:
        print(f"Bot: @{verificar_bot()}")
    except RuntimeError as error:
        sys.exit(f"❌ {error}")

    preparar_polling()
    pendientes = obtener_mensajes()
    if not pendientes:
        print("📭 No hay mensajes nuevos. Fin.")
        return

    lote = pendientes[:config.MAX_ANALISIS_POR_RUN]          # el resto queda para la siguiente revisión
    print(f"📬 {len(pendientes)} mensaje(s) pendiente(s); se atenderán {len(lote)} en esta revisión.")
    for actualizacion in lote:
        mensaje = actualizacion.get("message")
        try:
            if mensaje:
                resultado = atender(mensaje)
                if resultado:
                    print(f"✅ {resultado['ticker']} atendido · evidencia: {resultado['archivo']}")
        except Exception as error:                           # un error no detiene a los demás
            print(f"⚠️ Error con el mensaje {actualizacion['update_id']}: {type(error).__name__}: {error}")
        finally:
            confirmar_leidos(actualizacion["update_id"])      # nunca se procesa dos veces


if __name__ == "__main__":
    main()
