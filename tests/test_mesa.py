"""Pruebas en modo simulación: verifican la cadena sin llaves ni internet.  Ejecutar: pytest -q"""
import json
import os
from types import SimpleNamespace

import pytest

os.environ["MODO_SIMULACION"] = "1"

from mesa import agentes, config, pipeline as pl          # noqa: E402
from mesa import comandos, telegram_io                     # noqa: E402


@pytest.fixture(autouse=True)
def simulacion(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "MODO_SIMULACION", True)
    monkeypatch.setattr(config, "CARPETA_SALIDAS", str(tmp_path))


def test_formula_posicion_rango_52_semanas():
    ind = agentes.calcular_indicadores({"precio": "250.5", "max_52s": "300", "min_52s": "200", "beta": "0.7"})
    assert ind["posicion_rango_52s_pct"] == 50.5          # (250.5-200)/(300-200)*100
    assert ind["semaforo_beta"].startswith("🟢")


@pytest.mark.parametrize("beta, color", [(0.5, "🟢"), (0.8, "🟡"), (1.2, "🟡"), (1.3, "🔴"), (None, "⚪")])
def test_semaforo_beta(beta, color):
    assert agentes.calcular_indicadores({"beta": beta})["semaforo_beta"].startswith(color)


def test_datos_faltantes_no_rompen_el_calculo():
    ind = agentes.calcular_indicadores({"precio": None, "max_52s": "100", "min_52s": "100"})
    assert ind["posicion_rango_52s_pct"] is None


def test_euler_es_esceptico_constructivo_tambien_en_simulacion():
    assert "escéptico constructivo" in agentes.PROMPT_ANALISTA
    lectura = agentes.lectura_simulada(agentes.calcular_indicadores({}))
    pregunta = lectura["pregunta_para_investigar"]
    assert "confirmar o contradecir" in pregunta


def test_extraer_json_con_texto_alrededor():
    assert agentes.extraer_json('Aquí tienes: {"a": 1} listo')["a"] == 1
    with pytest.raises(ValueError):
        agentes.extraer_json("sin json")


def test_openai_responses_configura_mcp_sin_llamada_real(monkeypatch):
    llamadas = []

    class ResponsesFalsas:
        def create(self, **kwargs):
            llamadas.append(kwargs)
            return SimpleNamespace(
                output_text='{"estado":"consultado"}',
                output=[SimpleNamespace(type="mcp_call", name="TIME_SERIES_DAILY", output='{"ok":true}')],
            )

    cliente_falso = SimpleNamespace(responses=ResponsesFalsas())
    monkeypatch.setattr(agentes, "_cliente_openai", lambda: cliente_falso)
    monkeypatch.setattr(config, "ALPHAVANTAGE_API_KEY", "llave-de-prueba")

    texto, herramientas, salidas = agentes.llamar_openai("instrucciones", "Acción: IBM", usar_mcp=True)

    assert texto == '{"estado":"consultado"}'
    assert herramientas == ["TIME_SERIES_DAILY"]
    assert salidas == ['{"ok":true}']
    assert llamadas[0]["instructions"] == "instrucciones"
    assert llamadas[0]["input"] == "Acción: IBM"
    assert llamadas[0]["max_output_tokens"] == 900
    assert llamadas[0]["tools"][0]["type"] == "mcp"
    assert llamadas[0]["tools"][0]["server_label"] == "alphavantage"
    assert llamadas[0]["tools"][0]["server_url"] == "https://mcp.alphavantage.co/mcp"
    assert llamadas[0]["tools"][0]["authorization"] == "llave-de-prueba"
    assert llamadas[0]["tools"][0]["allowed_tools"] == ["TIME_SERIES_DAILY"]
    assert llamadas[0]["tools"][0]["require_approval"] == "never"


def test_serie_diaria_gratuita_produce_metricas_deterministas():
    serie = {}
    for dia in range(1, 61):
        fecha = f"2026-08-{dia:02d}" if dia <= 31 else f"2026-09-{dia - 31:02d}"
        cierre = 100 + dia
        serie[fecha] = {
            "1. open": str(cierre - 1), "2. high": str(cierre + 2),
            "3. low": str(cierre - 2), "4. close": str(cierre),
            "5. volume": str(1000 + dia),
        }

    ficha = agentes.ficha_desde_serie_diaria("TEST", serie)
    indicadores = agentes.calcular_indicadores(ficha)

    assert ficha["precio"] == 160
    assert ficha["fecha_dato"] == "2026-09-29"
    assert ficha["sesiones_disponibles"] == 60
    assert ficha["sma_20"] == 150.5
    assert ficha["sma_50"] == 135.5
    assert ficha["rsi_14"] == 100.0
    assert ficha["tipo_precio"].startswith("cierre diario")
    assert indicadores["tendencia_medias"].startswith("🟢")


def test_localiza_serie_en_salida_mcp_envuelta_y_en_rest(monkeypatch):
    serie = {
        "2026-10-19": {"1. open": "98", "2. high": "101", "3. low": "97",
                       "4. close": "100", "5. volume": "900"},
        "2026-10-20": {"1. open": "100", "2. high": "103", "3. low": "99",
                       "4. close": "102", "5. volume": "1000"},
    }
    salida = json.dumps({"content": [{"type": "text", "text": json.dumps({"Time Series (Daily)": serie})}]})
    assert agentes._buscar_serie_diaria([salida]) == serie

    class Respuesta:
        def raise_for_status(self):
            return None

        def json(self):
            return {"Time Series (Daily)": serie}

    monkeypatch.setattr(agentes.requests, "get", lambda *args, **kwargs: Respuesta())
    assert agentes.consultar_serie_diaria_rest("TEST") == serie

    monkeypatch.setattr(config, "MODO_SIMULACION", False)
    monkeypatch.setattr(
        agentes, "llamar_openai", lambda *args, **kwargs: ('{"estado":"consultado"}', [], [])
    )
    ficha, herramientas = agentes.agente_recolector("TEST")
    assert ficha["canal_datos"] == "REST"
    assert ficha["precio"] == 102
    assert herramientas == []


@pytest.mark.parametrize("entrada, esperado", [(" aapl ", "AAPL"), ("brk.b", "BRK.B")])
def test_ticker_valido(entrada, esperado):
    assert pl.normalizar_ticker(entrada) == esperado


@pytest.mark.parametrize("entrada", ["", "AAPL; rm -rf", "ACCIONMUYLARGAXYZ"])
def test_ticker_invalido(entrada):
    with pytest.raises(ValueError):
        pl.normalizar_ticker(entrada)


def test_cadena_completa_output_es_input():
    avisos = []
    r = pl.pipeline("msft", avisar=avisos.append)
    assert r["entrega_2_analisis"]["ficha"] == r["entrega_1_ficha"]       # 1 → 2
    assert r["entrega_1_ficha"]["ticker"] in r["entrega_3_nota"]          # 2 → 3
    assert agentes.DESCARGO in r["entrega_3_nota"]
    assert any("Entrega 1→2" in a for a in avisos) and any("Entrega 2→3" in a for a in avisos)
    with open(r["archivo"], encoding="utf-8") as f:
        assert json.load(f)["ticker"] == "MSFT"


def test_modo_real_no_sustituye_fallo_de_datos_con_demo(monkeypatch):
    monkeypatch.setattr(config, "MODO_SIMULACION", False)

    def falla(*args, **kwargs):
        raise ConnectionError("sin red")
    monkeypatch.setattr(agentes, "llamar_openai", falla)
    monkeypatch.setattr(agentes, "consultar_serie_diaria_rest", falla)
    with pytest.raises(agentes.DatosAlphaVantageError) as error:
        agentes.agente_recolector("AAPL")
    assert error.value.codigo == "conexion_o_respuesta"


def test_agentes_reales_encadenan_con_openai_simulado(monkeypatch):
    """Imita las respuestas de OpenAI para revisar el camino 'real' sin gastar llaves."""
    monkeypatch.setattr(config, "MODO_SIMULACION", False)

    serie = {}
    for dia in range(1, 61):
        fecha = f"2026-08-{dia:02d}" if dia <= 31 else f"2026-09-{dia - 31:02d}"
        cierre = 200 + dia
        serie[fecha] = {"1. open": str(cierre - 1), "2. high": str(cierre + 2),
                        "3. low": str(cierre - 2), "4. close": str(cierre), "5. volume": "1000"}

    def openai_falso(system, mensaje, usar_mcp=False, max_tokens=900):
        if usar_mcp:
            return '{"estado":"consultado"}', ["TIME_SERIES_DAILY"], [
                json.dumps({"Time Series (Daily)": serie})
            ]
        if "Analista" in system:
            datos = json.loads(mensaje)
            assert datos["indicadores"]["tendencia_medias"].startswith("🟢")
            return ('{"lectura_precio":"a","lectura_tendencia":"b","lectura_riesgo":"c",'
                    '"lectura_volumen":"d","pregunta_para_investigar":"e"}', [], [])
        assert '"lectura_precio": "a"' in mensaje                           # recibió la entrega 2
        return "IBM: nota sin descargo", [], []

    monkeypatch.setattr(agentes, "llamar_openai", openai_falso)
    r = pl.pipeline("IBM", avisar=lambda t: None)
    assert r["herramientas_mcp"] == ["TIME_SERIES_DAILY"]
    assert "datos gratuitos" in r["entrega_1_ficha"]["fuente"]
    assert r["entrega_3_nota"].endswith(agentes.DESCARGO)                   # el descargo se garantiza


def test_bot_falla_cerrado_e_ignora_chats_ajenos(monkeypatch):
    enviados = []
    monkeypatch.setattr(comandos, "enviar", lambda chat, texto: enviados.append((chat, texto)))
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "")
    assert comandos.atender({"chat": {"id": 111}, "text": "/analiza AAPL"}) is None
    assert enviados == []
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "111")
    assert comandos.atender({"chat": {"id": 999}, "text": "/analiza AAPL"}) is None
    assert enviados == []
    comandos.atender({"chat": {"id": 111}, "text": "hola"})
    assert "Mesa Financiera" in enviados[-1][1]
    r = comandos.atender({"chat": {"id": 111}, "text": "/analiza aapl"})
    assert r["ticker"] == "AAPL" and agentes.DESCARGO in enviados[-1][1]


def test_error_de_telegram_no_revela_el_token(monkeypatch):
    token = "123456789:secreto-que-no-debe-aparecer"
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", token)

    def falla(*args, **kwargs):
        raise telegram_io.requests.ConnectionError(f"falló https://api.telegram.org/bot{token}/getMe")

    monkeypatch.setattr(telegram_io.requests, "get", falla)
    with pytest.raises(RuntimeError) as error:
        telegram_io.verificar_bot()
    assert token not in str(error.value)


def test_revision_de_github_actions_atiende_y_confirma(monkeypatch):
    """Simula la corrida de GitHub Actions: 4 mensajes pendientes, límite de 3 por revisión."""
    import revisar_telegram as rt
    pendientes = [{"update_id": i, "message": {"chat": {"id": 111}, "text": t}}
                  for i, t in enumerate(["/analiza AAPL", "hola", "/analiza MSFT", "/analiza NVDA"], start=10)]
    confirmados, enviados = [], []
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(config, "MAX_ANALISIS_POR_RUN", 3)
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "token-de-prueba")
    monkeypatch.setattr(rt, "verificar_bot", lambda: "bot_prueba")
    monkeypatch.setattr(rt, "preparar_polling", lambda: None)
    monkeypatch.setattr(rt, "obtener_mensajes", lambda: pendientes)
    monkeypatch.setattr(rt, "confirmar_leidos", confirmados.append)
    monkeypatch.setattr(comandos, "enviar", lambda chat, texto: enviados.append(texto))
    rt.main()
    assert confirmados == [10, 11, 12]                      # NVDA queda para la siguiente revisión
    assert sum(agentes.DESCARGO in t for t in enviados) == 2  # AAPL y MSFT recibieron su nota


def test_revision_sin_token_termina_sin_error(monkeypatch, capsys):
    """Una copia de la plantilla sin Secrets no debe marcar error en Actions cada 8 minutos."""
    import revisar_telegram as rt
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    rt.main()
    assert "nada que revisar" in capsys.readouterr().out


def test_revision_sin_chat_id_se_bloquea(monkeypatch, capsys):
    import revisar_telegram as rt
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "token-de-prueba")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "")
    rt.main()
    assert "bloqueada por seguridad" in capsys.readouterr().out


def test_cli_avisa_en_telegram_si_openai_falla_sin_revelar_detalles(monkeypatch):
    import analizar

    enviados = []
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "111")
    monkeypatch.setattr(telegram_io, "enviar", lambda chat, texto: enviados.append(texto))
    monkeypatch.setattr(pl, "pipeline", lambda *args, **kwargs: (_ for _ in ()).throw(
        RuntimeError("detalle sensible que no debe salir")
    ))
    monkeypatch.setattr(os.sys, "argv", ["analizar.py", "AAPL", "--telegram"])

    with pytest.raises(SystemExit) as salida:
        analizar.main()

    assert "RuntimeError" in enviados[-1]
    assert "detalle sensible" not in enviados[-1]
    assert "detalle sensible" not in str(salida.value)


def test_los_agentes_se_presentan_con_su_nombre():
    """Los nombres del mockup (Batuta, Iris, Euler, Vera) aparecen en Telegram."""
    avisos = []
    r = pl.pipeline("AAPL", avisar=avisos.append)
    texto = "\n".join(avisos)
    for nombre in ("Batuta", "Iris", "Euler", "Vera"):
        assert nombre in texto
    assert r["entrega_3_nota"].startswith(agentes.FIRMA_VERA)
