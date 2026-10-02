<#
  disinstalla.ps1 - Kit "VLC Aurora": toglie tutto quello che installa.ps1 ha messo e rimette le cose com'erano.

  Fase 1 (utente):          stato dell'installazione (%LOCALAPPDATA%\VLC-Aurora-Kit\stato.json), scelta sui programmi,
                            conferma, chiusura di VLC, richiesta dei diritti di amministratore (una sola finestra UAC).
  Fase 2 (amministratore):  plugin skins2 ufficiale al posto di quello del kit, regola firewall, skin / script YouTube /
                            interfaccia web tolti dal profilo, opzioni di vlcrc e vlc-qt-interface.ini e chiavi di
                            registro Java riportate a com'erano, VLC e Java disinstallati con winget (solo se richiesto).
  Fase 3 (utente):          riepilogo, yt-dlp (solo se richiesto), voce in "App installate" e cartella del kit rimosse.

  Le opzioni di VLC cambiate dopo l'installazione restano come sono; il resto del profilo di VLC (altre skin,
  cronologia, altre opzioni) non viene toccato. Se il kit era stato installato da una versione senza stato.json,
  le sue opzioni tornano al valore predefinito di VLC.
  -SoloVerifica               mostra cosa verrebbe fatto senza modificare nulla e senza chiedere i diritti di amministratore.
  -Programmi Tutti|Kit|Nessuno  programmi da disinstallare (VLC, Java Temurin 17 JRE, yt-dlp) senza chiederlo:
                              tutti, solo quelli installati dal kit, nessuno.
  -Si                         non chiede la conferma iniziale.
  -Pausa                      aspetta INVIO prima di chiudere la finestra (avvio da "App installate").
#>
[CmdletBinding()]
param(
    [switch]$Elevato,
    [string]$UserAppData = '',
    [string]$UserLocalAppData = '',
    [string]$Log = '',
    [string]$FileEsito = '',
    [switch]$RimuoviVlc,
    [switch]$RimuoviJava,
    [ValidateSet('', 'Tutti', 'Kit', 'Nessuno')][string]$Programmi = '',
    [switch]$SoloVerifica,
    [switch]$Si,
    [switch]$Pausa
)
$ErrorActionPreference = 'Stop'
$argomentiAttuali = @()
foreach ($k in $PSBoundParameters.Keys) {
    $v = $PSBoundParameters[$k]
    if ($v -is [switch]) { if ($v.IsPresent) { $argomentiAttuali += ('-' + $k) } }
    else { $argomentiAttuali += ('-' + $k); $argomentiAttuali += [string]$v }
}
if ((-not [Environment]::Is64BitProcess) -and [Environment]::Is64BitOperatingSystem) {
    # avviati da un processo a 32 bit: Program Files e registro sarebbero quelli WOW64
    $ps64 = Join-Path $env:SystemRoot 'Sysnative\WindowsPowerShell\v1.0\powershell.exe'
    if (Test-Path -LiteralPath $ps64) {
        & $ps64 -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath @argomentiAttuali
        exit $LASTEXITCODE
    }
}
. (Join-Path $PSScriptRoot 'comuni.ps1')
if ($UserAppData -eq '') { $UserAppData = $env:APPDATA }
if ($UserLocalAppData -eq '') { $UserLocalAppData = $env:LOCALAPPDATA }
$CartellaKit = Join-Path $UserLocalAppData $NomeCartellaKit
$ProfiloVlc = Join-Path $UserAppData 'vlc'

if (-not $Elevato -and -not $SoloVerifica -and ($KitRoot -eq $CartellaKit)) {
    # Avviato dalla copia installata ("App installate"): quella cartella alla fine va rimossa, quindi si riparte
    # da una copia temporanea degli script, nella stessa finestra.
    $tmp = Join-Path $env:TEMP ('vlc-kit-disinstalla-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
    Copia-Cartella (Join-Path $KitRoot 'scripts') (Join-Path $tmp 'scripts') @() @()
    if ($Log -eq '') { $argomentiAttuali += @('-Log', (Join-Path $env:TEMP 'VLC-Aurora-Kit-disinstalla.log')) }
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $tmp 'scripts\disinstalla.ps1') @argomentiAttuali
    $codice = $LASTEXITCODE
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
    exit $codice
}

if ($Log -eq '') { $Log = Join-Path $KitRoot 'disinstalla.log' }
$script:LogFile = $Log
if ($FileEsito -eq '') { $FileEsito = Join-Path $KitRoot 'disinstalla.esito.json' }

# Stato scritto dall'installer. Per le installazioni fatte prima che esistesse si ripiega sui valori del kit:
# le opzioni di config\vlcrc.opzioni tornano al predefinito di VLC e nessun programma risulta "installato dal kit".
$stato = Apri-Stato $CartellaKit $ProfiloVlc
$opzioniKit = Leggi-Opzioni (Join-Path $KitRoot 'config\vlcrc.opzioni')
foreach ($k in $opzioniKit.Keys) { if (-not $stato.Vlcrc.Contains($k)) { $stato.Vlcrc[$k] = [ordered]@{ Prima = $null; Kit = $opzioniKit[$k] } } }
foreach ($k in @('skins2-last', 'skins2-config', 'http-password')) {
    if (-not $stato.Vlcrc.Contains($k)) { $stato.Vlcrc[$k] = [ordered]@{ Prima = $null; Kit = $null } }
}
if ($null -eq $stato.Vlcrc['skins2-last'].Kit) { $stato.Vlcrc['skins2-last'].Kit = Join-Path $ProfiloVlc 'skins2\Aurora.vlt' }
$fileSha = Join-Path $KitRoot 'plugin\libskins2_plugin.dll.sha256'
if (Test-Path -LiteralPath $fileSha) {
    $h = ((Get-Content -LiteralPath $fileSha -Raw) -split '\s+')[0].ToUpper()
    if ($h -and $stato.PluginSha256 -notcontains $h) { [void]$stato.PluginSha256.Add($h) }
}

function Esito-Passo([string]$Fatto, [string]$InVerifica) { if ($SoloVerifica) { return $InVerifica } return $Fatto }

function Disinstalla-ConWinget([string]$Id) {
    $r = Invoke-Winget @('uninstall', '--id', $Id, '-e', '--silent', '--accept-source-agreements', '--disable-interactivity')
    if ($r.Codice -ne 0) { throw ('winget non e'' riuscito a disinstallare ' + $Id + ': ' + $r.Testo.Trim().Split("`n")[-1]) }
}

# ====================================================================== passi della fase amministrativa
# Con -SoloVerifica gli stessi passi girano nella fase utente e descrivono soltanto che cosa farebbero.
$PassiSistema = @(
    @{ Nome = 'Plugin skins2 ufficiale (plugins\gui)'; Azione = {
        $exe = Trova-VlcExe
        $gui = Join-Path (Split-Path -Parent $exe) 'plugins\gui'
        $dll = Join-Path $gui 'libskins2_plugin.dll'
        $orig = $dll + '.orig'
        if (-not (Test-Path -LiteralPath $dll)) { return 'VLC non installato: niente da rimettere' }
        if (Firma-Valida $dll) {
            # la dll e' gia' quella di VideoLAN (kit mai installato qui, o VLC aggiornato dopo): la copia .orig e' superata
            if (-not (Test-Path -LiteralPath $orig)) { return 'il plugin e'' gia'' quello ufficiale di VLC' }
            if (-not $SoloVerifica) { Remove-Item -LiteralPath $orig -Force }
            return ('il plugin e'' gia'' quello ufficiale di VLC; ' + (Esito-Passo 'tolta la copia .orig' 'la copia .orig verrebbe tolta'))
        }
        if (-not (Test-Path -LiteralPath $orig)) {
            if ($stato.PluginSha256 -contains (Get-FileHash -LiteralPath $dll -Algorithm SHA256).Hash) {
                throw 'c''e'' il plugin del kit ma manca libskins2_plugin.dll.orig: per riavere l''ufficiale reinstalla VLC (winget install VideoLAN.VLC --force)'
            }
            return 'il plugin non e'' quello del kit: lasciato com''e'''
        }
        $vOrig = (Get-Item -LiteralPath $orig).VersionInfo.ProductVersion
        $vVlc = (Get-Item -LiteralPath $exe).VersionInfo.ProductVersion
        if ($vOrig -and $vVlc -and $vOrig -ne $vVlc) {
            throw ('la copia .orig e'' di un''altra versione di VLC ({0}, installata {1}): non la rimetto. Reinstalla VLC (winget install VideoLAN.VLC --force)' -f $vOrig, $vVlc)
        }
        if ($SoloVerifica) { return 'libskins2_plugin.dll.orig verrebbe rimesso al posto del plugin del kit (cache dei plugin rigenerata)' }
        try {
            Copy-Item -LiteralPath $orig -Destination $dll -Force
        } catch {
            throw ('copia non riuscita (VLC ancora aperto o permessi): ' + $_.Exception.Message)
        }
        Remove-Item -LiteralPath $orig -Force
        Rigenera-CachePlugin $exe
        return 'rimesso il plugin ufficiale di VLC (cache dei plugin rigenerata)'
    } },

    @{ Nome = 'Regola firewall interfaccia web'; Azione = {
        $fatti = @()
        $regola = Get-NetFirewallRule -DisplayName $NomeRegolaFirewall -ErrorAction SilentlyContinue
        if ($regola) {
            if (-not $SoloVerifica) { $regola | Remove-NetFirewallRule }
            $fatti += (Esito-Passo 'regola rimossa' 'la regola verrebbe rimossa')
        } else { $fatti += 'regola non presente' }
        # le regole di blocco di Windows per vlc.exe che l'installer aveva disattivato tornano attive
        foreach ($n in $stato.RegoleFirewall) {
            $r = Get-NetFirewallRule -Name $n -ErrorAction SilentlyContinue
            if ($r -and $r.Enabled -eq 'False') {
                if (-not $SoloVerifica) { Enable-NetFirewallRule -Name $n }
                $fatti += ((Esito-Passo 'riattivata la regola di blocco "{0}"' 'la regola di blocco "{0}" verrebbe riattivata') -f $r.DisplayName)
            }
        }
        return ($fatti -join '; ')
    } },

    @{ Nome = 'Skin Aurora, script YouTube e interfaccia web nel profilo'; Azione = {
        $skins = Join-Path $ProfiloVlc 'skins2'
        $voci = @(
            (Join-Path $skins 'Aurora.vlt'), (Join-Path $skins 'aurora-src'), (Join-Path $ProfiloVlc 'lua\playlist\youtube.lua'),
            (Join-Path $ProfiloVlc 'lua\http'), (Join-Path $ProfiloVlc $NomeFileInfo)
        )
        # le varianti di scala copiate a mano accanto ad Aurora.vlt (Aurora-100.vlt, Aurora-150.vlt...)
        $voci += @(Get-ChildItem -LiteralPath $skins -File -Filter 'Aurora-*.vlt' -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^Aurora-\d+\.vlt$' } | ForEach-Object { $_.FullName })
        $tolti = @()
        foreach ($v in $voci) {
            if (Test-Path -LiteralPath $v) {
                if (-not $SoloVerifica) { Remove-Item -LiteralPath $v -Recurse -Force }
                $tolti += $v.Substring($ProfiloVlc.Length + 1)
            }
        }
        # quello che c'era prima del kit, tenuto da parte dall'installer
        $rimessi = @()
        $prima = Join-Path $CartellaKit 'prima'
        if (Test-Path -LiteralPath (Join-Path $prima 'youtube.lua')) {
            if (-not $SoloVerifica) {
                New-Item -ItemType Directory -Path (Join-Path $ProfiloVlc 'lua\playlist') -Force | Out-Null
                Copy-Item -LiteralPath (Join-Path $prima 'youtube.lua') -Destination (Join-Path $ProfiloVlc 'lua\playlist\youtube.lua') -Force
            }
            $rimessi += 'lua\playlist\youtube.lua'
        }
        if (Test-Path -LiteralPath (Join-Path $prima 'lua-http')) {
            if (-not $SoloVerifica) { Copia-Cartella (Join-Path $prima 'lua-http') (Join-Path $ProfiloVlc 'lua\http') @() @() }
            $rimessi += 'lua\http'
        }
        # cartelle rimaste vuote
        foreach ($d in @('lua\playlist', 'lua', 'skins2')) {
            $p = Join-Path $ProfiloVlc $d
            if (-not $SoloVerifica -and (Test-Path -LiteralPath $p) -and -not (Get-ChildItem -LiteralPath $p -Force)) { Remove-Item -LiteralPath $p -Force }
        }
        $msg = 'nessun file del kit nel profilo'
        if ($tolti.Count -gt 0) { $msg = (Esito-Passo 'tolti: ' 'verrebbero tolti: ') + ($tolti -join ', ') }
        if ($rimessi.Count -gt 0) { $msg += (Esito-Passo '; rimessi quelli di prima del kit: ' '; verrebbero rimessi quelli di prima del kit: ') + ($rimessi -join ', ') }
        return $msg
    } },

    @{ Nome = 'Opzioni di VLC (vlcrc)'; Azione = {
        $cambi = @(Ripristina-OpzioniVlcrc (Join-Path $ProfiloVlc 'vlcrc') $stato.Vlcrc -SoloVerifica:$SoloVerifica)
        foreach ($c in $cambi) { Scrivi-Info $c }
        if ($cambi.Count -eq 0) { return 'nessuna opzione del kit da riportare indietro' }
        return ((Esito-Passo '{0} opzioni riportate a com''erano prima del kit' '{0} opzioni verrebbero riportate a com''erano prima del kit') -f $cambi.Count)
    } },

    @{ Nome = 'Stile delle finestre Qt (vlc-qt-interface.ini)'; Azione = {
        $prima = $null
        if ($stato.QtStyle) { $prima = $stato.QtStyle.Prima }
        return (Ripristina-QtStyle (Join-Path $ProfiloVlc 'vlc-qt-interface.ini') $prima -SoloVerifica:$SoloVerifica)
    } },

    @{ Nome = 'Chiavi di registro Java e JAVA_HOME'; Azione = {
        # solo i valori che l'installer ha annotato di aver cambiato, e solo se valgono ancora quello che ha messo lui
        $fatti = @()
        foreach ($v in $stato.Registro) {
            if (-not (Test-Path $v.Chiave)) { continue }
            $cur = (Get-ItemProperty -Path $v.Chiave -Name $v.Nome -ErrorAction SilentlyContinue).($v.Nome)
            if ($null -eq $cur -or $cur -ne $v.Kit) { continue }
            if (-not $SoloVerifica) {
                if ($null -ne $v.Prima) { New-ItemProperty -Path $v.Chiave -Name $v.Nome -Value $v.Prima -PropertyType String -Force | Out-Null }
                else { Remove-ItemProperty -Path $v.Chiave -Name $v.Nome -Force }
            }
            $fatti += ((Split-Path -Leaf $v.Chiave) + '\' + $v.Nome)
        }
        foreach ($k in @($stato.ChiaviCreate | Sort-Object Length -Descending)) {
            if (-not (Test-Path $k)) { continue }
            $chiave = Get-Item -Path $k
            # in verifica i valori qui sopra non sono stati tolti davvero: la chiave puo' non risultare ancora vuota
            if ($chiave.SubKeyCount -eq 0 -and $chiave.ValueCount -eq 0) {
                if (-not $SoloVerifica) { Remove-Item -Path $k -Force }
                $fatti += ('chiave ' + (Split-Path -Leaf $k))
            }
        }
        if ($stato.JavaHome -and [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine') -eq $stato.JavaHome.Kit) {
            if (-not $SoloVerifica) { [Environment]::SetEnvironmentVariable('JAVA_HOME', $stato.JavaHome.Prima, 'Machine') }
            $fatti += 'JAVA_HOME'
        }
        if ($fatti.Count -eq 0) { return 'nessuna modifica del kit da annullare (le chiavi servono al JRE installato)' }
        return ((Esito-Passo 'riportati a com''erano: ' 'verrebbero riportati a com''erano: ') + ($fatti -join ', '))
    } },

    @{ Nome = 'VLC media player'; Azione = {
        $exe = Trova-VlcExe
        if (-not (Test-Path -LiteralPath $exe)) { return 'non installato' }
        if (-not $RimuoviVlc) { return ('resta installato (versione ' + (Versione-Vlc $exe).Testo + ')') }
        if ($SoloVerifica) { return 'verrebbe disinstallato con winget (il profilo %APPDATA%\vlc resta)' }
        $dir = Split-Path -Parent $exe
        Disinstalla-ConWinget 'VideoLAN.VLC'
        # il disinstallatore di VLC continua per qualche secondo dopo che winget e' tornato
        for ($i = 0; $i -lt 60 -and (Test-Path -LiteralPath $exe); $i++) { Start-Sleep -Seconds 1 }
        if (Test-Path -LiteralPath $exe) { throw ('winget ha finito ma vlc.exe c''e'' ancora in ' + $dir) }
        # file non suoi che il disinstallatore di VLC lascia nella sua cartella (es. la cache dei plugin rigenerata)
        if ((Test-Path -LiteralPath $dir) -and $dir -match '\\VideoLAN\\VLC\\?$') {
            Start-Sleep -Seconds 2
            Remove-Item -LiteralPath $dir -Recurse -Force -ErrorAction SilentlyContinue
            $madre = Split-Path -Parent $dir
            if ((Test-Path -LiteralPath $madre) -and -not (Get-ChildItem -LiteralPath $madre -Force)) { Remove-Item -LiteralPath $madre -Force -ErrorAction SilentlyContinue }
        }
        return 'disinstallato (il profilo %APPDATA%\vlc resta, senza le cose del kit)'
    } },

    @{ Nome = 'Java Temurin 17 JRE'; Azione = {
        $jre = Trova-Jre17
        if (-not $jre) { return 'non installato' }
        if (-not $RimuoviJava) { return ('resta installato (' + $jre + ')') }
        if ($SoloVerifica) { return 'verrebbe disinstallato con winget' }
        Disinstalla-ConWinget 'EclipseAdoptium.Temurin.17.JRE'
        # quello che nel registro punta ancora al JRE appena tolto
        $radice = 'HKLM:\SOFTWARE\JavaSoft\JRE'
        if (Test-Path $radice) {
            foreach ($sk in @(Get-ChildItem -Path $radice)) {
                $casa = (Get-ItemProperty -Path $sk.PSPath -Name JavaHome -ErrorAction SilentlyContinue).JavaHome
                if ($casa -and -not (Test-Path -LiteralPath $casa)) { Remove-Item -Path $sk.PSPath -Recurse -Force }
            }
            $corrente = (Get-ItemProperty -Path $radice -Name CurrentVersion -ErrorAction SilentlyContinue).CurrentVersion
            if ($corrente -and -not (Test-Path (Join-Path $radice $corrente))) { Remove-ItemProperty -Path $radice -Name CurrentVersion -Force }
            foreach ($k in @($radice, (Split-Path -Parent $radice))) {
                $chiave = Get-Item -Path $k
                if ($chiave.SubKeyCount -eq 0 -and $chiave.ValueCount -eq 0) { Remove-Item -Path $k -Force }
            }
        }
        $javaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine')
        if ($javaHome -and $javaHome -like '*\Eclipse Adoptium\jre-17*' -and -not (Test-Path -LiteralPath $javaHome)) {
            [Environment]::SetEnvironmentVariable('JAVA_HOME', $null, 'Machine')
        }
        return 'disinstallato'
    } }
)

# ====================================================================== FASE 2: amministratore
if ($Elevato) {
    Logga ('--- fase amministrativa della disinstallazione (utente ' + $env:USERNAME + ', profilo ' + $UserAppData + ')')
    Write-Host ''
    Write-Host '  Kit VLC Aurora - disinstallazione, fase amministrativa' -ForegroundColor White
    if (-not (Test-Path -LiteralPath $UserAppData)) { Scrivi-Errore 'Profilo utente non indicato o inesistente.'; exit 1 }
    $Passi = New-Object System.Collections.ArrayList
    foreach ($p in $PassiSistema) { Esegui-Passo $p.Nome $p.Azione }
    $ko = @($Passi | Where-Object { $_.Stato -eq 'KO' }).Count
    [PSCustomObject]@{ Passi = $Passi; Log = $Log; Errori = $ko } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $FileEsito -Encoding UTF8
    Logga ('--- fine fase amministrativa, errori: ' + $ko)
    if ($ko -gt 0) { exit 1 } else { exit 0 }
}

# ====================================================================== FASE 1 e 3: utente
function Esci([int]$Codice) {
    if ($Pausa) { Write-Host ''; Read-Host '  Premi INVIO per chiudere' | Out-Null }
    exit $Codice
}

Write-Host ''
Write-Host '  Kit VLC Aurora - disinstallazione' -ForegroundColor White
Logga ('--- avvio disinstallazione (utente ' + $env:USERNAME + ')')
if ($SoloVerifica) { Scrivi-Avviso 'Modalita'' SOLO VERIFICA: nessuna modifica verra'' effettuata.' }

Scrivi-Titolo 'Che cosa viene tolto'
Scrivi-Info ('skin Aurora, script YouTube e interfaccia web nel profilo di VLC (' + $ProfiloVlc + ')')
Scrivi-Info 'opzioni del kit in vlcrc e vlc-qt-interface.ini: tornano com''erano, quelle cambiate dopo restano'
Scrivi-Info 'plugin skins2 del kit (torna quello ufficiale di VLC), regola firewall, chiavi di registro Java messe dal kit'
Scrivi-Info 'voce "Kit VLC Aurora" in "App installate" e cartella del kit'
Scrivi-Info 'Il resto del profilo di VLC (altre skin, cronologia, altre opzioni) non viene toccato.'
if (-not (Test-Path -LiteralPath (Join-Path $CartellaKit 'stato.json'))) {
    Scrivi-Avviso 'Installazione senza stato.json (versione precedente del kit): le opzioni del kit tornano al valore predefinito di VLC.'
}

# --- programmi: restano, a meno che non venga chiesto di toglierli
Scrivi-Titolo 'Programmi installati'
$vlcExe = Trova-VlcExe
$jre = Trova-Jre17
$pacchetti = Pacchetti-WingetUtente
$delKit = { param($si) if ($si) { return 'installato dal kit' } return 'c''era gia'' prima del kit, o non e'' noto chi l''ha installato' }
$presenti = 0; $messiDalKit = 0
if (Test-Path -LiteralPath $vlcExe) { $presenti++; if ($stato.Vlc) { $messiDalKit++ }; Scrivi-Info ('VLC media player ' + (Versione-Vlc $vlcExe).Testo + ': ' + (& $delKit $stato.Vlc)) }
if ($jre) { $presenti++; if ($stato.Java) { $messiDalKit++ }; Scrivi-Info ('Java Temurin 17 JRE: ' + (& $delKit $stato.Java)) }
$ytDelKit = @($stato.PacchettiUtente | Where-Object { $pacchetti -contains $_ })
if ($pacchetti -contains 'yt-dlp.yt-dlp') {
    $presenti++
    if ($ytDelKit.Count -gt 0) { $messiDalKit++; Scrivi-Info ('yt-dlp: installato dal kit (pacchetti winget: ' + ($ytDelKit -join ', ') + ')') }
    else { Scrivi-Info ('yt-dlp: ' + (& $delKit $false)) }
}
if ($presenti -eq 0) { Scrivi-Info 'nessuno (VLC, Java Temurin 17 JRE e yt-dlp non risultano installati)' }
if ($Programmi -eq '') {
    $Programmi = 'Nessuno'
    if ($SoloVerifica) { Scrivi-Info 'Restano installati. Per vedere anche la loro rimozione: -Programmi Tutti  oppure  -Programmi Kit' }
    elseif ($presenti -gt 0) {
        $domanda = 'Disinstallo anche i programmi? [T] tutti   [N] nessuno'
        if ($messiDalKit -gt 0) { $domanda = 'Disinstallo anche i programmi? [T] tutti   [K] solo quelli installati dal kit   [N] nessuno' }
        $risp = Read-Host ('  ' + $domanda)
        if ($risp -match '^[tT]') { $Programmi = 'Tutti' } elseif ($risp -match '^[kK]' -and $messiDalKit -gt 0) { $Programmi = 'Kit' }
    }
}
$RimuoviVlc = ($Programmi -eq 'Tutti') -or ($Programmi -eq 'Kit' -and $stato.Vlc)
$RimuoviJava = ($Programmi -eq 'Tutti') -or ($Programmi -eq 'Kit' -and $stato.Java)
$pacchettiDaTogliere = @()
if ($Programmi -ne 'Nessuno') { $pacchettiDaTogliere = @($ytDelKit) }
if ($Programmi -eq 'Tutti' -and $pacchetti -contains 'yt-dlp.yt-dlp' -and $pacchettiDaTogliere -notcontains 'yt-dlp.yt-dlp') { $pacchettiDaTogliere += 'yt-dlp.yt-dlp' }
$daTogliere = @()
if ($RimuoviVlc -and (Test-Path -LiteralPath $vlcExe)) { $daTogliere += 'VLC media player' }
if ($RimuoviJava -and $jre) { $daTogliere += 'Java Temurin 17 JRE' }
$daTogliere += $pacchettiDaTogliere
if ($daTogliere.Count -gt 0) { Scrivi-Avviso ('Da disinstallare: ' + ($daTogliere -join ', ')) } elseif ($presenti -gt 0) { Scrivi-Ok 'I programmi restano installati.' }

$vlcAperto = [bool](Get-Process vlc -ErrorAction SilentlyContinue)

if ($SoloVerifica) {
    if ($vlcAperto) { Scrivi-Avviso 'VLC e'' aperto: verrebbe chiuso prima di cominciare.' }
    $Passi = New-Object System.Collections.ArrayList
    foreach ($p in $PassiSistema) { Esegui-Passo $p.Nome $p.Azione }
    Scrivi-Titolo 'yt-dlp, voce in "App installate" e cartella del kit'
    if ($pacchettiDaTogliere.Count -gt 0) { Scrivi-Info ('verrebbero disinstallati con winget: ' + ($pacchettiDaTogliere -join ', ')) }
    if ($stato.AccessBridge -and -not (Test-AccessBridgeAttivo)) { Scrivi-Info 'il Java Access Bridge, che il kit aveva disattivato, verrebbe riattivato' }
    if (Test-Path $ChiaveDisinstallazione) { Scrivi-Info 'la voce "Kit VLC Aurora" verrebbe tolta da "App installate"' } else { Scrivi-Info 'voce in "App installate" non presente' }
    if (Test-Path -LiteralPath $CartellaKit) { Scrivi-Info ($CartellaKit + ' verrebbe rimossa') } else { Scrivi-Info ($CartellaKit + ' non presente') }
    Write-Host ''
    Scrivi-Ok 'Verifica completata. Esegui disinstalla.cmd senza -SoloVerifica per applicare.'
    Esci 0
}

Write-Host ''
if ($vlcAperto) { Scrivi-Avviso 'VLC e'' aperto: verra'' chiuso.' }
if (-not $Si) {
    $risp = Read-Host '  Procedo con la disinstallazione? [S/N]'
    if ($risp -notmatch '^[sSyY]') { Scrivi-Avviso 'Disinstallazione annullata: nulla e'' stato modificato.'; Esci 2 }
}
if ($vlcAperto) { Chiudi-Vlc; Scrivi-Ok 'VLC chiuso.' }

Scrivi-Titolo 'Diritti di amministratore'
Scrivi-Info 'Si apre una seconda finestra: approva la richiesta di Windows (UAC). Serve per il plugin di VLC, il firewall e il registro.'
Remove-Item -LiteralPath $FileEsito -Force -ErrorAction SilentlyContinue
$argomenti = @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $PSCommandPath),
    '-Elevato', '-UserAppData', ('"{0}"' -f $UserAppData), '-UserLocalAppData', ('"{0}"' -f $UserLocalAppData),
    '-Log', ('"{0}"' -f $Log), '-FileEsito', ('"{0}"' -f $FileEsito)
)
if ($RimuoviVlc) { $argomenti += '-RimuoviVlc' }
if ($RimuoviJava) { $argomenti += '-RimuoviJava' }
try {
    $p = Start-Process -FilePath 'powershell.exe' -ArgumentList ($argomenti -join ' ') -Verb RunAs -Wait -PassThru
} catch {
    Scrivi-Errore 'Richiesta di amministratore annullata o negata: nulla e'' stato modificato.'
    Esci 3
}

Scrivi-Titolo 'Riepilogo'
if (-not (Test-Path -LiteralPath $FileEsito)) {
    Scrivi-Errore ('La fase amministrativa non ha prodotto un esito. Controlla il log: ' + $Log)
    Esci 1
}
$esito = Get-Content -LiteralPath $FileEsito -Raw -Encoding UTF8 | ConvertFrom-Json
Remove-Item -LiteralPath $FileEsito -Force -ErrorAction SilentlyContinue
foreach ($s in $esito.Passi) {
    if ($s.Stato -eq 'OK') { Scrivi-Ok ($s.Passo + ': ' + $s.Dettaglio) } else { Scrivi-Errore ($s.Passo + ': ' + $s.Dettaglio) }
}
$errori = [int]$esito.Errori

# --- yt-dlp e le sue dipendenze: pacchetti winget in ambito utente, quindi senza diritti di amministratore
foreach ($id in $pacchettiDaTogliere) {
    try { Disinstalla-ConWinget $id; Scrivi-Ok ($id + ': disinstallato') }
    catch { Scrivi-Errore $_.Exception.Message; $errori++ }
}

if ($errori -gt 0) {
    Scrivi-Info ('Log completo: ' + $Log)
    Scrivi-Avviso 'Completata con errori: vedi le righe [KO]. La voce in "App installate" resta, per poter riprovare.'
    Esci 1
}

# --- Java Access Bridge: se l'aveva disattivato il kit torna attivo (impostazione dell'utente, niente amministratore)
if ($stato.AccessBridge -and -not (Test-AccessBridgeAttivo)) {
    if (Imposta-AccessBridge $true) { Scrivi-Ok 'Java Access Bridge riattivato: lo aveva disattivato il kit.' }
    else { Scrivi-Avviso 'Java Access Bridge non riattivato (lo aveva disattivato il kit): a mano, jabswitch.exe -enable.' }
}

# --- voce in "App installate" e cartella del kit (stato, copia del disinstallatore, file tenuti da parte)
Remove-Item -Path $ChiaveDisinstallazione -Recurse -Force -ErrorAction SilentlyContinue
if ((Test-Path -LiteralPath $CartellaKit) -and $KitRoot -ne $CartellaKit) { Remove-Item -LiteralPath $CartellaKit -Recurse -Force -ErrorAction SilentlyContinue }
Scrivi-Ok 'Voce in "App installate" e cartella del kit rimosse.'
Scrivi-Info ('Log completo: ' + $Log)
Write-Host ''
Scrivi-Ok 'Disinstallazione completata.'
Esci 0
