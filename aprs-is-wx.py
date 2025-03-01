#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
APRS Weather Packet Submitter

This script builds and submits Amateur Packet Reporting System (APRS) weather 
packets to the APRS Internet Service (APRS-IS)

Loosely based on the program from Tom Hayward
https://github.com/kd7lxl/pywxtd/blob/master/pywxtd.py

Further enchanced by FilipsPL 2017-2025
"""

import sys
import os
import time
import json
import logging
import unittest
from datetime import datetime, timedelta
from socket import *
import configparser

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    # handlers=[logging.FileHandler("aprs_weather.log"), logging.StreamHandler(sys.stdout)],
    handlers=[logging.StreamHandler(sys.stdout)],
)


def get_wx_data(json_file, elevation=0):
    """
    Read meteorological data from a JSON file and convert it to appropriate units.
    All weather fields are optional.

    Args:
        json_file (str): Path to the JSON file containing meteorological data
        elevation (float, optional): Station elevation in meters

    Returns:
        dict: A dictionary containing all available weather data in APRS-compatible units

    Raises:
        FileNotFoundError: If the JSON file is not found
        ValueError: If the data cannot be parsed
    """
    try:
        with open(json_file, "r") as f:
            weather_data = json.load(f)

        # Initialize APRS-compatible data dictionary with all fields as None
        aprs_data = {
            "temperature": None,
            "pressure": None,
            "humidity": None,
            "wind_dir": None,
            "wind_speed": None,
            "wind_gust": None,
            "rain_since_midnight": None,
        }

        # Process temperature if available
        if "temperature" in weather_data:
            temp = float(weather_data["temperature"])
            # Convert from Celsius to Fahrenheit if needed
            if weather_data.get("temperature_unit", "C").upper() == "C":
                temp = 9.0 / 5.0 * temp + 32
            aprs_data["temperature"] = temp

        # Process pressure if available
        if "pressure" in weather_data:
            p = float(weather_data["pressure"])
            pressure_unit = weather_data.get("pressure_unit", "hPa").lower()

            # Convert to hPa if needed
            if pressure_unit == "inhg":
                p = p * 33.8639

            # Apply elevation correction if elevation is provided
            if elevation > 0:
                p = p * pow((1.0 + 0.000084229 * (elevation / pow(p, 0.19028))), 5.2553)

            # Convert to tenths of hPa for APRS
            p = int(float(p) * 10)
            aprs_data["pressure"] = p

        # Process humidity if available
        if "humidity" in weather_data:
            aprs_data["humidity"] = float(weather_data["humidity"])

        # Process wind direction if available
        if "wind_direction" in weather_data:
            aprs_data["wind_dir"] = int(weather_data["wind_direction"])

        # Process wind speed if available
        if "wind_speed" in weather_data:
            wind_speed = float(weather_data["wind_speed"])
            wind_unit = weather_data.get("wind_speed_unit", "mph").lower()

            # Convert to mph if needed
            if wind_unit == "m/s":
                wind_speed = wind_speed * 2.23694
            elif wind_unit == "km/h":
                wind_speed = wind_speed * 0.621371

            aprs_data["wind_speed"] = wind_speed

        # Process wind gust if available
        if "wind_gust" in weather_data:
            wind_gust = float(weather_data["wind_gust"])
            gust_unit = weather_data.get("wind_gust_unit", weather_data.get("wind_speed_unit", "mph")).lower()

            # Convert to mph if needed
            if gust_unit == "m/s":
                wind_gust = wind_gust * 2.23694
            elif gust_unit == "km/h":
                wind_gust = wind_gust * 0.621371

            aprs_data["wind_gust"] = wind_gust

        # Process rainfall if available
        if "rain_since_midnight" in weather_data:
            rain = float(weather_data["rain_since_midnight"])
            rain_unit = weather_data.get("rain_unit", "in").lower()

            # Convert to inches if needed
            if rain_unit == "mm":
                rain = rain * 0.0393701

            aprs_data["rain_since_midnight"] = rain

        # Log available weather data
        available_data = [k for k, v in aprs_data.items() if v is not None]
        logging.debug(f"Available weather data: {', '.join(available_data)}")
        logging.debug(f"Processed weather data: {aprs_data}")

        logging.info(f"APRS WX dictionary: {aprs_data}")
        return aprs_data

    except FileNotFoundError:
        logging.error(f"Weather data file {json_file} not found")
        raise
    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON data: {e}")
        raise ValueError(f"Invalid JSON format in {json_file}")
    except Exception as e:
        logging.error(f"Error processing weather data: {e}")
        # Return empty data with all fields None if there's an error
        return {
            "temperature": None,
            "pressure": None,
            "humidity": None,
            "wind_dir": None,
            "wind_speed": None,
            "wind_gust": None,
            "rain_since_midnight": None,
        }


def make_aprs_wx(config, weather_data):
    """
    Assembles the payload of the APRS weather packet.

    Args:
        config (dict): Configuration containing station information
        weather_data (dict): Dictionary containing all weather data in APRS-compatible units

    Returns:
        str: Formatted APRS weather packet string
    """

    def str_or_dots(number, length):
        """
        Format a number with zero-padding or dots if None.

        Args:
            number: Number to format or None
            length (int): Length of the resulting string

        Returns:
            str: Formatted string
        """
        if number is None:
            return "." * length

        if isinstance(number, int):
            format_type = "d"
        elif isinstance(number, float):
            format_type = ".0f"
        else:
            raise TypeError(f"Unsupported type for APRS formatting: {type(number)}")

        return f"{number:{format_type}}".zfill(length)

    # Get the HHMMZ time string in Zulu/UTC
    timeStringZulu = time.strftime("%d%H%M")

    # Convert decimal coordinates to APRS format
    lat_str, lon_str = convert_coordinates_to_aprs_format(config["STATIONLATITUDE"], config["STATIONLONGITUDE"])

    wx_packet = "@%sz%s/%s_%s/%sg%st%sP%sh%sb%s%s" % (
        timeStringZulu,
        lat_str,
        lon_str,
        str_or_dots(weather_data.get("wind_dir"), 3),
        str_or_dots(weather_data.get("wind_speed"), 3),
        str_or_dots(weather_data.get("wind_gust"), 3),
        str_or_dots(weather_data.get("temperature"), 3),
        str_or_dots(weather_data.get("rain_since_midnight"), 3),
        str_or_dots(weather_data.get("humidity"), 2),
        str_or_dots(weather_data.get("pressure"), 5),
        config["STATION_TYPE"],
    )

    logging.debug(f"Created APRS packet: {wx_packet}")
    return wx_packet


# Load configuration from ini file
def load_config(config_file="aprs-is-wx.ini"):
    """
    Load configuration settings from an INI file.

    Args:
        config_file (str): Path to the configuration file

    Returns:
        dict: Dictionary containing configuration settings

    Raises:
        FileNotFoundError: If the configuration file doesn't exist
        configparser.Error: If there's an error parsing the configuration
    """
    try:
        config = configparser.ConfigParser()
        config.read(config_file)

        settings = {
            "ELEVATION": config.getfloat("Station", "elevation"),
            "STATIONLATITUDE": config.getfloat("Station", "lat"),
            "STATIONLONGITUDE": config.getfloat("Station", "lon"),
            "STATION_TYPE": config.get("Station", "type"),
            "METEO_FILE": config.get("Station", "meteo_json"),
            "APRS_HOST": config.get("APRS", "host"),
            "APRS_PORT": config.getint("APRS", "port"),
            "APRS_USER": config.get("APRS", "user"),
            "APRS_PASS": config.get("APRS", "pass"),
            "CALLSIGN": config.get("APRS", "callsign"),
        }

        return settings
    except FileNotFoundError:
        logging.error(f"Configuration file {config_file} not found")
        raise
    except configparser.Error as e:
        logging.error(f"Error parsing configuration: {e}")
        raise


def convert_coordinates_to_aprs_format(lat, lon):
    """
    Convert decimal degrees coordinates to APRS format.

    Args:
        lat (float): Latitude in decimal degrees format (e.g., 37.4025)
        lon (float): Longitude in decimal degrees format (e.g., -122.1392)

    Returns:
        tuple: A tuple containing (latitude_str, longitude_str) in APRS format
    """
    # Process latitude
    lat_direction = "N" if lat >= 0 else "S"
    lat_abs = abs(lat)
    lat_degrees = int(lat_abs)
    lat_minutes = (lat_abs - lat_degrees) * 60
    lat_str = f"{lat_degrees:02d}{lat_minutes:05.2f}{lat_direction}"

    # Process longitude
    lon_direction = "E" if lon >= 0 else "W"
    lon_abs = abs(lon)
    lon_degrees = int(lon_abs)
    lon_minutes = (lon_abs - lon_degrees) * 60
    lon_str = f"{lon_degrees:03d}{lon_minutes:05.2f}{lon_direction}"

    return (lat_str, lon_str)


def send_aprs_with_retry(config, wx, max_retries=3, retry_delay=5):
    """
    Send APRS packet with retry mechanism.

    Args:
        config (dict): Configuration containing APRS server information
        wx (str): APRS weather packet or status message
        max_retries (int): Maximum number of connection retries
        retry_delay (int): Delay between retries in seconds

    Returns:
        bool: True if sending was successful, False otherwise
    """
    host = config["APRS_HOST"]
    port = config["APRS_PORT"]
    user = config["APRS_USER"]
    passcode = config["APRS_PASS"]
    callsign = config["CALLSIGN"]

    for attempt in range(max_retries):
        try:
            logging.info(f"Sending APRS packet (attempt {attempt+1}/{max_retries})")

            # start the aprs server socket
            s = socket(AF_INET, SOCK_STREAM)
            s.settimeout(30)  # Set timeout to 30 seconds
            s.connect((host, port))

            # aprs login
            login_string = f"user {user} pass {passcode} vers aprs-is-wx.py\n"
            s.send(login_string.encode())

            # send packet
            packet_string = f"{callsign}>APRS:{wx}\n"
            s.send(packet_string.encode())

            # Give server time to process
            time.sleep(3)

            # Graceful shutdown
            s.shutdown(SHUT_RDWR)
            s.close()

            logging.info(f"Successfully sent APRS packet")
            return True

        except (timeout, error, ConnectionRefusedError, ConnectionResetError) as e:
            logging.error(f"Network error on attempt {attempt+1}: {e}")

            if attempt < max_retries - 1:
                logging.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error(f"Failed to send APRS packet after {max_retries} attempts")
                return False

        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            return False


def uptime():
    """
    Get the system uptime.

    Returns:
        str: System uptime as a string

    Raises:
        FileNotFoundError: If the uptime file doesn't exist
        ValueError: If the uptime format is invalid
    """
    try:
        with open("/proc/uptime", "r") as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_string = str(timedelta(seconds=uptime_seconds))

        logging.debug(f"System uptime: {uptime_string}")
        return uptime_string

    except FileNotFoundError:
        logging.error("Could not read uptime from /proc/uptime")
        raise
    except ValueError as e:
        logging.error(f"Error parsing uptime: {e}")
        raise


def main():
    try:
        # Load configuration
        config = load_config()

        # Get weather data
        weather_data = get_wx_data(config["METEO_FILE"], config["ELEVATION"])

        # Create weather packet with all available data
        wx = make_aprs_wx(config, weather_data)

        # Log the packet
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"{timestamp} - Weather packet: {wx}")

        # Send weather data
        if send_aprs_with_retry(config, wx):
            # Send uptime status
            try:
                status = f">Uptime: {uptime()}"
                logging.info(f"Sending status: {status}")
                send_aprs_with_retry(config, status)
            except Exception as e:
                logging.error(f"Error sending uptime status: {e}")

    except Exception as e:
        logging.error(f"Program execution failed: {e}")
        return 1

    return 0


if __name__ == "__main__":
    # Run the script if called directly
    sys.exit(main())
