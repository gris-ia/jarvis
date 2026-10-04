"""Memoria a lungo termine: fatti sull'utente che JARVIS ricorda tra una sessione e l'altra."""

from __future__ import annotations

import json
from datetime import date

from ..config import CARTELLA_DATI
from . import strumento

FILE_MEMORIA = CARTELLA_DATI / "memoria.json"


def carica() -> list[dict[str, str]]:
    try:
        return json.loads(FILE_MEMORIA.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _salva(fatti: list[dict[str, str]]) -> None:
    FILE_MEMORIA.parent.mkdir(parents=True, exist_ok=True)
    FILE_MEMORIA.write_text(json.dumps(fatti, ensure_ascii=False, indent=2), encoding="utf-8")


@strumento(
    "ricorda",
    "Salva in memoria permanente un'informazione utile sull'utente o sulle sue preferenze "
    "(es. 'Il progetto principale è in D:/Lavoro', 'Preferisce Spotify a YouTube per la musica').",
    {"fatto": {"type": "string", "description": "L'informazione da ricordare."}},
    ["fatto"],
)
def ricorda(fatto: str) -> str:
    fatti = carica()
    fatti.append({"fatto": fatto, "data": date.today().isoformat()})
    _salva(fatti)
    return f"Memorizzato (#{len(fatti)})."


@strumento(
    "dimentica",
    "Rimuove dalla memoria permanente i fatti che contengono il testo indicato.",
    {"testo": {"type": "string"}},
    ["testo"],
)
def dimentica(testo: str) -> str:
    fatti = carica()
    rimasti = [f for f in fatti if testo.lower() not in f["fatto"].lower()]
    _salva(rimasti)
    return f"Rimossi {len(fatti) - len(rimasti)} fatti."


@strumento("leggi_memoria", "Restituisce tutti i fatti salvati nella memoria permanente.")
def leggi_memoria() -> str:
    fatti = carica()
    if not fatti:
        return "La memoria è vuota."
    return "\n".join(f"- {f['fatto']} ({f['data']})" for f in fatti)
