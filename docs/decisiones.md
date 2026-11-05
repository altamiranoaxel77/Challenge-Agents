# Registro de decisiones y delegación

## Parte A: Decisiones significativas (ADR breve)

| # | Decisión | Alternativas | Motivo | Consecuencias |
|---|---|---|---|---|
| D1 | **Python 3.14 + solo biblioteca estándar** en runtime | Node/TypeScript; Python con FastAPI | Lo eligió el autor. Necesita cero dependencias para ejecutarse, así que se reproduce sin la cuenta de modelo del autor | Solo pytest como dependencia de desarrollo, fijada en `requirements-dev.txt` |
| D2 | **SQLite** como almacenamiento | Archivo JSON; CSV | Lo eligió el autor. Tiene transacciones atómicas (`BEGIN IMMEDIATE`) y `AUTOINCREMENT`, que no reutiliza IDs | La BD es un archivo binario ignorado por git: los datos no se versionan |
| D3 | **CLI** con argparse | API REST local | Lo eligió el autor. Es lo más simple de probar con subprocesos y de documentar | No hay servidor. Cada comando es un proceso, así que "reiniciar la aplicación" equivale a ejecutar otro comando |
| D4 | **Intervalos semiabiertos `[inicio, fin)`** con una única función `se_superpone` | Intervalos cerrados; una consulta SQL con un `WHERE` equivalente | Cumple "permitir límites consecutivos". Tener una sola función garantiza que la disponibilidad y la reserva usen las mismas reglas (RN10) | La superposición se filtra en Python sobre las reservas activas de la unidad. Para un laboratorio pequeño, el costo no importa |
| D5 | **Cancelar = UPDATE de estado**, nunca DELETE | Mover la reserva a una tabla histórica | Conserva el ID y los datos (R4) con un único modelo | `listar` muestra activas y canceladas; se filtra con `--estado` |
| D6 | **El "ahora" se puede inyectar** (`ahora=` en la API y `RESERVAS_AHORA` en el CLI) | Mockear `datetime` | Pruebas deterministas aunque cambie la fecha real (S8) | Las pruebas fijan 2026-11-30 08:00 y siguen siendo válidas en el futuro |
| D7 | **Rechazar fechas pasadas y duraciones de más de 12 h** (S3, S4) | Permitirlas; 8 h | El autor lo confirmó en el checkpoint 1 | La disponibilidad también rechaza esas entradas (RN10) |
| D8 | **IDs `R-NNNN` derivados de `AUTOINCREMENT`**, sin reutilizarse tras un reinicio (S6, v1.1) | Reiniciar la numeración en R-0001 | Lo eligió el autor en el Episodio 2: un ID viejo anotado en una planilla nunca debe señalar otra reserva | CA-16 |
| D9 | **Hora del laboratorio = UTC−3 fijo** (S1, v1.2) | `datetime.now()` local; `zoneinfo` | Lo aceptó el autor en el Episodio 3. `zoneinfo` en Windows requiere `tzdata`, que no es parte de la biblioteca estándar. Argentina no usa horario de verano | Si Argentina volviera a usar horario de verano, habría que cambiar `ZONA_LABORATORIO` |
| D10 | **Errores de inventario o BD → `ErrorAlmacenamiento`** (`ERROR:` + código 1) | Dejar el traceback | Episodio 3, hallazgos #1 y #2 | Mensajes comprensibles y códigos de salida coherentes |

## Parte B: Tres episodios reales de delegación

Cada episodio sigue la misma cadena: objetivo → contexto e instrucción → resultado del agente → decisión humana → evidencia. Todos los commits pertenecen a la rama `main` entregada.

### Episodio 1: implementación del núcleo (agente principal)
- **Objetivo y requisito.** Implementar R1–R6 y RN1–RN11 de la especificación v1: inventario, disponibilidad, reservar, cancelar, persistencia y listado.
- **Contexto e instrucción.**
  - Contexto: `docs/especificacion.md` v1, aprobada por el autor; `docs/interfaz.md`; y `CLAUDE.md`, con sus reglas de dominio y su procedimiento de persistencia.
  - Extracto de la instrucción (`CLAUDE.md`):
    > "Existe **una única función** `se_superpone()` [...] Tanto `reservar` como `disponibilidad` deben usarla [...] Toda escritura dentro de una transacción `BEGIN IMMEDIATE`; la verificación de superposición y el `INSERT` ocurren en la **misma** transacción."
- **Acción y resultado del agente.**
  - Creó `src/reservas/` (dominio, repositorio SQLite, servicio y CLI), `data/inventario.json`, `pyproject.toml` y `requirements-dev.txt`.
  - Probó el CLI con el ejemplo literal de la consigna, con una BD temporal y `RESERVAS_AHORA=2026-11-30 08:00`.
  - MIC-01 de 10:30 a 11:30 dio `ERROR` con código 1; MIC-01 de 11:00 a 12:00 dio `CREADA R-0002`; MIC-02 de 10:00 a 11:00 dio `CREADA R-0003`.
  - Después de `cancelar R-0001`, la consulta de MIC-01 de 10:00 a 11:00 dio `DISPONIBLE`.
- **Decisión humana: aceptar.**
  - El autor aprobó el commit. Primero lo había rechazado sin querer y después confirmó: "Hacé los commits igual".
  - Motivo: el comportamiento coincide con el ejemplo de la consigna.
  - Este episodio no se corrigió en ese momento. Los defectos que tenía aparecieron recién en los episodios 2 y 3.
- **Evidencia.**
  - Commit `8e68a63` ([src/reservas/](../src/reservas/)).
  - La prueba rápida está registrada en `docs/progreso.md` (Etapa 2).
  - Las pruebas `test_ca_01_*`, `test_ca_02_*`, `test_ca_04_*` y `test_ca_05_*` la cubren hoy.

### Episodio 2: suite de pruebas desde la especificación (subagente `redactor-pruebas`)
- **Objetivo y requisito.** Las pruebas automáticas que exige la consigna: creación válida, superposición, límites consecutivos, unidades distintas, entradas inválidas, cancelación y persistencia, es decir, CA-01…CA-15.
- **Contexto e instrucción.**
  - Contexto: la especificación, la interfaz y `CLAUDE.md`. **Se le excluyó `src/`.**
  - Extracto de la instrucción:
    > "NO leas nada dentro de `src/` [...] Si alguna prueba falla, NO modifiques `src/` ni 'arregles' la prueba para que pase: reportá cuál falla [...]"
- **Acción y resultado del agente.**
  - Escribió 114 pruebas en 10 archivos.
  - Informó `3 failed, 111 passed`. Las 3 fallas venían de que `Disponibilidad.conflictos` devolvía una `tuple` y el contrato dice `list`.
  - También listó 11 ambigüedades de la especificación.
  - El agente principal **re-ejecutó** las pruebas y confirmó el resultado: `3 failed, 111 passed in 99.13s`.
- **Decisión humana: corregir la implementación, no las pruebas.**
  - Motivo: el contrato publicado manda.
  - Además, el autor decidió aclarar la ambigüedad S6/S9 (IDs después de un reinicio). Así salió la especificación v1.1 con CA-16.
  - Las demás ambigüedades no se aclararon en ese momento.
- **Evidencia.**
  - `d76aeb4`: pruebas con 3 fallas.
  - `ed6385c`: corrección; `114 passed`.
  - `1f29ccb`: especificación v1.1 y `test_ca_16_ids_no_se_reutilizan_tras_reiniciar`.
  - Detalle en [evidencia/episodio2-redactor-pruebas.md](evidencia/episodio2-redactor-pruebas.md).

### Episodio 3: auditoría de reglas (subagente `revisor-reglas`, solo lectura)
- **Objetivo y requisito.** Comprobar que el código cumple RN1–RN11 y S1–S9, sin requisitos ocultos, y que los errores del CLI son coherentes (§8 de la especificación).
- **Contexto e instrucción.**
  - Contexto: todo el repositorio, sin escritura ni ejecución.
  - Extracto de la instrucción:
    > "auditá `src/` contra el checklist de 7 ítems [...] casos borde de fechas [...] ¿hay excepciones no capturadas que produzcan traceback en vez de `ERROR:` + exit 1? [...] No inventes problemas: si un ítem está bien, decí 'OK' con la evidencia."
- **Acción y resultado del agente.**
  - Informó 13 hallazgos: 0 de severidad alta, 2 de media y 11 de baja.
  - La checklist de reglas centrales dio OK: `se_superpone` única, mismas reglas en reserva y disponibilidad, transacción y ausencia de DELETE.
  - El agente principal **reprodujo** cinco hallazgos ejecutando código. Los #1, #2, #8 y #13 se confirmaron.
  - El **#7 resultó correcto solo en parte**. Los dígitos no ASCII ya se rechazaban; los espacios alrededor de la fecha, en cambio, sí se aceptaban.
- **Decisión humana: aceptar los 4 grupos.**
  - A: errores sin traceback.
  - B: entradas estrictas.
  - C: documentar la interfaz.
  - D: zona horaria y rutas.
  - Motivo: robustez y una especificación sin requisitos ocultos.
  - Se aplicaron las correcciones, y el agente principal escribió las pruebas de regresión `tests/test_revision.py`.
- **Evidencia.**
  - Commit `7f502bd`: especificación v1.2, `docs/interfaz.md` y `tests/test_revision.py` (23 pruebas).
  - Resultado: `138 passed in 154.13s`.
  - Detalle en [evidencia/episodio3-revisor-reglas.md](evidencia/episodio3-revisor-reglas.md).
