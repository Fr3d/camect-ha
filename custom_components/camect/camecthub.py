"""Code to handle a Camect Hub."""
from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING

import camect

from homeassistant.components import camera
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_CONFIGURATION_URL,
    ATTR_DEVICE_ID,
    ATTR_IDENTIFIERS,
    ATTR_MANUFACTURER,
    ATTR_MODE,
    ATTR_MODEL,
    ATTR_NAME,
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TYPE,
    CONF_USERNAME,
    EVENT_LOGBOOK_ENTRY,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, Entity

from .const import (
    ATTR_ALERT,
    ATTR_CAM_OFFLINE,
    ATTR_CAM_ONLINE,
    ATTR_CAMECT_EVENT,
    ATTR_CAMECT_MAKE,
    ATTR_CAMECT_MODEL,
    ATTR_MODE_DEFAULT,
    ATTR_MODE_HOME,
    ATTR_RAW_DATA,
    ATTR_UNKNOWN_OBJ,
    DOMAIN,
    LOGBOOK_ENTRY_DOMAIN,
    LOGBOOK_ENTRY_ENTITY_ID,
    LOGBOOK_ENTRY_MESSAGE,
    LOGBOOK_ENTRY_NAME,
)

if TYPE_CHECKING:
    from .camera import Camera as CamectCamera
    from .switch import HubModeSwitch

_LOGGER = logging.getLogger(__name__)


class CamectHub(Entity):
    """Manages a single Camect Hub."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize the system."""
        self.config_entry = config_entry
        self.hass = hass
        self.api: camect.Hub = None
        self.id: str = ""
        self.entity_id: str = ""
        self.hub_id: str = ""
        self.info: dict = {}
        self.hub_name: str = ""
        self.local_https_url: str = ""
        self.mode = ATTR_MODE_DEFAULT
        self.modeswitch: list[HubModeSwitch] = []
        self.cameras: list[CamectCamera] = []

        hass.data.setdefault(DOMAIN, {})[self.config_entry.entry_id] = self

    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.id)},
            ATTR_NAME: self.hub_name,
            # ATTR_SW_VERSION: "1.0",
            ATTR_MODEL: ATTR_CAMECT_MODEL,
            ATTR_MANUFACTURER: ATTR_CAMECT_MAKE,
            ATTR_CONFIGURATION_URL: self.local_https_url,
            # ATTR_VIA_DEVICE: (DOMAIN, self.id),
        }

    @property
    def name(self) -> str | None:
        """Return the human-friendly name of the hub."""
        return self.hub_name

    @property
    def host(self) -> str:
        """Return the host of this hub."""
        return self.config_entry.data[CONF_HOST]

    @property
    def port(self) -> str:
        """Return the port of this hub."""
        return self.config_entry.data[CONF_PORT]

    @property
    def username(self) -> str:
        """Return the username."""
        return self.config_entry.data[CONF_USERNAME]

    @property
    def password(self) -> str:
        """Return the password."""
        return self.config_entry.data[CONF_PASSWORD]

    async def async_initialize_hub(self, hass: HomeAssistant) -> bool:
        """Initialize Connection with the Camect Hub."""
        try:
            self.api = await hass.async_add_executor_job(
                camect.Hub,
                f"{self.host}:{self.port}",
                self.username,
                self.password,
            )
            await self.update_hub_info()
            self.hub_id = self.info["id"]
            self.id = f"{DOMAIN}_{self.hub_id}"
            self.entity_id = f"{DOMAIN}.{self.id}"
            self.hub_name = self.info["name"]
            self.local_https_url = (
                self.info["local_https_url"] or f"https://{self.host}:{self.port}"
            )
            await self.update_mode_property()
            # pylint: disable=unnecessary-lambda
            self.api.add_event_listener(lambda evt: self.handle_camect_event(evt))

        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception("Unknown error connecting to hub: %s", str(ex))
            return False

        return True

    async def update_hub_info(self) -> None:
        """Update the info property from the API."""
        self.info = await self.hass.async_add_executor_job(self.api.get_info)

    async def update_mode_property(self) -> None:
        """Update the mode property."""
        if self.info["mode"] in (ATTR_MODE_DEFAULT, ATTR_MODE_HOME):
            self.mode = self.info["mode"]
        else:
            self.mode = ATTR_MODE_DEFAULT

    def handle_camect_event(self, evt):
        """Handle an event from the Camect API."""
        try:
            if ATTR_MODE in evt["type"]:
                if evt["desc"] in (ATTR_MODE_DEFAULT, ATTR_MODE_HOME):
                    if self.mode in evt["desc"]:
                        # Camect sends a mode change whenever the user has
                        # configured a scheduled change in the Hub's alert
                        # configuration, however the mode itself doesn't
                        # change value.
                        # I don't think it's beneficial to do anything with
                        # these events, so for now, we'll just ignore them.
                        return
                    self.mode = evt["desc"]
                    for modeswitch in self.modeswitch:
                        modeswitch.schedule_update_ha_state()
                else:
                    _LOGGER.warning(
                        "Received mode change event to unknown mode: %s", evt["desc"]
                    )
            elif ATTR_ALERT in evt["type"]:
                for cam in self.cameras:
                    if evt["cam_id"] in cam.device_id:
                        cam.last_motion = datetime.now()
                        cam.last_detected_obj = evt["detected_obj"] or ATTR_UNKNOWN_OBJ
                        cam.schedule_update_ha_state()
                        for motionsensor in cam.motion_sensor:
                            motionsensor.schedule_update_ha_state()
                self.fire_camera_event(ATTR_ALERT, evt)
            elif ATTR_CAM_OFFLINE in evt["type"]:
                _LOGGER.info(
                    "Camera %s (ID %s) went offline", evt["cam_name"], evt["cam_id"]
                )
                for cam in self.cameras:
                    if evt["cam_id"] in cam.device_id:
                        cam.offline = True
                        cam.schedule_update_ha_state()
                self.fire_camera_event(ATTR_CAM_OFFLINE, evt)
            elif ATTR_CAM_ONLINE in evt["type"]:
                _LOGGER.info(
                    "Camera %s (ID %s) came online", evt["cam_name"], evt["cam_id"]
                )
                for cam in self.cameras:
                    if evt["cam_id"] in cam.device_id:
                        cam.offline = False
                        cam.schedule_update_ha_state()
                self.fire_camera_event(ATTR_CAM_ONLINE, evt)
            else:
                _LOGGER.warning("Got an unhandled event type from Camect: %s", str(evt))
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception(
                "Unknown error receiving event: %s. Error was: %s", str(evt), str(ex)
            )

    def fire_camera_event(self, evt_type: str, evt):
        """Fire an event when there's a camera alert."""
        # Might not need this later
        if evt["cam_id"] is not None:
            cam_id = f"{self.id}_{evt['cam_id']}"
            cam_entity_id = f"{camera.DOMAIN}.{cam_id}"
        else:
            cam_id = self.id
            cam_entity_id = self.entity_id

        data = {
            # CONF_ID: self.config_entry.entry_id,
            # ATTR_ENTITY_ID: cam_entity_id,
            ATTR_DEVICE_ID: cam_entity_id,
            CONF_TYPE: evt_type,
            ATTR_RAW_DATA: evt,
        }
        _LOGGER.info("Firing camera event to bus: %s", str(data))
        self.hass.bus.async_fire(ATTR_CAMECT_EVENT, data)
        # self.log_event(
        #     cam_entity_id,
        #     "{} Motion Alert".format(evt["cam_name"]),
        #     "Camera {} detected a {}".format(evt["cam_name"], evt["detected_obj"]),
        # )

    def log_event(self, entity_id, name, message) -> None:
        """Add an entry to the logbook."""
        data = {LOGBOOK_ENTRY_NAME: name, LOGBOOK_ENTRY_MESSAGE: message}
        data[LOGBOOK_ENTRY_DOMAIN] = DOMAIN
        if entity_id is not None:
            data[LOGBOOK_ENTRY_ENTITY_ID] = entity_id
        self.hass.bus.async_fire(EVENT_LOGBOOK_ENTRY, data)


async def _update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle ConfigEntry options update."""
    await hass.config_entries.async_reload(entry.entry_id)


def create_config_flow(hass: HomeAssistant, host: str) -> None:
    """Start a config flow."""
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={"host": host},
        )
    )
