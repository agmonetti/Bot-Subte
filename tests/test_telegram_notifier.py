import requests

from src.config import Config
from src.services.telegram_notifier import enviar_alerta_telegram, enviar_mensaje_telegram


class FakeResponse:
    def raise_for_status(self):
        pass


def test_enviar_alerta_formatea_mensaje_completo(monkeypatch):
    capturado = {}

    def fake_post(url, data, timeout):
        capturado["url"] = url
        capturado["data"] = data
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)

    cambios = {"A": ["Demora de 20 minutos"]}
    obras = {"B": ["Cerrada por obras de renovación integral"]}
    ren = {"C": ["Obra en curso"]}

    enviar_alerta_telegram(cambios, obras, ren)

    texto = capturado["data"]["text"]
    assert "Obras Programadas Detectadas" in texto
    assert "Cerrada por obras de renovación integral" in texto
    assert "Novedades" in texto
    assert "Demora de 20 minutos" in texto
    assert "Recordatorio - Obras Programadas Activas" in texto
    assert capturado["data"]["chat_id"] == Config.TELEGRAM_CHAT_ID


def test_enviar_alerta_sin_cambios_no_envia(monkeypatch):
    llamadas = []
    monkeypatch.setattr(
        "src.services.telegram_notifier.enviar_mensaje_telegram",
        lambda mensaje, chat_id=None: llamadas.append(mensaje),
    )
    enviar_alerta_telegram({}, {}, {})
    assert llamadas == []


def test_enviar_mensaje_usa_chat_id_personalizado(monkeypatch):
    capturado = {}

    def fake_post(url, data, timeout):
        capturado["data"] = data
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    enviar_mensaje_telegram("Hola", chat_id=42)
    assert capturado["data"]["chat_id"] == 42


def test_enviar_mensaje_default_chat_id(monkeypatch):
    capturado = {}

    def fake_post(url, data, timeout):
        capturado["data"] = data
        return FakeResponse()

    monkeypatch.setattr(requests, "post", fake_post)
    enviar_mensaje_telegram("Hola")
    assert capturado["data"]["chat_id"] == Config.TELEGRAM_CHAT_ID


def test_enviar_mensaje_error_de_red_no_rompe(monkeypatch, capsys):
    def fake_post(url, data, timeout):
        raise requests.exceptions.ConnectionError("boom")

    monkeypatch.setattr(requests, "post", fake_post)
    assert enviar_mensaje_telegram("Hola") is None
    assert "Error de red" in capsys.readouterr().out
