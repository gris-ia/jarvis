#!/usr/bin/env bash
# Installazione di JARVIS su macOS e Linux
set -e
cd "$(dirname "$0")"
if [[ "$(uname)" == "Darwin" ]]; then
  command -v brew >/dev/null && brew install portaudio || echo "Installa portaudio (brew install portaudio) per il microfono."
elif command -v apt-get >/dev/null; then
  sudo apt-get install -y portaudio19-dev python3-venv python3-tk python3-dev scrot xclip espeak-ng
fi
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
echo "Installazione completata. Inserisci la tua ANTHROPIC_API_KEY in .env e avvia con ./avvia_jarvis.sh"
