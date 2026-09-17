import json

import pytest

from aprs_is_wx import get_wx_data


def write_json(tmp_path, data):
    path = tmp_path / "meteo.json"
    path.write_text(json.dumps(data))
    return str(path)


def test_all_fields_missing_returns_all_none(tmp_path):
    path = write_json(tmp_path, {})
    result = get_wx_data(path)
    assert result == {
        "temperature": None,
        "pressure": None,
        "humidity": None,
        "wind_dir": None,
        "wind_speed": None,
        "wind_gust": None,
        "rain_since_midnight": None,
    }


def test_temperature_converted_from_celsius_by_default(tmp_path):
    path = write_json(tmp_path, {"temperature": 20})
    result = get_wx_data(path)
    assert result["temperature"] == pytest.approx(68.0)


def test_temperature_left_alone_when_already_fahrenheit(tmp_path):
    path = write_json(tmp_path, {"temperature": 68, "temperature_unit": "F"})
    result = get_wx_data(path)
    assert result["temperature"] == pytest.approx(68.0)


def test_pressure_hpa_converted_to_tenths(tmp_path):
    path = write_json(tmp_path, {"pressure": 1012.1})
    result = get_wx_data(path)
    assert result["pressure"] == 10121


def test_pressure_inhg_converted_to_hpa(tmp_path):
    path = write_json(tmp_path, {"pressure": 29.92, "pressure_unit": "inHg"})
    result = get_wx_data(path)
    assert result["pressure"] == int(29.92 * 33.8639 * 10)


def test_pressure_elevation_correction_increases_value(tmp_path):
    path = write_json(tmp_path, {"pressure": 1000})
    no_elevation = get_wx_data(path, elevation=0)
    with_elevation = get_wx_data(path, elevation=200)
    assert with_elevation["pressure"] > no_elevation["pressure"]


def test_humidity_passthrough(tmp_path):
    path = write_json(tmp_path, {"humidity": 99.9})
    result = get_wx_data(path)
    assert result["humidity"] == pytest.approx(99.9)


def test_wind_direction_passthrough(tmp_path):
    path = write_json(tmp_path, {"wind_direction": 270})
    result = get_wx_data(path)
    assert result["wind_dir"] == 270


def test_wind_speed_converted_from_ms(tmp_path):
    path = write_json(tmp_path, {"wind_speed": 10, "wind_speed_unit": "m/s"})
    result = get_wx_data(path)
    assert result["wind_speed"] == pytest.approx(22.3694)


def test_wind_speed_converted_from_kmh(tmp_path):
    path = write_json(tmp_path, {"wind_speed": 10, "wind_speed_unit": "km/h"})
    result = get_wx_data(path)
    assert result["wind_speed"] == pytest.approx(6.21371)


def test_wind_gust_falls_back_to_wind_speed_unit(tmp_path):
    path = write_json(tmp_path, {"wind_gust": 10, "wind_speed_unit": "km/h"})
    result = get_wx_data(path)
    assert result["wind_gust"] == pytest.approx(6.21371)


def test_rain_converted_from_mm(tmp_path):
    path = write_json(tmp_path, {"rain_since_midnight": 5, "rain_unit": "mm"})
    result = get_wx_data(path)
    assert result["rain_since_midnight"] == pytest.approx(5 * 0.0393701 * 100)


def test_rain_left_alone_when_already_inches(tmp_path):
    path = write_json(tmp_path, {"rain_since_midnight": 1.5, "rain_unit": "in"})
    result = get_wx_data(path)
    assert result["rain_since_midnight"] == pytest.approx(1.5)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        get_wx_data(str(tmp_path / "does-not-exist.json"))


def test_invalid_json_raises_value_error(tmp_path):
    path = tmp_path / "meteo.json"
    path.write_text("{not valid json")
    with pytest.raises(ValueError):
        get_wx_data(str(path))
