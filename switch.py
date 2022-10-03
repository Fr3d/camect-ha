"""Support for switches that do things within Camect Hub."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from homeassistant.components import switch
from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_IDENTIFIERS, ATTR_MODE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    ATTR_ALERT_DISABLED,
    ATTR_ALERT_ENABLED,
    ATTR_HUB_MODE,
    ATTR_MODE_DEFAULT,
    ATTR_MODE_HOME,
    ATTR_MODE_REASON,
    DOMAIN,
)

if TYPE_CHECKING:
    from .camecthub import CamectHub
    from .camera import Camera as CamectCamera


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switches within a Camect Hub."""
    hub: CamectHub = hass.data[DOMAIN][config_entry.entry_id]
    new_switches: list[SwitchEntity] = []
    new_switches.append(HubModeSwitch(hub))
    for camect_camera in hub.cameras:
        new_switches.append(CameraAlertSwitch(hub, camect_camera))

    async_add_entities(new_switches)


class CameraAlertSwitch(SwitchEntity):
    """An implementation of a switch within Camect Hub."""

    _attr_entity_category: Literal[EntityCategory.CONFIG]

    def __init__(self, hub: CamectHub, cam: CamectCamera) -> None:
        """Set up a switch within a Camect Hub camera that controls the alert setting for that camera."""
        super().__init__()
        self.hub = hub
        self.cam = cam
        self.entity_id = f"{self.cam.entity_id}_{ATTR_ALERT_DISABLED}"
        cam.alert_switch.append(self)

    @property
    def name(self) -> str:
        """Return the human-friendly name of this switch."""
        return f"{self.cam.name} {ATTR_ALERT_ENABLED}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of this switch."""
        return f"{self.cam.entity_id}_{ATTR_MODE}"

    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.cam.entity_id)},
        }

    @property
    def icon(self) -> str:
        """Return the appropriate MDI icon."""
        return "mdi:bell-cancel" if self.cam.is_alert_disabled else "mdi:bell"

    @property
    def is_on(self) -> bool:
        """Return true if the camera's alerts are enabled."""
        return not self.cam.is_alert_disabled

    @property
    def available(self) -> bool:
        """Return True if the camera is available."""
        return self.cam.available

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable alerts for this camera."""
        await self.hass.async_add_executor_job(
            self.hub.api.enable_alert, self.cam.device_id, ATTR_MODE_REASON
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable alerts for this camera."""
        await self.hass.async_add_executor_job(
            self.hub.api.disable_alert, self.cam.device_id, ATTR_MODE_REASON
        )


class HubModeSwitch(SwitchEntity):
    """
    An implementation of a switch within Camect Hub.

    Control the mode (either "Default" (switch is off) or "Home" (switch is on)).
    """

    def __init__(self, hub: CamectHub) -> None:
        """Initialize a switch within by Camect Hub."""
        super().__init__()
        self.hub = hub
        self.entity_id = f"{switch.DOMAIN}.{self.hub.id}_{ATTR_MODE}"
        hub.modeswitch.append(self)

    async def async_update(self) -> None:
        """Ensure the mode is kept up-to-date in case we don't receive an event of it being changed outside of HA."""
        await self.hub.update_hub_info()
        await self.hub.update_mode_property()

    @property
    def device_info(self) -> DeviceInfo:
        """Information about this entity/device."""
        return {
            ATTR_IDENTIFIERS: {(DOMAIN, self.hub.id)},
        }

    @property
    def name(self) -> str:
        """Return the human-friendly name of this switch."""
        return f"{self.hub.name} {ATTR_HUB_MODE}"

    @property
    def unique_id(self) -> str:
        """Return the unique ID of this switch."""
        return f"{self.hub.id}_{ATTR_MODE}"

    @property
    def is_on(self) -> bool:
        """Return true if the switch is on."""
        return self.hub.mode in ATTR_MODE_DEFAULT

    @property
    def icon(self) -> str:
        """Return the closest MDI icons to what the Camect Hub v2 UI displays."""
        return "mdi:shield-check" if self.hub.mode in ATTR_MODE_DEFAULT else "mdi:home"

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Set the mode to Default."""
        await self.hass.async_add_executor_job(
            self.hub.api.set_mode, ATTR_MODE_DEFAULT, ATTR_MODE_REASON
        )
        await self.hub.update_mode_property()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Set the mode to Home."""
        await self.hass.async_add_executor_job(
            self.hub.api.set_mode, ATTR_MODE_HOME, ATTR_MODE_REASON
        )
        await self.hub.update_mode_property()
