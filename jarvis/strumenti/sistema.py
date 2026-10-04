"""Strumenti di sistema: comandi, applicazioni, processi, informazioni, timer."""

from __future__ import annotations

import datetime as dt
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import webbrowser
from typing import Callable

from . import strumento

SISTEMA = platform.system()  # "Windows", "Darwin" o "Linux"
LIMITE_OUTPUT = 12000

# Funzione chiamata quando scatta un promemoria (impostata dall'interfaccia).
notifica: Callable[[str], None] = lambda testo: print(f"\n⏰ {testo}")


def _tronca(testo: str) -> str:
    if len(testo) <= LIMITE_OUTPUT:
        return testo
    meta = LIMITE_OUTPUT // 2
    return f"{testo[:meta]}\n... [output troncato, {len(testo) - LIMITE_OUTPUT} caratteri omessi] ...\n{testo[-meta:]}"


@strumento(
    "esegui_comando",
    "Esegue un comando nella shell del PC (PowerShell su Windows, bash/zsh su macOS e Linux) "
    "e restituisce output ed exit code. Usalo per qualsiasi operazione che non ha uno strumento dedicato: "
    "installare programmi, gestire file in blocco, git, rete, impostazioni di sistema, ecc.",
    {
        "comando": {"type": "string", "description": "Il comando da eseguire."},
        "cartella": {"type": "string", "description": "Cartella di lavoro (facoltativa)."},
        "timeout": {"type": "integer", "description": "Secondi massimi di attesa (predefinito 120)."},
    },
    ["comando"],
    pericoloso=True,
)
def esegui_comando(comando: str, cartella: str | None = None, timeout: int = 120) -> str:
    if SISTEMA == "Windows":
        argomenti = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", comando]
        shell = False
    else:
        argomenti = comando
        shell = True
    cwd = os.path.expanduser(cartella) if cartella else None
    try:
        r = subprocess.run(
            argomenti, shell=shell, cwd=cwd, capture_output=True, text=True,
            timeout=timeout, encoding="utf-8", errors="replace",
        )
    except subprocess.TimeoutExpired:
        return f"Timeout: il comando ha superato {timeout} secondi."
    uscita = f"exit code: {r.returncode}\n"
    if r.stdout:
        uscita += f"--- stdout ---\n{r.stdout}"
    if r.stderr:
        uscita += f"\n--- stderr ---\n{r.stderr}"
    return _tronca(uscita)


@strumento(
    "esegui_python",
    "Esegue codice Python sul PC in un processo separato e restituisce l'output. "
    "Utile per calcoli, elaborazione di dati, automazioni complesse e librerie Python installate.",
    {"codice": {"type": "string", "description": "Codice Python completo da eseguire."}},
    ["codice"],
    pericoloso=True,
)
def esegui_python(codice: str) -> str:
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(codice)
        percorso = f.name
    try:
        r = subprocess.run(
            [sys.executable, percorso], capture_output=True, text=True,
            timeout=300, encoding="utf-8", errors="replace",
        )
        return _tronca(f"exit code: {r.returncode}\n{r.stdout}\n{r.stderr}".strip())
    except subprocess.TimeoutExpired:
        return "Timeout: lo script ha superato 300 secondi."
    finally:
        os.unlink(percorso)


@strumento(
    "apri",
    "Apre un'applicazione, un file, una cartella o un URL con il programma predefinito del sistema. "
    "Esempi: 'notepad', 'calc', 'spotify', 'C:/Users/me/Documenti', 'https://youtube.com'.",
    {"destinazione": {"type": "string", "description": "Nome dell'app, percorso o URL."}},
    ["destinazione"],
)
def apri(destinazione: str) -> str:
    d = os.path.expanduser(destinazione.strip())
    if d.startswith(("http://", "https://", "www.")):
        webbrowser.open(d if d.startswith("http") else f"https://{d}")
        return f"Aperto nel browser: {d}"
    if SISTEMA == "Windows":
        # "start" gestisce app registrate, file, cartelle e protocolli (es. spotify:, ms-settings:)
        subprocess.Popen(["cmd", "/c", "start", "", d], shell=False)
    elif SISTEMA == "Darwin":
        if os.path.exists(d):
            subprocess.Popen(["open", d])
        else:
            subprocess.Popen(["open", "-a", d])
    else:
        if os.path.exists(d) or ":" in d:
            subprocess.Popen(["xdg-open", d])
        elif shutil.which(d):
            subprocess.Popen([d], start_new_session=True)
        else:
            subprocess.Popen(["gtk-launch", d])
    return f"Avviato: {d}"


@strumento(
    "cerca_sul_web_browser",
    "Apre il browser con una ricerca Google o un video su YouTube per mostrare i risultati all'utente.",
    {
        "testo": {"type": "string", "description": "Cosa cercare."},
        "sito": {"type": "string", "enum": ["google", "youtube"], "description": "Dove cercare."},
    },
    ["testo"],
)
def cerca_sul_web_browser(testo: str, sito: str = "google") -> str:
    from urllib.parse import quote_plus

    url = (
        f"https://www.youtube.com/results?search_query={quote_plus(testo)}"
        if sito == "youtube"
        else f"https://www.google.com/search?q={quote_plus(testo)}"
    )
    webbrowser.open(url)
    return f"Aperta la ricerca: {url}"


@strumento(
    "info_sistema",
    "Restituisce lo stato del PC: sistema operativo, CPU, RAM, dischi, batteria, rete e uptime.",
)
def info_sistema() -> str:
    import psutil

    righe = [
        f"Sistema: {platform.system()} {platform.release()} ({platform.machine()})",
        f"Nome PC: {platform.node()}  Utente: {os.getenv('USERNAME') or os.getenv('USER')}",
        f"CPU: {psutil.cpu_count()} core, utilizzo {psutil.cpu_percent(interval=0.5)}%",
    ]
    ram = psutil.virtual_memory()
    righe.append(f"RAM: {ram.used / 2**30:.1f}/{ram.total / 2**30:.1f} GB ({ram.percent}%)")
    for p in psutil.disk_partitions(all=False):
        try:
            u = psutil.disk_usage(p.mountpoint)
            righe.append(f"Disco {p.mountpoint}: {u.free / 2**30:.0f} GB liberi su {u.total / 2**30:.0f} GB")
        except (PermissionError, OSError):
            continue
    batteria = psutil.sensors_battery() if hasattr(psutil, "sensors_battery") else None
    if batteria:
        stato = "in carica" if batteria.power_plugged else "a batteria"
        righe.append(f"Batteria: {batteria.percent:.0f}% ({stato})")
    avvio = dt.datetime.fromtimestamp(psutil.boot_time())
    righe.append(f"Acceso dal: {avvio:%d/%m/%Y %H:%M}")
    return "\n".join(righe)


@strumento(
    "elenca_processi",
    "Elenca i processi in esecuzione, ordinati per uso di memoria. Può filtrare per nome.",
    {
        "filtro": {"type": "string", "description": "Parte del nome del processo (facoltativo)."},
        "limite": {"type": "integer", "description": "Numero massimo di risultati (predefinito 25)."},
    },
)
def elenca_processi(filtro: str | None = None, limite: int = 25) -> str:
    import psutil

    processi = []
    for p in psutil.process_iter(["pid", "name", "memory_info"]):
        nome = p.info["name"] or ""
        if filtro and filtro.lower() not in nome.lower():
            continue
        mem = p.info["memory_info"].rss / 2**20 if p.info["memory_info"] else 0
        processi.append((mem, p.info["pid"], nome))
    processi.sort(reverse=True)
    if not processi:
        return "Nessun processo trovato."
    return "\n".join(f"PID {pid:>7}  {mem:8.0f} MB  {nome}" for mem, pid, nome in processi[:limite])


@strumento(
    "termina_processo",
    "Chiude un programma dato il nome del processo (es. 'chrome.exe', 'spotify') o il PID.",
    {
        "nome": {"type": "string", "description": "Nome del processo."},
        "pid": {"type": "integer", "description": "PID del processo."},
    },
    pericoloso=True,
)
def termina_processo(nome: str | None = None, pid: int | None = None) -> str:
    import psutil

    terminati = []
    for p in psutil.process_iter(["pid", "name"]):
        if (pid is not None and p.info["pid"] == pid) or (
            nome and (p.info["name"] or "").lower().startswith(nome.lower().removesuffix(".exe"))
        ):
            try:
                p.terminate()
                terminati.append(f"{p.info['name']} ({p.info['pid']})")
            except psutil.Error as e:
                terminati.append(f"{p.info['name']}: impossibile ({e})")
    return "Terminati: " + ", ".join(terminati) if terminati else "Nessun processo corrispondente."


@strumento("data_ora", "Restituisce data, ora e giorno della settimana correnti.")
def data_ora() -> str:
    giorni = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    ora = dt.datetime.now()
    return f"{giorni[ora.weekday()]} {ora:%d/%m/%Y}, ore {ora:%H:%M:%S}"


@strumento(
    "imposta_promemoria",
    "Imposta un timer o promemoria: dopo il numero di minuti indicato JARVIS avviserà l'utente a voce.",
    {
        "minuti": {"type": "number", "description": "Tra quanti minuti avvisare."},
        "messaggio": {"type": "string", "description": "Cosa ricordare all'utente."},
    },
    ["minuti", "messaggio"],
)
def imposta_promemoria(minuti: float, messaggio: str) -> str:
    t = threading.Timer(minuti * 60, lambda: notifica(f"Promemoria: {messaggio}"))
    t.daemon = True
    t.start()
    scadenza = dt.datetime.now() + dt.timedelta(minutes=minuti)
    return f"Promemoria impostato per le {scadenza:%H:%M}: {messaggio}"


@strumento(
    "alimentazione",
    "Spegne, riavvia, sospende o blocca il PC.",
    {"azione": {"type": "string", "enum": ["spegni", "riavvia", "sospendi", "blocca"]}},
    ["azione"],
    pericoloso=True,
)
def alimentazione(azione: str) -> str:
    comandi = {
        "Windows": {
            "spegni": "shutdown /s /t 5",
            "riavvia": "shutdown /r /t 5",
            "sospendi": "rundll32.exe powrprof.dll,SetSuspendState 0,1,0",
            "blocca": "rundll32.exe user32.dll,LockWorkStation",
        },
        "Darwin": {
            "spegni": "osascript -e 'tell app \"System Events\" to shut down'",
            "riavvia": "osascript -e 'tell app \"System Events\" to restart'",
            "sospendi": "pmset sleepnow",
            "blocca": "pmset displaysleepnow",
        },
        "Linux": {
            "spegni": "systemctl poweroff",
            "riavvia": "systemctl reboot",
            "sospendi": "systemctl suspend",
            "blocca": "loginctl lock-session",
        },
    }
    comando = comandi.get(SISTEMA, comandi["Linux"])[azione]
    subprocess.Popen(comando, shell=True)
    return f"Azione '{azione}' avviata."
