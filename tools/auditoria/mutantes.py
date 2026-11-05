"""Prueba de mutantes manual: ¿las pruebas detectan defectos reales en las reglas?

Para cada mutante:
  1. copia src/, tests/, data/ y pyproject.toml a un directorio temporal;
  2. inyecta UN defecto en la copia (reemplazo exacto de texto);
  3. corre pytest sobre la copia con PYTHONPATH=<copia>/src (así el CLI de los
     subprocesos también usa el código mutado);
  4. informa DETECTADO (alguna prueba falló) o SOBREVIVIÓ (todas pasaron).

No modifica el src/ real. Uso (desde la raíz del repo):
    .venv/Scripts/python tools/auditoria/mutantes.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

# (id, descripción, archivo relativo a src/reservas, texto original, texto mutado)
MUTANTES = [
    ("M1", "se_superpone con <= (rompe límites consecutivos)", "dominio.py",
     "return a_inicio < b_fin and b_inicio < a_fin",
     "return a_inicio <= b_fin and b_inicio <= a_fin"),
    ("M2", "conflictos ignora el estado (cancelada sigue bloqueando)", "dominio.py",
     "r for r in reservas if r.bloquea and se_superpone(",
     "r for r in reservas if se_superpone("),
    ("M3", "acepta inicio == fin", "dominio.py",
     "if not inicio < fin:",
     "if inicio > fin:"),
    ("M4", "acepta solicitante vacío o solo espacios", "dominio.py",
     "    if not limpio:\n        raise ErrorValidacion(\"El solicitante no puede estar vacío",
     "    if False:\n        raise ErrorValidacion(\"El solicitante no puede estar vacío"),
    ("M5", "reservar no rechaza superposiciones", "servicio.py",
     "if choques:",
     "if False:"),
    ("M6", "cancelar borra la reserva (DELETE) en vez de conservarla", "repositorio.py",
     "\"UPDATE reservas SET estado = ?, cancelada_en = ? WHERE num = ? AND estado = ?\"",
     "\"DELETE FROM reservas WHERE ?1 IS NOT NULL AND ?2 IS NOT NULL AND num = ?3 AND ?4 IS NOT NULL\""),
    ("M7", "no valida que la unidad exista", "servicio.py",
     "if unidad not in self._unidades:",
     "if False:"),
    ("M8", "las escrituras no se confirman (ROLLBACK en lugar de COMMIT)", "repositorio.py",
     "con.execute(\"COMMIT\")",
     "con.execute(\"ROLLBACK\")"),
    ("M9", "disponibilidad ignora las reservas activas", "servicio.py",
     "return Disponibilidad(unidad, ini, fi, dominio.conflictos(ini, fi, activas))",
     "return Disponibilidad(unidad, ini, fi, [])"),
]


def preparar_copia(destino: Path) -> None:
    for carpeta in ("src", "tests", "data"):
        shutil.copytree(RAIZ / carpeta, destino / carpeta,
                        ignore=shutil.ignore_patterns("__pycache__", "*.db"))
    shutil.copy2(RAIZ / "pyproject.toml", destino / "pyproject.toml")


def entorno(copia: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(copia / "src")
    env["PYTHONIOENCODING"] = "utf-8"
    env.pop("RESERVAS_DB", None)
    env.pop("RESERVAS_AHORA", None)
    return env


def correr(id_, descripcion, archivo, original, mutado) -> tuple[str, str, float]:
    with tempfile.TemporaryDirectory(prefix=f"mutante_{id_}_") as tmp:
        copia = Path(tmp)
        preparar_copia(copia)
        objetivo = copia / "src" / "reservas" / archivo
        texto = objetivo.read_text(encoding="utf-8")
        if texto.count(original) != 1:
            return "ERROR", f"texto original no encontrado exactamente una vez en {archivo}", 0.0
        objetivo.write_text(texto.replace(original, mutado), encoding="utf-8")
        env = entorno(copia)

        # Comprobación: el intérprete de los subprocesos importa el código mutado.
        origen = subprocess.run([sys.executable, "-c", "import reservas; print(reservas.__file__)"],
                                capture_output=True, text=True, env=env, cwd=copia).stdout.strip()
        if not origen.startswith(str(copia)):
            return "ERROR", f"el subproceso no usa la copia mutada ({origen})", 0.0

        t0 = time.time()
        res = subprocess.run([sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider"],
                             capture_output=True, text=True, encoding="utf-8", env=env, cwd=copia,
                             timeout=900)
        dur = time.time() - t0
        lineas = [l for l in res.stdout.splitlines() if l.strip()]
        fallida = next((l.split(" - ")[0].replace("FAILED ", "") for l in lineas if l.startswith("FAILED")), "")
        resumen = lineas[-1] if lineas else res.stderr.strip()[-200:]
        if res.returncode == 0:
            return "SOBREVIVIÓ", resumen, dur
        return "DETECTADO", f"{fallida} | {resumen}", dur


def main() -> int:
    print(f"Prueba de mutantes sobre {RAIZ}")
    print(f"Python {sys.version.split()[0]}  ·  {len(MUTANTES)} mutantes  ·  pytest -x por mutante\n")
    resultados = []
    for m in MUTANTES:
        estado, detalle, dur = correr(*m)
        resultados.append((m[0], m[1], estado, detalle, dur))
        print(f"{m[0]}  {estado:<11} {dur:6.1f}s  {m[1]}")
        print(f"      {detalle}")
    detectados = sum(1 for r in resultados if r[2] == "DETECTADO")
    print(f"\nRESULTADO: {detectados}/{len(MUTANTES)} mutantes detectados por las pruebas")
    return 0 if detectados == len(MUTANTES) else 1


if __name__ == "__main__":
    sys.exit(main())
