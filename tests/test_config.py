"""Tests for settings and the MQTT topic contract."""
import yaml

from config.settings import get_settings


def test_settings_load_with_expected_types():
    s = get_settings()
    assert isinstance(s.postgres_port, int)
    assert s.database_url.startswith("postgresql://")
    assert s.campus_model_path.exists()
    assert s.mqtt_topics_path.exists()


def test_topic_pattern_builds_example_topic():
    s = get_settings()
    contract = yaml.safe_load(s.mqtt_topics_path.read_text(encoding="utf-8"))
    topic = contract["topic_pattern"].format(
        building_id="B03", floor_id="F2", device_type="hvac", device_id="ac-07"
    )
    assert topic == "campus/B03/F2/hvac/ac-07"
    assert "hvac" in contract["device_types"]