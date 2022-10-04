"""Pseudo motion sensors from Camect camera motion alerts."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import TYPE_CHECKING, Literal

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_IDENTIFIERS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import ATTR_MOTION, ATTR_MOTION_LABEL, DOMAIN

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .camecthub import CamectHub
    from .camera import Camera as CamectCamera


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Add binary sensors for a config entry."""
    hub: CamectHub = hass.data[DOMAIN][config_entry.entry_id]
    new_sensors = []
    for camect_camera in hub.cameras:
        new_sensors.append(CameraMotionSensor(hub, camect_camera))
    async_add_entities(new_sensors)


class CameraMotionSensor(BinarySensorEntity):
    """Define a Camect motion sensor."""

    _attr_device_class: Literal[BinarySensorDeviceClass.MOTION]

    def __init__(self, hub: CamectHub, cam: CamectCamera) -> None:
        """Init the class."""
        super().__init__()
        self.entity_description = BinarySensorEntityDescription(
            key="motion_detected",
            name="Motion Detected",
            device_class=BinarySensorDeviceClass.MOTION,
        )
        self.hub = hub
        self.cam = cam
        self.entity_id = f"{self.cam.entity_id}_{ATTR_MOTION}"
        cam.motion_sensor.append(self)

    @property
    def name(self) -> str:
        """Return the name of the binary sensor."""
        return f"{self.cam.name} {ATTR_MOTION_LABEL}"

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"{self.cam.entity_id}_{ATTR_MOTION}"

    @property
    def is_on(self) -> bool:
        """Return true if the Hub reported this camera generated an alert within the last 20 seconds."""
        if self.cam.last_motion is None:
            return False
        if self.cam.last_motion > (datetime.now() - timedelta(seconds=20)):
            return True
        return False

    @property
    def available(self) -> bool:
        """Return True if the camera is available."""
        return self.cam.available

    @property
    def icon(self) -> str:
        """Return the appropriate MDI icons."""
        return "mdi:motion-sensor" if self.is_on else "mdi:motion-sensor-off"

    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.cam.entity_id)},
        }

    @property
    def extra_state_attributes(self) -> dict[str, str] | None:
        """Return the state attributes."""
        return {"detected_obj": self.cam.last_detected_obj}
