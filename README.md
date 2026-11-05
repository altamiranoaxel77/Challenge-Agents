# Reservas de laboratorio: Challenge IA

Esta es una herramienta de consola local para **consultar disponibilidad, reservar y cancelar** las unidades físicas de un laboratorio (MIC-01, MIC-02, OSC-01, MUL-01 y FUE-01). Conserva el historial y evita dos problemas: que se confirmen horarios superpuestos y que una reserva cancelada siga bloqueando el horario.

El desarrollo se hizo con un agente de programación, **Claude Code 2.1.305** con el modelo `claude-opus-5-5`, y tres subagentes. El autor revisó cada paso en checkpoints.

> Entrega: rama `main`. El commit entregado se identifica con `git log -1`.
>
> 📄 **Informe de resolución en PDF:** [docs/informe-resolucion.pdf](docs/informe-resolucion.pdf) · 📸 **Capturas de funcionamiento:** [docs/capturas/](docs/capturas/) · 🔎 **Auditoría de pruebas:** [docs/auditoria-pruebas.md](docs/auditoria-pruebas.md)

---

## 1. Especificación breve
La especificación completa está en [docs/especificacion.md](docs/especificacion.md) (v1.2). Su evolución se recupera con `git log -p docs/especificacion.md`; el historial de versiones está en §9 de ese documento.

- **Problema.** La coordinación del laboratorio registra los pedidos en mensajes y en una planilla. Eso produce dos fallas: la misma unidad queda confirmada para horarios superpuestos, y las cancelaciones siguen bloqueando el horario.
- **Alcance.**
  - Inventario precargado de solo lectura.
  - Consulta de disponibilidad por unidad e intervalo.
  - Creación de reservas (una unidad por reserva).
  - Cancelación que conserva el registro.
  - Listado de reservas.
  - Persistencia local.
  - Interfaz de consola.
- **Fuera de alcance.**
  - Autenticación y roles.
  - Notificaciones, pagos e integraciones.
  - Interfaz gráfica y despliegue.
  - Concurrencia distribuida.
  - Edición de reservas: para cambiar una, se cancela y se crea otra.
- **Requisitos verificables (R1–R6):**
  - R1: inventario.
  - R2: disponibilidad con conflictos.
  - R3: reserva con ID `R-NNNN`.
  - R4: cancelación que conserva los datos y libera el horario.
  - R5: persistencia tras reiniciar.
  - R6: listado con filtros.
- **Reglas (RN1–RN11).**
  - La unidad debe ser una del inventario, escrita exacta.
  - El solicitante no puede estar vacío ni tener solo espacios.
  - Las fechas deben ser válidas, en formato `YYYY-MM-DD HH:MM`.
  - `inicio < fin`, estrictamente.
  - Los intervalos son **semiabiertos `[inicio, fin)`**.
  - Se rechazan las superposiciones entre reservas **activas** de la misma unidad.
  - Las canceladas no bloquean.
  - Se permiten los límites consecutivos y las reservas simultáneas de unidades distintas.
  - **La disponibilidad aplica las mismas reglas que la reserva.**
- **Supuestos (S1–S11):**
  - Zona horaria: America/Argentina/Buenos_Aires, **UTC−3 fijo**, sin depender de la PC.
  - Formato `YYYY-MM-DD HH:MM`, con el minuto como resolución.
  - **Se rechaza reservar o consultar disponibilidad con inicio en el pasado.** Una reserva vencida igual se puede listar y cancelar.
  - **La duración máxima es de 12 h.** No hay límite de anticipación.
  - Los IDs nunca se reutilizan, ni siquiera después de un reinicio de datos.
  - El solicitante puede tener hasta 100 caracteres, sin caracteres de control.
  - El "ahora" se puede fijar con `RESERVAS_AHORA`.
  - `reiniciar-datos` exige `--confirmar`.
- **Criterios de aceptación:** CA-01…CA-16, en formato dado/cuando/entonces. Incluyen el ejemplo de la consigna:
  - Con MIC-01 reservado de 10:00 a 11:00, se rechaza MIC-01 de 10:30 a 11:30.
  - Se permite MIC-01 de 11:00 a 12:00.
  - Se permite MIC-02 de 10:00 a 11:00.

## 2. Solución

### Estructura
```
data/inventario.json        inventario inicial (versionado)
src/reservas/
  dominio.py                reglas puras: validaciones, se_superpone() [inicio, fin), conflictos()
  repositorio.py            SQLite: esquema, transacciones BEGIN IMMEDIATE, sin DELETE salvo reinicio
  servicio.py               casos de uso: inventario, disponibilidad, reservar, cancelar, listar
  cli.py / __main__.py      interfaz de consola (python -m reservas)
  errores.py, inventario.py
tests/                      148 pruebas pytest (CA-01..CA-16, regresión del Episodio 3, dominio)
docs/                       especificación, interfaz, agente, decisiones, verificación, progreso, plan
CLAUDE.md, .claude/         configuración real del agente y subagentes
tools/                      auditoría de mutantes, capturas reales, generador del informe PDF
```

### Decisiones técnicas
- Usa solo la **biblioteca estándar** de Python: `sqlite3`, `argparse`, `json` y `datetime`.
- **SQLite** guarda los datos con transacciones atómicas.
- Hay una **única** función de superposición.
- Cancelar es un `UPDATE`; nunca se borra una reserva.

El detalle y las alternativas están en [docs/decisiones.md](docs/decisiones.md) (Parte A). El contrato completo de la API y del CLI está en [docs/interfaz.md](docs/interfaz.md).

### Requisitos previos y versiones
- **Python ≥ 3.12.** El desarrollo y la verificación se hicieron con Python 3.14.2 en Windows 10.
- **pytest 9.2.0**, solo para las pruebas. Las versiones fijadas están en [requirements-dev.txt](requirements-dev.txt), que hace de archivo de bloqueo.
- **No hace falta** red ni cuenta de modelo para ejecutar la aplicación o sus pruebas.

### Instalación
```bash
python -m venv .venv
# Windows:
.venv/Scripts/python -m pip install -r requirements-dev.txt -e .
# Linux/macOS:
.venv/bin/python -m pip install -r requirements-dev.txt -e .
```
Los ejemplos que siguen usan `.venv/Scripts/python`. En Linux y macOS, reemplazalo por `.venv/bin/python`.

### Carga inicial, ubicación de los datos y reinicio
- **Inventario:** se lee de `data/inventario.json` y no requiere ninguna carga. Para usar otro archivo, definí `RESERVAS_INVENTARIO`.
- **Reservas:** se guardan en `data/reservas.db`. SQLite crea el archivo automáticamente con el primer comando que lo necesita. Está **ignorado por git**. Para usar otra ruta, pasá `--db RUTA` o definí `RESERVAS_DB`.
- **Reinicio de datos:**
  > ⚠️ `python -m reservas reiniciar-datos --confirmar` **BORRA TODAS LAS RESERVAS** (activas y canceladas). No se puede deshacer.
  - Sin `--confirmar` no hace nada y sale con código 1.
  - Los IDs no se reutilizan: después de un reinicio, la numeración sigue donde estaba.
  - Otra forma de reiniciar es borrar a mano `data/reservas.db`. En ese caso la numeración **sí** vuelve a empezar.

### Comandos
| Acción | Comando |
|---|---|
| Ver el inventario | `.venv/Scripts/python -m reservas inventario` |
| Consultar disponibilidad | `.venv/Scripts/python -m reservas disponibilidad MIC-01 "2026-12-01 10:00" "2026-12-01 11:00"` |
| Reservar | `.venv/Scripts/python -m reservas reservar MIC-01 "Ana Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"` |
| Cancelar | `.venv/Scripts/python -m reservas cancelar R-0001` |
| Listar | `.venv/Scripts/python -m reservas listar [--unidad MIC-01] [--estado activa\|cancelada]` |
| Correr las pruebas | `.venv/Scripts/python -m pytest -v` (unos 2–3 minutos: algunas pruebas lanzan el CLI como subproceso) |

Códigos de salida:
- `0`: la operación salió bien.
- `1`: error de negocio o de validación. El mensaje sale por stderr con el prefijo `ERROR:`.
- `2`: uso incorrecto del comando.

### Ejemplo de entrada y salida
Esta es la salida real de la secuencia, ejecutada por el agente principal el 2026-11-05 con una base de datos temporal. Para que el resultado sea reproducible, el "ahora" se fijó con `RESERVAS_AHORA="2026-11-30 08:00"`. Cada comando corre en un proceso distinto. El procedimiento equivalente que ejecutó el verificador, con otros nombres ficticios, está en [docs/verificacion.md](docs/verificacion.md).
```text
$ python -m reservas reservar MIC-01 "Ana Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"
CREADA R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  activa  Ana Ficticia
$ python -m reservas reservar MIC-01 "Beto Ficticio" "2026-12-01 10:30" "2026-12-01 11:30"
ERROR: MIC-01 ya está reservada en ese intervalo (conflicto con R-0001)        [exit 1]
$ python -m reservas reservar MIC-01 "Beto Ficticio" "2026-12-01 11:00" "2026-12-01 12:00"
CREADA R-0002  MIC-01  2026-12-01 11:00  2026-12-01 12:00  activa  Beto Ficticio
$ python -m reservas reservar MIC-02 "Carla Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"
CREADA R-0003  MIC-02  2026-12-01 10:00  2026-12-01 11:00  activa  Carla Ficticia
$ python -m reservas cancelar R-0001
CANCELADA R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  cancelada  Ana Ficticia  (cancelada_en 2026-11-30 08:00:00)
$ python -m reservas disponibilidad MIC-01 "2026-12-01 10:00" "2026-12-01 11:00"
DISPONIBLE MIC-01 2026-12-01 10:00 -> 2026-12-01 11:00
$ python -m reservas listar          # en un proceso nuevo: los datos persisten
R-0001  MIC-01  2026-12-01 10:00  2026-12-01 11:00  cancelada  Ana Ficticia
R-0003  MIC-02  2026-12-01 10:00  2026-12-01 11:00  activa  Carla Ficticia
R-0002  MIC-01  2026-12-01 11:00  2026-12-01 12:00  activa  Beto Ficticio
```

### Verificación
- **Auditoría posterior de las pruebas** ([docs/auditoria-pruebas.md](docs/auditoria-pruebas.md)): las 7 verificaciones que exige la consigna tienen pruebas. Se corrigieron 3 debilidades y la prueba de mutantes (`tools/auditoria/mutantes.py`) detecta **9 de 9** defectos inyectados. La suite actual da `148 passed`.
- **Capturas reales** de cada escenario en [docs/capturas/](docs/capturas/), como complemento visual de las pruebas.

La verificación original está en [docs/verificacion.md](docs/verificacion.md). La ejecutó el subagente `verificador` sobre el commit `7f502bd`, antes de la auditoría.
- **Pruebas automáticas:** `138 passed in 141.63s`. Cubren:
  - creación válida;
  - rechazo de superposiciones;
  - límites consecutivos;
  - unidades distintas reservadas al mismo tiempo;
  - entradas inválidas;
  - cancelación que conserva el registro y libera el horario;
  - persistencia comprobada con subprocesos separados.
- **Procedimiento manual de persistencia:** 9 pasos, cada uno en un proceso distinto. Los 9 dieron el resultado esperado.

### Pendientes y limitaciones
- No se probó con procesos simultáneos compitiendo por la misma BD. `BEGIN IMMEDIATE` serializa las escrituras, pero esa situación no se ejercitó.
- La verificación se hizo solo en Windows 10. En consolas Windows con una codificación distinta de UTF-8, los acentos pueden verse mal (`Mult�metro`). Los datos se guardan bien; para evitarlo, definí `PYTHONIOENCODING=utf-8`.
- La zona horaria es UTC−3 fijo. Si Argentina volviera a usar horario de verano, habría que ajustar `dominio.ZONA_LABORATORIO`.
- Las rutas por defecto (`data/`) suponen una instalación editable (`-e .`) o una ejecución desde el repositorio. En otros casos, usá `--db` y `RESERVAS_INVENTARIO`.
- No hay edición ni reprogramación de reservas, ni reservas de varias unidades a la vez (fuera de alcance).

## 3. Preparación del agente
El detalle completo y los enlaces a la evidencia están en [docs/agente.md](docs/agente.md).

- **Entorno y modelo.**
  - Claude Code `2.1.305`, como extensión de VS Code en Windows 10.
  - Modelo `claude-opus-5-5`.
  - No se informan datos que el harness no expone (ver §1 de agente.md).
- **Instrucciones.**
  - [CLAUDE.md](CLAUDE.md) define las reglas de dominio no negociables, el procedimiento de persistencia y la forma de trabajo por etapas con commits.
  - Los subagentes están definidos en [.claude/agents/](.claude/agents/):
    - `redactor-pruebas`: escribe las pruebas sin leer `src/`.
    - `revisor-reglas`: audita el código con permiso de solo lectura.
    - `verificador`: ejecuta y registra las verificaciones.
- **Contexto.**
  - Se le dio la consigna, la especificación y la interfaz.
  - Se excluyeron `.venv/`, `*.db`, `.env` y la web.
  - Al `redactor-pruebas` se le negó el acceso a `src/`.
- **Permisos.** Están en [.claude/settings.json](.claude/settings.json).
  - **allow:** pytest, el CLI y comandos de git de solo lectura.
  - **ask:** `git commit`, `git push`, `rm`, `pip install` y `reiniciar-datos`.
  - **deny:** `.env`, `*.db` y el acceso web.
- **Adaptación específica, con evidencia de uso.**
  - Regla de intervalos `[inicio, fin)` con una función única `se_superpone()`.
  - Procedimiento de persistencia transaccional sin `DELETE`.
  - El revisor verificó las dos (checklist ítems 1 y 5 en OK) y las cubren las pruebas `test_ca_04_*`, `test_ca_11_*` y `test_ca_14_*`.
- **Retención del progreso.**
  - [docs/progreso.md](docs/progreso.md) se actualizó al cerrar cada etapa y está versionado.
  - El plan aprobado está en [docs/plan/](docs/plan/), en formato md, docx y pdf.

## 4. Registro de decisiones y delegación
El detalle completo está en [docs/decisiones.md](docs/decisiones.md).

**Decisiones (D1–D10):** stack, SQLite, CLI, `[inicio, fin)`, cancelación por UPDATE, "ahora" inyectable, rechazo del pasado y de más de 12 h, IDs no reutilizables, UTC−3 fijo y errores sin traceback. Cada una figura con sus alternativas, motivo y consecuencias.

**Tres episodios reales de delegación:**
| # | Delegado a | Resultado del agente | Decisión humana | Evidencia |
|---|---|---|---|---|
| 1 | Agente principal: implementación | Código completo. La prueba rápida coincide con el ejemplo de la consigna | **Aceptar** | `8e68a63` |
| 2 | `redactor-pruebas`: pruebas desde los CA, sin ver el código | 114 pruebas. **3 fallan**: devolvía `tuple` donde el contrato pide `list`. Además señaló 11 ambigüedades | **Corregir la implementación**, no las pruebas, y aclarar en la especificación los IDs tras un reinicio (v1.1, CA-16) | `d76aeb4` → `ed6385c`, `1f29ccb`, [evidencia](docs/evidencia/episodio2-redactor-pruebas.md) |
| 3 | `revisor-reglas`: auditoría de solo lectura | 13 hallazgos (2 de severidad media). Uno resultó **correcto solo en parte** al reproducirlo | **Aceptar los 4 grupos de correcciones**. Especificación v1.2 y 23 pruebas de regresión | `7f502bd`, [evidencia](docs/evidencia/episodio3-revisor-reglas.md) |

**Qué informó el agente y qué se ejecutó:** cada afirmación de un subagente se comprobó volviendo a ejecutar pytest o reproduciendo el caso. Los resultados de esas ejecuciones, con su comando y su salida, están en `docs/progreso.md`, `docs/evidencia/` y `docs/verificacion.md`.
