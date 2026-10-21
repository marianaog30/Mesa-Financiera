"""Comunicación con Telegram mediante la Bot API (solo peticiones HTTP, sin librerías extra)."""
import requests

from . import config

LIMITE_MENSAJE = 4000          # Telegram acepta hasta 4096 caracteres por mensaje


def _url(metodo):
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("Falta TELEGRAM_BOT_TOKEN (créalo con @BotFather).")
    return f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/{metodo}"


def _solicitar(metodo, verbo="get", timeout=20, **kwargs):
    """Llama a Telegram sin permitir que el token aparezca en una excepción o registro."""
    try:
        peticion = requests.post if verbo == "post" else requests.get
        respuesta = peticion(_url(metodo), timeout=timeout, **kwargs)
        respuesta.raise_for_status()
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        raise RuntimeError(f"Telegram no respondió correctamente ({metodo}).") from None
    if not isinstance(datos, dict) or not datos.get("ok"):
        descripcion = datos.get("description") if isinstance(datos, dict) else "respuesta inválida"
        if config.TELEGRAM_BOT_TOKEN:
            descripcion = str(descripcion).replace(config.TELEGRAM_BOT_TOKEN, "[SECRETO OCULTO]")
        raise RuntimeError(f"Telegram rechazó {metodo}: {descripcion}")
    return datos


def enviar(chat_id, texto):
    return _solicitar("sendMessage", verbo="post",
                      data={"chat_id": chat_id, "text": texto[:LIMITE_MENSAJE]})


def verificar_bot():
    """Devuelve el @usuario del bot o lanza un error claro si el token es inválido."""
    datos = _solicitar("getMe")
    return datos["result"]["username"]


def preparar_polling():
    """Quita un webhook previo; si existe, getUpdates no funciona."""
    _solicitar("deleteWebhook")


def obtener_mensajes(offset=None, espera=0):
    """Mensajes pendientes. Telegram los guarda hasta 24 h si nadie los lee."""
    parametros = {"timeout": espera}
    if offset is not None:
        parametros["offset"] = offset
    datos = _solicitar("getUpdates", params=parametros, timeout=espera + 15)
    return datos["result"]


def confirmar_leidos(ultimo_update_id):
    """Marca como leídos todos los mensajes hasta ese id, para no procesarlos dos veces."""
    obtener_mensajes(offset=ultimo_update_id + 1)


def chat_autorizado(chat_id):
    """Falla de forma cerrada: sin chat configurado, nadie puede usar el bot."""
    return bool(config.TELEGRAM_CHAT_ID) and str(chat_id) == config.TELEGRAM_CHAT_ID
