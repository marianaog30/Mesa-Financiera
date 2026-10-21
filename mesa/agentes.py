"""Los tres agentes de la Mesa Financiera.

  Iris  · La Recolectora  (Agente 1) → consulta Alpha Vantage por MCP y entrega una FICHA (JSON)
  Euler · El Analista     (Agente 2) → recibe la ficha, Python calcula y OpenAI interpreta → ANÁLISIS (JSON)
  Vera  · La Comunicadora (Agente 3) → recibe el análisis y redacta la NOTA final para Telegram
  (Batuta, el orquestador que los dirige, vive en mesa/pipeline.py)

Regla de oro: los números los calcula el código; la IA solo interpreta.
"""
import json
import math
import re
import statistics

from . import config

DESCARGO = "Nota educativa, no es recomendación de inversión."
FIRMA_VERA = "✍️ Vera · Comunicadora"

# ----------------------------------------------------------------------
# Conexión con OpenAI (solo se usa fuera del modo simulación)
# ----------------------------------------------------------------------
_cliente = None


def _cliente_openai():
    global _cliente
    if _cliente is None:
        from openai import OpenAI
        _cliente = OpenAI(api_key=config.OPEN_API_KEY)
    return _cliente


def llamar_openai(system, mensaje, usar_mcp=False, max_tokens=900):
    """Devuelve texto, nombres de herramientas MCP y sus salidas originales."""
    base = dict(model=config.MODELO, max_output_tokens=max_tokens,
                instructions=system, input=mensaje)
    cliente = _cliente_openai()
    if usar_mcp:
        respuesta = cliente.responses.create(
            **base,
            tools=[{
                "type": "mcp",
                "server_label": "alphavantage",
                "server_description": "Datos bursátiles de Alpha Vantage para una actividad educativa.",
                "server_url": "https://mcp.alphavantage.co/mcp",
                "authorization": config.ALPHAVANTAGE_API_KEY,
                "require_approval": "never",
                "allowed_tools": ["TIME_SERIES_DAILY"],
            }],
        )
    else:
        respuesta = cliente.responses.create(**base)
    texto = (respuesta.output_text or "").strip()
    herramientas = [
        elemento.name
        for elemento in respuesta.output
        if elemento.type == "mcp_call" and getattr(elemento, "name", None)
    ]
    salidas_mcp = [
        elemento.output
        for elemento in respuesta.output
        if elemento.type == "mcp_call" and getattr(elemento, "output", None)
    ]
    return texto, herramientas, salidas_mcp


def extraer_json(texto):
    """Recupera el objeto JSON de un texto (a veces el modelo agrega palabras alrededor)."""
    inicio, fin = texto.find("{"), texto.rfind("}")
    if inicio == -1 or fin <= inicio:
        raise ValueError("El agente no devolvió JSON")
    return json.loads(texto[inicio:fin + 1])


def a_numero(valor):
    """Convierte '123.4', '-0.8%' o '1,234' en número; si no se puede, None."""
    try:
        return float(str(valor).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return None


def _buscar_serie_diaria(objeto):
    """Localiza la serie diaria aunque el servidor MCP la envuelva en bloques de contenido."""
    if isinstance(objeto, str):
        texto = objeto.strip().strip("`")
        try:
            return _buscar_serie_diaria(json.loads(texto))
        except (json.JSONDecodeError, TypeError):
            inicio, fin = texto.find("{"), texto.rfind("}")
            if inicio != -1 and fin > inicio:
                try:
                    return _buscar_serie_diaria(json.loads(texto[inicio:fin + 1]))
                except json.JSONDecodeError:
                    return None
        return None
    if isinstance(objeto, list):
        for elemento in objeto:
            encontrado = _buscar_serie_diaria(elemento)
            if encontrado:
                return encontrado
        return None
    if not isinstance(objeto, dict):
        return None
    for clave, valor in objeto.items():
        if "time series" in str(clave).lower() and "daily" in str(clave).lower() and isinstance(valor, dict):
            return valor
    fechas = [clave for clave in objeto if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(clave))]
    if fechas and isinstance(objeto[fechas[0]], dict):
        return objeto
    for valor in objeto.values():
        encontrado = _buscar_serie_diaria(valor)
        if encontrado:
            return encontrado
    return None


def _campo_alpha(fila, nombre):
    for clave, valor in fila.items():
        if str(clave).lower().strip().endswith(nombre):
            return a_numero(valor)
    return None


def _rsi_wilder(cierres, periodo=14):
    if len(cierres) <= periodo:
        return None
    cambios = [actual - anterior for anterior, actual in zip(cierres, cierres[1:])]
    ganancias = [max(cambio, 0) for cambio in cambios]
    perdidas = [max(-cambio, 0) for cambio in cambios]
    promedio_ganancia = sum(ganancias[:periodo]) / periodo
    promedio_perdida = sum(perdidas[:periodo]) / periodo
    for ganancia, perdida in zip(ganancias[periodo:], perdidas[periodo:]):
        promedio_ganancia = (promedio_ganancia * (periodo - 1) + ganancia) / periodo
        promedio_perdida = (promedio_perdida * (periodo - 1) + perdida) / periodo
    if promedio_perdida == 0:
        return 100.0
    fuerza = promedio_ganancia / promedio_perdida
    return round(100 - 100 / (1 + fuerza), 1)


def ficha_desde_serie_diaria(ticker, serie):
    """Convierte OHLCV diario gratuito en una ficha con métricas reproducibles."""
    filas = []
    for fecha in sorted(serie):
        fila = serie[fecha]
        if not isinstance(fila, dict):
            continue
        datos = {
            "fecha": fecha,
            "apertura": _campo_alpha(fila, "open"),
            "maximo": _campo_alpha(fila, "high"),
            "minimo": _campo_alpha(fila, "low"),
            "cierre": _campo_alpha(fila, "close"),
            "volumen": _campo_alpha(fila, "volume"),
        }
        if None not in (datos["maximo"], datos["minimo"], datos["cierre"]):
            filas.append(datos)
    if len(filas) < 2:
        raise ValueError("Alpha Vantage no devolvió suficientes sesiones diarias")

    cierres = [fila["cierre"] for fila in filas]
    retornos = [actual / anterior - 1 for anterior, actual in zip(cierres, cierres[1:]) if anterior]
    ultima, anterior = filas[-1], filas[-2]
    ultimas_20 = filas[-20:]
    maximos = [fila["maximo"] for fila in filas[-100:]]
    minimos = [fila["minimo"] for fila in filas[-100:]]
    volumenes_20 = [fila["volumen"] for fila in ultimas_20 if fila["volumen"] is not None]

    def promedio(valores):
        return round(sum(valores) / len(valores), 2) if valores else None

    volatilidad = None
    if len(retornos) >= 20:
        volatilidad = round(statistics.stdev(retornos[-20:]) * math.sqrt(252) * 100, 1)

    return {
        "ticker": ticker,
        "nombre": None,
        "sector": None,
        "precio": round(ultima["cierre"], 2),
        "tipo_precio": "cierre diario histórico; no es cotización en tiempo real",
        "cambio_pct": round((ultima["cierre"] / anterior["cierre"] - 1) * 100, 2),
        "fecha_dato": ultima["fecha"],
        "apertura": round(ultima["apertura"], 2) if ultima["apertura"] is not None else None,
        "maximo_dia": round(ultima["maximo"], 2),
        "minimo_dia": round(ultima["minimo"], 2),
        "volumen": round(ultima["volumen"]) if ultima["volumen"] is not None else None,
        "promedio_volumen_20d": round(promedio(volumenes_20)) if volumenes_20 else None,
        "max_100_sesiones": round(max(maximos), 2),
        "min_100_sesiones": round(min(minimos), 2),
        "sma_20": promedio(cierres[-20:]) if len(cierres) >= 20 else None,
        "sma_50": promedio(cierres[-50:]) if len(cierres) >= 50 else None,
        "rsi_14": _rsi_wilder(cierres),
        "retorno_20d_pct": round((cierres[-1] / cierres[-21] - 1) * 100, 2) if len(cierres) >= 21 else None,
        "volatilidad_20d_anual_pct": volatilidad,
        "sesiones_disponibles": len(filas),
        "pe_ratio": None,
        "beta": None,
        "max_52s": None,
        "min_52s": None,
        "cap_mercado_usd": None,
        "fuente": "Alpha Vantage TIME_SERIES_DAILY compact vía MCP (datos gratuitos)",
    }


# ----------------------------------------------------------------------
# IRIS · La Recolectora (Agente 1)
# ----------------------------------------------------------------------
PROMPT_RECOLECTOR = """Eres Iris, la Recolectora (Agente 1) de una mesa financiera educativa.
Tu personalidad: curiosa y meticulosa; jamás inventas un dato.
Tarea: obtener la serie diaria histórica de la acción indicada con Alpha Vantage.
Reglas:
- Haz exactamente 1 consulta con TIME_SERIES_DAILY y outputsize compact.
- No uses funciones premium ni afirmes que el dato es en tiempo real.
- El código leerá directamente la salida de la herramienta y hará todos los cálculos.
- Después de consultar responde solamente: {"estado":"consultado"}."""

DATOS_DEMO = {
    "nombre": "Empresa ficticia (simulación)", "sector": "Tecnología",
    "precio": 150.0, "cambio_pct": 1.2, "fecha_dato": "dato ficticio",
    "pe_ratio": None, "beta": None, "max_52s": None, "min_52s": None,
    "cap_mercado_usd": None, "max_100_sesiones": 180.0, "min_100_sesiones": 120.0,
    "sma_20": 148.0, "sma_50": 145.0, "rsi_14": 55.0, "retorno_20d_pct": 2.4,
    "volatilidad_20d_anual_pct": 24.0, "volumen": 1000000,
    "promedio_volumen_20d": 900000, "sesiones_disponibles": 100,
    "tipo_precio": "dato ficticio de cierre diario",
}


def ficha_demo(ticker, motivo):
    ficha = {"ticker": ticker, **DATOS_DEMO}
    ficha["fuente"] = f"DATOS DEMO, no son reales ({motivo})"
    return ficha


def agente_recolector(ticker):
    """Devuelve (ficha, herramientas_usadas)."""
    if config.MODO_SIMULACION:
        return ficha_demo(ticker, "modo simulación"), []
    try:
        _, herramientas, salidas = llamar_openai(
            PROMPT_RECOLECTOR, f"Acción: {ticker}", usar_mcp=True, max_tokens=200
        )
        serie = _buscar_serie_diaria(salidas)
        if not serie:
            raise ValueError("TIME_SERIES_DAILY no devolvió una serie utilizable")
        ficha = ficha_desde_serie_diaria(ticker, serie)
        return ficha, herramientas
    except Exception as error:                     # MCP caído, cuota agotada o JSON inválido
        return ficha_demo(ticker, f"MCP no disponible: {type(error).__name__}"), []


# ----------------------------------------------------------------------
# EULER · El Analista (Agente 2)
# ----------------------------------------------------------------------
def calcular_indicadores(ficha):
    """Cálculos deterministas (la IA no hace aritmética)."""
    # Estas claves antiguas se conservan anulables para no romper copias previas del proyecto;
    # la ruta gratuita actual no solicita datos de 52 semanas, beta ni P/E.
    precio, maximo, minimo = (a_numero(ficha.get(k)) for k in ("precio", "max_52s", "min_52s"))
    beta, pe = a_numero(ficha.get("beta")), a_numero(ficha.get("pe_ratio"))

    # Posición en el rango de 52 semanas: (P - min) / (max - min) × 100
    posicion = None
    if None not in (precio, maximo, minimo) and maximo > minimo:
        posicion = round((precio - minimo) / (maximo - minimo) * 100, 1)

    # Semáforo de beta (umbrales didácticos, no normativos)
    if beta is None:
        semaforo = "⚪ sin dato de beta"
    elif beta < 0.8:
        semaforo = "🟢 volatilidad baja"
    elif beta <= 1.2:
        semaforo = "🟡 volatilidad similar al mercado"
    else:
        semaforo = "🔴 volatilidad alta"

    precio_100, maximo_100, minimo_100 = (
        a_numero(ficha.get(k)) for k in ("precio", "max_100_sesiones", "min_100_sesiones")
    )
    posicion_100 = None
    if None not in (precio_100, maximo_100, minimo_100) and maximo_100 > minimo_100:
        posicion_100 = round((precio_100 - minimo_100) / (maximo_100 - minimo_100) * 100, 1)

    sma_20, sma_50 = a_numero(ficha.get("sma_20")), a_numero(ficha.get("sma_50"))
    if None not in (precio_100, sma_20, sma_50) and precio_100 > sma_20 > sma_50:
        tendencia = "🟢 cierre sobre SMA 20 y SMA 50"
    elif None not in (precio_100, sma_20, sma_50) and precio_100 < sma_20 < sma_50:
        tendencia = "🔴 cierre bajo SMA 20 y SMA 50"
    else:
        tendencia = "🟡 tendencia mixta o sin datos suficientes"

    rsi = a_numero(ficha.get("rsi_14"))
    if rsi is None:
        zona_rsi = "⚪ RSI no disponible"
    elif rsi > 70:
        zona_rsi = "🟠 RSI por encima de 70; posible sobrecompra, no señal automática"
    elif rsi < 30:
        zona_rsi = "🔵 RSI por debajo de 30; posible sobreventa, no señal automática"
    else:
        zona_rsi = "🟢 RSI entre 30 y 70"

    volatilidad = a_numero(ficha.get("volatilidad_20d_anual_pct"))
    if volatilidad is None:
        semaforo_volatilidad = "⚪ volatilidad no disponible"
    elif volatilidad < 20:
        semaforo_volatilidad = "🟢 volatilidad histórica baja"
    elif volatilidad <= 40:
        semaforo_volatilidad = "🟡 volatilidad histórica moderada"
    else:
        semaforo_volatilidad = "🔴 volatilidad histórica alta"

    volumen = a_numero(ficha.get("volumen"))
    volumen_promedio = a_numero(ficha.get("promedio_volumen_20d"))
    volumen_relativo = None
    if None not in (volumen, volumen_promedio) and volumen_promedio > 0:
        volumen_relativo = round(volumen / volumen_promedio, 2)

    return {
        "posicion_rango_52s_pct": posicion,
        "semaforo_beta": semaforo,
        "beta": beta,
        "pe_ratio": pe,
        "cambio_pct": a_numero(ficha.get("cambio_pct")),
        "posicion_rango_100_sesiones_pct": posicion_100,
        "tendencia_medias": tendencia,
        "zona_rsi_14": zona_rsi,
        "rsi_14": rsi,
        "retorno_20d_pct": a_numero(ficha.get("retorno_20d_pct")),
        "volatilidad_20d_anual_pct": volatilidad,
        "semaforo_volatilidad": semaforo_volatilidad,
        "volumen_relativo_20d": volumen_relativo,
    }


PROMPT_ANALISTA = """Eres Euler, el Analista (Agente 2). Recibes la ficha de Iris y unos indicadores ya calculados.
Tu personalidad: escéptico constructivo, riguroso con los números y paciente para explicarlos.
Cuestiona las interpretaciones apresuradas, distingue el dato de su interpretación y busca
una explicación alternativa antes de concluir. No seas alarmista ni lleves la contraria por sistema.
NO recalcules ni cambies cifras. Interprétalas para un principiante. El precio es el último cierre
diario histórico disponible, no una cotización en tiempo real. No hay P/E ni beta porque esas
funciones son premium; no los solicites ni los sustituyas con otras fuentes.
Responde SOLO con JSON con las claves:
  lectura_precio (1 frase), lectura_tendencia (1 frase sobre SMA y RSI),
  lectura_riesgo (1 frase sobre volatilidad histórica), lectura_volumen (1 frase),
  pregunta_para_investigar (1 pregunta que busque evidencia capaz de confirmar o contradecir la interpretación)"""


def lectura_simulada(ind):
    pos = ind["posicion_rango_100_sesiones_pct"]
    lectura_precio = ("No hay datos suficientes para ubicar el cierre en su rango observado." if pos is None else
                      f"El cierre está al {pos} % de su rango de hasta 100 sesiones "
                      "(0 % = mínimo, 100 % = máximo).")
    return {
        "lectura_precio": lectura_precio,
        "lectura_tendencia": ind["tendencia_medias"],
        "lectura_riesgo": ind["semaforo_volatilidad"],
        "lectura_volumen": f"Volumen relativo: {ind['volumen_relativo_20d']} veces el promedio de 20 sesiones.",
        "pregunta_para_investigar": (
            "¿Qué noticia o dato corporativo podría confirmar o contradecir este patrón de precio y volumen?"
        ),
    }


def agente_analista(ficha):
    indicadores = calcular_indicadores(ficha)
    if config.MODO_SIMULACION:
        lectura = lectura_simulada(indicadores)
    else:
        entrada = json.dumps({"ficha": ficha, "indicadores": indicadores}, ensure_ascii=False)
        texto, _, _ = llamar_openai(PROMPT_ANALISTA, entrada)
        try:
            lectura = extraer_json(texto)
        except ValueError:
            lectura = {"lectura_precio": texto[:300]}
    return {"ficha": ficha, "indicadores": indicadores, "lectura": lectura}


# ----------------------------------------------------------------------
# VERA · La Comunicadora (Agente 3)
# ----------------------------------------------------------------------
PROMPT_COMUNICADOR = f"""Eres Vera, la Comunicadora (Agente 3). Con el análisis de Euler, redacta una nota para Telegram.
Tu personalidad: clara, breve y honesta sobre los límites del análisis.
- Máximo 900 caracteres, español claro, 3 a 5 emojis como máximo.
- Estructura: título con ticker y fecha · último cierre y cambio · SMA 20/50 y RSI 14 ·
  volatilidad y volumen relativo · interpretación · pregunta para investigar.
- Aclara que es cierre diario histórico, no una cotización en tiempo real.
- Usa solo las cifras recibidas; si la fuente dice DEMO, adviértelo en la primera línea.
- Cierra SIEMPRE con: "{DESCARGO}"
Texto plano, sin Markdown."""


def nota_simulada(analisis):
    f, ind, lec = analisis["ficha"], analisis["indicadores"], analisis["lectura"]
    return (f"{FIRMA_VERA}\n⚠️ {f['fuente']}\n"
            f"📊 {f['ticker']} · {f['nombre']}\n"
            f"Cierre: {f['precio']} USD ({ind['cambio_pct']} % frente a la sesión previa)\n"
            f"Tendencia: {ind['tendencia_medias']} · RSI {ind['rsi_14']}\n"
            f"Riesgo: {ind['semaforo_volatilidad']}\n"
            f"{lec['lectura_precio']}\n"
            f"{lec['lectura_volumen']}\n"
            f"🔎 {lec['pregunta_para_investigar']}\n\n{DESCARGO}")


def agente_comunicador(analisis):
    if config.MODO_SIMULACION:
        return nota_simulada(analisis)
    texto, _, _ = llamar_openai(PROMPT_COMUNICADOR, json.dumps(analisis, ensure_ascii=False), max_tokens=600)
    if DESCARGO not in texto:                      # garantía aunque el modelo lo olvide
        texto += f"\n\n{DESCARGO}"
    return f"{FIRMA_VERA}\n{texto}"
