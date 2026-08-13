from src.services.storage import cargar_estados_anteriores, guardar_estados


def test_guardar_y_cargar_round_trip(tmp_config):
    estados = {"A": "Normal", "B": "Cerrada por obras"}
    historial = {"B_obra": {"estado": "Cerrada por obras", "tipo": "obra"}}
    fecha = "2026-08-13T10:00:00-03:00"

    guardar_estados(estados, historial, fecha)
    data = cargar_estados_anteriores()

    assert data["ultima_actualizacion"] == fecha
    assert data["estados_actuales"] == estados
    assert data["historial"] == historial


def test_cargar_sin_archivo_devuelve_vacio(tmp_config):
    assert cargar_estados_anteriores() == {}


def test_cargar_json_corrupto_devuelve_vacio(tmp_config, monkeypatch, capsys):
    tmp_config.joinpath("estados_persistentes.json").write_text("{no valido", encoding="utf-8")
    assert cargar_estados_anteriores() == {}
    assert "Error de I/O" in capsys.readouterr().out
