# Instrucciones para el agente — Sistema de reservas de laboratorio

Este archivo es leído por Claude Code al iniciar cada sesión en este repositorio.
Es la **configuración real usada** durante el desarrollo (ver `docs/agente.md`).

## Objetivo
CLI local en Python para consultar disponibilidad, reservar y cancelar unidades
de laboratorio (MIC-01, MIC-02, OSC-01, MUL-01, FUE-01) sin perder historial.
La fuente de verdad de requisitos es `docs/especificacion.md`. Si una tarea
contradice la especificación, **detenerse y preguntar** antes de cambiar código.

## Stack y comandos
- Python >= 3.12 (desarrollo en 3.14), solo biblioteca estándar en runtime (`sqlite3`, `argparse`, `json`, `datetime`).
- Pruebas: `pytest` (única dependencia de desarrollo, versión fijada en `requirements-dev.txt`).
- Instalar: `python -m venv .venv` → `.venv/Scripts/python -m pip install -r requirements-dev.txt -e .`
- Probar: `.venv/Scripts/python -m pytest -v`
- CLI: `.venv/Scripts/python -m reservas <comando>`

## Reglas de dominio (adaptación específica — NO negociables)
1. **Intervalos semiabiertos `[inicio, fin)`**. Dos reservas se superponen si y solo si
   `a.inicio < b.fin and b.inicio < a.fin`. Un `fin` igual al `inicio` de otra
   reserva NO es superposición (turnos consecutivos permitidos).
2. Existe **una única función** `se_superpone()` en `src/reservas/dominio.py`. Tanto
   `reservar` como `disponibilidad` deben usarla (o la misma consulta derivada de ella);
   prohibido duplicar la lógica de comparación de intervalos.
3. Solo las reservas con estado `activa` bloquean. Las `cancelada` nunca bloquean.
4. Validar siempre: unidad del inventario, solicitante con `strip()` no vacío,
   formato `YYYY-MM-DD HH:MM`, `inicio < fin` estricto, más los supuestos de la especificación.
5. Reservas simultáneas de unidades distintas son válidas.

## Procedimiento de persistencia (adaptación específica)
- SQLite en `data/reservas.db` (configurable con `--db` o `RESERVAS_DB`).
- Toda escritura dentro de una transacción `BEGIN IMMEDIATE`; la verificación de
  superposición y el `INSERT` ocurren en la **misma** transacción.
- **Nunca** ejecutar `DELETE` sobre reservas, salvo el comando explícito
  `reiniciar-datos --confirmar`. Cancelar = `UPDATE estado='cancelada'` + `cancelada_en`.
- Las pruebas usan una BD temporal (`tmp_path`), jamás `data/reservas.db`.

## Forma de trabajo
- Trabajar por etapas del plan (`docs/plan/plan-trabajo.md`). Al cerrar cada etapa:
  1. actualizar `docs/progreso.md` (qué se hizo, decisiones, pendientes);
  2. correr las pruebas si existen;
  3. proponer commit (el humano aprueba). Mensajes en español, prefijo convencional (`feat:`, `test:`, `docs:`, `fix:`, `chore:`).
- No inventar resultados: en la documentación, distinguir **"informado por el agente"**
  de **"ejecutado y verificado"** con comando y salida real.
- Solicitantes siempre ficticios (p. ej. "Ana Ficticia"). Nunca datos reales.
- Antes de editar `docs/especificacion.md` después de su v1, pedir aprobación y registrar el motivo.

## Subagentes disponibles (`.claude/agents/`)
- `redactor-pruebas`: escribe pruebas desde los criterios CA-xx sin leer `src/`.
- `revisor-reglas`: audita `src/` contra las reglas; solo lectura; devuelve hallazgos.
- `verificador`: ejecuta pruebas y procedimiento de persistencia; registra evidencia en `docs/verificacion.md`.

## Excluido del contexto
- `.venv/`, `data/*.db`, `docs/plan/*.pdf|*.docx` (binarios derivados del plan).
