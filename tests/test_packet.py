import re

from aprs_is_wx import make_aprs_wx

CONFIG = {
    "STATIONLATITUDE": 52.021166667,
    "STATIONLONGITUDE": 20.603666667,
    "STATION_TYPE": "WX Test",
}

EMPTY_WX = {
    "temperature": None,
    "pressure": None,
    "humidity": None,
    "wind_dir": None,
    "wind_speed": None,
    "wind_gust": None,
    "rain_since_midnight": None,
}


def test_missing_fields_are_rendered_as_dots():
    packet = make_aprs_wx(CONFIG, EMPTY_WX)
    match = re.match(
        r"^@\d{6}z5201\.27N/02036\.22E_\.{3}/\.{3}g\.{3}t\.{3}P\.{3}h\.{2}b\.{5}WX Test$",
        packet,
    )
    assert match, packet


def test_full_data_is_formatted_with_fixed_width_fields():
    wx_data = {
        "temperature": 57.38,
        "pressure": 10121,
        "humidity": 99.9,
        "wind_dir": 270,
        "wind_speed": 5.4,
        "wind_gust": 12.3,
        "rain_since_midnight": 1.23,
    }
    packet = make_aprs_wx(CONFIG, wx_data)
    match = re.match(
        r"^@(?P<ts>\d{6})z5201\.27N/02036\.22E_270/005g012t057P001h100b10121WX Test$",
        packet,
    )
    assert match, packet
