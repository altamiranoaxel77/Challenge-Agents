<#
.SYNOPSIS
  Genera capturas de pantalla REALES de ventanas de PowerShell ejecutando las pruebas
  y el CLI del sistema de reservas. Guarda los PNG en docs/capturas/.

.DESCRIPTION
  Por cada escenario: escribe un .ps1 temporal, lo abre en una ventana de consola nueva
  (Start-Process powershell), espera a que termine (archivo marcador), captura la ventana
  con la API PrintWindow de user32 (fallback: CopyFromScreen) y la cierra.
  Las reservas usan una BD de demostración en %TEMP%\reservas-capturas (nunca data/reservas.db)
  y RESERVAS_AHORA="2026-11-30 08:00" para que la salida sea reproducible.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File tools\capturas\capturar.ps1
  powershell -ExecutionPolicy Bypass -File tools\capturas\capturar.ps1 -Solo 04,05,06
#>
param([string[]]$Solo = @())

$ErrorActionPreference = "Stop"
$Raiz = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$Py = Join-Path $Raiz ".venv\Scripts\python.exe"
$Salida = Join-Path $Raiz "docs\capturas"
$Tmp = Join-Path $env:TEMP "reservas-capturas"
New-Item -ItemType Directory -Force $Salida, $Tmp | Out-Null

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public static class Ventana {
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr h);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
}
"@
[Ventana]::SetProcessDPIAware() | Out-Null

# --- Encabezado común de cada escenario -------------------------------------------------
$Comun = @'
$ErrorActionPreference = "Continue"
$Host.UI.RawUI.WindowTitle = "Reservas de laboratorio - __TITULO__"
try {
    $Host.UI.RawUI.BufferSize = New-Object Management.Automation.Host.Size(120, 3000)
    $Host.UI.RawUI.WindowSize = New-Object Management.Automation.Host.Size(120, __ALTO__)
} catch {}
$Host.UI.RawUI.BackgroundColor = "Black"; $Host.UI.RawUI.ForegroundColor = "Gray"
chcp 65001 > $null
cmd /c color 07
[Console]::OutputEncoding = [Text.Encoding]::UTF8
Clear-Host
Set-Location "__RAIZ__"
$py = "__PY__"
function python { & $py @args }
$env:RESERVAS_DB = "__DB__"
$env:RESERVAS_AHORA = "2026-11-30 08:00"
Remove-Item Env:PYTHONIOENCODING -ErrorAction SilentlyContinue
function Paso([string]$cmd) {
    Write-Host ("PS " + (Get-Location).Path + "> ") -NoNewline -ForegroundColor DarkGray
    Write-Host $cmd -ForegroundColor Yellow
    Invoke-Expression $cmd
    $c = $LASTEXITCODE
    $color = if ($c -eq 0) { "Green" } else { "Red" }
    Write-Host ("  [exit " + $c + "]") -ForegroundColor $color
}
function Nota([string]$t) { Write-Host ("# " + $t) -ForegroundColor Cyan }
Nota "__TITULO__   ($(Get-Date -Format 'yyyy-MM-dd HH:mm'), RESERVAS_AHORA=2026-11-30 08:00)"
'@

$Db = Join-Path $Tmp "demo.db"

# --- Escenarios: id, archivo, título, alto de ventana, cuerpo ---------------------------
$Escenarios = @(
    @{ Id = "01"; Archivo = "01-entorno.png"; Titulo = "Entorno y versiones"; Alto = 22; Cuerpo = @'
Paso 'python --version'
Paso 'python -m pytest --version'
Paso 'git -c color.ui=never log -1 --format="%h %s (%ad)" --date=short | Out-String -Stream'
Paso 'git -c color.ui=never status --short --branch | Out-String -Stream'
'@ },
    @{ Id = "02"; Archivo = "02-pytest-completo.png"; Titulo = "Suite completa de pruebas automaticas"; Alto = 14; Cuerpo = @'
Paso 'python -m pytest -q -p no:cacheprovider'
'@ },
    @{ Id = "03"; Archivo = "03-pytest-verificaciones-consigna.png"; Titulo = "Pruebas de las 7 verificaciones exigidas por la consigna"; Alto = 36; Cuerpo = @'
Paso 'python -m pytest -v -p no:cacheprovider --no-header -k "ca_01_crear_reserva_valida or ca_02_rechaza_superposicion_parcial or ca_04_limites_consecutivos or ca_04_consecutivos_cruzando or ca_05_unidades or ca_06_unidad_desconocida[XYZ or ca_07_solicitante_vacio_se_rechaza[espacios or ca_08_inicio_mal_formado[abc or ca_09_inicio_no_anterior or ca_11_cancelar_conserva or ca_11_cancelar_libera or ca_14_listar_en_nuevo_proceso or ca_14_intervalo_cancelado or ca_14_activa_sigue"'
'@ },
    @{ Id = "04"; Archivo = "04-ejemplo-consigna.png"; Titulo = "Ejemplo de la consigna: superposicion, consecutivos y otra unidad"; Alto = 30; Cuerpo = @'
Remove-Item $env:RESERVAS_DB -ErrorAction SilentlyContinue
Nota "BD de demostracion nueva: $env:RESERVAS_DB"
Paso 'python -m reservas inventario'
Paso 'python -m reservas reservar MIC-01 "Ana Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"'
Paso 'python -m reservas reservar MIC-01 "Beto Ficticio" "2026-12-01 10:30" "2026-12-01 11:30"'
Paso 'python -m reservas reservar MIC-01 "Beto Ficticio" "2026-12-01 11:00" "2026-12-01 12:00"'
Paso 'python -m reservas reservar MIC-02 "Carla Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"'
'@ },
    @{ Id = "05"; Archivo = "05-cancelacion.png"; Titulo = "Cancelacion: conserva el registro y libera el horario"; Alto = 22; Cuerpo = @'
Paso 'python -m reservas disponibilidad MIC-01 "2026-12-01 10:00" "2026-12-01 11:00"'
Paso 'python -m reservas cancelar R-0001'
Paso 'python -m reservas disponibilidad MIC-01 "2026-12-01 10:00" "2026-12-01 11:00"'
Paso 'python -m reservas listar'
'@ },
    @{ Id = "06"; Archivo = "06-persistencia-nueva-ventana.png"; Titulo = "Persistencia: ventana y proceso NUEVOS sobre la misma BD"; Alto = 24; Cuerpo = @'
Nota ("Proceso PowerShell nuevo, PID " + $PID + ". La BD fue escrita por las ventanas anteriores, ya cerradas.")
Paso 'Get-Item $env:RESERVAS_DB | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize | Out-String -Stream | Where-Object { $_ }'
Paso 'python -m reservas listar'
Paso 'python -m reservas listar --estado cancelada'
Paso 'python -m reservas disponibilidad MIC-01 "2026-12-01 11:30" "2026-12-01 12:30"'
'@ },
    @{ Id = "07"; Archivo = "07-entradas-invalidas.png"; Titulo = "Entradas invalidas: se rechazan con ERROR y exit 1"; Alto = 36; Cuerpo = @'
Paso 'python -m reservas reservar XYZ-99 "Ana Ficticia" "2026-12-01 10:00" "2026-12-01 11:00"'
Paso 'python -m reservas reservar MIC-01 "   " "2026-12-03 10:00" "2026-12-03 11:00"'
Paso 'python -m reservas reservar MIC-01 "Ana Ficticia" "2026-02-30 10:00" "2026-02-30 11:00"'
Paso 'python -m reservas reservar MIC-01 "Ana Ficticia" "2026-12-03 11:00" "2026-12-03 10:00"'
Paso 'python -m reservas reservar MIC-01 "Ana Ficticia" "2026-11-29 10:00" "2026-11-29 11:00"'
Paso 'python -m reservas reservar MIC-01 "Ana Ficticia" "2026-12-03 08:00" "2026-12-03 20:01"'
Paso 'python -m reservas cancelar R-0001'
'@ },
    @{ Id = "08"; Archivo = "08-reiniciar-datos.png"; Titulo = "reiniciar-datos sin --confirmar no borra nada"; Alto = 16; Cuerpo = @'
Paso 'python -m reservas reiniciar-datos'
Paso 'python -m reservas listar'
'@ },
    @{ Id = "09"; Archivo = "09-auditoria-mutantes.png"; Titulo = "Auditoria: prueba de mutantes (defectos inyectados en una copia)"; Alto = 30; Cuerpo = @'
Paso 'python tools\auditoria\mutantes.py'
'@ }
)

function Capturar-Ventana([IntPtr]$hwnd, [string]$destino) {
    [Ventana]::SetForegroundWindow($hwnd) | Out-Null
    Start-Sleep -Milliseconds 800
    $r = New-Object Ventana+RECT
    [Ventana]::GetWindowRect($hwnd, [ref]$r) | Out-Null
    $w = $r.Right - $r.Left; $h = $r.Bottom - $r.Top
    $bmp = New-Object Drawing.Bitmap $w, $h
    $g = [Drawing.Graphics]::FromImage($bmp)
    $hdc = $g.GetHdc()
    $ok = [Ventana]::PrintWindow($hwnd, $hdc, 2)   # PW_RENDERFULLCONTENT
    $g.ReleaseHdc($hdc)
    if (-not $ok) { $g.CopyFromScreen($r.Left, $r.Top, 0, 0, $bmp.Size) }
    $g.Dispose()
    $bmp.Save($destino, [Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
}

foreach ($e in $Escenarios) {
    if ($Solo.Count -gt 0 -and $Solo -notcontains $e.Id) { continue }
    $marcador = Join-Path $Tmp ("listo-" + $e.Id)
    Remove-Item $marcador -ErrorAction SilentlyContinue
    $script = $Comun.Replace("__TITULO__", $e.Titulo).Replace("__ALTO__", [string]$e.Alto). `
        Replace("__RAIZ__", $Raiz).Replace("__PY__", $Py).Replace("__DB__", $Db)
    $script += "`n" + $e.Cuerpo + "`nSet-Content -Path '$marcador' -Value 'ok'`n"
    $archivoPs1 = Join-Path $Tmp ("escenario-" + $e.Id + ".ps1")
    Set-Content -Path $archivoPs1 -Value $script -Encoding UTF8

    Write-Host ("[" + $e.Id + "] " + $e.Titulo + " ...")
    $p = Start-Process powershell -PassThru -ArgumentList @("-NoProfile", "-NoExit", "-ExecutionPolicy", "Bypass", "-File", $archivoPs1)
    $limite = (Get-Date).AddMinutes(10)
    while (-not (Test-Path $marcador)) {
        if ((Get-Date) -gt $limite) { throw "Tiempo agotado en el escenario $($e.Id)" }
        Start-Sleep -Milliseconds 500
    }
    Start-Sleep -Milliseconds 700
    $p.Refresh()
    $hwnd = $p.MainWindowHandle
    if ($hwnd -eq [IntPtr]::Zero) { throw "No se encontró la ventana del escenario $($e.Id)" }
    $destino = Join-Path $Salida $e.Archivo
    Capturar-Ventana $hwnd $destino
    Stop-Process -Id $p.Id -Force
    Write-Host ("      -> " + $destino)
}
Write-Host "Listo. Capturas en $Salida"
