# Evidencia del Episodio 2: informe del subagente `redactor-pruebas`

Este archivo es un extracto del informe final que devolvió el subagente el 2026-11-05. No es la transcripción completa.

- **Commit con las pruebas tal como las entregó el subagente:** `d76aeb4`.
- **Commit con la corrección:** `ed6385c`.

## Instrucción dada (extracto)
> Actuás como el subagente `redactor-pruebas` [...] PRIMERO leé tu definición en `.claude/agents/redactor-pruebas.md` [...] **NO leas nada dentro de `src/`** [...] Escribí la suite pytest completa que cubra los criterios CA-01 a CA-15 [...] Si alguna prueba falla, NO modifiques `src/` ni "arregles" la prueba para que pase: reportá cuál falla [...]

**Contexto que recibió:**
- `docs/especificacion.md` (v1)
- `docs/interfaz.md`
- `CLAUDE.md`
- su propia definición

**Contexto excluido:** `src/`.

## Resultado informado por el subagente
- Creó 10 archivos en `tests/` con 114 pruebas, mapeadas a CA-01…CA-15 y a los códigos de salida 0, 1 y 2.
- La ejecución que informó fue `3 failed, 111 passed in 131.85s`.
- Las 3 pruebas que fallan dan el mismo error:
  ```
  >       assert d.conflictos == []
  E       assert () == []
  ```
- Su diagnóstico: "una diferencia entre la implementación y `docs/interfaz.md`, no un error en las reglas de disponibilidad".
- Señaló 11 ambigüedades en la especificación y no resolvió ninguna. Entre ellas:
  - Si la numeración de los IDs vuelve a empezar después de `reiniciar-datos`.
  - Qué tipo de excepción corresponde a cada error.
  - El valor de `creada_en` y `cancelada_en`.
  - El código de salida de `listar --estado` con un valor inválido.
  - El formato exacto de las columnas de `listar`.

## Comprobación del agente principal (ejecutada)
```
$ .venv/Scripts/python -m pytest -q
FAILED tests/test_cancelacion.py::test_ca_11_cancelar_libera_el_intervalo
FAILED tests/test_disponibilidad.py::test_ca_13_consecutivo_disponible
FAILED tests/test_disponibilidad.py::test_ca_13_otra_unidad_disponible
3 failed, 111 passed in 99.13s
```

## Decisión humana
- **Corregir la implementación, no las pruebas.** Motivo: el contrato `docs/interfaz.md` manda. El cambio se hizo en `ed6385c`. Después de la corrección, la ejecución dio `114 passed in 138.24s`.
- De las ambigüedades, se aclara solo la de los IDs después de `reiniciar-datos`. Eso dio la especificación v1.1 y el criterio CA-16 (commit `1f29ccb`). Las demás quedaron sin cambios en ese momento. Varias se resolvieron después, en el Episodio 3: el formato de `listar` y la validación de `--estado`/`--unidad` (S10).
