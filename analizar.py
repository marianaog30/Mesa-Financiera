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

    print("\n" + "=" * 60 + "\nNOTA FINAL (Vera · Agente 3)\n" + "=" * 60)
    print(resultado["entrega_3_nota"])
    if args.telegram:
        from mesa.telegram_io import enviar
        enviar(config.TELEGRAM_CHAT_ID, resultado["entrega_3_nota"])
    print(f"\n💾 Evidencia guardada en: {resultado['archivo']}")


if __name__ == "__main__":
    main()
