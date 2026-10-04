"""Configurazione di JARVIS, letta da variabili d'ambiente o dal file .env."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # python-dotenv è opzionale
    pass


def _bool(nome: str, predefinito: bool) -> bool:
    valore = os.getenv(nome)
    if valore is None:
        return predefinito
    return valore.strip().lower() in {"1", "true", "si", "sì", "yes", "on"}


CARTELLA_DATI = Path(os.getenv("JARVIS_DATI", Path.home() / ".jarvis"))


@dataclass
class Config:
    # Modello e ragionamento
    modello: str = field(default_factory=lambda: os.getenv("JARVIS_MODELLO", "claude-opus-5-5"))
    sforzo: str = field(default_factory=lambda: os.getenv("JARVIS_SFORZO", "medium"))
    max_token: int = field(default_factory=lambda: int(os.getenv("JARVIS_MAX_TOKEN", "16000")))
    max_passi: int = field(default_factory=lambda: int(os.getenv("JARVIS_MAX_PASSI", "40")))

    # Identità
    nome_utente: str = field(default_factory=lambda: os.getenv("JARVIS_NOME_UTENTE", "signore"))

    # Voce
    voce_attiva: bool = field(default_factory=lambda: _bool("JARVIS_VOCE", True))
    ascolto_attivo: bool = field(default_factory=lambda: _bool("JARVIS_ASCOLTO", False))
    parola_attivazione: str = field(default_factory=lambda: os.getenv("JARVIS_PAROLA_ATTIVAZIONE", "jarvis"))
    voce_edge: str = field(default_factory=lambda: os.getenv("JARVIS_VOCE_EDGE", "it-IT-DiegoNeural"))
    lingua: str = field(default_factory=lambda: os.getenv("JARVIS_LINGUA", "it-IT"))

    # Sicurezza: chiede conferma prima delle azioni potenzialmente distruttive
    conferma_azioni: bool = field(default_factory=lambda: _bool("JARVIS_CONFERMA", True))

    # Ricerca web tramite il server tool di Anthropic
    ricerca_web: bool = field(default_factory=lambda: _bool("JARVIS_RICERCA_WEB", True))

    cartella_dati: Path = CARTELLA_DATI

    def __post_init__(self) -> None:
        self.cartella_dati.mkdir(parents=True, exist_ok=True)
