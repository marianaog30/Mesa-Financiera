"""Muestra el chat_id de tu conversación con el bot.

Pasos: 1) abre tu bot en Telegram y escríbele "hola"; 2) ejecuta: python obtener_chat_id.py
Copia el número en TELEGRAM_CHAT_ID (archivo .env o Secret de GitHub).
"""
import sys

from mesa.telegram_io import obtener_mensajes, preparar_polling, verificar_bot


def main():
    try:
        print(f"Bot: @{verificar_bot()}")
    except RuntimeError as error:
        sys.exit(f"❌ {error}")
    preparar_polling()
    chats = {}
    for actualizacion in obtener_mensajes():
        chat = (actualizacion.get("message") or {}).get("chat")
        if chat:
            chats[chat["id"]] = chat.get("first_name") or chat.get("title") or "sin nombre"
    if not chats:
        sys.exit("📭 No encontré mensajes. Escríbele 'hola' a tu bot y vuelve a ejecutar.")
    for chat_id, nombre in chats.items():
        print(f"👤 {nombre} → TELEGRAM_CHAT_ID={chat_id}")


if __name__ == "__main__":
    main()
