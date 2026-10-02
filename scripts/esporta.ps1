<#
  esporta.ps1 - aggiorna il kit con quello che c'e' sul PC attuale:
    - lua\playlist\youtube.lua dal profilo VLC
    - sorgenti della skin (skins2\aurora-src) in skin\src
    - valori attuali delle opzioni elencate in config\vlcrc.opzioni (password e posizioni escluse)
  -Varianti  rigenera anche le skin precompilate (serve Python 3 con Pillow)
  -Push      esegue git add/commit/push nel repository del kit
#>
[CmdletBinding()]
param([switch]$Varianti, [switch]$Push, [string]$Messaggio = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'comuni.ps1')
$script:LogFile = Join-Path $KitRoot 'esporta.log'
$Profilo = Join-Path $env:APPDATA 'vlc'

function Hash([string]$f) { if (Test-Path -LiteralPath $f) { return (Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash } return '' }

Write-Host ''
Write-Host '  Kit VLC Aurora - esportazione dal profilo di questo PC' -ForegroundColor White
Write-Host ('  Profilo VLC: ' + $Profilo) -ForegroundColor Gray

Scrivi-Titolo 'Script YouTube'
$da = Join-Path $Profilo 'lua\playlist\youtube.lua'; $a = Join-Path $KitRoot 'lua\playlist\youtube.lua'
if (Test-Path -LiteralPath $da) {
    if ((Hash $da) -ne (Hash $a)) { Copy-Item -LiteralPath $da -Destination $a -Force; Scrivi-Ok 'youtube.lua aggiornato nel kit' } else { Scrivi-Ok 'youtube.lua identico, nulla da fare' }
} else { Scrivi-Avviso 'youtube.lua non presente nel profilo' }

Scrivi-Titolo 'Sorgenti della skin'
$src = Join-Path $Profilo 'skins2\aurora-src'
if (Test-Path -LiteralPath $src) {
    Copia-Cartella $src (Join-Path $KitRoot 'skin\src') @('Aurora', '__pycache__') @('*.log', 'test-vlcrc', 'test.pid', 'Aurora.vlt', 'Aurora.json', '*.bak')
    Scrivi-Ok 'skins2\aurora-src copiato in skin\src'
} else { Scrivi-Avviso 'cartella aurora-src non presente nel profilo (sorgenti del kit lasciati com''erano)' }

Scrivi-Titolo 'Interfaccia web'
$httpDir = Join-Path $Profilo 'lua\http'
if (Test-Path -LiteralPath (Join-Path $httpDir 'aurora')) {
    Copy-Item -LiteralPath (Join-Path $httpDir 'index.html') -Destination (Join-Path $KitRoot 'web\index.html') -Force
    Copia-Cartella (Join-Path $httpDir 'aurora') (Join-Path $KitRoot 'web\aurora') @() @()
    Scrivi-Ok 'index.html e cartella aurora copiati in web'
} else { Scrivi-Avviso 'interfaccia web Aurora non presente nel profilo (file del kit lasciati com''erano)' }

Scrivi-Titolo 'Opzioni di vlcrc'
$fileOpz = Join-Path $KitRoot 'config\vlcrc.opzioni'
$opz = Leggi-Opzioni $fileOpz
$chiavi = @($opz.Keys | Where-Object { $_ -notin @('http-password', 'skins2-config', 'skins2-last') })
$attuali = Leggi-ValoriAttiviVlcrc (Join-Path $Profilo 'vlcrc') $chiavi
$righe = New-Object 'System.Collections.Generic.List[string]'
$righe.AddRange([string[]][System.IO.File]::ReadAllLines($fileOpz, [System.Text.Encoding]::UTF8))
$n = 0
for ($i = 0; $i -lt $righe.Count; $i++) {
    foreach ($k in $chiavi) {
        if ($righe[$i] -match ('^' + [regex]::Escape($k) + '=') -and $attuali.ContainsKey($k)) {
            $nuova = $k + '=' + $attuali[$k]
            if ($righe[$i] -ne $nuova) { Scrivi-Info ($righe[$i] + '  ->  ' + $nuova); $righe[$i] = $nuova; $n++ }
        }
    }
}
if ($n -gt 0) { Scrivi-Righe $fileOpz $righe; Scrivi-Ok ('{0} opzioni aggiornate in config\vlcrc.opzioni' -f $n) } else { Scrivi-Ok 'opzioni gia'' allineate' }

if ($Varianti) {
    & (Join-Path $PSScriptRoot 'genera-varianti.ps1')
}

if ($Push) {
    Scrivi-Titolo 'Git'
    if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { Scrivi-Errore 'git non trovato (winget install Git.Git)'; exit 1 }
    Push-Location $KitRoot
    try {
        $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        & git add -A 2>&1 | ForEach-Object { "$_" } | Out-Null
        $stato = & git status --porcelain 2>&1 | ForEach-Object { "$_" }
        if (-not $stato) { Scrivi-Ok 'nessuna modifica da pubblicare' }
        else {
            if ($Messaggio -eq '') { $Messaggio = 'Aggiornamento dal PC ' + $env:COMPUTERNAME + ' del ' + (Get-Date -Format 'yyyy-MM-dd') }
            & git commit -m $Messaggio 2>&1 | ForEach-Object { "$_" } | ForEach-Object { Scrivi-Info $_ }
            & git push 2>&1 | ForEach-Object { "$_" } | ForEach-Object { Scrivi-Info $_ }
            if ($LASTEXITCODE -eq 0) { Scrivi-Ok 'pubblicato su GitHub' } else { Scrivi-Errore 'push non riuscito (controlla accesso e rete)' }
        }
        $ErrorActionPreference = $eap
    } finally { Pop-Location }
}
Write-Host ''
Scrivi-Ok 'Esportazione completata.'
