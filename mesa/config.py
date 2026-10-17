"""Configuración: lee las llaves desde variables de entorno o desde el archivo .env.

Nunca escribas una llave dentro del código. En tu computadora van en .env;
en GitHub van en Settings → Secrets and variables → Actions; en Colab, en el panel 🔑.
"""
import os

try:                                    # python-dotenv es opcional: si existe, carga .env
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _texto(nombre, defecto=""):
    return (os.environ.get(nombre) or defecto).strip()


def _bandera(nombre, defecto="0"):
    return _texto(nombre, defecto).lower() in ("1", "true", "si", "sí", "yes")


TELEGRAM_BOT_TOKEN   = _texto("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID     = _texto("TELEGRAM_CHAT_ID")        # tu chat; el bot solo atiende a este chat
ANTHROPIC_API_KEY    = _texto("ANTHROPIC_API_KEY")
ALPHAVANTAGE_API_KEY = _texto("ALPHAVANTAGE_API_KEY")

MODELO     = _texto("MODELO", "claude-haiku-5-5")        # modelo rápido y económico
MODO_CLASE = _bandera("MODO_CLASE", "1")                  # 1 = muestra cada entrega entre agentes

# Modo simulación: sin llaves de IA ni de datos. Se activa solo o con MODO_SIMULACION=1.
MODO_SIMULACION = _bandera("MODO_SIMULACION") or not (ANTHROPIC_API_KEY and ALPHAVANTAGE_API_KEY)

MAX_ANALISIS_POR_RUN = int(_texto("MAX_ANALISIS_POR_RUN", "3"))   # cuida la cuota de Alpha Vantage
CARPETA_SALIDAS = _texto("CARPETA_SALIDAS", "salidas")


def resumen():
    """Estado de la configuración sin revelar ningún valor secreto."""
    def estado(valor):
        return "✅ configurada" if valor else "⬜ vacía"
    return {
        "TELEGRAM_BOT_TOKEN": estado(TELEGRAM_BOT_TOKEN),
        "TELEGRAM_CHAT_ID": estado(TELEGRAM_CHAT_ID),
        "ANTHROPIC_API_KEY": estado(ANTHROPIC_API_KEY),
        "ALPHAVANTAGE_API_KEY": estado(ALPHAVANTAGE_API_KEY),
        "MODELO": MODELO,
        "MODO_SIMULACION": "sí" if MODO_SIMULACION else "no (datos y agentes reales)",
    }
