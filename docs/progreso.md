# Progreso y decisiones (archivo versionado)

Registro cronológico mantenido por el agente principal al cerrar cada etapa
(regla de `CLAUDE.md`). Fechas en hora local (America/Argentina/Buenos_Aires).

| Etapa | Estado | Commit |
|---|---|---|
| -1. Plan exportado (md/docx/pdf) | ✔ hecho | ver etapa 0 |
| 0. Preparación del agente | ✔ hecho | `chore: preparación del agente` |
| 1. Especificación v1 | pendiente | |
| 2. Episodio 1 — implementación | pendiente | |
| 3. Episodio 2 — pruebas (redactor-pruebas) | pendiente | |
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
