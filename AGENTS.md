# Instrucciones para agentes de programación (Codex, Claude Code y otros)

Este repositorio es una **actividad educativa para principiantes** del diplomado de la Dra. Elda C. Morales:
un ecosistema de **3 agentes financieros** que se pasan el trabajo en cadena y se controlan desde Telegram.

```
Telegram /analiza AAPL ─► Batuta · Orquestador (mesa/pipeline.py)
   ├─ Iris  · Recolectora  (Agente 1: Claude + MCP de Alpha Vantage) ─► ficha JSON
   ├─ Euler · Analista     (Agente 2: Python calcula, Claude interpreta) ─► análisis JSON
   └─ Vera  · Comunicadora (Agente 3: Claude redacta) ─► nota final en Telegram
```

Usa siempre estos nombres (Batuta, Iris, Euler, Vera) al explicar el sistema: coinciden con el mockup y con las guías.

## Cómo hablar con la persona usuaria
- Responde en **español**, con lenguaje sencillo: la persona está aprendiendo.
- Antes de cada comando di en una línea qué va a hacer y qué debe ver al terminar.
- Si algo falla, explica la causa probable y el siguiente paso; no pegues trazas largas sin explicarlas.

## Reglas de seguridad (obligatorias)
1. **Nunca** imprimas, copies ni subas el valor de una llave. Para revisar llaves usa `python verificar_configuracion.py`, que solo dice si existen.
2. **Nunca** agregues `.env` a git ni escribas llaves dentro del código.
3. El modo real gasta cuota (Alpha Vantage gratuito: 25 consultas al día) y saldo de la API de Claude.
   **Pregunta antes** de ejecutar sin `--simulacion` más de una vez.
4. No cambies la regla de oro: los cálculos se hacen en Python (`calcular_indicadores`), no en el prompt.
5. Toda nota final debe terminar con: "Nota educativa, no es recomendación de inversión."

## Comandos
| Para qué | Comando |
|---|---|
| Instalar | `pip install -r requirements.txt pytest` |
| Pruebas (sin llaves) | `pytest -q` → debe decir `20 passed` o más |
| Cadena en simulación | `python analizar.py AAPL --simulacion` |
| Revisar configuración | `python verificar_configuracion.py` (`--mcp` gasta 1 consulta) |
| Cadena real | `python analizar.py AAPL` |
| Cadena real + Telegram | `python analizar.py AAPL --telegram` |
| Saber el chat_id | `python obtener_chat_id.py` (antes escribe "hola" al bot) |
| Bot en vivo | `python bot_continuo.py` (Ctrl + C para detener) |

Las llaves se leen de variables de entorno o del archivo `.env` (plantilla: `.env.example`).
Si faltan `ANTHROPIC_API_KEY` o `ALPHAVANTAGE_API_KEY`, el sistema entra solo en **modo simulación**.

## Rutina "ejecuta la actividad"
Cuando te pidan ejecutar o probar la actividad, sigue este orden y reporta cada resultado:
1. Instala dependencias y corre `pytest -q`.
2. Corre `python analizar.py AAPL --simulacion` y muestra las entregas 1→2 y 2→3.
3. Corre `python verificar_configuracion.py`. Si hay llaves, pregunta si desea el modo real.
4. En modo real, corre `python analizar.py <TICKER>` y confirma que la fuente diga "Alpha Vantage vía MCP".
5. Indica dónde quedó la evidencia (`salidas/*.json`) y qué capturas tomar para la rúbrica.

## Estructura
- `mesa/config.py` llaves y modos · `mesa/agentes.py` los 3 agentes · `mesa/pipeline.py` el orquestador
- `mesa/telegram_io.py` Bot API · `mesa/comandos.py` interpreta `/analiza`
- `revisar_telegram.py` lo usa GitHub Actions cada 10 minutos (funciona con la computadora apagada)
- `.github/workflows/` automatizaciones · `tests/` pruebas en simulación
