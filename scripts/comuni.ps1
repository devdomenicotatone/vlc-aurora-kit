# comuni.ps1 - funzioni condivise dagli script del kit "VLC Aurora" (Windows PowerShell 5.1 o superiore)
# Viene incluso con il punto (dot-source) da installa.ps1, disinstalla.ps1, esporta.ps1 e genera-varianti.ps1.

$script:KitRoot = Split-Path -Parent $PSScriptRoot
$script:LogFile = ''
$script:NomeRegolaFirewall = 'VLC interfaccia web (porta 8080)'
$script:NomeFileInfo = 'aurora-kit-info.txt'
# cartella in %LOCALAPPDATA% con lo stato dell'installazione e la copia del disinstallatore
$script:NomeCartellaKit = 'VLC-Aurora-Kit'
$script:ChiaveDisinstallazione = 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\VLC-Aurora-Kit'

# ------------------------------------------------------------------ output e log
function Logga([string]$Testo) {
    if ($script:LogFile -ne '') {
        try { Add-Content -LiteralPath $script:LogFile -Value ((Get-Date -Format 'yyyy-MM-dd HH:mm:ss') + '  ' + $Testo) -Encoding UTF8 } catch { }
    }
}
function Scrivi-Titolo([string]$t) { Write-Host ''; Write-Host ('== ' + $t) -ForegroundColor Cyan; Logga ('== ' + $t) }
function Scrivi-Ok([string]$t)     { Write-Host ('  [OK] ' + $t) -ForegroundColor Green;  Logga ('[OK] ' + $t) }
function Scrivi-Avviso([string]$t) { Write-Host ('  [!!] ' + $t) -ForegroundColor Yellow; Logga ('[!!] ' + $t) }
function Scrivi-Errore([string]$t) { Write-Host ('  [KO] ' + $t) -ForegroundColor Red;    Logga ('[KO] ' + $t) }
function Scrivi-Info([string]$t)   { Write-Host ('       ' + $t) -ForegroundColor Gray;   Logga ('     ' + $t) }

function Esegui-Passo([string]$Nome, [scriptblock]$Azione) {
    # Esegue un passo e ne annota l'esito in $Passi (elenco preparato dallo script chiamante) per il riepilogo finale.
    Scrivi-Titolo $Nome
    try {
        $dettaglio = [string](& $Azione)
        [void]$Passi.Add([PSCustomObject]@{ Passo = $Nome; Stato = 'OK'; Dettaglio = $dettaglio })
        Scrivi-Ok $dettaglio
    } catch {
        [void]$Passi.Add([PSCustomObject]@{ Passo = $Nome; Stato = 'KO'; Dettaglio = $_.Exception.Message })
        Scrivi-Errore $_.Exception.Message
    }
}

# ------------------------------------------------------------------ file di opzioni key=value
function Leggi-Opzioni([string]$File) {
    # Legge un file "chiave=valore" (righe vuote e commenti # ignorati) in un dizionario ordinato.
    $d = New-Object System.Collections.Specialized.OrderedDictionary
    if (-not (Test-Path -LiteralPath $File)) { return $d }
    foreach ($r in [System.IO.File]::ReadAllLines($File, [System.Text.Encoding]::UTF8)) {
        $riga = $r.Trim()
        if ($riga -eq '' -or $riga.StartsWith('#')) { continue }
        $i = $riga.IndexOf('=')
        if ($i -lt 1) { continue }
        $d[$riga.Substring(0, $i).Trim()] = $riga.Substring($i + 1).Trim()
    }
    return $d
}

function Scrivi-Righe([string]$Percorso, [System.Collections.Generic.List[string]]$Righe) {
    $dir = Split-Path -Parent $Percorso
    if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
    [System.IO.File]::WriteAllLines($Percorso, $Righe, (New-Object System.Text.UTF8Encoding $false))
}

# ------------------------------------------------------------------ vlcrc
function Imposta-OpzioniVlcrc([string]$Percorso, [System.Collections.IDictionary]$Opzioni, [switch]$SoloVerifica) {
    # Imposta "chiave=valore" in vlcrc. VLC ignora le sezioni [modulo] e usa l'ultima occorrenza di una chiave:
    # la prima riga "chiave=" o "#chiave=" viene sostituita, le eventuali ripetizioni rimosse, altrimenti si aggiunge in coda.
    # Se il file non esiste viene creato parziale: VLC lo completa alla prima chiusura. Restituisce l'elenco dei cambiamenti.
    $righe = New-Object 'System.Collections.Generic.List[string]'
    if (Test-Path -LiteralPath $Percorso) {
        $righe.AddRange([string[]][System.IO.File]::ReadAllLines($Percorso, [System.Text.Encoding]::UTF8))
    } else {
        $righe.Add('###')
        $righe.Add('### vlcrc creato dal kit VLC Aurora: VLC aggiunge le altre opzioni alla prima chiusura')
        $righe.Add('###')
        $righe.Add('')
    }
    $cambi = New-Object 'System.Collections.Generic.List[string]'
    foreach ($k in $Opzioni.Keys) {
        $nuova = '{0}={1}' -f $k, $Opzioni[$k]
        $rx = '^#?' + [regex]::Escape($k) + '='
        $prima = -1
        for ($i = $righe.Count - 1; $i -ge 0; $i--) {
            if ($righe[$i] -match $rx) {
                if ($prima -ge 0) { $righe.RemoveAt($prima); $cambi.Add('(doppione rimosso) ' + $k) }
                $prima = $i
            }
        }
        if ($prima -ge 0) {
            if ($righe[$prima] -ne $nuova) { $cambi.Add(('{0}  ->  {1}' -f $righe[$prima], $nuova)); $righe[$prima] = $nuova }
        } else {
            $righe.Add($nuova); $cambi.Add('(aggiunta) ' + $nuova)
        }
    }
    if (-not $SoloVerifica) { Scrivi-Righe $Percorso $righe }
    return $cambi
}

function Leggi-ValoriAttiviVlcrc([string]$Percorso, [string[]]$Chiavi) {
    # Restituisce i valori attivi (riga non commentata) delle chiavi indicate; usa l'ultima occorrenza come VLC.
    $v = @{}
    if (-not (Test-Path -LiteralPath $Percorso)) { return $v }
    foreach ($r in [System.IO.File]::ReadAllLines($Percorso, [System.Text.Encoding]::UTF8)) {
        foreach ($k in $Chiavi) {
            if ($r.StartsWith($k + '=')) { $v[$k] = $r.Substring($k.Length + 1) }
        }
    }
    return $v
}

function Riga-Vlcrc($Righe, [string]$Chiave) {
    # Riga in vigore per una chiave: l'ultima attiva "chiave=..." come fa VLC, altrimenti quella commentata
    # "#chiave=..." (il valore predefinito, che VLC scrive cosi'); $null se la chiave non compare.
    $attiva = $null; $commentata = $null
    foreach ($r in $Righe) {
        if ($r.StartsWith($Chiave + '=')) { $attiva = $r }
        elseif ($null -eq $commentata -and $r.StartsWith('#' + $Chiave + '=')) { $commentata = $r }
    }
    if ($null -ne $attiva) { return $attiva }
    return $commentata
}

function Annota-OpzioniVlcrc($Stato, [string]$Percorso, [System.Collections.IDictionary]$Opzioni) {
    # Per il disinstallatore, da chiamare prima di Imposta-OpzioniVlcrc: di ogni chiave annota la riga che c'era
    # (solo la prima volta, e solo se la situazione di partenza e' nota) e il valore messo dal kit.
    $righe = @()
    if (Test-Path -LiteralPath $Percorso) { $righe = [System.IO.File]::ReadAllLines($Percorso, [System.Text.Encoding]::UTF8) }
    foreach ($k in $Opzioni.Keys) {
        if (-not $Stato.Vlcrc.Contains($k)) {
            $prima = $null
            if ($Stato.PrecedenteNoto) { $prima = Riga-Vlcrc $righe $k }
            $Stato.Vlcrc[$k] = [ordered]@{ Prima = $prima; Kit = $null }
        }
        $Stato.Vlcrc[$k].Kit = [string]$Opzioni[$k]
    }
}

function Ripristina-OpzioniVlcrc([string]$Percorso, [System.Collections.IDictionary]$Voci, [switch]$SoloVerifica) {
    # Inverso di Imposta-OpzioniVlcrc. $Voci: chiave -> @{ Prima = riga che c'era; Kit = valore messo dal kit }.
    # Dove vale ancora il valore del kit rimette la riga di prima, oppure "#chiave=" (valore predefinito di VLC) se non
    # c'era o non e' nota; le opzioni cambiate dopo l'installazione restano come sono (Kit = $null: si ripristina sempre).
    # skins2-config, che VLC riscrive a ogni chiusura, si ripristina solo se la skin in uso e' ancora Aurora.
    # Restituisce l'elenco dei cambiamenti, senza mostrare la password dell'interfaccia web.
    $cambi = New-Object 'System.Collections.Generic.List[string]'
    if (-not (Test-Path -LiteralPath $Percorso)) { return $cambi }
    $righe = New-Object 'System.Collections.Generic.List[string]'
    $righe.AddRange([string[]][System.IO.File]::ReadAllLines($Percorso, [System.Text.Encoding]::UTF8))
    $skinDelKit = ((Riga-Vlcrc $righe 'skins2-last') -like 'skins2-last=*\skins2\Aurora.vlt')
    foreach ($k in @($Voci.Keys)) {
        $attuale = Riga-Vlcrc $righe $k
        if ($null -eq $attuale) { continue }
        $valore = $attuale.Substring($attuale.IndexOf('=') + 1)
        $kit = $Voci[$k].Kit
        if ($k -eq 'skins2-config') { if (-not $skinDelKit) { continue } }
        elseif ($null -ne $kit -and $valore -ne [string]$kit) { continue }
        $prima = $Voci[$k].Prima
        if ($null -eq $prima) {
            if ($attuale.StartsWith('#')) { continue }
            $prima = '#' + $k + '='
        }
        if ($attuale -ceq $prima) { continue }
        # come Imposta-OpzioniVlcrc: resta la prima riga della chiave, le eventuali ripetizioni vengono tolte
        $rx = '^#?' + [regex]::Escape($k) + '='
        $posto = -1
        for ($i = $righe.Count - 1; $i -ge 0; $i--) {
            if ($righe[$i] -match $rx) {
                if ($posto -ge 0) { $righe.RemoveAt($posto) }
                $posto = $i
            }
        }
        $righe[$posto] = $prima
        $cambi.Add((('{0}  ->  {1}' -f $attuale, $prima) -replace '(#?http-password=)[^ ]+', '$1********'))
    }
    if ($cambi.Count -gt 0 -and -not $SoloVerifica) { Scrivi-Righe $Percorso $righe }
    return $cambi
}

# ------------------------------------------------------------------ vlc-qt-interface.ini
function Imposta-QtStyleFusion([string]$Percorso, [switch]$SoloVerifica) {
    # Garantisce "QtStyle=Fusion" nella sezione [MainWindow]: con la palette scura lo stile nativo di Windows
    # lascia campi chiari e testi illeggibili, Fusion disegna tutto dalla palette.
    $righe = New-Object 'System.Collections.Generic.List[string]'
    if (Test-Path -LiteralPath $Percorso) {
        $righe.AddRange([string[]][System.IO.File]::ReadAllLines($Percorso, [System.Text.Encoding]::UTF8))
    }
    $sez = -1
    for ($i = 0; $i -lt $righe.Count; $i++) { if ($righe[$i].Trim() -eq '[MainWindow]') { $sez = $i; break } }
    if ($sez -lt 0) {
        if ($righe.Count -gt 0 -and $righe[$righe.Count - 1].Trim() -ne '') { $righe.Add('') }
        $righe.Add('[MainWindow]'); $righe.Add('QtStyle=Fusion')
        $esito = 'sezione [MainWindow] creata con QtStyle=Fusion'
    } else {
        $fine = $righe.Count
        for ($j = $sez + 1; $j -lt $righe.Count; $j++) { if ($righe[$j].Trim().StartsWith('[')) { $fine = $j; break } }
        $trovata = $false
        for ($j = $sez + 1; $j -lt $fine; $j++) {
            if ($righe[$j] -match '^QtStyle=') {
                if ($righe[$j] -eq 'QtStyle=Fusion') { $esito = 'QtStyle=Fusion era gia'' impostato' }
                else { $esito = ('{0}  ->  QtStyle=Fusion' -f $righe[$j]); $righe[$j] = 'QtStyle=Fusion' }
                $trovata = $true; break
            }
        }
        if (-not $trovata) { $righe.Insert($sez + 1, 'QtStyle=Fusion'); $esito = 'QtStyle=Fusion aggiunto in [MainWindow]' }
    }
    if (-not $SoloVerifica) { Scrivi-Righe $Percorso $righe }
    return $esito
}

function Indice-QtStyle([System.Collections.Generic.List[string]]$Righe) {
    # Posizione della riga "QtStyle=" nella sezione [MainWindow], oppure -1.
    $dentro = $false
    for ($i = 0; $i -lt $Righe.Count; $i++) {
        $t = $Righe[$i].Trim()
        if ($t.StartsWith('[')) { $dentro = ($t -eq '[MainWindow]') }
        elseif ($dentro -and $Righe[$i] -match '^QtStyle=') { return $i }
    }
    return -1
}

function Leggi-QtStyle([string]$Percorso) {
    # Riga "QtStyle=..." attuale di [MainWindow], oppure $null (per il disinstallatore).
    if (-not (Test-Path -LiteralPath $Percorso)) { return $null }
    $righe = New-Object 'System.Collections.Generic.List[string]'
    $righe.AddRange([string[]][System.IO.File]::ReadAllLines($Percorso, [System.Text.Encoding]::UTF8))
    $i = Indice-QtStyle $righe
    if ($i -lt 0) { return $null }
    return $righe[$i]
}

function Ripristina-QtStyle([string]$Percorso, $Prima, [switch]$SoloVerifica) {
    # Inverso di Imposta-QtStyleFusion: se c'e' ancora "QtStyle=Fusion" rimette la riga di prima ($Prima),
    # oppure la toglie se prima non c'era (stile predefinito di Qt).
    if (-not (Test-Path -LiteralPath $Percorso)) { return 'vlc-qt-interface.ini non presente' }
    $righe = New-Object 'System.Collections.Generic.List[string]'
    $righe.AddRange([string[]][System.IO.File]::ReadAllLines($Percorso, [System.Text.Encoding]::UTF8))
    $i = Indice-QtStyle $righe
    if ($i -lt 0 -or $righe[$i] -ne 'QtStyle=Fusion') { return 'QtStyle=Fusion non c''e'' piu'': lasciato com''e''' }
    if ($Prima -eq 'QtStyle=Fusion') { return 'QtStyle=Fusion c''era gia'' prima del kit: lasciato' }
    if ($Prima) { $righe[$i] = [string]$Prima; $esito = ('QtStyle=Fusion  ->  {0}' -f $Prima) }
    else { $righe.RemoveAt($i); $esito = 'QtStyle=Fusion  ->  (riga tolta: stile predefinito di Qt)' }
    if (-not $SoloVerifica) { Scrivi-Righe $Percorso $righe }
    return $esito
}

# ------------------------------------------------------------------ schermo e skin
function Rileva-Schermo {
    # DPI di sistema e dimensione fisica dello schermo principale. VLC disegna la skin 1:1 in pixel fisici,
    # quindi la variante della skin va scelta in base alla scala di Windows (100, 125, 150...).
    $sig = @'
using System; using System.Runtime.InteropServices;
public static class KitDpi {
  [DllImport("user32.dll")] public static extern bool SetProcessDpiAwarenessContext(IntPtr ctx);
  [DllImport("user32.dll")] public static extern uint GetDpiForSystem();
  [DllImport("user32.dll")] public static extern int GetSystemMetrics(int n);
}
'@
    if (-not ('KitDpi' -as [type])) { Add-Type -TypeDefinition $sig }
    $aware = $false
    try { $aware = [KitDpi]::SetProcessDpiAwarenessContext([IntPtr](-4)) } catch { $aware = $false }
    $dpi = 96
    try { $dpi = [int][KitDpi]::GetDpiForSystem() } catch { }
    try {
        $applied = (Get-ItemProperty -Path 'HKCU:\Control Panel\Desktop\WindowMetrics' -Name AppliedDPI -ErrorAction Stop).AppliedDPI
        if ($applied -gt $dpi) { $dpi = [int]$applied }
    } catch { }
    if ($dpi -lt 96) { $dpi = 96 }
    $w = [KitDpi]::GetSystemMetrics(0); $h = [KitDpi]::GetSystemMetrics(1)
    if (-not $aware) { $w = [int]($w * $dpi / 96); $h = [int]($h * $dpi / 96) }
    return [PSCustomObject]@{ Dpi = $dpi; Percento = [int][Math]::Round($dpi * 100.0 / 96.0); Larghezza = $w; Altezza = $h }
}

function Scegli-Variante([int]$Percento) {
    # Variante precompilata (skin\Aurora-NNN.vlt) con la scala piu' vicina a quella dello schermo.
    $disp = @()
    foreach ($f in (Get-ChildItem -LiteralPath (Join-Path $script:KitRoot 'skin') -Filter 'Aurora-*.vlt')) {
        if ($f.BaseName -match '^Aurora-(\d+)$') { $disp += [int]$Matches[1] }
    }
    if ($disp.Count -eq 0) { throw 'Nessuna skin precompilata trovata in skin\ (Aurora-NNN.vlt)' }
    $best = $disp[0]
    foreach ($p in $disp) { if ([Math]::Abs($p - $Percento) -lt [Math]::Abs($best - $Percento)) { $best = $p } }
    return $best
}

function Leggi-InfoSkin([int]$Percento) {
    # Dimensioni delle finestre della variante (scritte dal generatore in Aurora-NNN.json).
    $json = Join-Path $script:KitRoot ('skin\Aurora-{0}.json' -f $Percento)
    if (Test-Path -LiteralPath $json) { return (Get-Content -LiteralPath $json -Raw -Encoding UTF8 | ConvertFrom-Json) }
    return $null
}

function Componi-Skins2Config($Info, [int]$SchermoW, [int]$SchermoH, [string]$Esistente = '') {
    # Posizioni iniziali delle finestre della skin (pixel fisici): principale centrata lasciando spazio alla
    # playlist a destra, menu agganciato al pulsante, equalizzatore sotto la playlist, tutto tranne la principale nascosto.
    if ($null -eq $Info) { return $null }
    $mw = [int]$Info.main[0]; $mh = [int]$Info.main[1]
    $pw = [int]$Info.playlist[0]; $ph = [int]$Info.playlist[1]
    $fw = [int]$Info.fullscreenController[0]; $fh = [int]$Info.fullscreenController[1]
    $x0 = [int][Math]::Max(0, [Math]::Floor(($SchermoW - $mw - $pw) / 2))
    $y0 = [int][Math]::Max(0, [Math]::Floor(($SchermoH - $mh) / 2) - 40)
    # se l'utente aveva gia' sistemato la finestra principale, la lascia dov'era (se sta nello schermo)
    if ($Esistente -match '\["main" "\w+" (-?\d+) (-?\d+) (\d+) (\d+) \d\]') {
        $ex = [int]$Matches[1]; $ey = [int]$Matches[2]; $ew = [int]$Matches[3]; $eh = [int]$Matches[4]
        $minw = if ($Info.minimo) { [int]$Info.minimo[0] } else { $mw }
        $minh = if ($Info.minimo) { [int]$Info.minimo[1] } else { $mh }
        if ($ew -ge $minw -and $eh -ge $minh -and $ex -gt -100 -and $ey -gt -100 -and $ex -lt $SchermoW -and $ey -lt $SchermoH) {
            $x0 = $ex; $y0 = $ey; $mw = $ew; $mh = $eh
        }
    }
    # colonna playlist + equalizzatore: a destra della principale; se non ci sta, a sinistra; altrimenti dentro lo schermo
    $px = $x0 + $mw
    if ($px + $pw -gt $SchermoW) { if ($x0 - $pw -ge 0) { $px = $x0 - $pw } else { $px = [Math]::Max(0, $SchermoW - $pw) } }
    $py = $y0
    $eh2 = [int]$Info.eqwin[1]
    if ($py + $ph + $eh2 -gt $SchermoH) { $py = [Math]::Max(0, $SchermoH - $ph - $eh2) }
    $parti = @(
        ('["fullscreenController" "fsLayout" {0} {1} {2} {3} 0]' -f $x0, [Math]::Max(0, $SchermoH - $fh - 60), $fw, $fh),
        ('["main" "mainLayout" {0} {1} {2} {3} 1]' -f $x0, $y0, $mw, $mh),
        ('["playlist" "playlistLayout" {0} {1} {2} {3} 0]' -f $px, $py, $pw, $ph),
        ('["eqwin" "eqLayout" {0} {1} {2} {3} 0]' -f $px, ($py + $ph), [int]$Info.eqwin[0], $eh2)
    )
    return ($parti -join '')
}

function Prepara-OpzioniVlcrc([string]$AppData, [int]$Pct, $Info, [int]$SchermoW, [int]$SchermoH) {
    # Opzioni da scrivere in vlcrc: quelle di config\vlcrc.opzioni piu' skin, posizioni e password web.
    # Password e posizioni gia' presenti (con la finestra eqwin) vengono mantenute.
    $vlcrc = Join-Path $AppData 'vlc\vlcrc'
    $opz = Leggi-Opzioni (Join-Path $script:KitRoot 'config\vlcrc.opzioni')
    $opz['skins2-last'] = Join-Path $AppData 'vlc\skins2\Aurora.vlt'
    $esist = Leggi-ValoriAttiviVlcrc $vlcrc @('skins2-config', 'http-password')
    $nuovaPassword = $null
    if ($esist.ContainsKey('http-password') -and $esist['http-password'].Trim() -ne '') {
        $opz['http-password'] = $esist['http-password'].Trim()
    } else {
        $nuovaPassword = Nuova-Password
        $opz['http-password'] = $nuovaPassword
    }
    # posizioni gia' salvate: le tiene solo se appartengono a questa versione della skin (finestra eqwin presente,
    # nessuna vecchia finestra menuwin, playlist larga quanto previsto); altrimenti le ricalcola per lo schermo
    $tieni = $false
    if ($Info -and $esist.ContainsKey('skins2-config')) {
        $c = $esist['skins2-config']
        $tieni = ($c -like '*"eqwin"*') -and ($c -notlike '*"menuwin"*') -and ($c -match ('"playlist" "playlistLayout" -?\d+ -?\d+ ' + [int]$Info.playlist[0] + ' '))
        # ...e solo se ogni finestra salvata sta dentro lo schermo attuale
        foreach ($m in [regex]::Matches($c, '\["\w+" "\w+" (-?\d+) (-?\d+) (\d+) (\d+) \d\]')) {
            $wx = [int]$m.Groups[1].Value; $wy = [int]$m.Groups[2].Value; $ww = [int]$m.Groups[3].Value; $wh = [int]$m.Groups[4].Value
            if ($wx -lt -50 -or $wy -lt -50 -or ($wx + $ww) -gt ($SchermoW + 50) -or ($wy + $wh) -gt ($SchermoH + 50)) { $tieni = $false }
        }
    }
    if (-not $tieni) {
        $vecchia = if ($esist.ContainsKey('skins2-config')) { $esist['skins2-config'] } else { '' }
        $cfg = Componi-Skins2Config $Info $SchermoW $SchermoH $vecchia
        if ($cfg) { $opz['skins2-config'] = $cfg }
    }
    return [PSCustomObject]@{ Opzioni = $opz; NuovaPassword = $nuovaPassword }
}

function Nuova-Password {
    $alfabeto = 'abcdefghjkmnpqrstuvwxyz23456789'
    $s = ''
    for ($i = 0; $i -lt 10; $i++) { $s += $alfabeto[(Get-Random -Maximum $alfabeto.Length)] }
    return ('vlc-' + $s)
}

# ------------------------------------------------------------------ programmi
function Trova-VlcExe {
    try {
        $dir = (Get-ItemProperty -Path 'HKLM:\SOFTWARE\VideoLAN\VLC' -Name InstallDir -ErrorAction Stop).InstallDir
        if ($dir) { return (Join-Path $dir 'vlc.exe') }
    } catch { }
    return (Join-Path $env:ProgramFiles 'VideoLAN\VLC\vlc.exe')
}

function Versione-Vlc([string]$Exe) {
    # Versione come "3.0.24" indipendentemente dalla lingua (il testo ProductVersion in italiano usa le virgole).
    $vi = (Get-Item -LiteralPath $Exe).VersionInfo
    return [PSCustomObject]@{ Testo = ('{0}.{1}.{2}' -f $vi.ProductMajorPart, $vi.ProductMinorPart, $vi.ProductBuildPart); Major = [int]$vi.ProductMajorPart }
}

function Chiudi-Vlc {
    # Chiude VLC con garbo (cosi' salva le sue opzioni) e, se dopo 10 secondi e' ancora aperto, lo termina.
    # Con l'interfaccia a skin la finestra principale del processo e' la finestra madre della skin (invisibile, quella
    # della barra delle applicazioni), che ignora il WM_CLOSE di CloseMainWindow ed esce solo con il comando di
    # sistema "Chiudi", quello di Alt+F4.
    $sig = @'
using System; using System.Text; using System.Runtime.InteropServices;
public static class KitFinestre {
  [DllImport("user32.dll", CharSet = CharSet.Unicode)] public static extern int GetClassName(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint msg, IntPtr w, IntPtr l);
  public static bool ChiudiSkin(IntPtr h) {
    var c = new StringBuilder(64); GetClassName(h, c, 64);
    if (c.ToString() != "SkinWindowClass") return false;
    return PostMessage(h, 0x0112, (IntPtr)0xF060, IntPtr.Zero);  // WM_SYSCOMMAND, SC_CLOSE
  }
}
'@
    if (-not ('KitFinestre' -as [type])) { Add-Type -TypeDefinition $sig }
    foreach ($p in @(Get-Process vlc -ErrorAction SilentlyContinue)) {
        try { if (-not [KitFinestre]::ChiudiSkin($p.MainWindowHandle)) { $p.CloseMainWindow() | Out-Null } } catch { }
    }
    Wait-Process -Name vlc -Timeout 10 -ErrorAction SilentlyContinue
    if (Get-Process vlc -ErrorAction SilentlyContinue) { Stop-Process -Name vlc -Force -ErrorAction SilentlyContinue }
    Start-Sleep -Seconds 1
}

function Rigenera-CachePlugin([string]$VlcExe) {
    # Rigenera la cache dei plugin (plugins\plugins.dat) come fa l'installer di VLC, cosi' VLC carica la dll cambiata.
    # Toglie anche il plugins.dat che le prime versioni del kit creavano dentro plugins\gui: a VLC non serve.
    $dir = Split-Path -Parent $VlcExe
    $cacheGen = Join-Path $dir 'vlc-cache-gen.exe'
    if (Test-Path -LiteralPath $cacheGen) {
        $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        try { & $cacheGen (Join-Path $dir 'plugins') 2>&1 | Out-Null } finally { $ErrorActionPreference = $eap }
    }
    Remove-Item -LiteralPath (Join-Path $dir 'plugins\gui\plugins.dat') -Force -ErrorAction SilentlyContinue
}

function Firma-Valida([string]$File) {
    # true per i file firmati digitalmente (le dll ufficiali di VideoLAN lo sono, il plugin ricompilato del kit no).
    return ((Get-AuthenticodeSignature -LiteralPath $File).Status -eq 'Valid')
}

function Trova-Jre17 {
    $base = Join-Path $env:ProgramFiles 'Eclipse Adoptium'
    $d = @(Get-ChildItem -LiteralPath $base -Directory -Filter 'jre-17*' -ErrorAction SilentlyContinue | Sort-Object Name -Descending)
    if ($d.Count -gt 0 -and (Test-Path -LiteralPath (Join-Path $d[0].FullName 'bin\server\jvm.dll'))) { return $d[0].FullName }
    return $null
}

# Java Access Bridge (il ponte di Java per lettori di schermo e lenti d'ingrandimento). Quando e' attivo nel profilo
# (%USERPROFILE%\.accessibility.properties), Java prova a caricarlo anche dentro VLC: li' non ci riesce e i menu Java
# dei Blu-ray non partono. Con Java 9 o successivo la libreria Blu-ray di VLC non lo disattiva da sola.
function Test-AccessBridgeAttivo([string]$File = '') {
    if ($File -eq '') { $File = Join-Path $env:USERPROFILE '.accessibility.properties' }
    if (-not (Test-Path -LiteralPath $File)) { return $false }
    return [bool](Select-String -LiteralPath $File -Pattern '^\s*assistive_technologies\s*=.*AccessBridge' -Quiet)
}

function Imposta-AccessBridge([bool]$Attivo, [string]$File = '') {
    # Attiva o disattiva il ponte per l'utente corrente con lo strumento di Java (jabswitch). Se Java non c'e' (o viene
    # indicato un altro file) fa la stessa cosa sul file: commenta o ripristina le righe del ponte.
    # Restituisce $true se alla fine lo stato e' quello richiesto.
    $jre = Trova-Jre17
    $jab = if ($jre) { Join-Path $jre 'bin\jabswitch.exe' } else { '' }
    if ($File -eq '' -and $jab -ne '' -and (Test-Path -LiteralPath $jab)) {
        $opzione = if ($Attivo) { '-enable' } else { '-disable' }
        $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
        try { & $jab $opzione 2>&1 | Out-Null } finally { $ErrorActionPreference = $eap }
    } else {
        if ($File -eq '') { $File = Join-Path $env:USERPROFILE '.accessibility.properties' }
        if (Test-Path -LiteralPath $File) {
            $righe = New-Object 'System.Collections.Generic.List[string]'
            foreach ($r in [System.IO.File]::ReadAllLines($File)) {
                if ($Attivo) { $righe.Add(($r -replace '^#\s*((assistive_technologies\s*=.*AccessBridge|screen_magnifier_present\s*=).*)$', '$1')) }
                else { $righe.Add(($r -replace '^\s*((assistive_technologies\s*=.*AccessBridge|screen_magnifier_present\s*=).*)$', '#$1')) }
            }
            [System.IO.File]::WriteAllLines($File, $righe)
        }
    }
    return ((Test-AccessBridgeAttivo $File) -eq $Attivo)
}

function Test-Winget { return [bool](Get-Command winget.exe -ErrorAction SilentlyContinue) }

function Pacchetti-WingetUtente {
    # Id dei pacchetti winget "portatili" installati in ambito utente (una cartella per pacchetto): confrontando prima
    # e dopo si sa che cosa ha aggiunto l'installazione di yt-dlp, dipendenze comprese.
    $d = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages'
    return @(Get-ChildItem -LiteralPath $d -Directory -ErrorAction SilentlyContinue | ForEach-Object { $_.Name -replace '_Microsoft\.Winget\.Source_.*$', '' })
}

function Invoke-Winget([string[]]$Argomenti) {
    # Esegue winget senza che l'output su stderr interrompa lo script (comportamento di PowerShell 5.1).
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try {
        $out = & winget.exe @Argomenti 2>&1 | ForEach-Object { "$_" }
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $eap }
    Logga ('winget ' + ($Argomenti -join ' ') + ' -> codice ' + $code)
    return [PSCustomObject]@{ Codice = $code; Testo = (($out | Where-Object { $_ -notmatch '^[\s\-\\|/]*$' }) -join "`n") }
}

function Winget-Installato([string]$Id) {
    $r = Invoke-Winget @('list', '--id', $Id, '-e', '--accept-source-agreements', '--disable-interactivity')
    return ($r.Codice -eq 0 -and $r.Testo -match [regex]::Escape($Id))
}

function Winget-Esito($r) {
    # true se l'operazione e' andata bene o non era necessaria.
    if ($r.Codice -eq 0) { return $true }
    if ($r.Testo -match 'already installed|gi. installat|No available upgrade|No newer package|Nessun aggiornamento|non . applicabile|not applicable|No applicable update') { return $true }
    return $false
}

function Trova-VersioneVlc3 {
    # Ultima versione 3.x pubblicata su winget (la serie 3 e' quella supportata dalla skin).
    $r = Invoke-Winget @('show', '--id', 'VideoLAN.VLC', '-e', '--versions', '--accept-source-agreements', '--disable-interactivity')
    $vers = @()
    foreach ($m in [regex]::Matches($r.Testo, '(?m)^\s*(3\.\d+(\.\d+)*)\s*$')) { $vers += $m.Groups[1].Value }
    if ($vers.Count -eq 0) { return $null }
    return ($vers | Sort-Object { [version]$_ } -Descending | Select-Object -First 1)
}

function Copia-Cartella([string]$Da, [string]$A, [string[]]$EscludiCartelle, [string[]]$EscludiFile) {
    # Copia ricorsiva con robocopy (presente in ogni Windows); codici < 8 = successo.
    if (-not (Test-Path -LiteralPath $A)) { New-Item -ItemType Directory -Path $A -Force | Out-Null }
    $arg = @($Da, $A, '/E', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/R:1', '/W:1')
    if ($EscludiCartelle.Count -gt 0) { $arg += '/XD'; $arg += $EscludiCartelle }
    if ($EscludiFile.Count -gt 0) { $arg += '/XF'; $arg += $EscludiFile }
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    try { & robocopy.exe @arg | Out-Null; $code = $LASTEXITCODE } finally { $ErrorActionPreference = $eap }
    if ($code -ge 8) { throw ('robocopy ha restituito il codice {0} copiando {1}' -f $code, $Da) }
}

# ------------------------------------------------------------------ stato dell'installazione e disinstallatore
function In-Tabella($o) {
    # Oggetti di ConvertFrom-Json -> dizionari ordinati ed elenchi modificabili.
    if ($null -eq $o) { return $null }
    if ($o -is [System.Management.Automation.PSCustomObject]) {
        $t = [ordered]@{}
        foreach ($p in $o.PSObject.Properties) { $t[$p.Name] = In-Tabella $p.Value }
        return $t
    }
    if ($o -is [System.Collections.IEnumerable] -and $o -isnot [string]) {
        $l = New-Object System.Collections.ArrayList
        foreach ($e in $o) { [void]$l.Add((In-Tabella $e)) }
        return , $l
    }
    return $o
}

function Apri-Stato([string]$Cartella, [string]$ProfiloVlc) {
    # Stato dell'installazione (<cartella del kit>\stato.json): che cosa c'era prima e che cosa ha messo il kit.
    # Lo scrive installa.ps1, lo usa disinstalla.ps1 per rimettere le cose com'erano.
    $s = $null
    $f = Join-Path $Cartella 'stato.json'
    if (Test-Path -LiteralPath $f) { $s = In-Tabella (Get-Content -LiteralPath $f -Raw -Encoding UTF8 | ConvertFrom-Json) }
    if ($null -eq $s) {
        # kit gia' presente ma senza stato (installato da una versione precedente): la situazione di partenza non e' nota
        $s = [ordered]@{ PrecedenteNoto = (-not (Test-Path -LiteralPath (Join-Path $ProfiloVlc $script:NomeFileInfo))) }
    }
    if ($null -eq $s['Vlcrc']) { $s['Vlcrc'] = [ordered]@{} }
    foreach ($k in @('PacchettiUtente', 'Registro', 'ChiaviCreate', 'PluginSha256', 'RegoleFirewall')) {
        if ($null -eq $s[$k]) { $s[$k] = New-Object System.Collections.ArrayList }
    }
    return $s
}

function Salva-Stato([string]$Cartella, $Stato) {
    if (-not (Test-Path -LiteralPath $Cartella)) { New-Item -ItemType Directory -Path $Cartella -Force | Out-Null }
    [System.IO.File]::WriteAllText((Join-Path $Cartella 'stato.json'), ($Stato | ConvertTo-Json -Depth 6), (New-Object System.Text.UTF8Encoding $false))
}

function Registra-Disinstallatore([string]$Cartella, [string]$ProfiloVlc) {
    # Voce "Kit VLC Aurora" in Impostazioni > App > App installate. E' per utente (HKCU), come il profilo di VLC
    # che il kit modifica; i diritti di amministratore li chiede il disinstallatore quando parte.
    $ps = Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe'
    $testo = [ordered]@{
        DisplayName     = 'Kit VLC Aurora'
        Publisher       = 'Domenico Tatone'
        DisplayIcon     = Join-Path $Cartella 'aurora.ico'
        InstallLocation = $Cartella
        UninstallString = ('"{0}" -NoProfile -ExecutionPolicy Bypass -File "{1}" -Pausa' -f $ps, (Join-Path $Cartella 'scripts\disinstalla.ps1'))
        InstallDate     = (Get-Date -Format 'yyyyMMdd')
        URLInfoAbout    = 'https://github.com/devdomenicotatone/vlc-aurora-kit'
    }
    $ver = Join-Path $script:KitRoot 'VERSIONE.txt'
    if (Test-Path -LiteralPath $ver) { $testo['DisplayVersion'] = (Get-Content -LiteralPath $ver -Raw).Trim() }
    $posti = @($Cartella, (Join-Path $ProfiloVlc 'skins2\Aurora.vlt'), (Join-Path $ProfiloVlc 'skins2\aurora-src'), (Join-Path $ProfiloVlc 'lua\http'))
    $byte = (Get-ChildItem -LiteralPath $posti -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    $numeri = [ordered]@{ NoModify = 1; NoRepair = 1; EstimatedSize = [int]($byte / 1KB) }
    New-Item -Path $script:ChiaveDisinstallazione -Force | Out-Null
    foreach ($n in $testo.Keys) { New-ItemProperty -Path $script:ChiaveDisinstallazione -Name $n -Value $testo[$n] -PropertyType String -Force | Out-Null }
    foreach ($n in $numeri.Keys) { New-ItemProperty -Path $script:ChiaveDisinstallazione -Name $n -Value $numeri[$n] -PropertyType DWord -Force | Out-Null }
}
