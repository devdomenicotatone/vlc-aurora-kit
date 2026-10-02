<#
  installa.ps1 - Kit "VLC Aurora": installa e configura VLC con un clic (dettagli nel README.md).

  Fase 1 (utente):          controlli, rilevamento della scala dello schermo, yt-dlp con winget (ambito utente),
                            chiusura di VLC se aperto, richiesta dei diritti di amministratore (una sola finestra UAC).
  Fase 2 (amministratore):  VLC 3.x e Java Temurin 17 con winget, chiavi di registro Java per i menu Blu-ray,
                            skin Aurora e script YouTube nel profilo dell'utente, opzioni in vlcrc e
                            vlc-qt-interface.ini, regola firewall per l'interfaccia web (porta 8080, reti private),
                            copia del disinstallatore in %LOCALAPPDATA%\VLC-Aurora-Kit.
  Fase 3 (utente):          riepilogo, password dell'interfaccia web, voce in "App installate", avvio di VLC.

  Ogni passo annota in %LOCALAPPDATA%\VLC-Aurora-Kit\stato.json che cosa c'era prima e che cosa ha messo il kit:
  e' quello che disinstalla.ps1 usa per rimettere le cose com'erano.
  Si puo' rieseguire senza danni (ogni passo controlla lo stato attuale).
  -SoloVerifica  mostra cosa verrebbe fatto senza modificare nulla e senza chiedere i diritti di amministratore.
  -SenzaAvvio    non avvia VLC alla fine.
  -LasciaAccessBridge  non disattiva il Java Access Bridge (serve a chi usa un lettore di schermo con i programmi
                 Java; finche' resta attivo i menu Java dei Blu-ray non partono in VLC).
#>
[CmdletBinding()]
param(
    [switch]$Elevato,
    [string]$UserAppData = '',
    [string]$UserLocalAppData = '',
    [int]$Scala = 0,
    [int]$SchermoW = 0,
    [int]$SchermoH = 0,
    [string]$Log = '',
    [switch]$SoloVerifica,
    [switch]$SenzaAvvio,
    [switch]$LasciaAccessBridge
)
$ErrorActionPreference = 'Stop'
if ((-not [Environment]::Is64BitProcess) -and [Environment]::Is64BitOperatingSystem) {
    # avviati da un processo a 32 bit (es. l'auto-estraente): Program Files e registro sarebbero quelli WOW64
    $ps64 = Join-Path $env:SystemRoot 'Sysnative\WindowsPowerShell\v1.0\powershell.exe'
    if (Test-Path -LiteralPath $ps64) {
        $args64 = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $PSCommandPath)
        foreach ($k in $PSBoundParameters.Keys) {
            $v = $PSBoundParameters[$k]
            if ($v -is [switch]) { if ($v.IsPresent) { $args64 += ('-' + $k) } }
            else { $args64 += ('-' + $k); $args64 += [string]$v }
        }
        & $ps64 @args64
        exit $LASTEXITCODE
    }
}
. (Join-Path $PSScriptRoot 'comuni.ps1')
if ($Log -eq '') { $Log = Join-Path $KitRoot 'installa.log' }
$script:LogFile = $Log
$FileEsito = Join-Path $KitRoot 'installa.esito.json'
if ($UserLocalAppData -eq '') { $UserLocalAppData = $env:LOCALAPPDATA }
$CartellaKit = Join-Path $UserLocalAppData $NomeCartellaKit

# ====================================================================== FASE 1 e 3: utente
if (-not $Elevato) {
    Write-Host ''
    Write-Host '  Kit VLC Aurora - installazione con un clic' -ForegroundColor White
    Write-Host ('  Cartella del kit: ' + $KitRoot) -ForegroundColor Gray
    Logga ('--- avvio installazione (utente ' + $env:USERNAME + ')')
    if ($SoloVerifica) { Scrivi-Avviso 'Modalita'' SOLO VERIFICA: nessuna modifica verra'' effettuata.' }

    Scrivi-Titolo 'Controlli preliminari'
    if ([Environment]::OSVersion.Version.Major -lt 10) { Scrivi-Errore 'Serve Windows 10 o 11.'; exit 1 }
    if (-not (Test-Winget)) {
        Scrivi-Errore 'winget non trovato. Installa "Programma di installazione app" dal Microsoft Store (o aggiorna Windows) e riprova.'
        exit 1
    }
    Scrivi-Ok ('winget ' + (Invoke-Winget @('--version')).Testo.Trim())
    $sch = Rileva-Schermo
    $pct = Scegli-Variante $sch.Percento
    Scrivi-Ok ('Schermo {0}x{1} pixel, scala di Windows {2}% -> skin Aurora-{3}' -f $sch.Larghezza, $sch.Altezza, $sch.Percento, $pct)
    $vlcExe = Trova-VlcExe
    if (Test-Path -LiteralPath $vlcExe) { Scrivi-Info ('VLC presente: ' + (Versione-Vlc $vlcExe).Testo + ' in ' + (Split-Path -Parent $vlcExe)) }
    else { Scrivi-Info 'VLC non ancora installato: verra'' installata l''ultima versione 3.x da winget.' }
    $stato = Apri-Stato $CartellaKit (Join-Path $env:APPDATA 'vlc')

    Scrivi-Titolo 'yt-dlp (riproduzione YouTube)'
    if ($SoloVerifica) {
        if (Winget-Installato 'yt-dlp.yt-dlp') { Scrivi-Info 'yt-dlp gia'' installato: verrebbe aggiornato all''ultima versione.' }
        else { Scrivi-Info 'yt-dlp verrebbe installato con winget (ambito utente).' }
    } else {
        if (Winget-Installato 'yt-dlp.yt-dlp') {
            $r = Invoke-Winget @('upgrade', '--id', 'yt-dlp.yt-dlp', '-e', '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity')
            if (Winget-Esito $r) { Scrivi-Ok 'yt-dlp aggiornato (o gia'' all''ultima versione).' } else { Scrivi-Avviso ('aggiornamento di yt-dlp non riuscito: ' + $r.Testo.Trim().Split("`n")[-1]) }
        } else {
            $pacchettiPrima = Pacchetti-WingetUtente
            $r = Invoke-Winget @('install', '--id', 'yt-dlp.yt-dlp', '-e', '--scope', 'user', '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity')
            if (Winget-Esito $r) { Scrivi-Ok 'yt-dlp installato (ambito utente).' } else { Scrivi-Avviso ('installazione di yt-dlp non riuscita: ' + $r.Testo.Trim().Split("`n")[-1]) }
            # per il disinstallatore: yt-dlp e le dipendenze che winget ha aggiunto con lui
            foreach ($id in (Pacchetti-WingetUtente)) {
                if ($pacchettiPrima -notcontains $id -and $stato.PacchettiUtente -notcontains $id) { [void]$stato.PacchettiUtente.Add($id) }
            }
        }
        $link = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Links\yt-dlp.exe'
        if (Test-Path -LiteralPath $link) { Scrivi-Info ('eseguibile: ' + $link) }
    }

    Scrivi-Titolo 'VLC in esecuzione'
    $proc = @(Get-Process vlc -ErrorAction SilentlyContinue)
    if ($proc.Count -gt 0) {
        if ($SoloVerifica) { Scrivi-Avviso 'VLC e'' aperto: verrebbe chiuso prima di applicare le opzioni.' }
        else {
            $risp = Read-Host 'VLC e'' aperto e va chiuso per applicare le opzioni. Lo chiudo adesso? [S/N]'
            if ($risp -notmatch '^[sSyY]') { Scrivi-Avviso 'Installazione interrotta su richiesta.'; exit 2 }
            Chiudi-Vlc
            Scrivi-Ok 'VLC chiuso.'
        }
    } else { Scrivi-Ok 'VLC non e'' in esecuzione.' }

    if ($SoloVerifica) {
        Scrivi-Titolo 'Anteprima delle modifiche al profilo (nessuna scrittura)'
        $app = Join-Path $env:APPDATA 'vlc'
        $prep = Prepara-OpzioniVlcrc -AppData $env:APPDATA -Pct $pct -Info (Leggi-InfoSkin $pct) -SchermoW $sch.Larghezza -SchermoH $sch.Altezza
        $cambi = @(Imposta-OpzioniVlcrc (Join-Path $app 'vlcrc') $prep.Opzioni -SoloVerifica)
        if ($cambi.Count -eq 0) { Scrivi-Info 'vlcrc: nessuna modifica necessaria' } else { foreach ($c in $cambi) { Scrivi-Info ('vlcrc: ' + $c) } }
        if ($prep.NuovaPassword) { Scrivi-Info 'vlcrc: verrebbe generata una nuova password per l''interfaccia web' }
        Scrivi-Info ('vlc-qt-interface.ini: ' + (Imposta-QtStyleFusion (Join-Path $app 'vlc-qt-interface.ini') -SoloVerifica))
        Scrivi-Info ('skin: skin\Aurora-{0}.vlt -> {1}' -f $pct, (Join-Path $app 'skins2\Aurora.vlt'))
        Scrivi-Info ('script: lua\playlist\youtube.lua -> ' + (Join-Path $app 'lua\playlist\youtube.lua'))
        Scrivi-Info ('interfaccia web: web\ + handler API di VLC -> ' + (Join-Path $app 'lua\http'))
        if (Test-Path -LiteralPath (Join-Path $KitRoot 'plugin\libskins2_plugin.dll')) {
            Scrivi-Info ('plugin Snap nativo: plugin\libskins2_plugin.dll -> ' + (Join-Path (Split-Path -Parent (Trova-VlcExe)) 'plugins\gui') + ' (backup .orig)')
        }
        $jre = @(Get-ChildItem -LiteralPath (Join-Path $env:ProgramFiles 'Eclipse Adoptium') -Directory -Filter 'jre-17*' -ErrorAction SilentlyContinue)
        if ($jre.Count -gt 0) { Scrivi-Info ('Java: presente ' + $jre[0].Name) } else { Scrivi-Info 'Java: Temurin 17 JRE verrebbe installato con winget' }
        if (Get-NetFirewallRule -DisplayName $NomeRegolaFirewall -ErrorAction SilentlyContinue) { Scrivi-Info ('firewall: regola "' + $NomeRegolaFirewall + '" gia'' presente') }
        else { Scrivi-Info ('firewall: verrebbe creata la regola "' + $NomeRegolaFirewall + '" (TCP 8080, reti private, solo vlc.exe)') }
        if (Test-AccessBridgeAttivo) {
            if ($LasciaAccessBridge) { Scrivi-Info 'Java Access Bridge: attivo, verrebbe lasciato com''e'' (i menu Java dei Blu-ray non partiranno)' }
            else { Scrivi-Info 'Java Access Bridge: attivo, verrebbe disattivato per questo utente (blocca i menu Java dei Blu-ray)' }
        } else { Scrivi-Info 'Java Access Bridge: non attivo, nulla da fare' }
        Scrivi-Info ('disinstallatore: verrebbe copiato in ' + $CartellaKit + ' e registrato in "App installate"')
        Write-Host ''
        Scrivi-Ok 'Verifica completata. Esegui installa.cmd senza -SoloVerifica per applicare.'
        exit 0
    }

    Scrivi-Titolo 'Diritti di amministratore'
    Scrivi-Info 'Si apre una seconda finestra: approva la richiesta di Windows (UAC). Serve per VLC, Java e la regola firewall.'
    Remove-Item -LiteralPath $FileEsito -Force -ErrorAction SilentlyContinue
    Salva-Stato $CartellaKit $stato
    $argomenti = @(
        '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', ('"{0}"' -f $PSCommandPath),
        '-Elevato', '-UserAppData', ('"{0}"' -f $env:APPDATA), '-UserLocalAppData', ('"{0}"' -f $env:LOCALAPPDATA),
        '-Scala', $pct, '-SchermoW', $sch.Larghezza, '-SchermoH', $sch.Altezza, '-Log', ('"{0}"' -f $Log)
    )
    try {
        $p = Start-Process -FilePath 'powershell.exe' -ArgumentList ($argomenti -join ' ') -Verb RunAs -Wait -PassThru
    } catch {
        Scrivi-Errore 'Richiesta di amministratore annullata o negata: installazione interrotta.'
        exit 3
    }

    Scrivi-Titolo 'Riepilogo'
    if (-not (Test-Path -LiteralPath $FileEsito)) {
        Scrivi-Errore ('La fase amministrativa non ha prodotto un esito. Controlla il log: ' + $Log)
        exit 1
    }
    $esito = Get-Content -LiteralPath $FileEsito -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($s in $esito.Passi) {
        if ($s.Stato -eq 'OK') { Scrivi-Ok ($s.Passo + ': ' + $s.Dettaglio) } else { Scrivi-Errore ($s.Passo + ': ' + $s.Dettaglio) }
    }
    if ($esito.Password) {
        Write-Host ''
        Write-Host ('  Password dell''interfaccia web (http://localhost:8080): ' + $esito.Password) -ForegroundColor White
        Write-Host ('  Salvata anche in ' + (Join-Path $env:APPDATA ('vlc\' + $NomeFileInfo))) -ForegroundColor Gray
    }
    # Java Access Bridge: e' un'impostazione dell'utente, quindi si tocca qui e non nella fase amministrativa.
    # Lo stato annota che l'ha disattivato il kit, cosi' il disinstallatore lo riattiva.
    if (Test-AccessBridgeAttivo) {
        if ($LasciaAccessBridge) {
            Scrivi-Avviso 'Java Access Bridge attivo e lasciato com''e'': i menu Java dei Blu-ray non partiranno in VLC.'
        } elseif (Imposta-AccessBridge $false) {
            try { $st = Apri-Stato $CartellaKit (Join-Path $env:APPDATA 'vlc'); $st.AccessBridge = $true; Salva-Stato $CartellaKit $st } catch { }
            Scrivi-Ok 'Java Access Bridge disattivato per questo utente: impediva ai menu Java dei Blu-ray di partire in VLC.'
            Scrivi-Info 'Serve solo ai lettori di schermo con i programmi Java. Per tenerlo: installa.cmd -LasciaAccessBridge'
        } else {
            Scrivi-Avviso 'Java Access Bridge attivo e non disattivato: i menu Java dei Blu-ray non partiranno. A mano: jabswitch.exe -disable (cartella bin di Java).'
        }
    }
    Scrivi-Info 'Dal telefono: menu della skin > Telecomando web, poi nella pagina il pulsante Telefono (codice QR).'
    # la regola firewall vale solo per le reti private: con la rete "Pubblica" il telefono non raggiunge il PC
    $pubbliche = @(Get-NetConnectionProfile -ErrorAction SilentlyContinue | Where-Object { $_.NetworkCategory -eq 'Public' })
    if ($pubbliche.Count -gt 0) {
        Scrivi-Avviso ('La rete "{0}" e'' impostata come Pubblica: dal telefono il telecomando non sara'' raggiungibile.' -f ($pubbliche[0].Name))
        Scrivi-Info 'Se e'' la rete di casa: Impostazioni > Rete e Internet > (la rete) > Tipo di profilo di rete > Rete privata.'
    }
    if (Test-Path -LiteralPath (Join-Path $CartellaKit 'scripts\disinstalla.ps1')) {
        try {
            Registra-Disinstallatore $CartellaKit (Join-Path $env:APPDATA 'vlc')
            Scrivi-Info 'Per togliere il kit: Impostazioni > App > App installate > Kit VLC Aurora > Disinstalla.'
        } catch { Scrivi-Avviso ('voce in "App installate" non creata: ' + $_.Exception.Message) }
    }
    Scrivi-Info ('Log completo: ' + $Log)
    if ($p.ExitCode -eq 0) {
        if (-not $SenzaAvvio) {
            $vlcExe = Trova-VlcExe
            if (Test-Path -LiteralPath $vlcExe) { Start-Process -FilePath $vlcExe | Out-Null; Scrivi-Ok 'VLC avviato con la skin Aurora.' }
        }
        Write-Host ''
        Scrivi-Ok 'Installazione completata.'
    } else {
        Scrivi-Avviso 'Completata con errori: vedi le righe [KO] e il log.'
    }
    exit $p.ExitCode
}

# ====================================================================== FASE 2: amministratore
Logga ('--- fase amministrativa (utente ' + $env:USERNAME + ', profilo di destinazione ' + $UserAppData + ')')
Write-Host ''
Write-Host '  Kit VLC Aurora - fase amministrativa' -ForegroundColor White
if ($UserAppData -eq '' -or -not (Test-Path -LiteralPath $UserAppData)) { Scrivi-Errore 'Profilo utente non indicato o inesistente.'; exit 1 }
$ProfiloVlc = Join-Path $UserAppData 'vlc'
$Passi = New-Object System.Collections.ArrayList
$script:PasswordNuova = $null
$stato = Apri-Stato $CartellaKit $ProfiloVlc

# --- 1. VLC
Esegui-Passo 'VLC media player' {
    $exe = Trova-VlcExe
    if (Test-Path -LiteralPath $exe) {
        $v = Versione-Vlc $exe
        if ($v.Major -ne 3) { Scrivi-Avviso ('VLC ' + $v.Testo + ' non e'' della serie 3: la skin Aurora e'' pensata per VLC 3.x.') }
        return ('gia'' installato (versione ' + $v.Testo + '), lasciato com''e''. Per aggiornare: winget upgrade VideoLAN.VLC')
    }
    $arg = @('install', '--id', 'VideoLAN.VLC', '-e', '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity')
    $v3 = Trova-VersioneVlc3
    if ($v3) { $arg += @('--version', $v3) } else { Scrivi-Avviso 'Nessuna versione 3.x trovata su winget: installo l''ultima disponibile (se e'' VLC 4 la skin potrebbe non funzionare).' }
    $r = Invoke-Winget $arg
    if (-not (Winget-Esito $r)) { throw ('winget non e'' riuscito a installare VLC: ' + $r.Testo.Trim().Split("`n")[-1]) }
    $exe = Trova-VlcExe
    if (-not (Test-Path -LiteralPath $exe)) { throw 'VLC risulta installato ma vlc.exe non si trova.' }
    $stato.Vlc = $true
    return ('installato VLC ' + (Versione-Vlc $exe).Testo)
}

# --- 2. Java per i menu Blu-ray (BD-J)
Esegui-Passo 'Java Temurin 17 JRE (menu dei Blu-ray)' {
    $jre = Trova-Jre17
    if ($jre) { return ('gia'' presente: ' + $jre) }
    $r = Invoke-Winget @('install', '--id', 'EclipseAdoptium.Temurin.17.JRE', '-e', '--accept-package-agreements', '--accept-source-agreements', '--disable-interactivity',
                         '--custom', 'ADDLOCAL=FeatureMain,FeatureEnvironment,FeatureJavaHome,FeatureOracleJavaSoft')
    if (-not (Winget-Esito $r)) { throw ('winget non e'' riuscito a installare Temurin 17: ' + $r.Testo.Trim().Split("`n")[-1]) }
    $jre = Trova-Jre17
    if (-not $jre) { throw 'Temurin risulta installato ma jvm.dll non si trova in Program Files\Eclipse Adoptium.' }
    $stato.Java = $true
    return ('installato in ' + $jre)
}

# --- 3. chiavi di registro che libbluray usa per trovare la JVM
function Crea-ChiaveRegistro([string]$Chiave) {
    # Crea la chiave se manca e la annota nello stato (insieme alle chiavi madri mancanti) per il disinstallatore.
    $mancanti = @(); $p = $Chiave
    while (-not (Test-Path $p)) { $mancanti += $p; $p = Split-Path -Parent $p }
    if ($mancanti.Count -eq 0) { return $false }
    New-Item -Path $Chiave -Force | Out-Null
    if ($stato.PrecedenteNoto) { foreach ($m in $mancanti) { if ($stato.ChiaviCreate -notcontains $m) { [void]$stato.ChiaviCreate.Add($m) } } }
    return $true
}
function Imposta-ValoreRegistro([string]$Chiave, [string]$Nome, [string]$Valore) {
    # Scrive il valore (stringa) se e' diverso e annota nello stato quello che c'era, solo la prima volta.
    $cur = (Get-ItemProperty -Path $Chiave -Name $Nome -ErrorAction SilentlyContinue).$Nome
    if ($cur -eq $Valore) { return $false }
    $voce = $stato.Registro | Where-Object { $_.Chiave -eq $Chiave -and $_.Nome -eq $Nome } | Select-Object -First 1
    if ($voce) { $voce.Kit = $Valore }
    elseif ($stato.PrecedenteNoto) { [void]$stato.Registro.Add([ordered]@{ Chiave = $Chiave; Nome = $Nome; Prima = $cur; Kit = $Valore }) }
    New-ItemProperty -Path $Chiave -Name $Nome -Value $Valore -PropertyType String -Force | Out-Null
    return $true
}
Esegui-Passo 'Chiavi di registro Java e JAVA_HOME' {
    $jre = Trova-Jre17
    if (-not $jre) { throw 'JRE 17 non trovato: passo saltato.' }
    $jreSlash = $jre.TrimEnd('\') + '\'
    $jvm = Join-Path $jre 'bin\server\jvm.dll'
    $ver = '17'
    if ((Split-Path -Leaf $jre) -match 'jre-(\d+(\.\d+)+)') { $ver = $Matches[1] }
    $fatti = @()
    $radice = 'HKLM:\SOFTWARE\JavaSoft\JRE'
    if (Crea-ChiaveRegistro $radice) { $fatti += 'JavaSoft\JRE' }
    if (Imposta-ValoreRegistro $radice 'CurrentVersion' '17') { $fatti += 'CurrentVersion=17' }
    foreach ($k in @('17', $ver)) {
        $p = Join-Path $radice $k
        [void](Crea-ChiaveRegistro $p)
        if (Imposta-ValoreRegistro $p 'JavaHome' $jreSlash) { $fatti += ('JRE\' + $k + '\JavaHome') }
        if (Imposta-ValoreRegistro $p 'RuntimeLib' $jvm) { $fatti += ('JRE\' + $k + '\RuntimeLib') }
    }
    $javaHome = [Environment]::GetEnvironmentVariable('JAVA_HOME', 'Machine')
    if ($javaHome -ne $jreSlash) {
        if ($stato.JavaHome) { $stato.JavaHome.Kit = $jreSlash }
        elseif ($stato.PrecedenteNoto) { $stato.JavaHome = [ordered]@{ Prima = $javaHome; Kit = $jreSlash } }
        [Environment]::SetEnvironmentVariable('JAVA_HOME', $jreSlash, 'Machine'); $fatti += 'JAVA_HOME'
    }
    if ($fatti.Count -eq 0) { return 'gia'' a posto (JavaSoft\JRE e JAVA_HOME puntano al JRE 17)' }
    return ('impostati: ' + ($fatti -join ', '))
}

# --- 4. skin, sorgenti e script YouTube nel profilo dell'utente
Esegui-Passo 'Skin Aurora e script YouTube nel profilo' {
    $skins = Join-Path $ProfiloVlc 'skins2'
    $luaDir = Join-Path $ProfiloVlc 'lua\playlist'
    foreach ($d in @($skins, $luaDir)) { if (-not (Test-Path -LiteralPath $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null } }
    $vlt = Join-Path $KitRoot ('skin\Aurora-{0}.vlt' -f $Scala)
    if (-not (Test-Path -LiteralPath $vlt)) { throw ('variante mancante: ' + $vlt) }
    Copy-Item -LiteralPath $vlt -Destination (Join-Path $skins 'Aurora.vlt') -Force
    Copia-Cartella (Join-Path $KitRoot 'skin\src') (Join-Path $skins 'aurora-src') @('Aurora', '__pycache__') @('*.log', 'test-vlcrc', 'test.pid', 'Aurora.vlt', 'Aurora.json')
    # uno youtube.lua che c'era gia' prima del kit va tenuto da parte: il disinstallatore lo rimette
    $lua = Join-Path $luaDir 'youtube.lua'
    $luaKit = Join-Path $KitRoot 'lua\playlist\youtube.lua'
    if ($null -eq $stato.YoutubeLua) {
        $stato.YoutubeLua = ($stato.PrecedenteNoto -and (Test-Path -LiteralPath $lua) -and
                             (Get-FileHash -LiteralPath $lua).Hash -ne (Get-FileHash -LiteralPath $luaKit).Hash)
        if ($stato.YoutubeLua) {
            New-Item -ItemType Directory -Path (Join-Path $CartellaKit 'prima') -Force | Out-Null
            Copy-Item -LiteralPath $lua -Destination (Join-Path $CartellaKit 'prima\youtube.lua') -Force
        }
    }
    Copy-Item -LiteralPath $luaKit -Destination $lua -Force
    return ('Aurora-{0}.vlt -> skins2\Aurora.vlt, sorgenti in skins2\aurora-src, lua\playlist\youtube.lua' -f $Scala)
}

# --- 4b. interfaccia web Aurora: la cartella utente lua\http sostituisce PER INTERO quella di sistema,
#        quindi vi si copiano anche gli handler dell'API (requests\) presi dall'installazione locale di VLC
Esegui-Passo 'Interfaccia web Aurora (lua\http)' {
    $exe = Trova-VlcExe
    $sys = Join-Path (Split-Path -Parent $exe) 'lua\http'
    if (-not (Test-Path -LiteralPath $sys)) { throw ('cartella di sistema non trovata: ' + $sys) }
    $dst = Join-Path $ProfiloVlc 'lua\http'
    # una cartella lua\http che c'era gia' prima del kit va tenuta da parte: il disinstallatore la rimette
    if ($null -eq $stato.LuaHttp) {
        $stato.LuaHttp = ($stato.PrecedenteNoto -and (Test-Path -LiteralPath $dst) -and -not (Test-Path -LiteralPath (Join-Path $dst 'aurora')))
        if ($stato.LuaHttp) { Copia-Cartella $dst (Join-Path $CartellaKit 'prima\lua-http') @() @() }
    }
    Copia-Cartella (Join-Path $sys 'requests') (Join-Path $dst 'requests') @() @()
    foreach ($f in @('custom.lua', 'favicon.ico')) {
        $src = Join-Path $sys $f
        if (Test-Path -LiteralPath $src) { Copy-Item -LiteralPath $src -Destination (Join-Path $dst $f) -Force }
    }
    Copia-Cartella (Join-Path $KitRoot 'web') $dst @() @()
    return ('pagina Aurora in ' + $dst + ', handler API copiati da ' + $sys)
}

# --- 4c. plugin skins2 patchato (Snap nativo di Windows per le finestre della skin)
Esegui-Passo 'Plugin skins2 con Snap nativo (plugins\gui)' {
    $src = Join-Path $KitRoot 'plugin\libskins2_plugin.dll'
    if (-not (Test-Path -LiteralPath $src)) { return 'plugin patchato non incluso nel kit: passo saltato' }
    $exe = Trova-VlcExe
    if (-not (Test-Path -LiteralPath $exe)) { throw 'vlc.exe non trovato' }
    $v = Versione-Vlc $exe
    if ($v.Major -ne 3) { return ('VLC ' + $v.Testo + ' non e'' 3.x: plugin non installato (ABI diversa)') }
    $gui = Join-Path (Split-Path -Parent $exe) 'plugins\gui'
    $dst = Join-Path $gui 'libskins2_plugin.dll'
    if (-not (Test-Path -LiteralPath $dst)) { throw ('plugin di sistema non trovato: ' + $dst) }
    $hNew = (Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash
    $hCur = (Get-FileHash -LiteralPath $dst -Algorithm SHA256).Hash
    if ($stato.PluginSha256 -notcontains $hNew) { [void]$stato.PluginSha256.Add($hNew) }
    # salta se gia' installato (stesso contenuto)
    if ($hNew -eq $hCur) { return 'gia'' installato (nessuna modifica)' }
    # backup dell'originale: la prima volta, e di nuovo quando un aggiornamento di VLC ha rimesso la sua dll
    # (firmata da VideoLAN), cosi' la copia .orig e' sempre quella della versione di VLC installata
    $bak = $dst + '.orig'
    if ((Firma-Valida $dst) -or -not (Test-Path -LiteralPath $bak)) { Copy-Item -LiteralPath $dst -Destination $bak -Force }
    try {
        Copy-Item -LiteralPath $src -Destination $dst -Force
    } catch {
        throw ('copia non riuscita (VLC ancora aperto o permessi): ' + $_.Exception.Message)
    }
    Rigenera-CachePlugin $exe
    return ('installato (originale salvato come libskins2_plugin.dll.orig; cache plugin rigenerata)')
}

# --- 5. opzioni di VLC
Esegui-Passo 'Opzioni di VLC (vlcrc)' {
    $prep = Prepara-OpzioniVlcrc -AppData $UserAppData -Pct $Scala -Info (Leggi-InfoSkin $Scala) -SchermoW $SchermoW -SchermoH $SchermoH
    Annota-OpzioniVlcrc $stato (Join-Path $ProfiloVlc 'vlcrc') $prep.Opzioni
    $cambi = @(Imposta-OpzioniVlcrc (Join-Path $ProfiloVlc 'vlcrc') $prep.Opzioni)
    foreach ($c in $cambi) { Scrivi-Info $c }
    $script:PasswordNuova = $prep.NuovaPassword
    $righe = @(
        ('Kit VLC Aurora - ' + (Get-Date -Format 'yyyy-MM-dd HH:mm')),
        ('Skin: Aurora-{0} (schermo {1}x{2})' -f $Scala, $SchermoW, $SchermoH),
        'Interfaccia web: http://localhost:8080  (dalla rete locale: http://<ip-del-pc>:8080)',
        ('Password interfaccia web: ' + $prep.Opzioni['http-password']),
        ('Regola firewall: ' + $NomeRegolaFirewall),
        ('Log installazione: ' + $Log)
    )
    [System.IO.File]::WriteAllLines((Join-Path $ProfiloVlc $NomeFileInfo), [string[]]$righe, (New-Object System.Text.UTF8Encoding $false))
    $msg = '{0} modifiche' -f $cambi.Count
    if ($prep.NuovaPassword) { $msg += ', nuova password web generata' } else { $msg += ', password web esistente mantenuta' }
    return $msg
}

# --- 6. stile scuro coerente per le finestre Qt
Esegui-Passo 'Finestre Qt scure (vlc-qt-interface.ini)' {
    $ini = Join-Path $ProfiloVlc 'vlc-qt-interface.ini'
    if ($null -eq $stato.QtStyle) {
        $prima = $null
        if ($stato.PrecedenteNoto) { $prima = Leggi-QtStyle $ini }
        $stato.QtStyle = [ordered]@{ Prima = $prima }
    }
    return (Imposta-QtStyleFusion $ini)
}

# --- 7. firewall per l'interfaccia web
Esegui-Passo 'Regola firewall interfaccia web (TCP 8080, reti private)' {
    $exe = Trova-VlcExe
    if (-not (Test-Path -LiteralPath $exe)) { throw 'vlc.exe non trovato: regola non creata.' }
    $fatti = @()
    if (Get-NetFirewallRule -DisplayName $NomeRegolaFirewall -ErrorAction SilentlyContinue) { $fatti += 'regola gia'' presente' }
    else {
        New-NetFirewallRule -DisplayName $NomeRegolaFirewall -Description 'Kit VLC Aurora: accesso dalla rete locale all''interfaccia web di VLC' `
            -Direction Inbound -Action Allow -Protocol TCP -LocalPort 8080 -Profile Private -Program $exe -Enabled True | Out-Null
        $fatti += 'regola creata'
    }
    # Le regole di blocco create automaticamente da Windows per vlc.exe prevarrebbero sulla nostra: disattivale.
    $filtri = @(Get-NetFirewallApplicationFilter -All -ErrorAction SilentlyContinue | Where-Object { $_.Program -and ($_.Program -like '*\vlc.exe') })
    foreach ($f in $filtri) {
        $r = $f | Get-NetFirewallRule -ErrorAction SilentlyContinue
        if ($r -and $r.Direction -eq 'Inbound' -and $r.Action -eq 'Block' -and $r.Enabled -eq 'True') {
            Disable-NetFirewallRule -Name $r.Name; $fatti += ('disattivata regola di blocco "' + $r.DisplayName + '"')
            if ($stato.RegoleFirewall -notcontains $r.Name) { [void]$stato.RegoleFirewall.Add($r.Name) }
        }
    }
    return ($fatti -join '; ')
}

# --- 8. disinstallatore: copia degli script e stato dell'installazione nella cartella del kit
#        (la voce in "App installate" la crea la fase utente, nel registro dell'utente)
Esegui-Passo 'Disinstallatore' {
    $dst = Join-Path $CartellaKit 'scripts'
    if (-not (Test-Path -LiteralPath $dst)) { New-Item -ItemType Directory -Path $dst -Force | Out-Null }
    foreach ($f in @('comuni.ps1', 'disinstalla.ps1')) { Copy-Item -LiteralPath (Join-Path $KitRoot ('scripts\' + $f)) -Destination (Join-Path $dst $f) -Force }
    Copy-Item -LiteralPath (Join-Path $KitRoot 'config\aurora.ico') -Destination (Join-Path $CartellaKit 'aurora.ico') -Force
    Salva-Stato $CartellaKit $stato
    return ('copiato in ' + $CartellaKit)
}

# --- esito per la fase utente
try { Salva-Stato $CartellaKit $stato } catch { Scrivi-Avviso ('stato dell''installazione non salvato: ' + $_.Exception.Message) }
$ko = @($Passi | Where-Object { $_.Stato -eq 'KO' }).Count
$esito = [PSCustomObject]@{ Passi = $Passi; Variante = $Scala; Password = $script:PasswordNuova; Log = $Log; Errori = $ko }
$esito | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $FileEsito -Encoding UTF8
Logga ('--- fine fase amministrativa, errori: ' + $ko)
if ($ko -gt 0) { exit 1 } else { exit 0 }
