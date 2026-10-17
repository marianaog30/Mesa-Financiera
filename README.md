# Mesa Financiera en Telegram 📊🤖

Actividad del diplomado · **Dra. Elda C. Morales**

Un ecosistema de **tres agentes de IA** que trabajan en cadena: el resultado de uno es la entrada del siguiente.
Tú das la orden desde **Telegram**, **Batuta** (el orquestador) dirige y tres especialistas hacen el trabajo:

| Agente | Personalidad | Qué hace |
|---|---|---|
| **Iris** · La Recolectora | Curiosa y meticulosa; jamás inventa un dato | Consulta datos reales de Alpha Vantage por MCP |
| **Euler** · El Analista | Riguroso con los números | Python calcula; Claude interpreta |
| **Vera** · La Comunicadora | Clara, breve y honesta | Redacta la nota final para Telegram |

```
Tú en Telegram: /analiza AAPL
        │
        ▼
 Batuta · Orquestador (mesa/pipeline.py)
        │
        ├─► Iris  · Recolectora ── consulta Alpha Vantage por MCP ──► ficha JSON
        ├─► Euler · Analista ───── Python calcula, Claude interpreta ─► análisis JSON
        └─► Vera  · Comunicadora ─ redacta la nota ───────────────────► mensaje en Telegram
```

## Paso cero: crea tu propia copia

👉 **[Usar esta plantilla](https://github.com/new?template_owner=eldamorales&template_name=mesa-financiera-telegram)**
(o el botón verde **Use this template → Create a new repository**). Elige tu usuario, visibilidad **Public** y pulsa *Create repository*.

Tu copia incluye todo, también la carpeta oculta `.github` con las automatizaciones. Ahí guardarás tus llaves y tus cambios.

## Elige tu ruta

| Ruta | Cómo empezar | ¿Computadora encendida? |
|---|---|---|
| **A · Google Colab** | [Abrir el notebook en Colab](https://colab.research.google.com/github/eldamorales/mesa-financiera-telegram/blob/main/notebook/Mesa_Financiera_Telegram.ipynb) | Sí, con la pestaña abierta |
| **B · GitHub Actions** | En tu copia: Settings → Secrets → Actions, y luego Actions → *mesa-financiera* → Run workflow | **No** |
| **C · Claude Code** | claude.ai/code con tu copia, o `claude` en la terminal | No, en la versión web |
| **D · Codex** | Codex en la nube o la CLI; lee `AGENTS.md` | No, en la nube |
| **E · Codespaces o clonar** | En tu copia: **Code → Codespaces → Create codespace on main** | Codespaces: no, mientras lo usas |

Las instrucciones paso a paso están en [`docs/`](docs/): Guía del estudiante y Guía del docente con rúbrica.

## Empezar en 1 minuto, sin llaves
```bash
pip install -r requirements.txt pytest
pytest -q                               # 20 passed
python analizar.py AAPL --simulacion    # la cadena completa con datos ficticios
```

## Clonar en tu computadora (Ruta E)
```bash
git clone https://github.com/TU_USUARIO/mesa-financiera-telegram.git
cd mesa-financiera-telegram
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt pytest
cp .env.example .env                                   # abre .env y pega tus llaves
```

## Llaves necesarias para el modo real
| Secreto | Dónde se obtiene |
|---|---|
| `TELEGRAM_BOT_TOKEN` | @BotFather en Telegram |
| `TELEGRAM_CHAT_ID` | `python obtener_chat_id.py` |
| `ANTHROPIC_API_KEY` | Claude Console (la entrega la docente) |
| `ALPHAVANTAGE_API_KEY` | https://www.alphavantage.co/support/#api-key (gratis, 25 consultas al día) |

Dónde guardarlas, según la ruta: **Colab** → panel 🔑 · **Actions** → Settings → Secrets and variables → Actions ·
**Codespaces** → tu perfil → Settings → Codespaces → Codespaces secrets · **Tu computadora** → archivo `.env`.
Nunca las escribas en el código ni las subas a GitHub.

> Material educativo. Las notas que generan los agentes **no son recomendaciones de inversión**.
