# APRS-IS Python Weather Station

A Python tool for submitting weather data to the Automatic Packet Reporting System (APRS) network.

## Overview

`aprs-is-wx.py` is a flexible and robust tool that collects weather data from JSON files and submits it to the APRS Internet Service (APRS-IS) or Citizen Weather Observer Program (CWOP). It handles unit conversions, coordinates formatting, and provides reliable network communication with error handling and retry mechanisms.


## Features

- Reads weather data from simple JSON files
- Converts units automatically (C to F, hPa to mmHg, etc.)
- Formats APRS packets according to specification
- Supports multiple weather parameters:
  - Temperature
  - Pressure (with elevation correction)
  - Humidity
  - Wind direction
  - Wind speed and gusts
  - Rainfall
- Provides robust error handling and logging
- Includes a retry mechanism for network communication
- Supports configuration via INI files
- Inspired by kd7lxl's https://github.com/kd7lxl/pywxtd/blob/master/pywxtd.py

## Requirements

- Python 3.6+
- Network connectivity to APRS servers
- APRS username and password assigned

## Installation

1. Clone this repository or download the source code
2. Create your configuration file from txt template (see below)

## Configuration

Create an `aprs_config.ini` file with the following parameters:

```ini
[Station]
elevation = 110
lat = 53.2320230
lon = 20.0713454
type = WX Meteo Station
meteo_json = meteo.json

[APRS]
host = radom.aprs2.net
port = 14580
user = SP5XXX
pass = 666666
callsign = SP5XXX-13
```

## Weather Data Format

Create a `meteo.json` file with your weather data:

```json
{
  "temperature": 18.5,
  "temperature_unit": "C",
  "pressure": 1013.25,
  "pressure_unit": "hPa",
  "humidity": 65,
  "wind_direction": 270,
  "wind_speed": 15.7,
  "wind_speed_unit": "km/h",
  "wind_gust": 25.3,
  "wind_gust_unit": "km/h",
  "rain_since_midnight": 2.5,
  "rain_unit": "mm"
}
```

All fields are optional, and the program will handle whatever data is available.

## Usage

Run the script:

```bash
python aprs-is-wx.py
```

The program will:
1. Read the configuration file
2. Load weather data from the JSON file
3. Convert and format the data into an APRS packet
4. Submit the packet to the APRS server
5. Send a station uptime status message

Screenshot:

```console
2025-03-01 17:26:05,036 - INFO - 2025-03-01 17:26:05 - Weather packet: @011726z5112.92N/02254.28E_.../...g...t037P...h100b10294WX Warszawa Południe
2025-03-01 17:26:05,036 - INFO - Sending APRS packet (attempt 1/3)
2025-03-01 17:26:08,088 - INFO - Successfully sent APRS packet
2025-03-01 17:26:08,088 - INFO - Sending status: >Uptime: 0:55:02.450000
2025-03-01 17:26:08,088 - INFO - Sending APRS packet (attempt 1/3)
2025-03-01 17:26:11,116 - INFO - Successfully sent APRS packet
```

## License

This program is based on work by Tom Hayward and is distributed under the BSD License.

## Acknowledgments

- Originally written by Tom Hayward
- Enhanced by Filip SP5FLS