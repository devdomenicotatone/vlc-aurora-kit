<#
  pubblica-release.ps1 - costruisce l'EXE (crea-exe.ps1), crea il tag di versione e pubblica una Release su
  GitHub con l'EXE e il file SHA256SUMS.txt allegati. Serve GitHub CLI autenticata (gh auth login).
  Uso: pubblica.cmd 1.0.0 ["note della versione"]
  Le modifiche al kit vanno prima committate e pubblicate (esporta.cmd -Push oppure git).
#>
[CmdletBinding()]
param([Parameter(Mandatory = $true)][string]$Versione, [string]$Note = '')
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'comuni.ps1')
$script:LogFile = Join-Path $KitRoot 'esporta.log'
if ($Versione -notmatch '^\d+\.\d+\.\d+$') { Scrivi-Errore 'La versione deve avere la forma 1.2.3'; exit 1 }
if (-not (Get-Command gh.exe -ErrorAction SilentlyContinue)) { Scrivi-Errore 'GitHub CLI non trovata: winget install GitHub.cli  e poi  gh auth login'; exit 1 }
if (-not (Get-Command git.exe -ErrorAction SilentlyContinue)) { Scrivi-Errore 'git non trovato: winget install Git.Git'; exit 1 }

& (Join-Path $PSScriptRoot 'crea-exe.ps1') -Versione $Versione
$exe = Join-Path $KitRoot 'dist\VLC-Aurora-Setup.exe'
$sums = Join-Path $KitRoot 'dist\SHA256SUMS.txt'
if (-not (Test-Path -LiteralPath $exe)) { Scrivi-Errore 'EXE non creato'; exit 1 }
$hash = ((Get-Content -LiteralPath $sums -Raw) -split '\s+')[0]
if ($Note -eq '') {
    $Note = "Installer con un clic del kit VLC Aurora: VLC 3.x, skin Aurora, YouTube con yt-dlp, menu Blu-ray (Java), finestre scure, interfaccia web Aurora e regola firewall.`n`n" +
            "1. Scarica VLC-Aurora-Setup.exe e avvialo.`n" +
            "2. Windows SmartScreen puo' avvisare perche' il file non e' firmato: Ulteriori informazioni -> Esegui comunque.`n" +
            "3. Approva la richiesta di amministratore (una sola volta).`n`n" +
            "Per toglierlo: Impostazioni -> App -> App installate -> Kit VLC Aurora -> Disinstalla.`n`n" +
            "SHA-256 di VLC-Aurora-Setup.exe: " + $hash
}
Scrivi-Titolo ('Release v' + $Versione)
Push-Location $KitRoot
try {
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $sporco = & git status --porcelain 2>&1 | ForEach-Object { "$_" }
    if ($sporco) { Scrivi-Avviso 'Ci sono modifiche non committate: la release usera'' l''ultimo commit pubblicato, il pacchetto EXE invece i file attuali.' }
    & git tag -a ('v' + $Versione) -m ('Versione ' + $Versione) 2>&1 | ForEach-Object { Scrivi-Info "$_" }
    & git push origin ('v' + $Versione) 2>&1 | ForEach-Object { Scrivi-Info "$_" }
    $out = & gh release create ('v' + $Versione) $exe $sums --title ('Kit VLC Aurora ' + $Versione) --notes $Note 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $eap
    if ($code -ne 0) { Scrivi-Errore ('gh release create: ' + ($out -join ' ')); exit 1 }
    Scrivi-Ok ('pubblicata: ' + (($out | Where-Object { $_ -like 'http*' }) -join ' '))
} finally { Pop-Location }
