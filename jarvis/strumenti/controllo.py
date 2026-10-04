"""Controllo diretto di schermo, mouse, tastiera, audio e appunti."""

from __future__ import annotations

import base64
import io
import platform
import subprocess
from typing import Any

from . import strumento

LARGHEZZA_MAX = 1366
# Rapporto tra coordinate reali dello schermo e quelle dell'ultimo screenshot inviato a Claude.
_scala = 1.0


def _pyautogui():
    import pyautogui

    pyautogui.FAILSAFE = True  # spostare il mouse nell'angolo in alto a sinistra interrompe tutto
    pyautogui.PAUSE = 0.05
    return pyautogui


def _reale(x: float, y: float) -> tuple[int, int]:
    return int(x * _scala), int(y * _scala)


@strumento(
    "screenshot",
    "Cattura lo schermo e te lo mostra come immagine, così puoi vedere cosa c'è sul PC. "
    "Le coordinate per click e movimenti del mouse si riferiscono a questa immagine.",
)
def screenshot() -> list[dict[str, Any]]:
    global _scala
    from PIL import ImageGrab

    img = ImageGrab.grab(all_screens=platform.system() == "Windows")
    _scala = max(1.0, img.width / LARGHEZZA_MAX)
    if _scala > 1.0:
        img = img.resize((int(img.width / _scala), int(img.height / _scala)))
    buffer = io.BytesIO()
    img.convert("RGB").save(buffer, format="JPEG", quality=80)
    dati = base64.standard_b64encode(buffer.getvalue()).decode()
    return [
        {"type": "text", "text": f"Screenshot {img.width}x{img.height}."},
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": dati}},
    ]


@strumento(
    "mouse",
    "Muove il mouse e/o clicca. Coordinate riferite all'ultimo screenshot.",
    {
        "azione": {"type": "string", "enum": ["click", "doppio_click", "click_destro", "muovi", "scorri"]},
        "x": {"type": "number"},
        "y": {"type": "number"},
        "quantita": {"type": "integer", "description": "Per 'scorri': positivo su, negativo giù."},
    },
    ["azione"],
)
def mouse(azione: str, x: float | None = None, y: float | None = None, quantita: int = -5) -> str:
    pg = _pyautogui()
    posizione = _reale(x, y) if x is not None and y is not None else None
    if azione == "muovi" and posizione:
        pg.moveTo(*posizione, duration=0.2)
    elif azione == "click":
        pg.click(*(posizione or ()))
    elif azione == "doppio_click":
        pg.doubleClick(*(posizione or ()))
    elif azione == "click_destro":
        pg.rightClick(*(posizione or ()))
    elif azione == "scorri":
        if posizione:
            pg.moveTo(*posizione)
        pg.scroll(quantita * 100)
    return f"Mouse: {azione} eseguito."


@strumento(
    "digita",
    "Scrive del testo nella finestra attiva, come se l'utente lo digitasse sulla tastiera.",
    {
        "testo": {"type": "string"},
        "invio": {"type": "boolean", "description": "Premi Invio alla fine."},
    },
    ["testo"],
)
def digita(testo: str, invio: bool = False) -> str:
    pg = _pyautogui()
    if testo.isascii():
        pg.write(testo, interval=0.01)
    else:
        # pyautogui non gestisce lettere accentate: passiamo dagli appunti
        import pyperclip

        precedente = pyperclip.paste()
        pyperclip.copy(testo)
        pg.hotkey("command" if platform.system() == "Darwin" else "ctrl", "v")
        pyperclip.copy(precedente)
    if invio:
        pg.press("enter")
    return "Testo digitato."


@strumento(
    "tasti",
    "Preme un tasto o una combinazione di tasti. Esempi: ['enter'], ['ctrl','c'], ['alt','tab'], "
    "['win','d'], ['command','space'], ['f5'].",
    {"tasti": {"type": "array", "items": {"type": "string"}}},
    ["tasti"],
)
def tasti(tasti: list[str]) -> str:
    pg = _pyautogui()
    if len(tasti) == 1:
        pg.press(tasti[0])
    else:
        pg.hotkey(*tasti)
    return f"Premuto: {'+'.join(tasti)}"


@strumento(
    "volume",
    "Regola il volume del sistema.",
    {
        "azione": {"type": "string", "enum": ["alza", "abbassa", "muto", "imposta"]},
        "livello": {"type": "integer", "description": "Per 'imposta': percentuale 0-100."},
    },
    ["azione"],
)
def volume(azione: str, livello: int | None = None) -> str:
    sistema = platform.system()
    if azione == "imposta" and livello is not None:
        livello = max(0, min(100, livello))
        if sistema == "Darwin":
            subprocess.run(["osascript", "-e", f"set volume output volume {livello}"])
            return f"Volume impostato al {livello}%."
        if sistema == "Linux":
            subprocess.run(["amixer", "-D", "pulse", "sset", "Master", f"{livello}%"], capture_output=True)
            return f"Volume impostato al {livello}%."
        # Windows: azzera e poi alza a passi di 2%
        pg = _pyautogui()
        pg.press("volumedown", presses=50)
        pg.press("volumeup", presses=livello // 2)
        return f"Volume impostato a circa il {livello}%."
    tasto = {"alza": "volumeup", "abbassa": "volumedown", "muto": "volumemute"}[azione]
    _pyautogui().press(tasto, presses=1 if azione == "muto" else 5)
    return f"Volume: {azione}."


@strumento(
    "multimedia",
    "Controlla la riproduzione multimediale (Spotify, YouTube, ecc.).",
    {"azione": {"type": "string", "enum": ["play_pausa", "successivo", "precedente", "stop"]}},
    ["azione"],
)
def multimedia(azione: str) -> str:
    tasto = {"play_pausa": "playpause", "successivo": "nexttrack", "precedente": "prevtrack", "stop": "stop"}[azione]
    _pyautogui().press(tasto)
    return f"Multimedia: {azione}."


@strumento(
    "appunti",
    "Legge o scrive il contenuto degli appunti (copia/incolla).",
    {
        "azione": {"type": "string", "enum": ["leggi", "scrivi"]},
        "testo": {"type": "string", "description": "Testo da copiare (per 'scrivi')."},
    },
    ["azione"],
)
def appunti(azione: str, testo: str = "") -> str:
    import pyperclip

    if azione == "leggi":
        return pyperclip.paste() or "(appunti vuoti)"
    pyperclip.copy(testo)
    return "Copiato negli appunti."


@strumento(
    "finestre",
    "Elenca le finestre aperte oppure porta in primo piano quella il cui titolo contiene il testo indicato.",
    {
        "azione": {"type": "string", "enum": ["elenca", "attiva", "minimizza", "massimizza", "chiudi"]},
        "titolo": {"type": "string"},
    },
    ["azione"],
)
def finestre(azione: str, titolo: str = "") -> str:
    try:
        import pygetwindow as gw
    except (ImportError, NotImplementedError):
        return "Gestione finestre non disponibile su questo sistema: usa 'tasti' (es. alt+tab) o 'esegui_comando'."
    if azione == "elenca":
        titoli = [t for t in gw.getAllTitles() if t.strip()]
        return "\n".join(titoli) or "Nessuna finestra."
    trovate = gw.getWindowsWithTitle(titolo)
    if not trovate:
        return f"Nessuna finestra con '{titolo}' nel titolo."
    f = trovate[0]
    {"attiva": f.activate, "minimizza": f.minimize, "massimizza": f.maximize, "chiudi": f.close}[azione]()
    return f"Finestra '{f.title}': {azione}."
