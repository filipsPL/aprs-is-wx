from datetime import timedelta
from unittest.mock import mock_open, patch

from aprs_is_wx import uptime


def test_uptime_formats_seconds_from_proc_uptime():
    with patch("builtins.open", mock_open(read_data="12345.67 6789.01\n")):
        result = uptime()

    assert result == str(timedelta(seconds=12345.67))
