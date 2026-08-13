from datetime import datetime, timedelta

import pytest

from src.config import Config
from src.services.analyzer import (
    analizar_cambios_con_historial,
    limpiar_historial_antiguo,
    normalizar_obra,
    procesar_estado_por_oraciones,
)


class TestProcesarEstadoPorOraciones:
    def test_abreviacion_no_corta_la_oracion(self):
        estado = "La estación C. de Tucumán permanece cerrada por obras. Normal"
        componentes = procesar_estado_por_oraciones(estado)
        assert "La estación C. de Tucumán permanece cerrada por obras" in componentes["obras"]
        assert componentes["otros"] == ["Normal"]

    def test_abreviacion_jm_rosas_no_corta(self):
        estado = "J.M. Rosas cerrada por obras. Servicio normal"
        componentes = procesar_estado_por_oraciones(estado)
        assert "J.M. Rosas cerrada por obras" in componentes["obras"]

    def test_abreviacion_leandro_n_alem_no_corta(self):
        estado = "Leandro N. Alem sin servicio por obras. Normal"
        componentes = procesar_estado_por_oraciones(estado)
        assert "Leandro N. Alem sin servicio por obras" in componentes["obras"]

    def test_clasificacion_obras_problemas_otros(self):
        estado = "Demora por incidente en la estación. Obras de renovación integral. Normal"
        componentes = procesar_estado_por_oraciones(estado)
        assert componentes["problemas"] == ["Demora por incidente en la estación"]
        assert componentes["obras"] == ["Obras de renovación integral"]
        assert componentes["otros"] == ["Normal"]

    def test_estado_normal_solo_otros(self):
        componentes = procesar_estado_por_oraciones("Normal")
        assert componentes["problemas"] == []
        assert componentes["obras"] == []
        assert componentes["otros"] == ["Normal"]


class TestNormalizarObra:
    def test_normaliza_mayusculas_y_prefijos(self):
        normalizado = normalizar_obra("Las estaciones C. de Tucumán cerradas por obras")
        assert normalizado == "c. de tucumán cerradas por obras"


class TestAnalizarCambiosConHistorial:
    def test_nuevo_problema_detectado(self):
        cambios, obras, ren, estados, _ = analizar_cambios_con_historial(
            {"A": "Demora de 20 minutos por incidente"}, {}
        )
        assert cambios["A"] == ["Demora de 20 minutos por incidente"]
        assert obras == {}
        assert ren == {}
        assert estados["A"] == "Demora de 20 minutos por incidente"

    def test_problema_resuelto_notifica_recuperacion(self):
        _, _, _, _, historial = analizar_cambios_con_historial({"A": "Demora"}, {})
        cambios, _, _, _, _ = analizar_cambios_con_historial({"A": "Normal"}, historial)
        assert cambios["A"] == ["Volvió a funcionar normalmente"]

    def test_obra_programada_nueva(self):
        cambios, obras, ren, _, _ = analizar_cambios_con_historial(
            {"B": "Cerrada por obras de renovación integral"}, {}
        )
        assert obras["B"] == ["Cerrada por obras de renovación integral"]
        assert cambios == {}
        assert ren == {}

    def test_problema_persistente_se_convierte_en_obra(self, monkeypatch):
        monkeypatch.setattr(Config, "UMBRAL_OBRA_PROGRAMADA", 2)
        historial = {}
        _, _, _, _, historial = analizar_cambios_con_historial({"B": "Demora"}, historial)
        _, obras, _, _, _ = analizar_cambios_con_historial({"B": "Demora"}, historial)
        assert "llegó a 2 apariciones" in obras["B"][0]

    def test_obra_renotifica_despues_de_dias(self, monkeypatch):
        monkeypatch.setattr(Config, "DIAS_RENOTIFICAR_OBRA", 15)
        ahora = datetime.now(Config.TIMEZONE_LOCAL)
        historial = {
            "B_obra": {
                "estado": "Cerrada por obras de renovación integral",
                "linea_original": "B",
                "tipo": "obra",
                "contador": 3,
                "primera_deteccion": (ahora - timedelta(days=20)).isoformat(),
                "ultima_notificacion": (ahora - timedelta(days=16)).isoformat(),
                "es_obra_programada": True,
                "detectada_por_texto": True,
                "activa": True,
                "ya_notificada": True,
            }
        }
        _, _, ren, _, _ = analizar_cambios_con_historial(
            {"B": "Cerrada por obras de renovación integral"}, historial
        )
        assert ren["B"] == ["Cerrada por obras de renovación integral"]

    def test_limpiar_historial_antiguo(self):
        ahora = datetime.now(Config.TIMEZONE_LOCAL)
        historial = {
            "X_problema": {
                "tipo": "problema",
                "es_obra_programada": False,
                "activa": False,
                "fecha_desaparicion": (ahora - timedelta(days=6)).isoformat(),
                "linea_original": "A",
            },
            "Y_obra": {
                "tipo": "obra",
                "es_obra_programada": True,
                "detectada_por_texto": True,
                "activa": False,
                "fecha_desaparicion": (ahora - timedelta(days=6)).isoformat(),
                "linea_original": "B",
            },
            "Z_obra_persistente": {
                "tipo": "obra",
                "es_obra_programada": True,
                "detectada_por_texto": False,
                "activa": False,
                "fecha_desaparicion": (ahora - timedelta(days=6)).isoformat(),
                "linea_original": "C",
            },
        }
        limpiar_historial_antiguo(historial)
        assert "X_problema" not in historial
        assert "Z_obra_persistente" not in historial
        assert "Y_obra" in historial
