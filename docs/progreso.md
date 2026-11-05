# Progreso y decisiones (archivo versionado)

Registro cronológico mantenido por el agente principal al cerrar cada etapa
(regla de `CLAUDE.md`). Fechas en hora local (America/Argentina/Buenos_Aires).

| Etapa | Estado | Commit |
|---|---|---|
| -1. Plan exportado (md/docx/pdf) | ✔ hecho | ver etapa 0 |
| 0. Preparación del agente | ✔ hecho | `chore: preparación del agente` |
| 1. Especificación v1 | ✔ aprobada sin cambios | `docs: especificación v1` |
| 2. Episodio 1 — implementación | ✔ hecho | `feat: implementación` |
| 3. Episodio 2 — pruebas (redactor-pruebas) | ✔ hecho (corrección aplicada) | `d76aeb4` + `fix:` |
| 4. Episodio 3 — revisión (revisor-reglas) | pendiente | |
| 5. Verificación (verificador) | pendiente | |
| 6. Documentación final | pendiente | |
| 7. Cierre y entrega | pendiente | |

## 2026-11-05 — Etapas -1 y 0

**Hecho**
- Plan aprobado por el humano y exportado a `docs/plan/plan-trabajo.{md,docx,pdf}`.
- Entorno detectado: Claude Code `2.1.305`, modelo `claude-opus-5-5`, Python 3.14.2, git 2.42.0, Windows 10.
- Creados `CLAUDE.md`, `.claude/settings.json`, subagentes `redactor-pruebas`, `revisor-reglas`, `verificador`.

**Decisiones (tomadas por el humano al aprobar el plan)**
- Python + SQLite + pytest; interfaz CLI; Claude Code + subagentes; repo local y push manual por el autor.

**Pendientes**
- pytest no está instalado globalmente → se instalará en `.venv` en la etapa 2.
- Repositorio remoto en GitHub: lo crea el autor al final.

## 2026-11-05 — Etapa 1: especificación v1

**Hecho**
- `docs/especificacion.md` v1: R1–R6, RN1–RN11, supuestos S1–S9, criterios CA-01…CA-15.
- `docs/interfaz.md`: contrato API/CLI para que `redactor-pruebas` escriba pruebas sin leer `src/`.

**Decisiones del agente (a validar por el humano)**
- Disponibilidad lanza los mismos errores de validación que reservar (RN10) en lugar de responder "no disponible" ante entradas inválidas.
- Pasado (S3) y duración máxima 12 h (S4) también aplican a la consulta de disponibilidad.
- Unidad sensible a mayúsculas (RN1).

**Pendientes**
- Checkpoint humano sobre supuestos y criterios.

## 2026-11-05 — Checkpoint 1 (decisión humana)
- El autor revisó la especificación v1 y **confirmó sin cambios** S3 (rechazar inicio en el pasado), S4 (duración máx. 12 h) y RN1 (ID exacto, `mic-01` se rechaza).
- Indicación del autor: "realizalo pudiendo cumplir todas las exigencias del challenge-agents.pdf".

## 2026-11-05 — Etapa 2 / Episodio 1: implementación (agente principal)

**Hecho**
- `src/reservas/`: `dominio.py` (reglas puras, `se_superpone`), `repositorio.py` (SQLite, `BEGIN IMMEDIATE`), `servicio.py`, `cli.py`, `errores.py`, `inventario.py`.
- `data/inventario.json`, `pyproject.toml`, `requirements-dev.txt` (lock con versiones fijadas).
- `.venv` con pytest 9.2.0; instalación editable.

**Verificación rápida (ejecutada, BD temporal, `RESERVAS_AHORA=2026-11-30 08:00`)**
- Ejemplo de la consigna: MIC-01 10:30–11:30 → `ERROR` exit 1; 11:00–12:00 → `CREADA R-0002`; MIC-02 10:00–11:00 → `CREADA R-0003`.
- `cancelar R-0001` → `CANCELADA`; luego `disponibilidad MIC-01 10:00–11:00` → `DISPONIBLE`.

**Decisiones técnicas**
- ID `R-NNNN` derivado de `INTEGER PRIMARY KEY AUTOINCREMENT` (SQLite no reutiliza valores → S6), sin columna id duplicada.
- La superposición se filtra en Python con `dominio.conflictos` sobre las activas de la unidad, en vez de un `WHERE` SQL equivalente, para que `se_superpone` sea la única comparación (regla 2 de CLAUDE.md).
- El "ahora" se trunca a minutos (S2).

**Control humano aplicado**
- El autor rechazó por error el primer intento de commit de esta etapa y luego confirmó explícitamente "Hacé los commits igual".

**Pendientes**
- Acentos en consola Windows dependen de la codificación de la terminal (observado en Git Bash: `Mult�metro`). No afecta datos (UTF-8 en SQLite/JSON).

## 2026-11-05 — Etapa 3 / Episodio 2: pruebas (subagente redactor-pruebas)

**Delegación**
- Subagente lanzado con la definición `.claude/agents/redactor-pruebas.md` (vía tipo `general-purpose`, porque el subagente se creó en la misma sesión y aún no estaba registrado). Restricción: no leer `src/`, escribir solo en `tests/`.
- Resultado informado por el subagente: 10 archivos en `tests/`, 114 pruebas, "3 failed, 111 passed", más 11 ambigüedades de la especificación.

**Comprobación propia (ejecutada)**
- `.venv/Scripts/python -m pytest -q` → `3 failed, 111 passed in 99.13s`. Coincide con el informe.
- Causa: `Disponibilidad.conflictos` devolvía `tuple` (`()`), el contrato `docs/interfaz.md` dice `list[Reserva]`.

**Decisión humana**
- El autor eligió **corregir la implementación** (el contrato manda), sin tocar las pruebas.
- De las ambigüedades, el autor eligió aclarar en la especificación solo "IDs tras reiniciar-datos" (→ v1.1).

**Corrección y verificación**
- `dominio.conflictos` y `Disponibilidad.conflictos` ahora son `list`.
- `.venv/Scripts/python -m pytest -q` → `114 passed in 138.24s`.

## 2026-11-05 — Especificación v1.1 (decisión humana del Episodio 2)
- S6 aclarado: los IDs no se reutilizan tras `reiniciar-datos`; nuevo CA-16. Historial de cambios agregado a la especificación (§9).
- Prueba nueva `tests/test_cli.py::test_ca_16_ids_no_se_reutilizan_tras_reiniciar`, escrita por el agente principal. Ejecutada: `1 passed`. La implementación ya cumplía (AUTOINCREMENT de SQLite); no hubo cambio de código.
