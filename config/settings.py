"""Central settings for the project.

Reads environment variables from the local .env file (see .env.example) and
exposes them as one typed object. Other modules call get_settings() instead of
reading environment variables directly.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings(BaseModel):
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int
    mqtt_host: str
    mqtt_port: int
    api_port: int
    campus_model_path: Path = BASE_DIR / "config" / "campus_model.yaml"
    mqtt_topics_path: Path = BASE_DIR / "config" / "mqtt_topics.yaml"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them."""
    return Settings(
        postgres_user=os.getenv("POSTGRES_USER", "campus"),
        postgres_password=os.getenv("POSTGRES_PASSWORD", "change_me"),
        postgres_db=os.getenv("POSTGRES_DB", "campus_twin"),
        postgres_host=os.getenv("POSTGRES_HOST", "localhost"),
        postgres_port=int(os.getenv("POSTGRES_PORT", "5432")),
        mqtt_host=os.getenv("MQTT_HOST", "localhost"),
        mqtt_port=int(os.getenv("MQTT_PORT", "1883")),
        api_port=int(os.getenv("API_PORT", "8000")),
    )