"""Ejecuta la cadena de 3 agentes desde la terminal (también lo usan Claude Code, Codex y GitHub Actions).

Ejemplos:
  python analizar.py AAPL                 → muestra todo en la terminal
  python analizar.py AAPL --simulacion    → sin llaves, con datos ficticios
  python analizar.py AAPL --telegram      → además envía cada etapa a tu chat de Telegram
"""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description="Mesa Financiera: Batuta dirige a Iris → Euler → Vera")
    parser.add_argument("ticker", help="Clave de la acción, por ejemplo AAPL")
    parser.add_argument("--simulacion", action="store_true", help="No usa llaves: datos y agentes simulados")
    parser.add_argument("--telegram", action="store_true", help="Envía el avance y la nota a TELEGRAM_CHAT_ID")
    args = parser.parse_args()

    if args.simulacion:
        os.environ["MODO_SIMULACION"] = "1"          # debe fijarse antes de importar la configuración

    from mesa import config
    from mesa.agentes import DatosAlphaVantageError
    from mesa.pipeline import pipeline

    avisar = print
    if args.telegram:
        from mesa.telegram_io import enviar
        if not config.TELEGRAM_CHAT_ID:
            sys.exit("❌ Falta TELEGRAM_CHAT_ID. Ejecuta primero: python obtener_chat_id.py")

        def avisar(texto):
            print(texto)
            enviar(config.TELEGRAM_CHAT_ID, texto)

    try:
        resultado = pipeline(args.ticker, avisar=avisar)
    except ValueError as error:
        sys.exit(f"❌ {error}")
    except DatosAlphaVantageError as error:
        mensajes = {
            "cuota_diaria": "Alpha Vantage alcanzó la cuota diaria de la llave gratuita.",
            "llave_no_valida": "Alpha Vantage rechazó la llave configurada.",
            "acceso_premium": "Alpha Vantage indicó que la consulta requiere acceso premium.",
            "solicitud_invalida": "Alpha Vantage rechazó los parámetros de la consulta.",
            "respuesta_sin_serie": "Alpha Vantage respondió, pero no entregó la serie diaria.",
            "conexion_o_respuesta": "No fue posible obtener una respuesta utilizable de Alpha Vantage.",
        }
        mensaje = f"⚠️ {mensajes.get(error.codigo, mensajes['conexion_o_respuesta'])}"
        if args.telegram:
            try:
                enviar(config.TELEGRAM_CHAT_ID, mensaje)
            except Exception:
                pass
        sys.exit(f"❌ {mensaje}")
    except Exception as error:
        mensaje = (f"⚠️ No pude completar el análisis ({type(error).__name__}). "
                   "Revisa las llaves y el saldo de las APIs; después intenta de nuevo.")
        if args.telegram:
            try:
                enviar(config.TELEGRAM_CHAT_ID, mensaje)
            except Exception:
                pass
        sys.exit(f"❌ {mensaje}")

    print("\n" + "=" * 60 + "\nNOTA FINAL (Vera · Agente 3)\n" + "=" * 60)
    print(resultado["entrega_3_nota"])
    if args.telegram:
        from mesa.telegram_io import enviar
        enviar(config.TELEGRAM_CHAT_ID, resultado["entrega_3_nota"])
    print(f"\n💾 Evidencia guardada en: {resultado['archivo']}")


if __name__ == "__main__":
    main()
