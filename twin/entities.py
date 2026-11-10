"""Digital twin entities: Campus, Building, Floor and Device.

Loads the virtual campus defined in config/campus_model.yaml into validated
Python objects used by the simulator, API and twin state.
"""
from __future__ import annotations

from enum import Enum
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, model_validator


class DeviceType(str, Enum):
    ENERGY_METER = "energy_meter"
    HVAC = "hvac"
    LIGHTING = "lighting"
    OCCUPANCY = "occupancy"


class Device(BaseModel):
    id: str
    type: DeviceType
    unit: str


class Floor(BaseModel):
    id: str
    devices: list[Device] = Field(default_factory=list)


class Building(BaseModel):
    id: str
    name: str
    type: str
    floor_area_m2: float = Field(gt=0)
    floors: list[Floor]

    def all_devices(self) -> list[Device]:
        return [d for floor in self.floors for d in floor.devices]


class Campus(BaseModel):
    name: str
    location: str
    timezone: str
    buildings: list[Building]

    @model_validator(mode="after")
    def _device_ids_must_be_unique(self) -> "Campus":
        ids = [d.id for d in self.all_devices()]
        duplicates = {i for i in ids if ids.count(i) > 1}
        if duplicates:
            raise ValueError(f"Duplicate device ids: {sorted(duplicates)}")
        return self

    def all_devices(self) -> list[Device]:
        return [d for b in self.buildings for d in b.all_devices()]

    def get_building(self, building_id: str) -> Building:
        for building in self.buildings:
            if building.id == building_id:
                return building
        raise KeyError(f"Unknown building: {building_id}")

    def get_device(self, device_id: str) -> Device:
        for device in self.all_devices():
            if device.id == device_id:
                return device
        raise KeyError(f"Unknown device: {device_id}")

    @classmethod
    def from_yaml(cls, path: str | Path = "config/campus_model.yaml") -> "Campus":
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls(**data["campus"], buildings=data["buildings"])