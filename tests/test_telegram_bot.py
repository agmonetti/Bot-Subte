import pytest
import requests

from src.services.storage import guardar_estados
from src.services.telegram_bot import (
    escuchar_comandos,
    formatear_estado_actual,
    obtener_respuesta_estado,
)


class TestFormatearEstadoActual:
    def test_mostrar_texto_completo_sin_cortar_oraciones(self):
        estados = {
            "A": "Servicio interrumpido por obras en C. de Tucumán",
            "B": "Normal",
        }
        texto = formatear_estado_actual(estados)
        assert "Servicio interrumpido por obras en C. de Tucumán" in texto
        assert "<b>B:</b> Normal" in texto

    def test_todas_las_lineas_presentes(self):
        texto = formatear_estado_actual({"A": "Normal"})
        for linea in ["A", "B", "C", "D", "E", "H", "Premetro"]:
            assert f"<b>{linea}:</b>" in texto
        assert "<b>C:</b> sin datos disponibles" in texto


class TestObtenerRespuestaEstado:
    def test_usa_estado_scrapeado(self, monkeypatch):
        monkeypatch.setattr(
            "src.services.telegram_bot.obtener_estado_subte",
            lambda: {"A": "Normal", "B": "Cerrada por obras"},
        )
        texto = obtener_respuesta_estado()
        assert "<b>A:</b> Normal" in texto
        assert "<b>B:</b> Cerrada por obras" in texto

    def test_fallback_a_estado_persistido(self, monkeypatch, tmp_config):
        monkeypatch.setattr("src.services.telegram_bot.obtener_estado_subte", lambda: {})
        guardar_estados({"A": "Normal"}, {}, "2026-08-13T10:00:00-03:00")
        texto = obtener_respuesta_estado()
        assert "<b>A:</b> Normal" in texto

    def test_sin_datos_devuelve_mensaje_de_error(self, monkeypatch, tmp_config):
        monkeypatch.setattr("src.services.telegram_bot.obtener_estado_subte", lambda: {})
        texto = obtener_respuesta_estado()
        assert "No se pudo obtener el estado del subte" in texto


class TestEscucharComandos:
    def test_responde_al_comando_estado(self, monkeypatch):
        capturados = []
        contador = {"n": 0}

        def fake_updates(offset):
            contador["n"] += 1
            if contador["n"] == 1:
                return {
                    "ok": True,
                    "result": [
                        {
                            "update_id": 5,
                            "message": {"text": "/estado", "chat": {"id": 999}},
                        }
                    ],
                }
            raise KeyboardInterrupt()

        monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
        monkeypatch.setattr(
            "src.services.telegram_bot.obtener_respuesta_estado", lambda: "Estado actual"
        )
        monkeypatch.setattr(
            "src.services.telegram_bot.enviar_mensaje_telegram",
            lambda mensaje, chat_id=None: capturados.append((mensaje, chat_id)),
        )

        with pytest.raises(KeyboardInterrupt):
            escuchar_comandos()

        assert capturados == [("Estado actual", 999)]

    def test_ignora_mensajes_que_no_son_comando(self, monkeypatch):
        capturados = []
        contador = {"n": 0}

        def fake_updates(offset):
            contador["n"] += 1
            if contador["n"] == 1:
                return {
                    "ok": True,
                    "result": [
                        {
                            "update_id": 6,
                            "message": {"text": "hola", "chat": {"id": 999}},
                        }
                    ],
                }
            raise KeyboardInterrupt()

        monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
        monkeypatch.setattr(
            "src.services.telegram_bot.enviar_mensaje_telegram",
            lambda mensaje, chat_id=None: capturados.append((mensaje, chat_id)),
        )

        with pytest.raises(KeyboardInterrupt):
            escuchar_comandos()

        assert capturados == []

    def test_error_de_red_no_rompe_el_loop(self, monkeypatch):
        contador = {"n": 0}

        def fake_updates(offset):
            contador["n"] += 1
            if contador["n"] == 1:
                raise requests.exceptions.ConnectionError("boom")
            raise KeyboardInterrupt()

        monkeypatch.setattr("src.services.telegram_bot.obtener_updates", fake_updates)
        monkeypatch.setattr(
            "src.services.telegram_bot.time",
            type("T", (), {"sleep": staticmethod(lambda s: None)})(),
        )

        with pytest.raises(KeyboardInterrupt):
            escuchar_comandos()
