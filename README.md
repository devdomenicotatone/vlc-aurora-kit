# Kit VLC Aurora

Rimette in piedi "il mio VLC" su un PC Windows con un clic: VLC 3.x, la skin **Aurora**, la riproduzione di
YouTube tramite yt-dlp, Java per i menu dei Blu-ray, le finestre Qt scure, l'**interfaccia web Aurora**
(telecomando da browser e telefono) con la regola firewall. Niente altro: solo la nostra skin e le nostre modifiche.

Software libero sotto licenza [GNU GPL versione 2 o successiva](COPYING). È un progetto indipendente: non è un
prodotto di VideoLAN e non ne ha l'approvazione (vedi [Licenza](#licenza)). Se ti è utile puoi
[offrirmi un caffè](https://www.paypal.com/paypalme/domenicotatone).

## Installazione su un PC nuovo

**Con l'EXE (consigliato).** Scarica l'ultima versione da
[**Releases → VLC-Aurora-Setup.exe**](../../releases/latest/download/VLC-Aurora-Setup.exe) e avviala.
L'auto-estraente scompatta il kit in una cartella temporanea, lancia `installa.cmd` e alla fine ripulisce.

- Windows SmartScreen può avvisare perché il file non è firmato digitalmente: **Ulteriori informazioni → Esegui comunque**.
  Il file `SHA256SUMS.txt` allegato alla release permette di verificare l'impronta
  (`Get-FileHash .\VLC-Aurora-Setup.exe` in PowerShell).
- Quando Windows lo chiede, approva la richiesta di amministratore (una sola volta).

**Senza EXE.** Code → Download ZIP (oppure `git clone`), scompatta e fai doppio clic su **`installa.cmd`**.

Alla fine la finestra mostra il riepilogo e la **password dell'interfaccia web** (salvata anche in
`%APPDATA%\vlc\aurora-kit-info.txt`), poi avvia VLC con la skin Aurora.
Per vedere prima cosa farebbe, senza toccare nulla: prompt nella cartella e `installa.cmd -SoloVerifica`.

Requisiti: Windows 10 o 11 con **winget** (di serie; se manca, "Programma di installazione app" dal Microsoft Store)
e collegamento a internet. Si può rieseguire quando si vuole: ogni passo controlla lo stato attuale.

## Cosa fa l'installer

| Passo | Dettaglio |
|---|---|
| VLC media player | `winget install VideoLAN.VLC` scegliendo l'ultima versione **3.x** (la skin è pensata per VLC 3). Se VLC c'è già lo lascia com'è. |
| yt-dlp | `winget install yt-dlp.yt-dlp` in ambito utente (o aggiornamento all'ultima versione). Lo script `youtube.lua` lo trova da solo. |
| Java Temurin 17 JRE | installazione con winget e chiavi di registro `HKLM\SOFTWARE\JavaSoft\JRE` + `JAVA_HOME`, usate da libbluray per i menu Blu-ray (BD-J). |
| Java Access Bridge | se nel profilo è attivo il ponte di Java per i lettori di schermo, lo disattiva (`jabswitch -disable`): dentro VLC non si carica e impedisce ai menu Java dei Blu-ray di partire. Con `installa.cmd -LasciaAccessBridge` resta com'è. |
| Skin Aurora | copia in `%APPDATA%\vlc\skins2\Aurora.vlt` la variante con la scala più vicina a quella di Windows (100, 125, 150, 175, 200%). I sorgenti vanno in `skins2\aurora-src`. |
| Script YouTube | `%APPDATA%\vlc\lua\playlist\youtube.lua`: risolve i link YouTube con yt-dlp (VLC 3.0.24 non ha più il suo). |
| Interfaccia web Aurora | `%APPDATA%\vlc\lua\http`: la pagina Aurora (`web\`) più gli handler dell'API copiati dall'installazione locale di VLC, perché la cartella utente sostituisce per intero quella di sistema. |
| Opzioni di VLC | in `vlcrc`: interfaccia skins2 con Aurora, palette scura Qt, interfaccia web, menu Blu-ray, posizioni iniziali delle finestre calcolate per lo schermo. Password web generata (o mantenuta se c'è già). |
| Finestre Qt scure | `QtStyle=Fusion` in `vlc-qt-interface.ini`: con lo stile nativo la palette scura lasciava testi illeggibili. |
| Plugin Snap nativo | `plugin\libskins2_plugin.dll` (modulo skins2 ricompilato) in `plugins\gui`: dà alle finestre della skin lo Snap di Windows, Win+frecce, i layout di aggancio e il ridimensionamento da tutti i lati, e lascia a Windows il contorno della finestra (angoli arrotondati, ombra, bordo). L'originale è salvato come `.orig` e la cache dei plugin viene rigenerata. |
| Firewall | regola in ingresso "VLC interfaccia web (porta 8080)": TCP 8080, solo reti private, solo `vlc.exe`. Disattiva le regole di blocco automatiche di Windows per vlc.exe. |
| Disinstallatore | copia di `disinstalla.ps1` e stato dell'installazione in `%LOCALAPPDATA%\VLC-Aurora-Kit`, voce **Kit VLC Aurora** in "App installate". |

Tutto ciò che riguarda VLC finisce nel profilo utente (`%APPDATA%\vlc`): gli aggiornamenti di VLC 3.0.x non lo toccano.

## Disinstallazione

**Impostazioni → App → App installate → Kit VLC Aurora → Disinstalla**, oppure doppio clic su **`disinstalla.cmd`**
nella cartella del kit. Chiede conferma, poi i diritti di amministratore (una sola volta), e toglie tutto insieme:

| Cosa | Come torna |
|---|---|
| Skin, script YouTube, interfaccia web | via `skins2\Aurora.vlt`, `skins2\aurora-src`, `lua\playlist\youtube.lua`, `lua\http` e `aurora-kit-info.txt` dal profilo; se prima del kit c'erano un tuo `youtube.lua` o una tua `lua\http`, tornano quelli. |
| Opzioni di VLC | in `vlcrc` e `vlc-qt-interface.ini` ogni opzione del kit torna alla riga che c'era prima. Quelle che hai cambiato dopo l'installazione restano come le hai messe. |
| Plugin skins2 | `libskins2_plugin.dll.orig` torna al posto del plugin del kit e la cache dei plugin viene rigenerata. Se nel frattempo VLC si è aggiornato e ha già rimesso il suo, viene solo tolta la copia `.orig`. |
| Firewall | la regola "VLC interfaccia web (porta 8080)" viene rimossa e le regole di blocco che l'installer aveva disattivato tornano attive. |
| Registro Java | i valori di `HKLM\SOFTWARE\JavaSoft\JRE` e `JAVA_HOME` cambiati dal kit tornano com'erano. |
| Java Access Bridge | se l'aveva disattivato il kit, torna attivo. |
| Programmi | VLC, Java Temurin 17 JRE e yt-dlp **restano**, a meno che tu non risponda di toglierli: **T** tutti, **K** solo quelli che aveva installato il kit, **N** nessuno. Con yt-dlp vanno via anche i pacchetti che winget aveva aggiunto insieme a lui (FFmpeg, Deno), se li aveva installati il kit. Il profilo `%APPDATA%\vlc` resta comunque. |
| Kit | voce in "App installate" e cartella `%LOCALAPPDATA%\VLC-Aurora-Kit`. |

Il resto del profilo di VLC (altre skin, cronologia, altre opzioni) non viene toccato.
Per vedere prima cosa farebbe: `disinstalla.cmd -SoloVerifica`. Senza domande: `disinstalla.cmd -Si -Programmi Nessuno`
(oppure `Kit` o `Tutti`).

Per rimettere le cose com'erano l'installer annota, la prima volta che gira, che cosa c'era prima
(`%LOCALAPPDATA%\VLC-Aurora-Kit\stato.json`). Un kit installato con una versione più vecchia non ha queste note:
il disinstallatore funziona lo stesso, ma riporta le opzioni del kit al valore predefinito di VLC e non sa quali
programmi aveva installato il kit (te lo chiede).

## La skin Aurora

Tema scuro grafite con accento arancione → rosa → viola, font Poppins, icone Segoe Fluent. Finestra principale con
menu a **cassetto laterale** (pulsante ≡: restringe il video, non può finire dietro la finestra), playlist ed
equalizzatore (preamplificazione + 10 bande) come finestre agganciabili della stessa larghezza, controller a
schermo intero, ripetizione a tre stati, controllo della velocità, stati "attivo" colorati con anello al passaggio del mouse.
Nel menu, **Telecomando web** apre nel browser la pagina dell'interfaccia web (serve il plugin skins2 del kit).
Generata da `skin\src\build_aurora.py` in cinque scale, perché VLC disegna le skin 1:1 in pixel fisici.

Le finestre sono rettangoli pieni e il contorno lo disegna Windows, come per le applicazioni moderne: su Windows 11
angoli arrotondati senza scalettature, ombra e bordo sottile nel colore della skin; da ingrandite o agganciate gli
angoli tornano vivi. Serve il plugin skins2 del kit (vedi sotto). Con `AURORA_NATIVE_FRAME=0` il generatore torna
alla sagoma ritagliata dalla skin (raggio 14, bordi netti, niente ombra).

## L'interfaccia web Aurora

Sul PC si apre dal menu della skin (**Telecomando web**) oppure all'indirizzo `http://localhost:8080`: utente vuoto e
la password del kit. Riproduzione, posizione, volume, velocità, casuale e ripetizione, schermo intero,
playlist (clic per riprodurre, cestino per togliere), **Sfoglia** per aprire file e cartelle del PC, **Equalizzatore**,
casella per incollare un indirizzo (anche YouTube). Scorciatoie da tastiera: spazio, frecce, M, F.

**Dal telefono.** Nella pagina aperta sul PC il pulsante **Telefono** mostra l'indirizzo del PC nella rete di casa
(`http://<ip-del-pc>:8080`), un codice QR da inquadrare con la fotocamera e, su richiesta, la password. Il telefono
deve essere sulla stessa rete e in Windows quella rete deve essere impostata come **Privata**: la regola firewall
del kit non vale per le reti pubbliche. L'indirizzo lo comunica alla pagina il plugin skins2 del kit; con il plugin
ufficiale di VLC il codice usa il nome del PC, che non tutti i telefoni sanno trovare. Il codice QR è generato
nella pagina, senza internet.

## Tenere aggiornato il kit

Dopo aver modificato qualcosa sul PC (skin, script, pagina web, opzioni), nella cartella del kit:

- **`esporta.cmd`** copia nel kit `youtube.lua`, i sorgenti della skin, la pagina web e i valori attuali delle opzioni.
- `esporta.cmd -Push` fa anche commit e push su GitHub.
- **`genera-varianti.cmd`** rigenera le cinque skin da `skin\src\build_aurora.py` (serve Python 3 con Pillow:
  `winget install Python.Python.3.12` e `python -m pip install pillow`). `esporta.cmd -Varianti -Push` fa tutto in una volta.
- **`crea-exe.cmd`** costruisce `dist\VLC-Aurora-Setup.exe` (auto-estraente 7-Zip: `tools\7zSD.sfx` + `tools\7zr.exe`,
  nessuna installazione richiesta). `crea-exe.cmd -Prova` crea una variante che esegue solo la verifica.
- **`pubblica.cmd 1.0.1`** costruisce l'EXE, crea il tag `v1.0.1` e pubblica la Release su GitHub con EXE e checksum
  (serve GitHub CLI: `winget install GitHub.cli`, poi `gh auth login`). Gli EXE non vengono mai committati nel repository.

## Struttura

```
installa.cmd / disinstalla.cmd / esporta.cmd / genera-varianti.cmd / crea-exe.cmd / pubblica.cmd   lanciatori a doppio clic
scripts/installa.ps1          installer (fase utente + fase amministratore con una sola UAC)
scripts/disinstalla.ps1       disinstallatore (stesse fasi, al contrario)
scripts/esporta.ps1           aggiorna il kit dal PC
scripts/genera-varianti.ps1   rigenera le skin
scripts/crea-exe.ps1          costruisce l'auto-estraente
scripts/pubblica-release.ps1  tag + Release su GitHub
scripts/comuni.ps1            funzioni condivise (vlcrc, ini, DPI, winget, firewall, copie, stato dell'installazione)
scripts/crea-icona.py         ridisegna config/aurora.ico (Python 3 con Pillow)
skin/Aurora-NNN.vlt           skin precompilate per scala 100..200% (+ Aurora-NNN.json con le dimensioni)
skin/src/                     generatore build_aurora.py, font Poppins (OFL), strumenti di prova, LEGGIMI.txt
web/                          interfaccia web Aurora (index.html, aurora/aurora.css, aurora/aurora.js, font, favicon;
                              aurora/qr.js genera i codici QR, aurora/telefono.json dà alla pagina gli indirizzi del PC)
plugin/libskins2_plugin.dll   modulo skins2 ricompilato (Snap nativo di Windows, telecomando web) + src/ con diff e script di build
plugin/src/skins2-patched/    sorgente completo del modulo skins2 modificato (GPL)
COPYING                       testo della GNU GPL versione 2
.github/FUNDING.yml           pulsante Sponsor di GitHub (link per le donazioni)
lua/playlist/youtube.lua      ponte YouTube -> yt-dlp
config/vlcrc.opzioni          opzioni applicate a vlcrc
config/aurora.ico             icona del kit: in "App installate" e sull'EXE di installazione
tools/                        7zr.exe e 7zSD.sfx di 7-Zip (licenza LGPL inclusa) per creare l'EXE
```

## Snap nativo di Windows (plugin ricompilato)

Le finestre delle skin di VLC normalmente non si agganciano ai bordi di Windows. Il kit include un modulo
`skins2` ricompilato che dà loro lo Snap nativo: trascinamento ai bordi, Win+frecce, massimizzazione all'area
di lavoro, layout di aggancio, con le finestre agganciate (playlist, equalizzatore) che seguono la principale.
Su Windows 11 il menu di disposizione compare anche fermando il mouse sul pulsante Ingrandisci della skin.

Le finestre si ridimensionano da tutti i lati e da tutti gli angoli, come ogni finestra di Windows: il puntatore
diventa la doppia freccia appena fuori dal bordo sinistro, destro e inferiore (anche accanto al video) e sulla fascia
in cima alla barra del titolo. È Windows a ridimensionare, con le misure minime della skin, e la skin si ridisegna
abbastanza in fretta da seguire il mouse senza scatti (un quinto del tempo di prima a ogni passo).

La cornice di sistema non si vede mai e la skin disegna tutto: il plugin impedisce a Windows di ridisegnare il
vecchio telaio sopra la skin quando la finestra perde o riprende il focus (era la cornice chiara che compariva
selezionando un'altra finestra). Alle finestre rettangolari non applica più una sagoma, così è il compositore di
Windows (DWM) a disegnarne il contorno: angoli arrotondati, ombra più leggera da inattiva, bordo nel colore della skin.
Le skin sagomate restano ritagliate come prima.

Lo stesso modulo aggiunge alle skin il comando che apre la pagina del telecomando web e comunica alla pagina gli
indirizzi di rete del PC, per il riquadro "Collega il telefono". Inoltre tiene le finestre di VLC (Apri media,
Preferenze, selettori di file…) sempre sopra il player, anche quando questo è "sempre in primo piano".

Dettagli, diff dei sorgenti e istruzioni per ricompilarlo sono in [`plugin/LEGGIMI.txt`](plugin/LEGGIMI.txt) e
`plugin/src/`. Vale per VLC 3.0.x a 64 bit.

## Note e limiti

- **Blu-ray originali (AACS).** I dischi commerciali sono cifrati con AACS: servono la libreria libaacs e un file di chiavi
  `KEYDB.cfg` in `%APPDATA%\aacs\`. Le chiavi appartengono ad AACS LA (studios e produttori) e non sono distribuite con VLC
  né con questo kit. Le cartelle Blu-ray già decifrate (struttura BDMV) non ne hanno bisogno: basta Java per i menu.
  Nella finestra "Apri disco" scegliere **Blu-ray** (prefisso `bluray:///`), non DVD.
- **Perché Java 17 e non una versione più recente.** La libreria Blu-ray di VLC 3.0.24 (libbluray 1.4.1) fa girare i
  menu dentro un recinto di sicurezza che si appoggia al Security Manager di Java. Con Java 17 il recinto è attivo; con
  Java 21 i menu partono ma il recinto no, e il codice del disco può leggere e scrivere file del PC; da Java 24 i menu
  non partono. Temurin 17 riceve aggiornamenti almeno fino a ottobre 2027.
- **Java Access Bridge.** Se un lettore di schermo o un altro programma lo riattiva nel profilo
  (`%USERPROFILE%\.accessibility.properties`), i menu Java dei Blu-ray smettono di partire: rilancia `installa.cmd`
  oppure esegui `jabswitch.exe -disable` dalla cartella `bin` di Java.
- **VLC 4.** Quando uscirà stabile cambia l'interfaccia e le skin skins2 potrebbero non essere più supportate:
  per questo l'installer sceglie l'ultima versione 3.x su winget.
- **Scala dello schermo.** VLC disegna la skin 1:1 in pixel fisici: l'installer sceglie la variante in base alla scala
  di Windows al momento dell'installazione. Se cambi scala, rilancia `installa.cmd` (o copia a mano un'altra
  `skin\Aurora-NNN.vlt` su `%APPDATA%\vlc\skins2\Aurora.vlt`).
- **Interfaccia web.** Raggiungibile con la password mostrata alla fine dell'installazione; la regola firewall vale solo
  per le reti private. Gli handler dell'API in `lua\http\requests` sono copiati dalla versione di VLC installata:
  dopo un aggiornamento importante di VLC rilancia `installa.cmd` per aggiornarli.
- **EXE non firmato.** Un certificato di firma del codice costa centinaia di euro l'anno e non ha senso per un uso
  personale: resta l'avviso SmartScreen e il checksum pubblicato nella release.
- **Plugin skins2 ricompilato.** `plugin\libskins2_plugin.dll` non è il modulo ufficiale di VideoLAN ma una build
  da sorgenti patchati (diff in `plugin/src`, checksum in `plugin/libskins2_plugin.dll.sha256`). Un aggiornamento di
  VLC lo sovrascrive con l'originale: in quel caso rilancia `installa.cmd` per rimetterlo (nel frattempo Aurora
  funziona lo stesso, ma senza Snap e con le finestre ad angoli vivi e senza ombra). Per tornare all'ufficiale
  senza disinstallare il kit: sostituisci la dll con `libskins2_plugin.dll.orig` in `plugins\gui` e rilancia
  `vlc-cache-gen.exe` (da amministratore).
- **Ripristino.** Per togliere tutto c'è il disinstallatore (vedi [Disinstallazione](#disinstallazione)). Per tornare
  solo all'interfaccia normale di VLC tenendo il resto: Preferenze → Interfaccia → "Usa l'interfaccia nativa".
  Installer e disinstallatore salvano un log (`installa.log`, `disinstalla.log`) nella cartella del kit; il
  disinstallatore avviato da "App installate" lo salva in `%TEMP%\VLC-Aurora-Kit-disinstalla.log`.

## Licenza

Copyright © 2026 Domenico Tatone. Il kit è software libero: puoi ridistribuirlo e modificarlo secondo i termini della
**GNU General Public License versione 2 o, a tua scelta, una versione successiva** (testo in [`COPYING`](COPYING)).
È distribuito senza alcuna garanzia.

- **Plugin skins2.** `plugin/libskins2_plugin.dll` è il modulo `skins2` di VLC media player 3.0.24 (copyright
  VideoLAN e autori, GPL versione 2 o successiva) con le modifiche del kit, sotto la stessa licenza. Il sorgente
  completo del modulo modificato è in `plugin/src/skins2-patched/` (ogni file cambiato lo dichiara nell'intestazione);
  `plugin/src/skins2-snap.patch` è la differenza rispetto all'originale, `apply_patch.py` e `build.sh` la riproducono
  e la compilano partendo dai sorgenti ufficiali di VLC. Chi scarica l'EXE trova lo stesso sorgente nella pagina
  della release ("Source code"). Le librerie collegate staticamente nella dll sono elencate in `plugin/LEGGIMI.txt`.
- **VLC non è nel pacchetto.** L'installer lo fa installare a winget dalla fonte ufficiale, così come Java e yt-dlp.
- **Marchi.** VLC, VLC media player e VideoLAN sono marchi di VideoLAN. Il nome "Kit VLC Aurora" dice solo a quale
  programma il kit è destinato: il progetto non è affiliato a VideoLAN né approvato da VideoLAN.
- **Font.** I font Poppins sono distribuiti con la licenza SIL Open Font License (`skin/src/fonts/OFL.txt`).
  Le icone della skin derivano dal font di sistema Segoe Fluent Icons al momento della generazione.
- **7-Zip.** `tools/7zr.exe` e `tools/7zSD.sfx` (il modulo su cui è costruito l'EXE) sono parte di 7-Zip
  (Igor Pavlov), licenza GNU LGPL (`tools/7-Zip-License.txt`, incluso anche nell'EXE). Nell'EXE il modulo ha una
  sola modifica: l'icona, sostituita con quella del kit da `scripts/crea-exe.ps1`.

## Sostieni il progetto

Il kit è gratuito. Se ti fa comodo e vuoi ringraziare, puoi offrirmi un caffè:
<https://www.paypal.com/paypalme/domenicotatone> (lo stesso indirizzo si apre dalla voce **Buy me a coffee** in fondo
al menu della skin e dal pulsante **Sponsor** di questa pagina). Le donazioni vanno all'autore del kit, non a VideoLAN:
per sostenere VLC c'è <https://www.videolan.org/contribute.html>.
