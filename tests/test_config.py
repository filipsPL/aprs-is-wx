import pytest

from aprs_is_wx import load_config

INI_CONTENT = """
[Station]
elevation = 123.4
lat = 52.021166667
lon = 20.603666667
type = WX Test
meteo_json = meteo.json

[APRS]
host = rotate.aprs.net
port = 14580
user = N0CALL
pass = 12345
callsign = N0CALL-13
"""


def test_load_config_parses_all_fields(tmp_path):
    ini_path = tmp_path / "aprs-is-wx.ini"
    ini_path.write_text(INI_CONTENT)

    config = load_config(str(ini_path))

    assert config == {
        "ELEVATION": 123.4,
        "STATIONLATITUDE": 52.021166667,
        "STATIONLONGITUDE": 20.603666667,
        "STATION_TYPE": "WX Test",
        "METEO_FILE": "meteo.json",
        "APRS_HOST": "rotate.aprs.net",
        "APRS_PORT": 14580,
        "APRS_USER": "N0CALL",
        "APRS_PASS": "12345",
        "CALLSIGN": "N0CALL-13",
    }


def test_load_config_missing_section_raises(tmp_path):
    ini_path = tmp_path / "aprs-is-wx.ini"
    ini_path.write_text("[Station]\nelevation = 0\n")

    with pytest.raises(Exception):
        load_config(str(ini_path))
