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


def get_wx_data(elevation):
    """
    Read meteorological data from a file and convert it to appropriate units.

    Args:
        meteo_file (str): Path to the file containing meteorological data
        elevation (float): Station elevation in meters

    Returns:
        list: A list containing [temperature(F), pressure(hPa*10), humidity(%)]

    Raises:
        FileNotFoundError: If the meteorological data file is not found
        ValueError: If the data cannot be parsed or converted
    """
    try:
        with open("meteo.txt", "r") as f:
            meteo = f.read()

        meteos = meteo.split("\n")

        # Convert temperature from Celsius to Fahrenheit
        temp = float(meteos[0])
        temp = 9.0 / 5.0 * temp + 32

        # Adjust pressure based on elevation
        p = float(meteos[1])
        p = p * pow((1.0 + 0.000084229 * (elevation / pow(p, 0.19028))), 5.2553)
        p = int(float(p) * 10)

        # Read humidity
        hum = float(meteos[2])

        logging.debug(f"Read data: temp={temp}F, pressure={p/10}hPa, humidity={hum}%")
        return [temp, p, hum]

    except FileNotFoundError:
        logging.error(f"Meteorological data file not found")
        raise
    except (ValueError, IndexError) as e:
        logging.error(f"Error parsing meteorological data: {e}")
        raise


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
   lat_direction = 'N' if lat >= 0 else 'S'
   lat_abs = abs(lat)
   lat_degrees = int(lat_abs)
   lat_minutes = (lat_abs - lat_degrees) * 60
   lat_str = f"{lat_degrees:02d}{lat_minutes:05.2f}{lat_direction}"
   
   # Process longitude
   lon_direction = 'E' if lon >= 0 else 'W'
   lon_abs = abs(lon)
   lon_degrees = int(lon_abs)
   lon_minutes = (lon_abs - lon_degrees) * 60
   lon_str = f"{lon_degrees:03d}{lon_minutes:05.2f}{lon_direction}"
   
   return (lat_str, lon_str)

def make_aprs_wx(
    config, wind_dir=None, wind_speed=None, wind_gust=None, temperature=None, rain_since_midnight=None, humidity=None, pressure=None
):
    """
    Assembles the payload of the APRS weather packet.

    Args:
        config (dict): Configuration containing station information
        wind_dir (int, optional): Wind direction in degrees
        wind_speed (float, optional): Wind speed
        wind_gust (float, optional): Wind gust speed
        temperature (float, optional): Temperature in Fahrenheit
        rain_since_midnight (float, optional): Rain since midnight
        humidity (float, optional): Humidity percentage
        pressure (int, optional): Pressure in tenths of hPa/mbar

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

    timeStringZulu = time.strftime("%d%H%M")

    lat_str, lon_str = convert_coordinates_to_aprs_format(config['STATIONLATITUDE'], config['STATIONLONGITUDE'])


    wx_packet = "@%sz%s/%s_%s/%sg%st%sP%sh%sb%s%s" % (
        timeStringZulu,
        lat_str,
        lon_str,
        str_or_dots(wind_dir, 3),
        str_or_dots(wind_speed, 3),
        str_or_dots(wind_gust, 3),
        str_or_dots(temperature, 3),
        str_or_dots(rain_since_midnight, 3),
        str_or_dots(humidity, 2),
        str_or_dots(pressure, 5),
        config["STATION_TYPE"],
    )

    logging.debug(f"Created APRS packet: {wx_packet}")
    return wx_packet


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
    """
    Main function to run the APRS weather packet submission.
    """
    try:
        # Load configuration
        config = load_config()

        # Get weather data
        temp, p, hum = get_wx_data(config["ELEVATION"])

        # Create weather packet
        wx = make_aprs_wx(
            config, wind_dir=None, wind_speed=None, wind_gust=None, temperature=temp, rain_since_midnight=None, humidity=hum, pressure=p
        )

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


if __name__ == "__main__":
    # Run the script if called directly
    sys.exit(main())
