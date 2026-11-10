"""Tests for the campus entities."""
import pytest
from pydantic import ValidationError

from twin.entities import Campus, DeviceType


def test_campus_loads_from_yaml():
    campus = Campus.from_yaml("config/campus_model.yaml")
    assert len(campus.buildings) == 5
    assert len(campus.all_devices()) == 28


def test_lookup_building_and_device():
    campus = Campus.from_yaml("config/campus_model.yaml")
    assert campus.get_building("B03").name == "Hostel"
    assert campus.get_device("ac-07").type == DeviceType.HVAC


def test_unknown_building_raises():
    campus = Campus.from_yaml("config/campus_model.yaml")
    with pytest.raises(KeyError):
        campus.get_building("B99")


def test_duplicate_device_ids_rejected():
    device = {"id": "x-1", "type": "hvac", "unit": "kWh"}
    building = {
        "id": "B01", "name": "A", "type": "t", "floor_area_m2": 10,
        "floors": [{"id": "F1", "devices": [device, device]}],
    }
    with pytest.raises(ValidationError):
        Campus(name="c", location="l", timezone="UTC", buildings=[building])