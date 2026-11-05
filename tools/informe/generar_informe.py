"""Genera docs/informe-resolucion.pdf: informe explicativo de la resolución del challenge.

Uso (desde la raíz del repo):
    .venv-tools/Scripts/python tools/informe/generar_informe.py

Toma los datos de git (commit, historial) y las capturas de docs/capturas/.
Los números de pruebas y mutantes se declaran en DATOS y deben coincidir con
docs/auditoria-pruebas.md y la captura 02/09.
"""
from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, PageBreak,
                                Paragraph, Preformatted, SimpleDocTemplate, Spacer, Table,
                                TableStyle)

RAIZ = Path(__file__).resolve().parents[2]
CAPTURAS = RAIZ / "docs" / "capturas"
SALIDA = RAIZ / "docs" / "informe-resolucion.pdf"

DATOS = {
    "pruebas": 148,
    "archivos_prueba": 11,
    "mutantes": "9/9",
    "modelo": "claude-opus-5-5 (Claude Opus 5.5)",
    "harness": "Claude Code 2.1.305 (extensión de VS Code, Windows 10)",
}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=RAIZ, capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()


# ----------------------------------------------------------------- estilos
def registrar_fuentes() -> tuple[str, str, str]:
    win = Path("C:/Windows/Fonts")
    try:
        pdfmetrics.registerFont(TTFont("Cuerpo", str(win / "calibri.ttf")))
        pdfmetrics.registerFont(TTFont("Cuerpo-B", str(win / "calibrib.ttf")))
        pdfmetrics.registerFont(TTFont("Cuerpo-I", str(win / "calibrii.ttf")))
        pdfmetrics.registerFont(TTFont("Mono", str(win / "consola.ttf")))
        addMapping("Cuerpo", 0, 0, "Cuerpo"); addMapping("Cuerpo", 1, 0, "Cuerpo-B")
        addMapping("Cuerpo", 0, 1, "Cuerpo-I"); addMapping("Cuerpo", 1, 1, "Cuerpo-B")
        return "Cuerpo", "Cuerpo-B", "Mono"
    except Exception:  # fuera de Windows: fuentes base de PDF
        return "Helvetica", "Helvetica-Bold", "Courier"


F, FB, FM = registrar_fuentes()
AZUL = colors.HexColor("#1F4E5A")
GRIS = colors.HexColor("#5B6770")
ss = getSampleStyleSheet()
E = {
    "p": ParagraphStyle("p", parent=ss["Normal"], fontName=F, fontSize=10.2, leading=14, spaceAfter=5),
    "h1": ParagraphStyle("h1", fontName=FB, fontSize=16, leading=20, textColor=AZUL, spaceBefore=4, spaceAfter=10),
    "h2": ParagraphStyle("h2", fontName=FB, fontSize=12.5, leading=16, textColor=AZUL, spaceBefore=10, spaceAfter=5),
    "celda": ParagraphStyle("celda", fontName=F, fontSize=8.6, leading=11),
    "pie": ParagraphStyle("pie", fontName=F, fontSize=8.6, leading=11, textColor=GRIS, alignment=TA_CENTER, spaceAfter=10),
    "codigo": ParagraphStyle("codigo", fontName=FM, fontSize=8, leading=10.5, backColor=colors.HexColor("#F2F4F5"),
                             borderPadding=6, spaceBefore=4, spaceAfter=8),
    "titulo": ParagraphStyle("titulo", fontName=FB, fontSize=24, leading=30, textColor=AZUL, alignment=TA_CENTER),
    "subtitulo": ParagraphStyle("sub", fontName=F, fontSize=13, leading=18, textColor=GRIS, alignment=TA_CENTER),
}
ANCHO = A4[0] - 4 * cm


def P(t): return Paragraph(t, E["p"])
def H1(t): return Paragraph(t, E["h1"])
def H2(t): return Paragraph(t, E["h2"])
def C(t): return f'<font face="{FM}" size="9">{t}</font>'


def lista(items):
    return ListFlowable([ListItem(P(i), leftIndent=12) for i in items],
                        bulletType="bullet", start="•", leftIndent=14)


def tabla(filas, anchos=None):
    datos = [[Paragraph(("<b>%s</b>" % c) if i == 0 else c, E["celda"]) for c in fila]
             for i, fila in enumerate(filas)]
    anchos = anchos or [ANCHO / len(filas[0])] * len(filas[0])
    t = Table(datos, colWidths=[a * ANCHO for a in anchos] if anchos and anchos[0] < 1.5 else anchos,
              repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#DCEBEE")),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#A9BEC3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [t, Spacer(1, 8)]


def captura(archivo, pie, comando):
    ruta = CAPTURAS / archivo
    if not ruta.exists():
        return [P(f"<i>[Falta la captura {archivo}: ejecutar tools/capturas/capturar.ps1]</i>")]
    from PIL import Image as PILImage
    with PILImage.open(ruta) as im:
        w, h = im.size
    ancho = ANCHO
    alto = ancho * h / w
    if alto > 17 * cm:
        alto = 17 * cm
        ancho = alto * w / h
    return [KeepTogether([
        Image(str(ruta), width=ancho, height=alto),
        Paragraph(f"<b>{archivo}</b> — {pie}<br/>Reproducir: {C(comando)}", E["pie"]),
    ])]


def pie_pagina(canvas, doc):
    canvas.saveState()
    canvas.setFont(F, 8)
    canvas.setFillColor(GRIS)
    canvas.drawString(2 * cm, 1.2 * cm, "Challenge IA — Sistema de reservas de laboratorio con agentes")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Página {doc.page}")
    canvas.restoreState()


# ----------------------------------------------------------------- contenido
def construir() -> list:
    commit = git("rev-parse", "--short", "HEAD")
    autor = git("log", "-1", "--format=%an")
    historial = [l.split(" ", 1) for l in git("log", "--reverse", "--format=%h %s").splitlines()]
    s: list = []

    # Portada
    s += [Spacer(1, 5 * cm), Paragraph("Desarrollo de un sistema de reservas con agentes", E["titulo"]),
          Spacer(1, 0.6 * cm), Paragraph("Informe de resolución — Challenge IA", E["subtitulo"]),
          Spacer(1, 2.5 * cm)]
    s += tabla([["Dato", "Valor"],
                ["Autor (git)", autor],
                ["Fecha del informe", date.today().isoformat()],
                ["Rama / commit base del informe", f"main / {commit}"],
                ["Agente", DATOS["harness"]],
                ["Modelo", DATOS["modelo"]],
                ["Lenguaje y almacenamiento", "Python 3.14 (stdlib) + SQLite · CLI · pytest 9.2.0"],
                ["Resultado", f"{DATOS['pruebas']} pruebas automáticas pasan · mutantes detectados {DATOS['mutantes']}"]],
               [0.32, 0.68])
    s += [Spacer(1, 1.5 * cm), P("<i>Este informe resume y enlaza la evidencia del repositorio. La fuente de verdad "
                                 "son los archivos versionados (README.md y docs/); las capturas son un complemento "
                                 "visual y no reemplazan las pruebas reproducibles.</i>"), PageBreak()]

    # Índice
    s += [H1("Contenido")]
    s += [lista(["1. Consigna y problema", "2. Especificación", "3. Solución técnica",
                 "4. Preparación del agente", "5. Tres episodios de delegación",
                 "6. Pruebas, auditoría y verificación", "7. Capturas de funcionamiento",
                 "8. Cómo reproducir", "9. Limitaciones y cumplimiento de la rúbrica",
                 "Anexo: historial de commits"]), PageBreak()]

    # 1
    s += [H1("1. Consigna y problema"),
          P("La consigna pide construir, <b>con un agente de programación que actúe sobre el repositorio con "
            "herramientas reales</b>, una solución local y verificable para la coordinación de un laboratorio "
            "que hoy registra pedidos en mensajes y una planilla. Dos fallas motivan el trabajo: la misma unidad "
            "se confirma para horarios superpuestos, y una cancelación sigue bloqueando el horario."),
          P("El inventario está fijo: cada ID es una unidad física distinta."),
          *tabla([["ID", "Equipo"], ["MIC-01", "Microscopio digital"], ["MIC-02", "Microscopio digital"],
                  ["OSC-01", "Osciloscopio"], ["MUL-01", "Multímetro"], ["FUE-01", "Fuente de alimentación"]],
                 [0.3, 0.7]),
          P("La entrega se evalúa por la evidencia del repositorio: especificación (25 %), preparación y uso del "
            "agente (25 %), funcionamiento y pruebas (30 %) y trazabilidad con tres episodios de delegación (20 %).")]

    # 2
    s += [H1("2. Especificación"),
          P("Documento completo: " + C("docs/especificacion.md") + " (versión 1.2). Su evolución v1 → v1.1 → v1.2 "
            "se recupera con " + C("git log -p docs/especificacion.md") + " y está resumida en su §9."),
          H2("Requisitos funcionales"),
          *tabla([["ID", "Requisito"],
                  ["R1", "Cargar y mostrar el inventario precargado."],
                  ["R2", "Informar si una unidad está disponible en un intervalo y, si no, con qué reservas activas choca."],
                  ["R3", "Crear una reserva (unidad, solicitante, inicio, fin) con ID R-NNNN y estado activa."],
                  ["R4", "Cancelar por ID conservando ID y datos; estado cancelada, se registra cancelada_en y se libera el intervalo."],
                  ["R5", "Persistir reservas y estados; recuperarlos al reiniciar la aplicación."],
                  ["R6", "Listar reservas activas y canceladas, con filtros por unidad y estado."]], [0.1, 0.9]),
          H2("Reglas de negocio centrales"),
          lista(["Unidad conocida y exacta (RN1); solicitante no vacío ni solo espacios (RN2); fecha y hora válidas "
                 "en formato YYYY-MM-DD HH:MM (RN3); inicio estrictamente anterior al fin (RN4).",
                 "Intervalos <b>semiabiertos [inicio, fin)</b>: A y B se superponen si A.inicio &lt; B.fin y "
                 "B.inicio &lt; A.fin (RN5). Por eso 10:00–11:00 y 11:00–12:00 son consecutivos y válidos (RN8).",
                 "Se rechaza la superposición con reservas <b>activas</b> de la <b>misma</b> unidad (RN6); una "
                 "cancelada nunca bloquea (RN7); unidades distintas pueden reservarse a la vez (RN9).",
                 "La consulta de disponibilidad aplica <b>exactamente las mismas reglas</b> que la creación (RN10).",
                 "Solo se cancela una reserva existente y activa (RN11)."]),
          H2("Supuestos (lo no especificado, resuelto)"),
          *tabla([["ID", "Supuesto"],
                  ["S1", "Hora local del laboratorio: America/Argentina/Buenos_Aires, UTC−3 fijo, independiente de la PC."],
                  ["S2", "Formato exacto YYYY-MM-DD HH:MM, dígitos ASCII, resolución de minutos."],
                  ["S3", "Se rechaza reservar o consultar con inicio en el pasado; una reserva pasada sí se puede cancelar."],
                  ["S4 / S5", "Duración máxima 12 h; sin límite de anticipación."],
                  ["S6", "IDs R-0001… secuenciales que nunca se reutilizan, ni tras reiniciar datos."],
                  ["S7", "Solicitante: máx. 100 caracteres, sin caracteres de control; siempre ficticio."],
                  ["S8", "El 'ahora' es fijable con RESERVAS_AHORA para pruebas reproducibles."],
                  ["S9", "reiniciar-datos --confirmar borra todas las reservas; sin --confirmar no hace nada."],
                  ["S10 / S11", "Filtros de listar validan unidad/estado; rutas configurables; errores de almacenamiento sin traceback."]],
                 [0.14, 0.86]),
          P("Hay <b>16 criterios de aceptación</b> (CA-01…CA-16) en formato dado/cuando/entonces; incluyen el ejemplo "
            "de la consigna: con MIC-01 reservado de 10:00 a 11:00 se rechaza 10:30–11:30, se permite 11:00–12:00 y "
            "MIC-02 de 10:00 a 11:00.")]

    # 3
    s += [PageBreak(), H1("3. Solución técnica"),
          P("Aplicación de consola en Python que usa solo la biblioteca estándar en tiempo de ejecución; pytest es "
            "la única dependencia de desarrollo y está fijada en " + C("requirements-dev.txt") + "."),
          Preformatted(
              "data/inventario.json      inventario inicial (versionado)\n"
              "src/reservas/\n"
              "  dominio.py              reglas puras: validaciones, se_superpone() [inicio, fin), conflictos()\n"
              "  repositorio.py          SQLite: esquema, transacciones BEGIN IMMEDIATE, sin DELETE salvo reinicio\n"
              "  servicio.py             casos de uso: inventario, disponibilidad, reservar, cancelar, listar\n"
              "  cli.py, __main__.py     interfaz: python -m reservas <comando>\n"
              "  errores.py, inventario.py\n"
              "tests/                    148 pruebas pytest\n"
              "tools/                    auditoría de mutantes, capturas, este informe", E["codigo"]),
          H2("Decisiones técnicas principales"),
          *tabla([["Decisión", "Motivo"],
                  ["SQLite (sqlite3 de la stdlib)", "Transacciones atómicas; AUTOINCREMENT no reutiliza IDs; sin servidor."],
                  ["Una única función se_superpone()", "Garantiza que reservar y disponibilidad usen la misma regla (RN10)."],
                  ["Chequeo + INSERT en la misma transacción BEGIN IMMEDIATE", "Evita dobles confirmaciones entre la verificación y la escritura."],
                  ["Cancelar = UPDATE de estado; nunca DELETE", "Conserva el historial (R4)."],
                  ["'Ahora' inyectable", "Pruebas deterministas que no caducan con el calendario."],
                  ["CLI con códigos de salida 0 / 1 / 2", "0 éxito · 1 error de negocio o validación ('ERROR:' en stderr) · 2 uso incorrecto."]],
                 [0.42, 0.58]),
          P("Las diez decisiones con alternativas y consecuencias están en " + C("docs/decisiones.md") + " (Parte A)."),
          H2("Persistencia y reinicio de datos"),
          P("Las reservas se guardan en " + C("data/reservas.db") + " (ignorado por git; configurable con "
            + C("--db") + " o " + C("RESERVAS_DB") + "). El comando " + C("reiniciar-datos --confirmar")
            + " <b>borra todas las reservas</b>; sin la bandera no hace nada.")]

    # 4
    s += [PageBreak(), H1("4. Preparación del agente"),
          *tabla([["Elemento", "Detalle"],
                  ["Harness", DATOS["harness"] + ". Se usó uno existente; no se construyó ninguno."],
                  ["Modelo", DATOS["modelo"] + ". Datos no expuestos por el harness (temperatura, ventana de contexto) no se informan."],
                  ["Instrucciones", "CLAUDE.md: reglas de dominio no negociables, procedimiento de persistencia, forma de trabajo por etapas con commit y registro en docs/progreso.md."],
                  ["Subagentes", ".claude/agents/: redactor-pruebas (escribe pruebas desde los CA sin leer src/), revisor-reglas (auditoría solo lectura), verificador (ejecuta y registra evidencia)."],
                  ["Permisos", ".claude/settings.json — allow: pytest, CLI, git de lectura · ask: git commit/push, rm, pip install, reiniciar-datos · deny: .env, *.db, acceso web."],
                  ["Contexto excluido", ".venv/, bases de datos, .env, web; al redactor-pruebas se le excluyó src/."]],
                 [0.2, 0.8]),
          H2("Adaptación específica comprobable"),
          lista(["<b>Turnos consecutivos:</b> CLAUDE.md exige [inicio, fin) y una única se_superpone(). El revisor lo "
                 "verificó con búsqueda en el código y lo cubren las pruebas test_ca_04_* y test_dominio.py.",
                 "<b>Procedimiento de persistencia:</b> transacción BEGIN IMMEDIATE, sin DELETE salvo reinicio, cancelar "
                 "por UPDATE. Lo cubren test_ca_11_* y test_ca_14_*; los mutantes M6 y M8 lo confirman.",
                 "<b>Retención del progreso:</b> docs/progreso.md se actualizó y versionó al cierre de cada etapa."]),
          H2("Controles humanos aplicados"),
          lista(["El autor eligió stack, interfaz y enfoque de agentes y aprobó el plan antes de empezar.",
                 "Checkpoint 1: confirmó sin cambios los supuestos S3, S4 y RN1 de la especificación v1.",
                 "Aprobó cada commit (rechazó uno por error y luego lo confirmó explícitamente).",
                 "Decidió aceptar, corregir o rechazar en los tres episodios (sección 5)."]),
          P("<b>Nota honesta:</b> los subagentes se definieron en la misma sesión en que se usaron; el harness aún no "
            "los registraba como tipos propios, por lo que se lanzaron como agentes genéricos con la orden de leer y "
            "seguir su archivo de definición. Detalle en " + C("docs/agente.md") + ".")]

    # 5
    s += [PageBreak(), H1("5. Tres episodios de delegación"),
          P("Cada episodio sigue la cadena exigida: objetivo → contexto e instrucción → resultado del agente → "
            "decisión humana → evidencia verificable."),
          *tabla([["", "Episodio 1: implementación", "Episodio 2: pruebas", "Episodio 3: revisión"],
                  ["Delegado a", "Agente principal", "Subagente redactor-pruebas", "Subagente revisor-reglas (solo lectura)"],
                  ["Objetivo", "R1–R6 y RN1–RN11 de la especificación v1", "Pruebas de CA-01…CA-15 desde la especificación", "Auditar el código contra reglas y supuestos"],
                  ["Contexto / instrucción", "Especificación, interfaz y CLAUDE.md ('una única se_superpone()', 'chequeo e INSERT en la misma transacción')", "Especificación e interfaz; <b>sin acceso a src/</b>; 'si una prueba falla, no la arregles: reportala'", "Todo el repo sin escritura; checklist de 7 ítems; 'no inventes problemas'"],
                  ["Resultado del agente", "Código completo; prueba rápida coincide con el ejemplo de la consigna", "114 pruebas; <b>3 fallaban</b>: tuple en lugar de list según el contrato; 11 ambigüedades", "13 hallazgos (2 media, 11 baja); uno resultó solo parcialmente correcto al reproducirlo"],
                  ["Decisión humana", "<b>Aceptar</b>", "<b>Corregir la implementación</b> (no las pruebas) y aclarar IDs tras reinicio (spec v1.1, CA-16)", "<b>Aceptar los 4 grupos</b> de correcciones (spec v1.2 + 23 pruebas de regresión)"],
                  ["Evidencia", "commit 8e68a63", "d76aeb4 → ed6385c, 1f29ccb; docs/evidencia/episodio2-*.md", "7f502bd; docs/evidencia/episodio3-*.md"]],
                 [0.16, 0.26, 0.29, 0.29]),
          P("En todos los casos, lo informado por un subagente se comprobó re-ejecutando pytest o reproduciendo el caso "
            "antes de decidir; así se detectó, por ejemplo, que el hallazgo #7 del revisor era parcialmente incorrecto.")]

    # 6
    s += [PageBreak(), H1("6. Pruebas, auditoría y verificación"),
          H2("Verificaciones exigidas por la consigna"),
          *tabla([["Verificación exigida", "Pruebas que la cubren"],
                  ["Creación válida", "test_crear.py; test_ca_01_cli_reservar_salida_creada"],
                  ["Rechazo de superposición", "test_superposicion.py (parcial, contiene, contenida, idéntica, solapes de 1 min)"],
                  ["Límites consecutivos", "test_limites.py (incluye cruce de medianoche); test_dominio.py"],
                  ["Unidades distintas simultáneas", "test_unidades.py::test_ca_05_*; test_ca_13_otra_unidad_disponible"],
                  ["Entradas inválidas", "test_validaciones.py (31); test_ca_06_*; 12 casos por CLI con exit 1; test_revision.py"],
                  ["Cancelación que conserva y libera", "test_cancelacion.py (CA-11, CA-12); test_dominio_conflictos_ignora_canceladas"],
                  ["Persistencia tras detener y reiniciar", "test_persistencia.py: cada comando en un proceso nuevo sobre la misma BD"]],
                 [0.35, 0.65]),
          H2("Auditoría de las pruebas y mutantes"),
          P("Se leyeron los 11 archivos de pruebas y se corrigieron tres debilidades (un pytest.raises(Exception) "
            "demasiado amplio, falta de casos de medianoche/bisiesto, y la regla RN7 sin prueba a nivel de dominio). "
            "Luego " + C("tools/auditoria/mutantes.py") + " inyectó 9 defectos, uno por vez, en una copia del "
            "proyecto: la primera corrida detectó 8/9 (sobrevivió M2) y, tras agregar " + C("tests/test_dominio.py")
            + ", la segunda detectó <b>9/9</b>. Detalle en " + C("docs/auditoria-pruebas.md") + "."),
          H2("Resultados ejecutados"),
          *tabla([["Verificación", "Comando", "Resultado"],
                  ["Suite completa (tras auditoría)", ".venv/Scripts/python -m pytest -q", f"{DATOS['pruebas']} passed"],
                  ["Mutantes", ".venv/Scripts/python tools/auditoria/mutantes.py", "9/9 detectados"],
                  ["Persistencia manual (subagente verificador)", "9 pasos, un proceso por paso (docs/verificacion.md)", "9/9 OK (sobre 7f502bd)"]],
                 [0.3, 0.45, 0.25]),
          P("No se verificó: escrituras simultáneas de varios procesos, fallas físicas de disco, otros sistemas "
            "operativos.")]

    # 7
    s += [PageBreak(), H1("7. Capturas de funcionamiento"),
          P("Capturas <b>reales</b> de ventanas de PowerShell generadas por " + C("tools/capturas/capturar.ps1")
            + ": cada escenario se ejecuta en una ventana nueva, se captura con la API PrintWindow y se cierra. "
            "Las reservas usan una base de demostración en %TEMP% y RESERVAS_AHORA=2026-11-30 08:00. "
            "Descripción de cada una en " + C("docs/capturas/README.md") + ".")]
    capturas = [
        ("01-entorno.png", "versiones de Python y pytest, commit y estado del árbol.", "capturar.ps1 -Solo 01"),
        ("02-pytest-completo.png", "suite completa de pruebas automáticas.", "python -m pytest -q"),
        ("03-pytest-verificaciones-consigna.png", "pruebas representativas de las 7 verificaciones exigidas.", "capturar.ps1 -Solo 03"),
        ("04-ejemplo-consigna.png", "MIC-01 10–11 creada; 10:30–11:30 rechazada; 11–12 aceptada; MIC-02 10–11 aceptada.", "capturar.ps1 -Solo 04"),
        ("05-cancelacion.png", "NO DISPONIBLE → cancelar R-0001 → DISPONIBLE; listar conserva la cancelada.", "capturar.ps1 -Solo 05"),
        ("06-persistencia-nueva-ventana.png", "proceso nuevo sobre la misma BD: las reservas activas y canceladas persisten.", "capturar.ps1 -Solo 06"),
        ("07-entradas-invalidas.png", "unidad, solicitante, fecha, orden, pasado, duración y cancelación repetida: ERROR + exit 1.", "capturar.ps1 -Solo 07"),
        ("08-reiniciar-datos.png", "reiniciar-datos sin --confirmar no borra nada.", "capturar.ps1 -Solo 08"),
        ("09-auditoria-mutantes.png", "9 defectos inyectados, todos detectados por las pruebas.", "python tools/auditoria/mutantes.py"),
    ]
    for archivo, pie, cmd in capturas:
        s += captura(archivo, pie, cmd)

    # 8
    s += [PageBreak(), H1("8. Cómo reproducir"),
          P("Requisitos: Python 3.12 o superior y git. No se necesita red ni cuenta de modelo."),
          Preformatted(
              "python -m venv .venv\n"
              ".venv/Scripts/python -m pip install -r requirements-dev.txt -e .\n"
              ".venv/Scripts/python -m pytest -v                         # pruebas automáticas\n"
              ".venv/Scripts/python tools/auditoria/mutantes.py          # prueba de mutantes\n\n"
              "# CLI (en PowerShell, BD de prueba y 'ahora' fijo):\n"
              "$env:RESERVAS_DB = \"$env:TEMP\\prueba.db\"; $env:RESERVAS_AHORA = \"2026-11-30 08:00\"\n"
              ".venv/Scripts/python -m reservas reservar MIC-01 \"Ana Ficticia\" \"2026-12-01 10:00\" \"2026-12-01 11:00\"\n"
              ".venv/Scripts/python -m reservas disponibilidad MIC-01 \"2026-12-01 10:30\" \"2026-12-01 11:30\"\n"
              ".venv/Scripts/python -m reservas cancelar R-0001\n"
              ".venv/Scripts/python -m reservas listar\n\n"
              "# Capturas e informe (Windows):\n"
              "powershell -ExecutionPolicy Bypass -File tools/capturas/capturar.ps1\n"
              "python -m venv .venv-tools; .venv-tools/Scripts/python -m pip install -r tools/requirements-tools.txt\n"
              ".venv-tools/Scripts/python tools/informe/generar_informe.py", E["codigo"])]

    # 9
    s += [H1("9. Limitaciones y cumplimiento de la rúbrica"),
          H2("Limitaciones declaradas"),
          lista(["Sin pruebas de escrituras simultáneas desde varios procesos (fuera del alcance de la consigna).",
                 "Verificado solo en Windows 10; en consolas no UTF-8 los acentos pueden verse mal (los datos no se alteran).",
                 "Zona horaria UTC−3 fija: si Argentina volviera al horario de verano habría que ajustar ZONA_LABORATORIO.",
                 "Sin edición/reprogramación de reservas ni reservas multi-unidad (fuera de alcance)."]),
          H2("Cumplimiento por dimensión"),
          *tabla([["Dimensión (peso)", "Evidencia en el repositorio"],
                  ["Especificación (25 %)", "docs/especificacion.md v1.2: R1–R6, RN1–RN11, S1–S11, CA-01…CA-16; historial v1→v1.2 con motivos en git."],
                  ["Preparación y uso del agente (25 %)", "CLAUDE.md, .claude/settings.json, .claude/agents/*.md, docs/agente.md, docs/progreso.md, docs/plan/."],
                  ["Funcionamiento y pruebas (30 %)", f"{DATOS['pruebas']} pruebas; persistencia por subprocesos; docs/verificacion.md; docs/auditoria-pruebas.md (mutantes 9/9); capturas."],
                  ["Trazabilidad y decisiones (20 %)", "docs/decisiones.md (D1–D10 y 3 episodios), docs/evidencia/, commits enlazados."]],
                 [0.3, 0.7])]

    # Anexo
    s += [PageBreak(), H1("Anexo: historial de commits"),
          P("La evolución del trabajo se recupera en git; cada etapa terminó con un commit."),
          *tabla([["Commit", "Mensaje"]] + [[h, m] for h, m in historial], [0.14, 0.86])]
    return s


def main() -> None:
    doc = SimpleDocTemplate(str(SALIDA), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=1.8 * cm, bottomMargin=2 * cm,
                            title="Informe de resolución — Challenge IA",
                            author=git("log", "-1", "--format=%an"),
                            subject="Sistema de reservas de laboratorio con agentes")
    doc.build(construir(), onFirstPage=pie_pagina, onLaterPages=pie_pagina)
    print(f"Generado {SALIDA}")


if __name__ == "__main__":
    main()
