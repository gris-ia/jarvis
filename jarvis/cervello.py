"""Il "cervello" di JARVIS: dialoga con Claude ed esegue gli strumenti richiesti."""

from __future__ import annotations

import platform
from datetime import date
from typing import Any, Callable

import anthropic

from . import strumenti
from .config import Config
from .strumenti import memoria

PROMPT_SISTEMA = """Sei J.A.R.V.I.S. (Just A Rather Very Intelligent System), l'assistente personale \
ispirato a quello di Tony Stark. Ti rivolgi all'utente chiamandolo "{nome}". Parli sempre in italiano, \
con tono elegante, calmo, leggermente ironico e britannico nello stile, ma sempre rispettoso ed efficiente.

Hai pieno accesso al computer dell'utente tramite gli strumenti a disposizione e puoi svolgere \
qualsiasi compito ti venga chiesto: aprire programmi e siti, gestire file, eseguire comandi e script, \
controllare mouse e tastiera, guardare lo schermo, regolare audio, cercare informazioni sul web e altro.

Come lavori:
- Agisci: quando ti viene chiesto di fare qualcosa, fallo con gli strumenti invece di spiegare come farlo.
- Per compiti con più passaggi, procedi in autonomia fino al completamento e verifica il risultato \
(ad esempio con uno screenshot o rileggendo un file).
- Se uno strumento fallisce, prova un approccio alternativo prima di arrenderti.
- Per interagire con interfacce grafiche: fai uno screenshot, individua l'elemento, poi usa mouse/tasti.
- Se l'utente nega un'azione, non riprovarla in altro modo: chiedi come preferisce procedere.
- Usa 'ricorda' per salvare informazioni durature sull'utente (preferenze, percorsi, abitudini) \
quando emergono nella conversazione.
- Prima di azioni irreversibili (eliminare dati, spegnere il PC) assicurati che sia ciò che l'utente vuole.

Stile delle risposte: le tue risposte vengono lette ad alta voce. Sii breve (una o due frasi quando \
possibile), non usare markdown, elenchi puntati, emoji o blocchi di codice nel testo finale, a meno che \
l'utente non chieda esplicitamente un testo lungo. Riassumi i risultati invece di ripeterli per intero.

Contesto:
- Sistema operativo: {sistema} {versione}
- Data di avvio della sessione: {data}
- Cartella home: {home}

Ciò che ricordi dell'utente:
{memoria}
"""

Conferma = Callable[[str], bool]


class Cervello:
    def __init__(
        self,
        config: Config,
        conferma: Conferma | None = None,
        su_testo: Callable[[str], None] | None = None,
        su_strumento: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        strumenti.carica_tutti()
        self.config = config
        self.client = anthropic.Anthropic()
        self.conferma = conferma if config.conferma_azioni else None
        self.su_testo = su_testo or (lambda t: None)
        self.su_strumento = su_strumento or (lambda n, a: None)
        self.messaggi: list[dict[str, Any]] = []
        self.sistema = self._prompt_sistema()
        self.tools: list[dict[str, Any]] = strumenti.schemi()
        if config.ricerca_web:
            self.tools.append({"type": "web_search_20260209", "name": "web_search", "max_uses": 5})

    def _prompt_sistema(self) -> str:
        from pathlib import Path

        fatti = memoria.carica()
        testo_memoria = "\n".join(f"- {f['fatto']}" for f in fatti) or "(ancora nulla)"
        return PROMPT_SISTEMA.format(
            nome=self.config.nome_utente,
            sistema=platform.system(),
            versione=platform.release(),
            data=date.today().strftime("%d/%m/%Y"),
            home=Path.home(),
            memoria=testo_memoria,
        )

    def nuova_conversazione(self) -> None:
        self.messaggi = []
        self.sistema = self._prompt_sistema()

    def _richiesta(self):
        return self.client.beta.messages.create(
            model=self.config.modello,
            max_tokens=self.config.max_token,
            system=self.sistema,
            tools=self.tools,
            messages=self.messaggi,
            thinking={"type": "adaptive"},
            output_config={"effort": self.config.sforzo},
            cache_control={"type": "ephemeral"},
            # Se il modello rifiuta una richiesta, l'API la ripete su un modello di riserva
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
        )

    @staticmethod
    def _messaggio_errore(e: anthropic.APIError) -> str:
        if isinstance(e, anthropic.AuthenticationError):
            return "Non riesco ad autenticarmi con i miei server. Controlli la chiave ANTHROPIC_API_KEY."
        if isinstance(e, anthropic.RateLimitError):
            return "Ho raggiunto il limite di richieste. Riprovi tra qualche istante."
        if isinstance(e, anthropic.APIStatusError):
            return f"I miei server hanno risposto con un errore ({e.status_code}): {e.message}"
        if isinstance(e, anthropic.APIConnectionError):
            return "Non riesco a connettermi a internet. Verifichi la connessione."
        return f"Errore imprevisto: {e}"

    def chiedi(self, richiesta: str) -> str:
        """Invia una richiesta e lavora (anche in più passi) finché il compito è completato.

        Restituisce il testo finale da mostrare/pronunciare.
        """
        inizio = len(self.messaggi)
        if self.messaggi and self.messaggi[-1]["role"] == "user":
            # Il compito precedente si è interrotto dopo dei risultati di strumenti: accodiamo
            self.messaggi[-1]["content"].append({"type": "text", "text": richiesta})
            inizio = None
        else:
            self.messaggi.append({"role": "user", "content": richiesta})
        ultimo_testo = ""

        for _ in range(self.config.max_passi):
            try:
                risposta = self._richiesta()
            except anthropic.APIError as e:
                # Annulla il turno in corso per lasciare la cronologia valida
                if inizio is not None:
                    del self.messaggi[inizio:]
                return self._messaggio_errore(e)

            self.messaggi.append({"role": "assistant", "content": risposta.content})
            testi = [b.text for b in risposta.content if b.type == "text" and b.text.strip()]
            if testi:
                ultimo_testo = "\n".join(testi)

            if risposta.stop_reason == "refusal":
                return ultimo_testo or "Temo di non poter eseguire questa richiesta."

            if risposta.stop_reason == "pause_turn":
                # La ricerca web lato server ha bisogno di continuare
                continue

            chiamate = [b for b in risposta.content if b.type == "tool_use"]
            if risposta.stop_reason != "tool_use" or not chiamate:
                return ultimo_testo or "Fatto."

            # Testo intermedio (es. "Apro il browser...") da pronunciare mentre lavora
            if testi:
                self.su_testo(ultimo_testo)

            risultati = []
            for c in chiamate:
                argomenti = c.input if isinstance(c.input, dict) else {}
                self.su_strumento(c.name, argomenti)
                esito, errore = strumenti.esegui(c.name, argomenti, self.conferma)
                contenuto = esito if isinstance(esito, list) else str(esito)
                risultati.append({
                    "type": "tool_result",
                    "tool_use_id": c.id,
                    "content": contenuto,
                    "is_error": errore,
                })
            # Tutti i risultati in un unico messaggio utente
            self.messaggi.append({"role": "user", "content": risultati})

        return "Ho raggiunto il numero massimo di passaggi per questo compito. Vuole che continui?"
