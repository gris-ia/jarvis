"""Strumenti per leggere, scrivere e cercare file."""

from __future__ import annotations

import fnmatch
import os
import shutil
from pathlib import Path

from . import strumento

LIMITE_LETTURA = 60000


def _percorso(p: str) -> Path:
    return Path(os.path.expandvars(os.path.expanduser(p))).resolve()


@strumento(
    "elenca_cartella",
    "Elenca il contenuto di una cartella con dimensioni e date. '~' indica la home dell'utente.",
    {"percorso": {"type": "string", "description": "Cartella da elencare (predefinita: home)."}},
)
def elenca_cartella(percorso: str = "~") -> str:
    cartella = _percorso(percorso)
    if not cartella.is_dir():
        return f"'{cartella}' non è una cartella."
    righe = [f"Contenuto di {cartella}:"]
    voci = sorted(cartella.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    for v in voci[:300]:
        try:
            if v.is_dir():
                righe.append(f"[DIR]  {v.name}")
            else:
                righe.append(f"       {v.name}  ({v.stat().st_size / 1024:.1f} KB)")
        except OSError:
            continue
    if len(voci) > 300:
        righe.append(f"... e altri {len(voci) - 300} elementi")
    return "\n".join(righe)


@strumento(
    "leggi_file",
    "Legge il contenuto di un file di testo (codice, documenti, log, csv...).",
    {"percorso": {"type": "string", "description": "Percorso del file."}},
    ["percorso"],
)
def leggi_file(percorso: str) -> str:
    f = _percorso(percorso)
    if f.suffix.lower() == ".pdf":
        try:
            from pypdf import PdfReader

            testo = "\n".join(pagina.extract_text() or "" for pagina in PdfReader(str(f)).pages)
        except ImportError:
            return "Per leggere i PDF installa 'pypdf'."
    elif f.suffix.lower() == ".docx":
        try:
            import docx

            testo = "\n".join(p.text for p in docx.Document(str(f)).paragraphs)
        except ImportError:
            return "Per leggere i file Word installa 'python-docx'."
    else:
        testo = f.read_text(encoding="utf-8", errors="replace")
    if len(testo) > LIMITE_LETTURA:
        return testo[:LIMITE_LETTURA] + f"\n... [file troncato: {len(testo)} caratteri totali]"
    return testo


@strumento(
    "scrivi_file",
    "Crea o sovrascrive un file di testo con il contenuto indicato (o lo aggiunge in coda).",
    {
        "percorso": {"type": "string", "description": "Percorso del file."},
        "contenuto": {"type": "string", "description": "Testo da scrivere."},
        "aggiungi": {"type": "boolean", "description": "Se true, aggiunge in coda invece di sovrascrivere."},
    },
    ["percorso", "contenuto"],
    pericoloso=True,
)
def scrivi_file(percorso: str, contenuto: str, aggiungi: bool = False) -> str:
    f = _percorso(percorso)
    f.parent.mkdir(parents=True, exist_ok=True)
    with open(f, "a" if aggiungi else "w", encoding="utf-8") as fh:
        fh.write(contenuto)
    return f"Scritti {len(contenuto)} caratteri in {f}"


@strumento(
    "cerca_file",
    "Cerca file per nome (supporta caratteri jolly, es. '*.pdf' o '*fattura*') a partire da una cartella.",
    {
        "schema": {"type": "string", "description": "Nome o pattern da cercare."},
        "cartella": {"type": "string", "description": "Cartella di partenza (predefinita: home)."},
        "limite": {"type": "integer", "description": "Numero massimo di risultati (predefinito 50)."},
    },
    ["schema"],
)
def cerca_file(schema: str, cartella: str = "~", limite: int = 50) -> str:
    radice = _percorso(cartella)
    if not any(c in schema for c in "*?["):
        schema = f"*{schema}*"
    schema = schema.lower()
    trovati: list[str] = []
    saltare = {"node_modules", ".git", "__pycache__", "AppData", "Library", ".cache"}
    for base, cartelle, files in os.walk(radice):
        cartelle[:] = [c for c in cartelle if c not in saltare and not c.startswith(".")]
        for nome in files + cartelle:
            if fnmatch.fnmatch(nome.lower(), schema):
                trovati.append(os.path.join(base, nome))
                if len(trovati) >= limite:
                    return "\n".join(trovati) + "\n(limite raggiunto)"
    return "\n".join(trovati) if trovati else "Nessun file trovato."


@strumento(
    "sposta_o_copia",
    "Sposta, rinomina o copia un file o una cartella.",
    {
        "origine": {"type": "string"},
        "destinazione": {"type": "string"},
        "copia": {"type": "boolean", "description": "true per copiare invece di spostare."},
    },
    ["origine", "destinazione"],
    pericoloso=True,
)
def sposta_o_copia(origine: str, destinazione: str, copia: bool = False) -> str:
    o, d = _percorso(origine), _percorso(destinazione)
    if copia:
        if o.is_dir():
            shutil.copytree(o, d)
        else:
            shutil.copy2(o, d)
        return f"Copiato {o} -> {d}"
    shutil.move(str(o), str(d))
    return f"Spostato {o} -> {d}"


@strumento(
    "elimina",
    "Elimina un file o una cartella (le cartelle vengono eliminate con tutto il contenuto).",
    {"percorso": {"type": "string"}},
    ["percorso"],
    pericoloso=True,
)
def elimina(percorso: str) -> str:
    p = _percorso(percorso)
    if p.is_dir():
        shutil.rmtree(p)
    else:
        p.unlink()
    return f"Eliminato {p}"
