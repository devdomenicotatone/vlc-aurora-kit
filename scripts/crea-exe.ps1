<#
  crea-exe.ps1 - costruisce dist\VLC-Aurora-Setup.exe, un auto-estraente 7-Zip che scompatta il kit in una
  cartella temporanea, avvia installa.cmd e alla fine ripulisce. Usa tools\7zr.exe (compressore 7z, LGPL) e
  tools\7zSD.sfx (modulo auto-estraente di 7-Zip 9.20, che legge la configurazione ;!@Install@!).
  -Versione 1.2.3  scrive VERSIONE.txt dentro il pacchetto.
  -Prova           costruisce dist\VLC-Aurora-Setup-prova.exe che esegue solo "installa.cmd -SoloVerifica"
                   senza pausa finale e lascia un marcatore in %TEMP%\kit-sfx-prova.txt (per collaudare il meccanismo).
#>
[CmdletBinding()]
param([string]$Versione = '', [switch]$Prova)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'comuni.ps1')
$script:LogFile = Join-Path $KitRoot 'esporta.log'
$tools = Join-Path $KitRoot 'tools'
$dist = Join-Path $KitRoot 'dist'
$sfx = Join-Path $tools '7zSD.sfx'
$sevenZr = Join-Path $tools '7zr.exe'
foreach ($f in @($sfx, $sevenZr)) { if (-not (Test-Path -LiteralPath $f)) { Scrivi-Errore ('manca ' + $f); exit 1 } }
if (-not (Test-Path -LiteralPath $dist)) { New-Item -ItemType Directory -Path $dist | Out-Null }
$nome = if ($Prova) { 'VLC-Aurora-Setup-prova.exe' } else { 'VLC-Aurora-Setup.exe' }

# Sostituzione delle icone di un eseguibile con quelle di un file .ico (API UpdateResource di Windows).
Add-Type -TypeDefinition @'
using System;
using System.IO;
using System.Collections.Generic;
using System.Runtime.InteropServices;
public static class IconaExe {
    delegate bool EnumNomi(IntPtr modulo, IntPtr tipo, IntPtr nome, IntPtr param);
    delegate bool EnumLingue(IntPtr modulo, IntPtr tipo, IntPtr nome, ushort lingua, IntPtr param);
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)] static extern IntPtr LoadLibraryEx(string file, IntPtr riservato, uint flag);
    [DllImport("kernel32.dll")] static extern bool FreeLibrary(IntPtr modulo);
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)] static extern bool EnumResourceNames(IntPtr modulo, IntPtr tipo, EnumNomi cb, IntPtr param);
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)] static extern bool EnumResourceLanguages(IntPtr modulo, IntPtr tipo, IntPtr nome, EnumLingue cb, IntPtr param);
    [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)] static extern IntPtr BeginUpdateResource(string file, bool eliminaEsistenti);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool UpdateResource(IntPtr agg, IntPtr tipo, IntPtr nome, ushort lingua, byte[] dati, uint dimensione);
    [DllImport("kernel32.dll", SetLastError = true)] static extern bool EndUpdateResource(IntPtr agg, bool scarta);
    const int RT_ICON = 3, RT_GROUP_ICON = 14;

    // Mette nell'eseguibile le immagini del file .ico, con il nome e la lingua del gruppo di icone che c'era gia'
    // (e' quello che il programma carica). Ritorna il numero di misure scritte.
    public static int Sostituisci(string exe, string ico) {
        var vecchie = new List<int[]>();   // tipo, nome, lingua delle icone presenti
        bool nomiTestuali = false;
        IntPtr modulo = LoadLibraryEx(exe, IntPtr.Zero, 2);   // LOAD_LIBRARY_AS_DATAFILE
        if (modulo == IntPtr.Zero) throw new Exception("LoadLibraryEx: errore " + Marshal.GetLastWin32Error());
        foreach (int tipo in new int[] { RT_ICON, RT_GROUP_ICON }) {
            int t = tipo;
            EnumResourceNames(modulo, (IntPtr)t, (m, ty, nome, p) => {
                if ((nome.ToInt64() >> 16) != 0) { nomiTestuali = true; return true; }
                EnumResourceLanguages(m, ty, nome, (m2, ty2, nome2, lingua, p2) => {
                    vecchie.Add(new int[] { t, (int)nome2.ToInt64(), lingua }); return true; }, IntPtr.Zero);
                return true; }, IntPtr.Zero);
        }
        FreeLibrary(modulo);
        if (nomiTestuali) throw new Exception("icone con nome testuale: non gestite");

        int gruppo = 1, linguaGruppo = 0;
        foreach (int[] v in vecchie) { if (v[0] == RT_GROUP_ICON) { gruppo = v[1]; linguaGruppo = v[2]; break; } }
        byte[] d = File.ReadAllBytes(ico);
        if (d.Length < 6 || BitConverter.ToUInt16(d, 2) != 1) throw new Exception("non e' un file .ico");
        int n = BitConverter.ToUInt16(d, 4);

        IntPtr agg = BeginUpdateResource(exe, false);
        if (agg == IntPtr.Zero) throw new Exception("BeginUpdateResource: errore " + Marshal.GetLastWin32Error());
        bool ok = true;
        // via le icone vecchie che non vengono riscritte qui sotto
        foreach (int[] v in vecchie) {
            bool riscritta = v[2] == linguaGruppo && ((v[0] == RT_ICON && v[1] >= 1 && v[1] <= n) || (v[0] == RT_GROUP_ICON && v[1] == gruppo));
            if (!riscritta) ok &= UpdateResource(agg, (IntPtr)v[0], (IntPtr)v[1], (ushort)v[2], null, 0);
        }
        var elenco = new MemoryStream();
        var w = new BinaryWriter(elenco);
        w.Write((ushort)0); w.Write((ushort)1); w.Write((ushort)n);
        for (int i = 0; i < n; i++) {
            int voce = 6 + 16 * i;
            int dimensione = BitConverter.ToInt32(d, voce + 8), inizio = BitConverter.ToInt32(d, voce + 12);
            byte[] immagine = new byte[dimensione];
            Array.Copy(d, inizio, immagine, 0, dimensione);
            ok &= UpdateResource(agg, (IntPtr)RT_ICON, (IntPtr)(i + 1), (ushort)linguaGruppo, immagine, (uint)dimensione);
            w.Write(d, voce, 12);         // larghezza, altezza, colori, riservato, piani, bit per pixel, dimensione
            w.Write((ushort)(i + 1));     // numero della risorsa RT_ICON
        }
        byte[] g = elenco.ToArray();
        ok &= UpdateResource(agg, (IntPtr)RT_GROUP_ICON, (IntPtr)gruppo, (ushort)linguaGruppo, g, (uint)g.Length);
        if (!EndUpdateResource(agg, !ok) || !ok) throw new Exception("UpdateResource: errore " + Marshal.GetLastWin32Error());
        return n;
    }
}
'@
Scrivi-Titolo ('Creazione di ' + $nome)

# 1. copia pulita del kit in una cartella temporanea (senza repository, pacchetti, strumenti e file di lavoro)
$stage = Join-Path $env:TEMP ('vlc-kit-stage-' + [guid]::NewGuid().ToString('N').Substring(0, 8))
# Le cartelle di lavoro vanno escluse con il percorso completo: robocopy scarta OVUNQUE le cartelle con il nome
# indicato, senza distinguere maiuscole (escludere "Aurora" toglieva anche web\aurora, cioe' la pagina web).
# Il sorgente del modulo skins2 modificato (plugin\src\skins2-patched) resta nel repository: chi scarica l'EXE lo trova
# nella stessa pagina della release, come "Source code" (la GPL chiede che sia offerto dallo stesso posto del binario).
$fuori = @('.git', '.github', 'dist', 'tools', 'skin\src\Aurora', 'plugin\src\src', 'plugin\src\sdk', 'plugin\src\skins2-patched', 'plugin\src\obj') | ForEach-Object { Join-Path $KitRoot $_ }
Copia-Cartella $KitRoot $stage ($fuori + '__pycache__') @('*.log', 'installa.esito.json', 'disinstalla.esito.json', 'test-vlcrc', 'test.pid', '.gitignore', '.gitattributes', 'Aurora.vlt', 'Aurora.json', (Join-Path $KitRoot 'plugin\src\libskins2_plugin.dll'))
# l'EXE e' costruito sul modulo auto-estraente di 7-Zip (LGPL): la sua licenza viaggia con il pacchetto
Copy-Item -LiteralPath (Join-Path $tools '7-Zip-License.txt') -Destination (Join-Path $stage '7-Zip-License.txt') -Force
if ($Versione -ne '') { [System.IO.File]::WriteAllText((Join-Path $stage 'VERSIONE.txt'), $Versione + "`r`n") }
if ($Prova) {
    # stesso lanciatore reale, ma in modalita' verifica, con output nel marcatore e senza pausa finale
    $cmd = Join-Path $stage 'installa.cmd'
    $testo = [System.IO.File]::ReadAllText($cmd)
    $testo = $testo.Replace('"%~dp0scripts\installa.ps1" %*', '"%~dp0scripts\installa.ps1" -SoloVerifica > "%TEMP%\kit-sfx-prova.txt" 2>&1')
    $testo = $testo.Replace('pause', 'echo FINE %ERRORLEVEL% >> "%TEMP%\kit-sfx-prova.txt"')
    [System.IO.File]::WriteAllText($cmd, $testo, [System.Text.Encoding]::ASCII)
}
Scrivi-Info ('{0} file preparati in {1}' -f (Get-ChildItem -LiteralPath $stage -Recurse -File).Count, $stage)

# 2. archivio 7z con LZMA (il modulo auto-estraente 9.20 non decodifica LZMA2)
$archivio = Join-Path $dist 'kit.7z'
if (Test-Path -LiteralPath $archivio) { [System.IO.File]::Delete($archivio) }
Push-Location $stage
try {
    $eap = $ErrorActionPreference; $ErrorActionPreference = 'Continue'
    $out = & $sevenZr a -y -t7z -m0=lzma -mx=7 $archivio '*' -r 2>&1 | ForEach-Object { "$_" }
    $code = $LASTEXITCODE
    $ErrorActionPreference = $eap
} finally { Pop-Location }
if ($code -ne 0) { Scrivi-Errore ('7zr ha restituito ' + $code + ': ' + (($out | Select-Object -Last 3) -join ' ')); exit 1 }

# 3. modulo auto-estraente con l'icona del kit (config\aurora.ico) al posto di quella generica di 7-Zip: e' l'icona
#    che Esplora file e il browser mostrano per l'EXE. Si lavora su una copia: tools\7zSD.sfx resta l'originale.
$modulo = Join-Path $dist 'modulo.sfx'
Copy-Item -LiteralPath $sfx -Destination $modulo -Force
try {
    $misure = [IconaExe]::Sostituisci($modulo, (Join-Path $KitRoot 'config\aurora.ico'))
    Scrivi-Info ('icona del kit nel modulo auto-estraente ({0} misure)' -f $misure)
} catch {
    Scrivi-Avviso ('icona non sostituita, resta quella di 7-Zip: ' + $_.Exception.Message)
    Copy-Item -LiteralPath $sfx -Destination $modulo -Force
}

# 4. configurazione dell'auto-estraente e concatenazione: modulo + configurazione + archivio
$cfg =";!@Install@!UTF-8!`r`n" + "Title=`"Kit VLC Aurora`"`r`n"
if (-not $Prova) { $cfg += "BeginPrompt=`"Installare e configurare VLC con la skin Aurora, YouTube, menu Blu-ray e interfaccia web?`"`r`n" }
# Directory="" fa cercare cmd.exe nelle cartelle di sistema (il predefinito ".\" lo cercherebbe nell'archivio);
# %%T e' la cartella temporanea di estrazione, \" sono virgolette letterali (sequenze del parser di 7zSD).
$cfg += 'Directory=""' + "`r`n" + 'RunProgram="cmd.exe /c \"%%T\installa.cmd\""' + "`r`n" + ";!@InstallEnd@!`r`n"
$exe = Join-Path $dist $nome
$ms = New-Object System.IO.MemoryStream
$b = [System.IO.File]::ReadAllBytes($modulo); $ms.Write($b, 0, $b.Length)
$b = [System.Text.Encoding]::UTF8.GetBytes($cfg); $ms.Write($b, 0, $b.Length)
$b = [System.IO.File]::ReadAllBytes($archivio); $ms.Write($b, 0, $b.Length)
[System.IO.File]::WriteAllBytes($exe, $ms.ToArray())
[System.IO.File]::Delete($archivio)
[System.IO.File]::Delete($modulo)
[System.IO.Directory]::Delete($stage, $true)

# 5. impronta SHA-256 (pubblicata con la release)
$hash = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLower()
if (-not $Prova) { [System.IO.File]::WriteAllText((Join-Path $dist 'SHA256SUMS.txt'), $hash + '  ' + $nome + "`n") }
Scrivi-Ok ('{0}  ({1:N1} MB)' -f $exe, ((Get-Item -LiteralPath $exe).Length / 1MB))
Scrivi-Info ('SHA-256: ' + $hash)
