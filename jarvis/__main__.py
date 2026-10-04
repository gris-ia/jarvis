"""Avvio di JARVIS: `python -m jarvis` (testo) oppure `python -m jarvis --voce` (comandi vocali)."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from .cervello import Cervello
from .config import Config
from .strumenti import memoria, sistema
from .voce import Orecchio, Voce

console = Console()

LOGO = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""

AIUTO = """[bold]Comandi:[/bold]
  /voce          attiva/disattiva la voce di JARVIS
  /ascolto       passa ai comandi vocali (di' "Jarvis" seguito dalla richiesta)
  /nuova         inizia una nuova conversazione
  /memoria       mostra cosa JARVIS ricorda di te
  /conferme      attiva/disattiva la richiesta di conferma per le azioni pericolose
  /esci          chiude JARVIS
Qualsiasi altro testo è una richiesta per JARVIS."""

SI = {"si", "sì", "certo", "procedi", "vai", "ok", "okay", "confermo", "affermativo", "esatto", "fallo"}
USCITA = {"esci", "chiudi jarvis", "spegniti", "arrivederci", "addio", "basta così", "/esci"}


def saluto(nome: str) -> str:
    ora = datetime.now().hour
    parte = "Buongiorno" if 5 <= ora < 13 else "Buon pomeriggio" if ora < 18 else "Buonasera"
    return f"{parte}, {nome}. Tutti i sistemi sono operativi. Come posso aiutarla?"


class Jarvis:
    def __init__(self, config: Config, modalita_voce: bool) -> None:
        self.config = config
        self.voce = Voce(config)
        self.orecchio: Orecchio | None = None
        self.modalita_voce = modalita_voce
        self.stato = None
        if modalita_voce:
            self._attiva_ascolto()
        sistema.notifica = self._notifica
        self.cervello = Cervello(
            config,
            conferma=self._conferma,
            su_testo=self._mostra_intermedio,
            su_strumento=self._mostra_strumento,
        )

    # --- Interazione con l'utente -------------------------------------------------

    def _attiva_ascolto(self) -> bool:
        if self.orecchio is None:
            try:
                with console.status("Calibro il microfono..."):
                    self.orecchio = Orecchio(self.config)
            except Exception as e:
                console.print(f"[red]Microfono non disponibile ({e}). Resto in modalità testo.[/red]")
                self.modalita_voce = False
                return False
        self.modalita_voce = True
        return True

    def dici(self, testo: str) -> None:
        console.print(Panel(testo, title="[bold cyan]JARVIS[/bold cyan]", border_style="cyan"))
        self.voce.parla(testo)

    def _notifica(self, testo: str) -> None:
        console.print(f"\n[bold yellow]⏰ {testo}[/bold yellow]")
        self.voce.parla(testo)

    def _mostra_intermedio(self, testo: str) -> None:
        console.print(f"[cyan]JARVIS:[/cyan] [dim]{testo}[/dim]")
        self.voce.parla(testo)

    def _mostra_strumento(self, nome: str, argomenti: dict) -> None:
        dettagli = ", ".join(f"{k}={str(v)[:80]!r}" for k, v in argomenti.items())
        console.print(f"  [dim magenta]⚙ {nome}({dettagli})[/dim magenta]")

    def _conferma(self, descrizione: str) -> bool:
        if self.stato:
            self.stato.stop()
        try:
            console.print(f"[bold yellow]⚠ JARVIS vuole eseguire:[/bold yellow] {descrizione}")
            if self.modalita_voce and self.orecchio:
                self.voce.parla("Questa azione richiede la sua autorizzazione. Procedo?")
                risposta = (self.orecchio.ascolta(timeout=8, limite=5) or "").lower()
                console.print(f"[dim]Risposta: {risposta or '(nessuna)'}[/dim]")
                return any(parola in SI for parola in risposta.replace(",", " ").split())
            return Confirm.ask("Autorizzi?", default=True)
        finally:
            if self.stato:
                self.stato.start()

    # --- Ciclo principale ---------------------------------------------------------

    def esegui_richiesta(self, testo: str) -> None:
        with console.status("[cyan]Elaboro...[/cyan]", spinner="dots") as stato:
            self.stato = stato
            try:
                risposta = self.cervello.chiedi(testo)
            finally:
                self.stato = None
        self.dici(risposta)

    def comando_interno(self, testo: str) -> bool:
        """Gestisce i comandi che iniziano con '/'. Restituisce False per uscire."""
        cmd = testo.lower().strip()
        if cmd in USCITA:
            return False
        if cmd == "/aiuto":
            console.print(AIUTO)
        elif cmd == "/voce":
            self.voce.attiva = not self.voce.attiva
            console.print(f"Voce {'attivata' if self.voce.attiva else 'disattivata'}.")
        elif cmd == "/ascolto":
            if self._attiva_ascolto():
                console.print('[green]Modalità vocale attiva: di\' "Jarvis" e la tua richiesta. '
                              'Premi Ctrl+C per tornare alla tastiera.[/green]')
        elif cmd == "/nuova":
            self.cervello.nuova_conversazione()
            console.print("Nuova conversazione iniziata.")
        elif cmd == "/memoria":
            console.print(memoria.leggi_memoria())
        elif cmd == "/conferme":
            if self.cervello.conferma:
                self.cervello.conferma = None
                console.print("[red]Conferme disattivate: JARVIS eseguirà ogni azione senza chiedere.[/red]")
            else:
                self.cervello.conferma = self._conferma
                console.print("Conferme attivate.")
        else:
            console.print(f"Comando sconosciuto. {AIUTO}")
        return True

    def ciclo_testo(self) -> bool:
        """Restituisce False se l'utente vuole uscire, True se passa alla voce."""
        while not self.modalita_voce:
            try:
                testo = console.input("[bold green]Tu ›[/bold green] ").strip()
            except (EOFError, KeyboardInterrupt):
                return False
            if not testo:
                continue
            if testo.startswith("/") or testo.lower() in USCITA:
                if not self.comando_interno(testo):
                    return False
                continue
            self.esegui_richiesta(testo)
        return True

    def ciclo_voce(self) -> None:
        parola = self.config.parola_attivazione.lower()
        console.print(f'[green]In ascolto... di\' "{parola.capitalize()}" seguito dalla richiesta.[/green]')
        try:
            while self.modalita_voce:
                frase = self.orecchio.ascolta()
                if not frase:
                    continue
                minuscola = frase.lower()
                if parola not in minuscola:
                    continue
                richiesta = minuscola.split(parola, 1)[1].strip(" ,.!?")
                if not richiesta:
                    self.voce.parla(f"Sì, {self.config.nome_utente}?")
                    richiesta = (self.orecchio.ascolta(timeout=8) or "").strip()
                    if not richiesta:
                        continue
                console.print(f"[bold green]Tu (voce) ›[/bold green] {richiesta}")
                if richiesta.lower() in USCITA:
                    raise SystemExit
                self.esegui_richiesta(richiesta)
        except KeyboardInterrupt:
            self.modalita_voce = False
            console.print("\n[yellow]Modalità tastiera.[/yellow]")

    def avvia(self) -> None:
        console.print(f"[bold cyan]{LOGO}[/bold cyan]")
        console.print("[dim]Scrivi /aiuto per l'elenco dei comandi.[/dim]\n")
        self.dici(saluto(self.config.nome_utente))
        try:
            while True:
                if self.modalita_voce:
                    self.ciclo_voce()
                elif not self.ciclo_testo():
                    break
        except SystemExit:
            pass
        self.dici(f"A presto, {self.config.nome_utente}.")


def main() -> None:
    parser = argparse.ArgumentParser(description="JARVIS - assistente personale per il PC")
    parser.add_argument("--voce", action="store_true", help="avvia in modalità comandi vocali")
    parser.add_argument("--muto", action="store_true", help="disattiva la sintesi vocale")
    parser.add_argument("--senza-conferme", action="store_true",
                        help="non chiedere conferma per le azioni pericolose (sconsigliato)")
    parser.add_argument("richiesta", nargs="*", help="esegue una singola richiesta ed esce")
    args = parser.parse_args()

    config = Config()
    if args.muto:
        config.voce_attiva = False
    if args.senza_conferme:
        config.conferma_azioni = False

    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("ANTHROPIC_AUTH_TOKEN"):
        console.print("[yellow]Attenzione: ANTHROPIC_API_KEY non è impostata. "
                      "Copia .env.example in .env e inserisci la tua chiave.[/yellow]")

    jarvis = Jarvis(config, modalita_voce=args.voce or config.ascolto_attivo)
    if args.richiesta:
        jarvis.esegui_richiesta(" ".join(args.richiesta))
        sys.exit(0)
    jarvis.avvia()


if __name__ == "__main__":
    main()
