"""Subscribe to campus/# and store validated readings in TimescaleDB.

Run: python -m ingestion.subscriber   (stop with Ctrl+C)
Start it BEFORE the simulator: messages sent while it is not running are lost.
"""
from __future__ import annotations

import argparse
import logging
import time

import paho.mqtt.client as mqtt
import psycopg

from ingestion.db import get_dsn, insert_readings
from ingestion.parser import TOPIC_ROOT, parse_message

log = logging.getLogger("ingestion")


class Ingestor:
    def __init__(self, conn, batch_size: int = 200):
        self.conn = conn
        self.batch_size = batch_size
        self.buffer = []
        self.stored = 0
        self.rejected = 0

    def handle(self, topic: str, payload) -> None:
        try:
            self.buffer.append(parse_message(topic, payload))
        except ValueError as exc:
            self.rejected += 1
            log.warning("rejected %s: %s", topic, exc)
            return
        if len(self.buffer) >= self.batch_size:
            self.flush()

    def flush(self) -> None:
        if self.buffer:
            self.stored += insert_readings(self.conn, self.buffer)
            self.buffer = []


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", default="localhost")
    ap.add_argument("--port", type=int, default=1883)
    ap.add_argument("--batch-size", type=int, default=200)
    ap.add_argument("--flush-seconds", type=float, default=2.0)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    conn = psycopg.connect(get_dsn())
    ing = Ingestor(conn, args.batch_size)
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def on_connect(c, userdata, flags, reason_code, properties=None):
        c.subscribe(f"{TOPIC_ROOT}/#", qos=1)
        log.info("connected to broker, subscribed to %s/#", TOPIC_ROOT)

    client.on_connect = on_connect
    client.on_message = lambda c, u, m: ing.handle(m.topic, m.payload)
    client.connect(args.host, args.port)

    last = time.monotonic()
    try:
        while True:
            client.loop(timeout=1.0)
            if time.monotonic() - last >= args.flush_seconds:
                ing.flush()
                last = time.monotonic()
                log.info("stored so far: %d, rejected: %d", ing.stored, ing.rejected)
    except KeyboardInterrupt:
        pass
    finally:
        ing.flush()
        client.disconnect()
        conn.close()
        print(f"Stored {ing.stored} readings, rejected {ing.rejected}.")


if __name__ == "__main__":
    main()