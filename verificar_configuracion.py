"""Revisa que todo esté listo, sin mostrar el valor de ninguna llave.

  python verificar_configuracion.py           → revisa llaves y el token de Telegram
  python verificar_configuracion.py --mcp     → además prueba el MCP de Alpha Vantage (gasta 1 consulta)
"""
import sys

from mesa import config


def main():
    print("🔎 Estado de la configuración")
    for nombre, estado in config.resumen().items():
        print(f"  {nombre:<22} {estado}")

    errores = 0
    if config.TELEGRAM_BOT_TOKEN:
        try:
            from mesa.telegram_io import verificar_bot
            print(f"  Telegram                ✅ bot @{verificar_bot()} responde")
        except Exception as error:
            errores += 1
            print(f"  Telegram                ❌ {error}")

    if "--mcp" in sys.argv:
        if config.MODO_SIMULACION:
            print("  MCP Alpha Vantage       ⬜ omitido: faltan ANTHROPIC_API_KEY o ALPHAVANTAGE_API_KEY")
        else:
            from mesa.agentes import agente_recolector
            ficha, herramientas = agente_recolector("IBM")
            if ficha["fuente"].startswith("Alpha Vantage"):
                print(f"  MCP Alpha Vantage       ✅ respondió (herramientas: {', '.join(herramientas) or 'n/d'})")
            else:
                errores += 1
                print(f"  MCP Alpha Vantage       ❌ {ficha['fuente']}")

    if config.MODO_SIMULACION:
        print("\nℹ️  Estás en MODO SIMULACIÓN: todo funciona, pero con datos ficticios.")
    sys.exit(1 if errores else 0)


if __name__ == "__main__":
    main()
