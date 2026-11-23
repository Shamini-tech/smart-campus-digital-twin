"""Replay simulated campus readings to the MQTT broker.

Example: python -m simulator.run_simulator --start 2016-10-05 --end 2016-10-05 --faults
"""
from __future__ import annotations

import argparse

import paho.mqtt.client as mqtt

from config.settings import BASE_DIR, get_settings
from features.calendar_features import load_calendar
from features.weather_client import load_site_weather
from simulator.fault_injector import inject_faults
from simulator.mqtt_publisher import publish_readings
from simulator.profile_loader import load_profiles
from simulator.sensor_simulator import simulate_readings
from twin.entities import Campus


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2016-10-03")
    ap.add_argument("--end", default="2016-10-09")
    ap.add_argument("--delay", type=float, default=0.2, help="seconds per simulated hour")
    ap.add_argument("--faults", action="store_true", help="inject labelled faults")
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    args = ap.parse_args()

    settings = get_settings()
    campus = Campus.from_yaml(settings.campus_model_path)
    values, statuses = load_profiles()
    weather = load_site_weather(BASE_DIR / "data" / "raw" / "weather.csv", "Fox")
    calendar = load_calendar(BASE_DIR / "data" / "academic_calendar.csv")
    readings = simulate_readings(campus, values, statuses, weather, calendar, args.start, args.end)
    if args.faults:
        readings = inject_faults(readings)

    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    client.connect(args.host, args.port)
    client.loop_start()
    sent = publish_readings(client, readings, delay_s=args.delay)
    client.loop_stop()
    client.disconnect()
    print(f"Published {sent} messages ({args.start} to {args.end}) to {args.host}:{args.port}")


if __name__ == "__main__":
    main()