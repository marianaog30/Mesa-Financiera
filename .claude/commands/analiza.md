---
description: Ejecuta la Mesa Financiera (Batuta dirige a Iris → Euler → Vera) para un ticker
argument-hint: TICKER [--simulacion] [--telegram]
---
Ejecuta la cadena de 3 agentes para: $ARGUMENTS

1. Si no se indicó ticker, usa AAPL.
2. Corre `python verificar_configuracion.py`. Si dice MODO SIMULACIÓN, avísalo y agrega `--simulacion`.
3. Corre `python analizar.py $ARGUMENTS`.
4. Explica en español sencillo, en este orden:
   - Qué entregó Iris, la Recolectora (ficha) y si la fuente fue "Alpha Vantage vía MCP" o datos DEMO.
   - Qué calculó Python dentro de Euler, el Analista: posición en el rango de 52 semanas = (precio − mínimo) / (máximo − mínimo) × 100, y el semáforo de beta.
   - La nota final de Vera, la Comunicadora.
5. Indica la ruta del archivo de evidencia en `salidas/`.
Nunca muestres el valor de ninguna llave.
