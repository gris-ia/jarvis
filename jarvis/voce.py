"""Voce di JARVIS: sintesi vocale (TTS) e riconoscimento vocale (STT) in italiano."""

from __future__ import annotations

import asyncio
import os
import re
import tempfile
import threading

from .config import Config


def _pulisci(testo: str) -> str:
    """Rimuove markdown e simboli che suonerebbero male letti ad alta voce."""
    testo = re.sub(r"```.*?```", " (codice omesso) ", testo, flags=re.S)
    testo = re.sub(r"https?://\S+", "il link", testo)
    testo = re.sub(r"[*_#`>|]", "", testo)
    return re.sub(r"\s+", " ", testo).strip()


class Voce:
    """Parla usando Microsoft Edge TTS (voce naturale, richiede internet) o pyttsx3 (offline)."""

    def __init__(self, config: Config) -> None:
        self.config = config
        self.attiva = config.voce_attiva
        self._blocco = threading.Lock()
        self._motore = None
        self._usa_edge = False
        if not self.attiva:
            return
        try:
            import edge_tts  # noqa: F401
            import pygame

            pygame.mixer.init()
            self._usa_edge = True
        except Exception:
            self._inizializza_pyttsx3()

    def _inizializza_pyttsx3(self) -> None:
        try:
            import pyttsx3

            self._motore = pyttsx3.init()
            self._motore.setProperty("rate", 175)
            for v in self._motore.getProperty("voices"):
                identita = f"{v.id} {v.name} {getattr(v, 'languages', '')}".lower()
                if "ital" in identita or "it_it" in identita or "it-it" in identita:
                    self._motore.setProperty("voice", v.id)
                    break
        except Exception as e:
            print(f"[voce] Sintesi vocale non disponibile: {e}")
            self.attiva = False

    def parla(self, testo: str) -> None:
        if not self.attiva or not testo:
            return
        testo = _pulisci(testo)
        with self._blocco:
            if self._usa_edge:
                try:
                    self._parla_edge(testo)
                    return
                except Exception:
                    # Senza internet: ripiega sulla voce offline
                    self._usa_edge = False
                    self._inizializza_pyttsx3()
            if self._motore:
                self._motore.say(testo)
                self._motore.runAndWait()

    def _parla_edge(self, testo: str) -> None:
        import edge_tts
        import pygame

        percorso = os.path.join(tempfile.gettempdir(), "jarvis_voce.mp3")
        asyncio.run(edge_tts.Communicate(testo, self.config.voce_edge, rate="+8%").save(percorso))
        pygame.mixer.music.load(percorso)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            pygame.time.wait(50)
        pygame.mixer.music.unload()


class Orecchio:
    """Ascolta il microfono e trascrive in italiano con il servizio di Google Speech."""

    def __init__(self, config: Config) -> None:
        import speech_recognition as sr

        self.sr = sr
        self.config = config
        self.riconoscitore = sr.Recognizer()
        self.riconoscitore.pause_threshold = 0.9
        self.riconoscitore.dynamic_energy_threshold = True
        self.microfono = sr.Microphone()
        with self.microfono as sorgente:
            self.riconoscitore.adjust_for_ambient_noise(sorgente, duration=1)

    def ascolta(self, timeout: float | None = None, limite: float = 20) -> str | None:
        """Ascolta una frase e la restituisce come testo (None se non ha capito)."""
        with self.microfono as sorgente:
            try:
                audio = self.riconoscitore.listen(sorgente, timeout=timeout, phrase_time_limit=limite)
            except self.sr.WaitTimeoutError:
                return None
        try:
            return self.riconoscitore.recognize_google(audio, language=self.config.lingua)
        except self.sr.UnknownValueError:
            return None
        except self.sr.RequestError as e:
            print(f"[ascolto] Servizio di riconoscimento non raggiungibile: {e}")
            return None
