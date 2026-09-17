from aprs_is_wx import convert_coordinates_to_aprs_format


def test_northern_eastern_hemisphere():
    lat_str, lon_str = convert_coordinates_to_aprs_format(52.021166667, 20.603666667)
    assert lat_str == "5201.27N"
    assert lon_str == "02036.22E"


def test_southern_western_hemisphere():
    lat_str, lon_str = convert_coordinates_to_aprs_format(-33.865, -151.209)
    assert lat_str == "3351.90S"
    assert lon_str == "15112.54W"


def test_zero_padding_for_small_degrees():
    lat_str, lon_str = convert_coordinates_to_aprs_format(5.5, 5.5)
    assert lat_str == "0530.00N"
    assert lon_str == "00530.00E"


def test_equator_and_prime_meridian():
    lat_str, lon_str = convert_coordinates_to_aprs_format(0.0, 0.0)
    assert lat_str == "0000.00N"
    assert lon_str == "00000.00E"
