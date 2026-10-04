"""Registro degli strumenti che JARVIS può usare sul PC.

Ogni strumento è una funzione Python registrata con il decoratore `@strumento`,
che produce automaticamente la definizione JSON Schema per l'API di Claude.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Strumento:
    nome: str
    descrizione: str
    parametri: dict[str, dict[str, Any]]
    obbligatori: list[str]
    funzione: Callable[..., Any]
    pericoloso: bool = False

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.nome,
            "description": self.descrizione,
            "input_schema": {
                "type": "object",
                "properties": self.parametri,
                "required": self.obbligatori,
            },
        }


REGISTRO: dict[str, Strumento] = {}


def strumento(
    nome: str,
    descrizione: str,
    parametri: dict[str, dict[str, Any]] | None = None,
    obbligatori: list[str] | None = None,
    pericoloso: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Registra una funzione come strumento utilizzabile da JARVIS."""

    def decoratore(funzione: Callable[..., Any]) -> Callable[..., Any]:
        REGISTRO[nome] = Strumento(
            nome=nome,
            descrizione=descrizione,
            parametri=parametri or {},
            obbligatori=obbligatori or [],
            funzione=funzione,
            pericoloso=pericoloso,
        )
        return funzione

    return decoratore


class AzioneRifiutata(Exception):
    """L'utente non ha autorizzato un'azione pericolosa."""


def esegui(nome: str, argomenti: dict[str, Any], conferma: Callable[[str], bool] | None = None) -> tuple[Any, bool]:
    """Esegue uno strumento. Restituisce (risultato, è_errore).

    `conferma` viene chiamata prima degli strumenti marcati come pericolosi;
    se restituisce False l'azione viene annullata.
    """
    s = REGISTRO.get(nome)
    if s is None:
        return f"Errore: strumento sconosciuto '{nome}'.", True

    mancanti = [p for p in s.obbligatori if p not in argomenti]
    if mancanti:
        return f"Errore: parametri mancanti: {', '.join(mancanti)}.", True

    if s.pericoloso and conferma is not None:
        dettagli = ", ".join(f"{k}={v!r}" for k, v in argomenti.items())
        if not conferma(f"{nome}({dettagli})"):
            return "L'utente ha negato l'autorizzazione per questa azione.", True

    try:
        return s.funzione(**argomenti), False
    except Exception as e:  # restituiamo l'errore a Claude perché possa correggersi
        return f"Errore durante '{nome}': {e}\n{traceback.format_exc(limit=2)}", True


def schemi() -> list[dict[str, Any]]:
    return [s.schema() for s in REGISTRO.values()]


def carica_tutti() -> None:
    """Importa i moduli che registrano gli strumenti."""
    from . import file, memoria, sistema, controllo  # noqa: F401
