<#
  genera-varianti.ps1 - rigenera le skin precompilate skin\Aurora-NNN.vlt (e i relativi .json con le
  dimensioni delle finestre) a partire da skin\src\build_aurora.py. Serve Python 3 con Pillow:
      winget install Python.Python.3.12
      python -m pip install pillow
  Uso: genera-varianti.cmd            (scale 100 125 150 175 200)
       genera-varianti.cmd 150        (solo alcune scale)
#>
[CmdletBinding()]
param([int[]]$Scale = @(100, 125, 150, 175, 200))
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'comuni.ps1')
$script:LogFile = Join-Path $KitRoot 'esporta.log'
$src = Join-Path $KitRoot 'skin\src'

Scrivi-Titolo 'Generazione delle varianti della skin'
$py = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $py) { Scrivi-Errore 'python non trovato: winget install Python.Python.3.12  e poi  python -m pip install pillow'; exit 1 }
$eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
$pil = & python.exe -c "import PIL; print(PIL.__version__)" 2>&1 | ForEach-Object { "$_" }
$ErrorActionPreference = $eap
if ($LASTEXITCODE -ne 0) { Scrivi-Errore 'Pillow non installato:  python -m pip install pillow'; exit 1 }
Scrivi-Ok ('Python ' + $py.Version + ', Pillow ' + ($pil -join ' '))

foreach ($pct in $Scale) {
    $k = ([double]$pct / 100).ToString([System.Globalization.CultureInfo]::InvariantCulture)
    Scrivi-Info ('scala ' + $k + ' ...')
    $env:AURORA_SCALE = $k
    Push-Location $src
    try {
        $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        $out = & python.exe build_aurora.py 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
        $ErrorActionPreference = $eap
    } finally { Pop-Location }
    if ($code -ne 0) { Scrivi-Errore ('build fallita per la scala ' + $k + ': ' + ($out -join ' ')); continue }
    Copy-Item -LiteralPath (Join-Path $src 'Aurora.vlt') -Destination (Join-Path $KitRoot ('skin\Aurora-{0}.vlt' -f $pct)) -Force
    Copy-Item -LiteralPath (Join-Path $src 'Aurora.json') -Destination (Join-Path $KitRoot ('skin\Aurora-{0}.json' -f $pct)) -Force
    Scrivi-Ok ('Aurora-{0}.vlt  ({1})' -f $pct, ($out | Select-Object -Last 1))
}
Remove-Item Env:\AURORA_SCALE -ErrorAction SilentlyContinue
