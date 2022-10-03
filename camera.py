"""Support for cameras connected to a Camect Hub."""
# Lots borrowed from https://github.com/camect/home-assistant-integration/blob/master/camect/camera.py

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.components import camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODEL,
    ATTR_NAME,
    ATTR_VIA_DEVICE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from .binary_sensor import CameraMotionSensor
    from .camecthub import CamectHub
    from .switch import CameraAlertSwitch


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the cameras connected to this Camect Hub."""
    hub: CamectHub = hass.data[DOMAIN][config_entry.entry_id]
    hub_cameras = await hass.async_add_executor_job(hub.api.list_cameras)
    async_add_entities(Camera(hub, camect_camera) for camect_camera in hub_cameras)


class Camera(camera.Camera):
    """An implementation of a camera supported by Camect Hub."""

    def __init__(self, hub: CamectHub, json: dict[str, str]) -> None:
        """Initialize a camera supported by Camect Hub."""
        super().__init__()
        self.hub = hub
        self.api = hub.api
        self.device_id = json["id"]
        self._id = f"{DOMAIN}_{hub.hub_id}_{json['id']}"
        self.entity_id = f"{camera.DOMAIN}.{self._id}"
        self._name = json["name"]
        self._make = json["make"] or ""
        self._model = json["model"] or ""
        self._url = json["url"]
        self._width = int(json["width"])
        self._height = int(json["height"])
        self.is_alert_disabled = json["is_alert_disabled"]
        self._disabled = json["disabled"]
        self.alert_switch: list[CameraAlertSwitch] = []
        self.motion_sensor: list[CameraMotionSensor] = []
        self.last_motion = None
        self.last_detected_obj = ""
        self.offline = False

        hub.cameras.append(self)

    @property
    def name(self) -> str:
        """Return the name of this camera."""
        return self._name

    @property
    def brand(self) -> str:
        """Return the camera brand."""
        return self._make

    @property
    def model(self) -> str:
        """Return the camera model."""
        return self._model

    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.entity_id)},
            ATTR_NAME: self._name,
            ATTR_MODEL: self._model,
            ATTR_MANUFACTURER: self._make,
            ATTR_VIA_DEVICE: (DOMAIN, self.hub.id),
        }

    @property
    def is_streaming(self) -> bool:
        """Return true if the device is streaming."""
        return not self._disabled and not self.offline

    @property
    def is_recording(self) -> bool:
        """Return true if the device is recording."""
        return not self._disabled and not self.offline

    @property
    def is_on(self) -> bool:
        """Return true if on."""
        return not self._disabled and not self.offline

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._id

    @property
    def available(self) -> bool:
        """Return True if camera and is enabled."""
        return not self._disabled and not self.offline

    @property
    def motion_detection_enabled(self) -> bool:
        """Return True if camera alerts are enabled."""
        return not self.is_alert_disabled

    def camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes:
        """Return a still image response from the camera."""
        # The Camect library doesn't handle width or height being None so we override
        # those parameters with the image dimensions previously reported by Camect
        if width is None:
            width = self._width
        if height is None:
            height = self._height
        return self.api.snapshot_camera(self.device_id, width, height)

    async def async_update(self) -> None:
        """Ensure the camera info is kept up-to-date."""
        cam_json = await self.hass.async_add_executor_job(self.hub.api.list_cameras)
        for json in cam_json:
            if json["id"] in self.device_id:
                self._name = json["name"]
                self._make = json["make"] or ""
                self._model = json["model"] or ""
                self._url = json["url"]
                self._width = int(json["width"])
                self._height = int(json["height"])
                self.is_alert_disabled = json["is_alert_disabled"]
                self._disabled = json["disabled"]

    @property
    def should_poll(self) -> bool:
        """We do want to poll so HA stays in sync with Camect."""
        return True
