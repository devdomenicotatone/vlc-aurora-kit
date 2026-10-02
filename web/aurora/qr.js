/* Aurora - generatore di codici QR (testo a byte, correzione d'errore M, versioni 1-6: fino a 106 byte).
   Basta per l'indirizzo dell'interfaccia web e non dipende da internet ne' da librerie esterne. */
(function (global) {
  "use strict";
  // versione -> [parole di codice totali, parole di correzione per blocco, numero di blocchi] al livello M
  const VERSIONI = [null, [26, 10, 1], [44, 16, 1], [70, 26, 1], [100, 18, 2], [134, 24, 2], [172, 16, 4]];

  // ---- aritmetica di Reed-Solomon in GF(256), polinomio 0x11D
  function mul(x, y) {
    let z = 0;
    for (let i = 7; i >= 0; i--) {
      z = (z << 1) ^ ((z >>> 7) * 0x11D);
      z ^= ((y >>> i) & 1) * x;
    }
    return z;
  }
  function divisore(grado) {
    const r = new Array(grado).fill(0);
    r[grado - 1] = 1;
    let radice = 1;
    for (let i = 0; i < grado; i++) {
      for (let j = 0; j < grado; j++) {
        r[j] = mul(r[j], radice);
        if (j + 1 < grado) r[j] ^= r[j + 1];
      }
      radice = mul(radice, 2);
    }
    return r;
  }
  function resto(dati, div) {
    const r = div.map(() => 0);
    for (const b of dati) {
      const f = b ^ r.shift();
      r.push(0);
      div.forEach((c, i) => { r[i] ^= mul(c, f); });
    }
    return r;
  }

  // ---- dal testo alle parole di codice (dati + correzione, intercalate per blocco)
  function paroleDiCodice(testo) {
    const byte = Array.from(new TextEncoder().encode(testo));
    let v = 1;
    const capienza = (ver) => VERSIONI[ver][0] - VERSIONI[ver][1] * VERSIONI[ver][2];
    while (v < VERSIONI.length && byte.length + 2 > capienza(v)) v++;   // 4 bit di modo + 8 di lunghezza + 4 di chiusura
    if (v >= VERSIONI.length) throw new Error("Testo troppo lungo per il codice QR");
    const [totali, ecc, blocchi] = VERSIONI[v];
    const nDati = totali - ecc * blocchi;
    const bit = [];
    const metti = (val, n) => { for (let i = n - 1; i >= 0; i--) bit.push((val >>> i) & 1); };
    metti(4, 4);                       // modo: byte
    metti(byte.length, 8);
    byte.forEach((b) => metti(b, 8));
    metti(0, Math.min(4, nDati * 8 - bit.length));
    while (bit.length % 8) bit.push(0);
    for (let pad = 0xEC; bit.length < nDati * 8; pad ^= 0xEC ^ 0x11) metti(pad, 8);
    const dati = [];
    for (let i = 0; i < bit.length; i += 8) dati.push(bit.slice(i, i + 8).reduce((a, b) => (a << 1) | b, 0));
    // blocchi: in queste versioni sono tutti della stessa lunghezza
    const div = divisore(ecc), lung = nDati / blocchi, gruppi = [];
    for (let b = 0; b < blocchi; b++) {
      const d = dati.slice(b * lung, (b + 1) * lung);
      gruppi.push({ d, e: resto(d, div) });
    }
    const out = [];
    for (let i = 0; i < lung; i++) gruppi.forEach((g) => out.push(g.d[i]));
    for (let i = 0; i < ecc; i++) gruppi.forEach((g) => out.push(g.e[i]));
    return { versione: v, parole: out };
  }

  // ---- matrice: true = modulo scuro; riga y, colonna x
  function matrice(testo) {
    const { versione, parole } = paroleDiCodice(testo);
    const n = versione * 4 + 17;
    const m = Array.from({ length: n }, () => new Array(n).fill(false));
    const fissa = Array.from({ length: n }, () => new Array(n).fill(false));   // moduli di servizio, non dati
    const servizio = (x, y, scuro) => { m[y][x] = scuro; fissa[y][x] = true; };
    const mirino = (cx, cy) => {
      for (let dy = -4; dy <= 4; dy++) for (let dx = -4; dx <= 4; dx++) {
        const x = cx + dx, y = cy + dy, d = Math.max(Math.abs(dx), Math.abs(dy));
        if (x >= 0 && x < n && y >= 0 && y < n) servizio(x, y, d !== 2 && d !== 4);
      }
    };
    for (let i = 0; i < n; i++) { servizio(6, i, i % 2 === 0); servizio(i, 6, i % 2 === 0); }   // linee di sincronismo
    mirino(3, 3); mirino(n - 4, 3); mirino(3, n - 4);
    if (versione >= 2) {                                                                          // riferimento di allineamento
      const c = n - 7;
      for (let dy = -2; dy <= 2; dy++) for (let dx = -2; dx <= 2; dx++) servizio(c + dx, c + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
    }
    const formato = (maschera) => {
      const dati = maschera;                 // livello M = 00, poi i 3 bit della maschera
      let r = dati;
      for (let i = 0; i < 10; i++) r = (r << 1) ^ ((r >>> 9) * 0x537);
      const b = ((dati << 10) | r) ^ 0x5412;
      const bitDi = (i) => ((b >>> i) & 1) !== 0;
      for (let i = 0; i <= 5; i++) servizio(8, i, bitDi(i));
      servizio(8, 7, bitDi(6)); servizio(8, 8, bitDi(7)); servizio(7, 8, bitDi(8));
      for (let i = 9; i < 15; i++) servizio(14 - i, 8, bitDi(i));
      for (let i = 0; i < 8; i++) servizio(n - 1 - i, 8, bitDi(i));
      for (let i = 8; i < 15; i++) servizio(8, n - 15 + i, bitDi(i));
      servizio(8, n - 8, true);
    };
    formato(0);                              // riserva i posti: il contenuto vero arriva con la maschera scelta
    // dati a zig-zag dal basso a destra, due colonne alla volta
    let k = 0;
    for (let destra = n - 1; destra >= 1; destra -= 2) {
      if (destra === 6) destra = 5;
      for (let vert = 0; vert < n; vert++) for (let j = 0; j < 2; j++) {
        const x = destra - j, su = ((destra + 1) & 2) === 0, y = su ? n - 1 - vert : vert;
        if (!fissa[y][x] && k < parole.length * 8) { m[y][x] = ((parole[k >>> 3] >>> (7 - (k & 7))) & 1) !== 0; k++; }
      }
    }
    const MASCHERE = [
      (x, y) => (x + y) % 2 === 0, (x, y) => y % 2 === 0, (x, y) => x % 3 === 0, (x, y) => (x + y) % 3 === 0,
      (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0, (x, y) => (x * y) % 2 + (x * y) % 3 === 0,
      (x, y) => ((x * y) % 2 + (x * y) % 3) % 2 === 0, (x, y) => ((x + y) % 2 + (x * y) % 3) % 2 === 0,
    ];
    const applica = (i) => { for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (!fissa[y][x] && MASCHERE[i](x, y)) m[y][x] = !m[y][x]; };
    const penalita = () => {
      let p = 0, scuri = 0;
      const linea = (cella) => {             // serie di 5 o piu' moduli uguali e sagome simili a un mirino
        for (let a = 0; a < n; a++) {
          let serie = 1, storia = "";
          for (let b = 0; b < n; b++) {
            storia += cella(a, b) ? "1" : "0";
            if (b > 0 && cella(a, b) === cella(a, b - 1)) { serie++; if (serie === 5) p += 3; else if (serie > 5) p++; } else serie = 1;
          }
          for (const sagoma of ["10111010000", "00001011101"]) for (let i = storia.indexOf(sagoma); i >= 0; i = storia.indexOf(sagoma, i + 1)) p += 40;
        }
      };
      linea((y, x) => m[y][x]); linea((x, y) => m[y][x]);
      for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) {
        if (m[y][x]) scuri++;
        if (x + 1 < n && y + 1 < n && m[y][x] === m[y][x + 1] && m[y][x] === m[y + 1][x] && m[y][x] === m[y + 1][x + 1]) p += 3;
      }
      return p + Math.floor(Math.abs(scuri * 20 - n * n * 10) / (n * n)) * 10;
    };
    let migliore = 0, minimo = Infinity;
    for (let i = 0; i < 8; i++) {
      applica(i); formato(i);
      const p = penalita();
      if (p < minimo) { minimo = p; migliore = i; }
      applica(i);                            // la stessa maschera due volte la toglie
    }
    applica(migliore); formato(migliore);
    return m;
  }

  // ---- disegno SVG: moduli scuri su fondo chiaro, con il margine bianco richiesto dallo standard (4 moduli)
  function svg(testo, margine) {
    const m = matrice(testo), n = m.length, q = margine == null ? 4 : margine, lato = n + q * 2;
    let d = "";
    for (let y = 0; y < n; y++) for (let x = 0; x < n; x++) if (m[y][x]) d += "M" + (x + q) + " " + (y + q) + "h1v1h-1z";
    return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + lato + " " + lato + '" shape-rendering="crispEdges" role="img">' +
      '<rect width="100%" height="100%" fill="#fff"/><path d="' + d + '" fill="#0F1218"/></svg>';
  }

  global.AuroraQR = { matrice, svg };
})(typeof window !== "undefined" ? window : globalThis);
