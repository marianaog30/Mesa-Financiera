"""Interpreta los mensajes que el alumno escribe en Telegram (lo comparten el bot continuo y GitHub Actions)."""
from .pipeline import normalizar_ticker, pipeline
from .telegram_io import chat_autorizado, enviar

AYUDA = ("🤖 Mesa Financiera de 3 agentes\n"
         "/analiza TICKER → ejemplo: /analiza AAPL\n"
         "Batuta dirige: Iris (datos por MCP) → Euler (análisis) → Vera (nota)\n"
         "Límite gratuito de Alpha Vantage: 25 consultas al día.")


def es_analisis(texto):
    return (texto or "").strip().lower().startswith("/analiza")


def atender(mensaje):
    """Procesa un mensaje de Telegram. Devuelve el resultado del pipeline o None."""
    chat_id = mensaje["chat"]["id"]
    texto = (mensaje.get("text") or "").strip()

    if not chat_autorizado(chat_id):
        enviar(chat_id, "Este bot es privado.")
        return None
    if not es_analisis(texto):
        enviar(chat_id, AYUDA)
        return None

    partes = texto.split()
    try:
        ticker = normalizar_ticker(partes[1] if len(partes) > 1 else "")
    except ValueError:
        enviar(chat_id, "Escribe un ticker válido. Ejemplo: /analiza MSFT")
        return None

    try:
        resultado = pipeline(ticker, avisar=lambda t: enviar(chat_id, t))
        enviar(chat_id, resultado["entrega_3_nota"])
        return resultado
    except Exception as error:
        enviar(chat_id, f"⚠️ No pude completar el análisis ({type(error).__name__}). "
                        "Revisa llaves y saldo, o intenta en unos minutos.")
        raise
