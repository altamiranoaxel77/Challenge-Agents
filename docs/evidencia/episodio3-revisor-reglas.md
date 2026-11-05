# Evidencia del Episodio 3: informe del subagente `revisor-reglas`

Este archivo es un extracto del informe final que devolvió el subagente el 2026-11-05. El subagente trabajó en modo de solo lectura (Read, Glob y Grep) y no ejecutó código.

## Instrucción dada (extracto)
> Actuás como el subagente `revisor-reglas` [...] Sos de **solo lectura**: no edites [...] auditá `src/` contra el checklist de 7 ítems de tu definición. Además prestá atención a: [...] requisitos ocultos; casos borde de fechas [...]; robustez de la transacción [...]; manejo de errores del CLI [...] No inventes problemas.

## Hallazgos informados: 13 en total (0 de severidad alta, 2 media, 11 baja)
| # | Sev. | Resumen | Verificación del agente principal | Decisión humana |
|---|---|---|---|---|
| 1 | media | Si el inventario falta o es inválido, se produce un traceback en lugar de `ERROR:` | ✔ reproducido: `FileNotFoundError` | Aceptado (grupo A) |
| 2 | media | Si la BD está corrupta, bloqueada o no es escribible, se produce un traceback | ✔ reproducido: `sqlite3.DatabaseError: file is not a database` | Aceptado (A) |
| 3 | baja | Si falla `BEGIN IMMEDIATE`, el `ROLLBACK` sin transacción abierta tapa el error real | Revisión de código | Aceptado (A) |
| 4 | baja | `listar` rellena el estado a 9 caracteres, mientras que el contrato separa con 2 espacios | Revisión de código | Aceptado (C) |
| 5 | baja | Hay salidas del CLI que no figuran en `interfaz.md` | Revisión de código | Aceptado (C) |
| 6 | baja | `reiniciar-datos` sin `--confirmar` e `inventario` crean el archivo de BD | Revisión de código | Aceptado (C) |
| 7 | baja | Se aceptan fechas con espacios alrededor y dígitos Unicode | **Parcial**: espacios ✔ aceptados (`" 2026-12-01 10:00 "` → R-0002); dígitos árabes ✘ **ya los rechazaba** `strptime`, aunque con un mensaje confuso | Aceptado (B) |
| 8 | baja | `R-1`, `R-00001` y `" R-0001 "` identifican a `R-0001` | ✔ reproducido: `cancelar("R-1")` → R-0001 cancelada | Aceptado (B) |
| 9 | baja | `listar --unidad` valida la unidad, pero eso no estaba especificado | Revisión de código | Aceptado (C): documentado como S10 |
| 10 | baja | El "ahora" depende de la zona horaria de la PC, no de UTC−3 | Revisión de código | Aceptado (D) |
| 11 | baja | Las rutas por defecto dependen de una instalación editable | Revisión de código | Aceptado (D): se agregó `RESERVAS_INVENTARIO` |
| 12 | baja | La conexión del esquema no se cierra explícitamente | Revisión de código | Aceptado (A) |
| 13 | baja | El solicitante admite `\n` y tabs, que rompen el formato de una línea por reserva | ✔ reproducido: `'Ana\nFicticia'` aceptado | Aceptado (B) |

**Checklist del revisor que dio OK:**
- (1) `se_superpone` es semiabierta y es la única comparación (`dominio.py`).
- (2) Disponibilidad y reserva aplican las mismas reglas.
- (3) Solo las reservas activas bloquean.
- (5) La verificación y la inserción ocurren en la misma transacción; no hay `DELETE` fuera de `reiniciar-datos`.

**Casos borde de fechas que el revisor dio por correctos:**
- 2028-02-29 se acepta y 2026-02-29 se rechaza.
- 23:00 → 00:00 del día siguiente se acepta.
- Una duración de exactamente 12 h se acepta y una de 12 h 01 min se rechaza.

## Decisión humana
El autor aceptó los 4 grupos: A (errores sin traceback), B (entradas estrictas), C (documentar la interfaz) y D (zona horaria y rutas).

## Corrección y verificación
- **Código:** `errores.py` (nuevo `ErrorAlmacenamiento`), `inventario.py`, `repositorio.py`, `dominio.py`, `servicio.py` y `cli.py`.
- **Pruebas de regresión:** `tests/test_revision.py`, escritas por el agente principal. Cada una cita el número de hallazgo.
- **Especificación:** v1.2 (S1, S2, S6, S7, S9, S10 y S11).
- **Interfaz:** se actualizó `docs/interfaz.md`.
- **Ejecución:** `.venv/Scripts/python -m pytest -q` → `138 passed in 154.13s`.
