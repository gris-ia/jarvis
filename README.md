# J.A.R.V.I.S. — il tuo assistente personale per il PC

> *"Buonasera, signore. Tutti i sistemi sono operativi."*

JARVIS è un assistente in **italiano**, ispirato a quello di Iron Man, che **esegue davvero i compiti sul tuo computer**:
lo comandi a voce o per iscritto e lui apre programmi, gestisce file, esegue comandi, guarda lo schermo,
usa mouse e tastiera, cerca sul web e ricorda le tue preferenze.

Il "cervello" è **Claude** (Anthropic), che ragiona sulla richiesta e decide quali strumenti usare, anche in più passaggi,
finché il compito non è completato.

## Cosa sa fare

| Area | Esempi di richieste |
|---|---|
| **Applicazioni e web** | "Apri Spotify", "Apri YouTube e cerca musica lo-fi", "Apri la calcolatrice" |
| **File** | "Trova tutti i PDF nella cartella Download", "Crea un file note.txt sul desktop con la lista della spesa", "Riassumi il documento relazione.docx" |
| **Sistema** | "Come sta il PC?", "Quanta RAM sta usando Chrome?", "Chiudi Discord", "Blocca il computer" |
| **Comandi e script** | "Installa VLC con winget", "Rinomina tutte le foto della cartella Vacanze con la data", "Fai un backup della cartella Documenti" |
| **Schermo, mouse e tastiera** | "Cosa c'è sullo schermo?", "Clicca su Invia", "Scrivi una mail di ringraziamento nella finestra aperta" |
| **Audio e multimedia** | "Alza il volume", "Volume al 30%", "Metti in pausa", "Canzone successiva" |
| **Informazioni** | "Che tempo fa a Roma?", "Ultime notizie sulla Formula 1" (ricerca web integrata) |
| **Promemoria** | "Ricordami tra 20 minuti di togliere la pizza dal forno" |
| **Memoria** | "Ricorda che i miei progetti sono in D:\Lavoro" — lo ricorderà anche nelle sessioni successive |

## Installazione

Serve **Python 3.10 o superiore** ([python.org](https://www.python.org/downloads/) — su Windows spunta *"Add Python to PATH"*)
e una **chiave API Anthropic** ([console.anthropic.com](https://console.anthropic.com/settings/keys)).

### Windows
1. Scarica questa cartella.
2. Fai doppio clic su **`installa_windows.bat`**.
3. Apri il file **`.env`** con il Blocco note e incolla la chiave in `ANTHROPIC_API_KEY=`.
4. Avvia con **`avvia_jarvis.bat`**.

### macOS / Linux
```bash
./installa.sh
nano .env            # inserisci ANTHROPIC_API_KEY
./avvia_jarvis.sh
```
Su macOS concedi al Terminale i permessi di **Accessibilità**, **Registrazione schermo** e **Microfono**
(Impostazioni di Sistema → Privacy e sicurezza).

> Se `pyaudio` non si installa su Windows: `pip install pipwin && pipwin install pyaudio`.
> Puoi comunque usare JARVIS in modalità testo.

## Utilizzo

```bash
python -m jarvis                 # modalità testo (con risposte vocali)
python -m jarvis --voce          # comandi vocali: di' "Jarvis, apri Chrome"
python -m jarvis --muto          # senza voce
python -m jarvis "che ore sono"  # singola richiesta ed esci
```

In modalità vocale pronuncia **"Jarvis"** seguito dalla richiesta, oppure solo "Jarvis" e attendi il *"Sì, signore?"*.
Premi `Ctrl+C` per tornare alla tastiera. Di' "arrivederci" per chiudere.

Comandi durante la conversazione: `/aiuto`, `/voce`, `/ascolto`, `/nuova`, `/memoria`, `/conferme`, `/esci`.

## Sicurezza

JARVIS ha accesso reale al tuo PC. Per questo, **prima di ogni azione potenzialmente pericolosa** (eseguire comandi o script,
scrivere/spostare/eliminare file, chiudere processi, spegnere il PC) **ti chiede conferma** — a voce ("sì"/"procedi") o da tastiera.

- Puoi disattivare le conferme con `/conferme` o `JARVIS_CONFERMA=false`, ma è **sconsigliato**.
- Mentre JARVIS controlla mouse e tastiera, sposta il mouse nell'**angolo in alto a sinistra** dello schermo per bloccarlo immediatamente.
- Non condividere mai il file `.env`: contiene la tua chiave API.

## Configurazione (`.env`)

| Variabile | Predefinito | Descrizione |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | La tua chiave API |
| `JARVIS_NOME_UTENTE` | `signore` | Come JARVIS ti chiama |
| `JARVIS_MODELLO` | `claude-opus-5-5` | Modello Claude |
| `JARVIS_SFORZO` | `medium` | Profondità di ragionamento: `low` (più rapido ed economico) … `max` |
| `JARVIS_VOCE` | `true` | Risposte vocali |
| `JARVIS_VOCE_EDGE` | `it-IT-DiegoNeural` | Voce neurale (alternative: `it-IT-GiuseppeNeural`, `it-IT-ElsaNeural`, `it-IT-IsabellaNeural`) |
| `JARVIS_ASCOLTO` | `false` | Avvia direttamente in ascolto vocale |
| `JARVIS_PAROLA_ATTIVAZIONE` | `jarvis` | Parola che attiva l'ascolto |
| `JARVIS_CONFERMA` | `true` | Conferma per le azioni pericolose |
| `JARVIS_RICERCA_WEB` | `true` | Ricerca web integrata |

La voce neurale usa Edge TTS (richiede internet); se non disponibile, JARVIS usa la voce offline del sistema (pyttsx3).
Il riconoscimento vocale usa il servizio gratuito di Google Speech in italiano.

## Struttura del progetto

```
jarvis/
├── __main__.py        interfaccia (testo + voce), comandi, conferme
├── cervello.py        ciclo di ragionamento con Claude e uso degli strumenti
├── voce.py            sintesi vocale (Edge TTS / pyttsx3) e riconoscimento (SpeechRecognition)
├── config.py          configurazione da .env
└── strumenti/
    ├── __init__.py    registro strumenti e sistema di conferma
    ├── sistema.py     comandi, app, processi, info PC, promemoria, alimentazione
    ├── file.py        leggi/scrivi/cerca/sposta/elimina file (anche PDF e Word)
    ├── controllo.py   screenshot, mouse, tastiera, volume, multimedia, appunti, finestre
    └── memoria.py     memoria permanente (~/.jarvis/memoria.json)
```

### Aggiungere un nuovo strumento

```python
from jarvis.strumenti import strumento

@strumento(
    "meteo_casa",
    "Legge la temperatura dal termostato di casa.",
    {"stanza": {"type": "string"}},
    ["stanza"],
)
def meteo_casa(stanza: str) -> str:
    return f"In {stanza} ci sono 21 gradi."
```
Importa il modulo in `carica_tutti()` (`jarvis/strumenti/__init__.py`) e JARVIS saprà usarlo.
Usa `pericoloso=True` per richiedere la conferma dell'utente.

## Test

```bash
pip install pytest
python -m pytest
```
