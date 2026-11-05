# Preparación y uso del agente

## 1. Entorno y modelo
| Dato | Valor | Cómo se obtuvo |
|---|---|---|
| Harness | Claude Code, extensión de VS Code en Windows 10 Pro (10.0.19045) | Entorno de trabajo del autor |
| Versión del harness | `2.1.305 (Claude Code)` | `claude --version`, ejecutado el 2026-11-05 (ver `docs/progreso.md`) |
| Modelo | `claude-opus-5-5` (Claude Opus 5.5) | Identificador expuesto por el harness en el contexto de la sesión |
| Subagentes | Corren dentro del mismo harness y heredan el modelo | Herramienta `Agent` de Claude Code |
| Python / git | Python 3.14.2 · git 2.42.0.windows.2 | `python --version`, `git --version` |
| Dato no visible | Temperatura, ventana de contexto efectiva y versión exacta del system prompt del harness | El harness no los expone. No se informan valores inventados |

**Función del agente:**
- Redactar la especificación a partir de la consigna.
- Implementar la solución.
- Coordinar a los subagentes.
- Ejecutar pruebas y comandos.
- Mantener el registro de progreso.

El autor decide en cada checkpoint.

**Motivo de la elección:**
- Claude Code actúa sobre el repositorio con herramientas reales: lee y edita archivos, ejecuta Bash, hace commits y lanza subagentes. Eso es lo que pide la consigna: un harness existente, no uno construido.
- Las instrucciones viven en archivos versionados (`CLAUDE.md`, `.claude/`), así que la configuración queda como evidencia en el repositorio.
- Los permisos (`allow`, `ask`, `deny`) permiten exigir aprobación humana para acciones sensibles.

## 2. Instrucciones y configuración usadas (todas versionadas)
| Archivo | Contenido | Cómo se aplica |
|---|---|---|
| [`CLAUDE.md`](../CLAUDE.md) | Objetivo, stack, **reglas de dominio no negociables**, procedimiento de persistencia, forma de trabajo por etapas y exclusiones | Claude Code lo carga automáticamente al iniciar cada sesión en la raíz del repositorio |
| [`.claude/settings.json`](../.claude/settings.json) | Permisos `allow`, `ask` y `deny` del proyecto | Claude Code lo aplica a cada llamada de herramienta |
| [`.claude/agents/redactor-pruebas.md`](../.claude/agents/redactor-pruebas.md) | Escribe pruebas desde los CA sin leer `src/` | Ver la nota de la sección 5 |
| [`.claude/agents/revisor-reglas.md`](../.claude/agents/revisor-reglas.md) | Auditoría de solo lectura contra las reglas, con una checklist de 7 ítems | Ver la nota de la sección 5 |
| [`.claude/agents/verificador.md`](../.claude/agents/verificador.md) | Ejecuta pruebas y el procedimiento de persistencia, y registra la evidencia | Ver la nota de la sección 5 |
| [`docs/plan/plan-trabajo.md`](plan/plan-trabajo.md) | Plan aprobado por el autor antes de empezar (también en `.docx` y `.pdf`) | El agente lo siguió etapa por etapa |

**Configuración externa al repositorio:**
- La instalación global de Claude Code y su modo de permisos los elige el usuario en la extensión de VS Code.
- No se usó `settings.local.json` (está ignorado por git).
- No se usaron MCP, servicios pagos adicionales ni memoria externa para el desarrollo.

## 3. Contexto suministrado y excluido
**Suministrado:**
- La consigna `challenge-agents.pdf`.
- Las respuestas del autor en cada checkpoint, que quedaron registradas en `docs/progreso.md`.
- Los archivos del repositorio.

**Contexto restringido por subagente:**
- `redactor-pruebas`: solo `docs/especificacion.md`, `docs/interfaz.md`, `CLAUDE.md` y `tests/`. **Se le excluyó `src/`**, para que las pruebas salgan de la especificación y no del código. El subagente declaró que no abrió `src/` (ver [evidencia](evidencia/episodio2-redactor-pruebas.md)).
- `revisor-reglas`: todo el repositorio, sin herramientas de escritura ni de ejecución.
- `verificador`: el repositorio y Bash. Solo escribe `docs/verificacion.md`.

**Excluido explícitamente** (sección "Excluido del contexto" de `CLAUDE.md` y `deny` de los permisos):
- `.venv/`
- `data/*.db`
- `.env`
- Los binarios derivados del plan
- Acceso web (`WebFetch` y `WebSearch` en `deny`)

No se usaron datos reales: los solicitantes son ficticios ("Ana Ficticia", "Beto Ficticio", …).

## 4. Permisos, controles y aprobaciones humanas
`.claude/settings.json`:
- **allow:** pytest, ejecutar el CLI, `git status`, `diff`, `log` y `show`.
- **ask** (requiere aprobación): `git commit`, `git push`, `rm`, `pip install` y cualquier comando con `reiniciar-datos`.
- **deny:** leer `.env` y `*.db`, `WebFetch` y `WebSearch`.

**Controles humanos aplicados (con evidencia):**
| Momento | Control | Evidencia |
|---|---|---|
| Antes de empezar | El autor eligió el stack, la interfaz y los agentes, y aprobó el plan | `docs/plan/`, `docs/progreso.md` |
| Checkpoint 1 | El autor revisó los supuestos S3, S4 y RN1 de la especificación v1 y los confirmó sin cambios | commit `674eadb` |
| Commit del Episodio 1 | El autor rechazó el comando de commit, luego aclaró que fue sin querer y lo aprobó | `docs/progreso.md` (control humano aplicado) |
| Episodio 2 | El autor decidió corregir la implementación y no las pruebas, y aclarar en la especificación los IDs tras un reinicio | commits `ed6385c` y `1f29ccb` |
| Episodio 3 | El autor decidió qué hallazgos del revisor aceptar (los 4 grupos) | commit `7f502bd`, [evidencia](evidencia/episodio3-revisor-reglas.md) |

**Qué se revisó antes de aceptar:**
- Los informes de los subagentes no se tomaron como ciertos. El agente principal **re-ejecutó** pytest para confirmar las 3 fallas del Episodio 2.
- También **reprodujo** los hallazgos #1, #2, #7, #8 y #13 del Episodio 3, y así encontró que el #7 era correcto solo en parte.
- Después, el autor decidió con esa información.

## 5. Adaptación específica comprobable
1. **Regla de turnos consecutivos.** La sección "Reglas de dominio" de `CLAUDE.md` exige intervalos `[inicio, fin)` y una **única** función `se_superpone()`.
   - Evidencia de uso: [`src/reservas/dominio.py`](../src/reservas/dominio.py) (`se_superpone`, `conflictos`).
   - El revisor verificó con grep que no hay otra comparación de intervalos (checklist ítem 1: OK).
   - Pruebas `test_ca_04_*` (límites consecutivos).
2. **Procedimiento de persistencia.** `CLAUDE.md` exige `BEGIN IMMEDIATE`, la verificación y la inserción en la misma transacción, ningún `DELETE` salvo `reiniciar-datos --confirmar`, y que cancelar sea un `UPDATE`.
   - Evidencia: [`src/reservas/repositorio.py`](../src/reservas/repositorio.py) y `servicio.reservar`.
   - Pruebas `test_ca_11_*` y `test_ca_14_*`.
   - Checklist ítem 5 del revisor: OK.
3. **Subagentes con contexto restringido.** El `redactor-pruebas` no lee `src/`.
   - Evidencia de uso: encontró una divergencia real entre el contrato y la implementación, que no habría aparecido si escribía las pruebas mirando el código.
4. **Retención del progreso.**
   - [`docs/progreso.md`](progreso.md) se actualizó al cerrar cada etapa y está versionado en cada commit.
   - [`docs/especificacion.md`](especificacion.md) §9 guarda el historial v1 → v1.1 → v1.2, que se puede recuperar con `git log -p docs/especificacion.md`.

**Nota sobre la invocación de subagentes.**
- Las definiciones `.claude/agents/*.md` se crearon durante la misma sesión en la que se usaron. El harness no las registró como tipos de agente invocables hasta reiniciar la sesión.
- Por eso, cada subagente se lanzó con la herramienta `Agent` (tipo `general-purpose`) y una instrucción que le ordenaba **leer y seguir su archivo de definición**, con las mismas restricciones (los extractos de esas instrucciones están en `docs/evidencia/`).
- La restricción de herramientas declarada en el *frontmatter* (por ejemplo, solo lectura para `revisor-reglas`) se impuso **por instrucción**, no por el harness. Los informes de los subagentes declaran que la respetaron, y `git status` no mostró cambios fuera de lo esperado.
- En una sesión nueva, los tres quedan disponibles directamente con su nombre.

## 6. Qué hizo el agente y qué hizo el humano
- **Agente:**
  - Redacción de la especificación y la interfaz.
  - Implementación.
  - Pruebas (a través del subagente).
  - Auditoría (a través del subagente).
  - Correcciones.
  - Verificación (a través del subagente).
  - Documentación.
- **Humano (autor):**
  - Elección del stack y del enfoque.
  - Aprobación del plan.
  - Validación de los supuestos.
  - Decisiones de aceptar, corregir o rechazar en los 3 episodios.
  - Aprobación de los commits.
  - Creación del repositorio remoto y entrega.
