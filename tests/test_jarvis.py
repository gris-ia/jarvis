"""Test di base: registro strumenti, strumenti senza effetti collaterali e ciclo del cervello."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from jarvis import strumenti


@pytest.fixture(autouse=True)
def dati_temporanei(tmp_path, monkeypatch):
    from jarvis.strumenti import memoria

    monkeypatch.setattr(memoria, "FILE_MEMORIA", tmp_path / "memoria.json")
    strumenti.carica_tutti()


def test_schemi_validi():
    nomi = set()
    for s in strumenti.schemi():
        assert s["name"] not in nomi
        nomi.add(s["name"])
        assert s["input_schema"]["type"] == "object"
        for obbligatorio in s["input_schema"]["required"]:
            assert obbligatorio in s["input_schema"]["properties"]
    assert {"esegui_comando", "apri", "screenshot", "ricorda", "leggi_file"} <= nomi


def test_strumento_sconosciuto():
    risultato, errore = strumenti.esegui("non_esiste", {})
    assert errore


def test_parametri_mancanti():
    risultato, errore = strumenti.esegui("leggi_file", {})
    assert errore and "percorso" in risultato


def test_conferma_negata_blocca_azioni_pericolose(tmp_path):
    file = tmp_path / "prova.txt"
    risultato, errore = strumenti.esegui(
        "scrivi_file", {"percorso": str(file), "contenuto": "ciao"}, conferma=lambda d: False
    )
    assert errore and not file.exists()


def test_file_scrivi_leggi_cerca(tmp_path):
    file = tmp_path / "sotto" / "nota.txt"
    strumenti.esegui("scrivi_file", {"percorso": str(file), "contenuto": "Ciao Jarvis"}, conferma=lambda d: True)
    assert strumenti.esegui("leggi_file", {"percorso": str(file)}) == ("Ciao Jarvis", False)
    trovati, _ = strumenti.esegui("cerca_file", {"schema": "nota", "cartella": str(tmp_path)})
    assert str(file) in trovati


def test_comando():
    risultato, errore = strumenti.esegui("esegui_comando", {"comando": "echo jarvis"})
    assert not errore and "jarvis" in risultato and "exit code: 0" in risultato


def test_memoria():
    strumenti.esegui("ricorda", {"fatto": "Preferisce il caffè amaro"})
    assert "caffè amaro" in strumenti.esegui("leggi_memoria", {})[0]
    strumenti.esegui("dimentica", {"testo": "caffè"})
    assert "vuota" in strumenti.esegui("leggi_memoria", {})[0]


def test_info_sistema():
    risultato, errore = strumenti.esegui("info_sistema", {})
    assert not errore and "RAM" in risultato


# --- Ciclo del cervello con un client finto ------------------------------------------


def _blocco_testo(testo):
    return SimpleNamespace(type="text", text=testo)


def _blocco_strumento(id_, nome, argomenti):
    return SimpleNamespace(type="tool_use", id=id_, name=nome, input=argomenti)


class ClientFinto:
    def __init__(self, risposte):
        self.risposte = list(risposte)
        self.richieste = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.richieste.append({**kwargs, "messages": list(kwargs["messages"])})
        return self.risposte.pop(0)


def test_ciclo_con_strumenti(monkeypatch):
    from jarvis.cervello import Cervello
    from jarvis.config import Config

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    cervello = Cervello(Config())
    cervello.client = ClientFinto([
        SimpleNamespace(
            stop_reason="tool_use",
            content=[_blocco_testo("Controllo l'ora."), _blocco_strumento("t1", "data_ora", {})],
        ),
        SimpleNamespace(stop_reason="end_turn", content=[_blocco_testo("Sono le dieci, signore.")]),
    ])
    intermedi = []
    cervello.su_testo = intermedi.append

    assert cervello.chiedi("Che ore sono?") == "Sono le dieci, signore."
    assert intermedi == ["Controllo l'ora."]
    seconda = cervello.client.richieste[1]
    risultato = seconda["messages"][-1]["content"][0]
    assert risultato["type"] == "tool_result" and risultato["tool_use_id"] == "t1"
    assert seconda["fallbacks"] == "default"
    assert [m["role"] for m in cervello.messaggi] == ["user", "assistant", "user", "assistant"]


def test_errore_api_ripristina_cronologia(monkeypatch):
    import anthropic

    from jarvis.cervello import Cervello
    from jarvis.config import Config

    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    cervello = Cervello(Config())

    def fallisci(**kwargs):
        raise anthropic.APIConnectionError(request=None)

    cervello.client = SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(create=fallisci)))
    assert "connettermi" in cervello.chiedi("ciao")
    assert cervello.messaggi == []
