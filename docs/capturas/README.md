# Capturas de funcionamiento

Son capturas de pantalla **reales**: cada escenario se ejecutó en una ventana nueva de PowerShell, se capturó con la API `PrintWindow` de Windows y después se cerró la ventana. Todo lo hace [`tools/capturas/capturar.ps1`](../../tools/capturas/capturar.ps1). Se tomaron el 2026-11-05 en Windows 10, con Python 3.14.2 y pytest 9.2.0.

> Estas imágenes **complementan** las pruebas, pero no las reemplazan, como pide la consigna. La evidencia que se puede reproducir está en los comandos de abajo, en [`../verificacion.md`](../verificacion.md) y en [`../auditoria-pruebas.md`](../auditoria-pruebas.md).

**Condiciones de las capturas:**
- Las reservas se guardan en una base de demostración, `%TEMP%\reservas-capturas\demo.db`. Nunca se usa `data/reservas.db`.
- El "ahora" está fijado con `RESERVAS_AHORA="2026-11-30 08:00"`.
- Los solicitantes son ficticios.
- Las capturas 04 a 08 se ejecutan en este orden y comparten la misma base de datos. La 06 abre una ventana nueva, en un proceso nuevo, para mostrar la persistencia.

**Commits sobre los que se tomaron:**
- 02, 03 y 09: commit `34e8743`.
- 01 y 04–08: commit `adb7542`. Se volvieron a capturar después de agrandar la ventana.

Entre esos commits y `ab1ee6f` (la auditoría de pruebas) solo cambiaron archivos de `tools/`: `src/` y `tests/` son idénticos.

| Archivo | Qué muestra | Resultado visible | Cómo reproducirla |
|---|---|---|---|
| [01-entorno.png](01-entorno.png) | Versiones de Python y pytest, último commit y estado del árbol | Python 3.14.2, pytest 9.2.0, rama `main` | `capturar.ps1 -Solo '01'` |
| [02-pytest-completo.png](02-pytest-completo.png) | La suite completa de pruebas automáticas | `148 passed in 138.61s`, exit 0 | `.venv\Scripts\python -m pytest -q` |
| [03-pytest-verificaciones-consigna.png](03-pytest-verificaciones-consigna.png) | 15 pruebas representativas de las 7 verificaciones que exige la consigna | `15 passed, 133 deselected` | `capturar.ps1 -Solo '03'` |
| [04-ejemplo-consigna.png](04-ejemplo-consigna.png) | El ejemplo literal de la consigna | MIC-01 de 10 a 11 se crea; de 10:30 a 11:30 da **ERROR** (exit 1); de 11 a 12 se crea; MIC-02 de 10 a 11 se crea | `capturar.ps1 -Solo '04'` |
| [05-cancelacion.png](05-cancelacion.png) | Cancelación que conserva el registro y libera el horario | NO DISPONIBLE → `CANCELADA R-0001` → DISPONIBLE; `listar` sigue mostrando R-0001 como `cancelada` | `capturar.ps1 -Solo '04','05'` |
| [06-persistencia-nueva-ventana.png](06-persistencia-nueva-ventana.png) | Un **proceso nuevo** (otro PID) sobre la misma base de datos | Las 3 reservas aparecen con su estado, y la activa R-0002 sigue bloqueando su horario | `capturar.ps1 -Solo '04','05','06'` |
| [07-entradas-invalidas.png](07-entradas-invalidas.png) | Entradas inválidas: unidad desconocida, solicitante vacío, fecha inexistente, inicio posterior al fin, fecha pasada, más de 12 h y cancelación repetida | 7 × `ERROR:` con exit 1 | `capturar.ps1 -Solo '04','05','07'` |
| [08-reiniciar-datos.png](08-reiniciar-datos.png) | `reiniciar-datos` sin `--confirmar` | ERROR con exit 1; `listar` sigue mostrando las 3 reservas | `capturar.ps1 -Solo '04','05','08'` |
| [09-auditoria-mutantes.png](09-auditoria-mutantes.png) | Prueba de mutantes: 9 defectos inyectados en una copia del proyecto | `9/9 mutantes detectados` | `.venv\Scripts\python tools\auditoria\mutantes.py` |

Para regenerar todas las capturas, en Windows:
```powershell
powershell -ExecutionPolicy Bypass -File tools\capturas\capturar.ps1
```
Durante la ejecución se abren y se cierran ventanas. El proceso completo tarda unos 8 minutos, porque incluye la suite de pruebas y la prueba de mutantes.
