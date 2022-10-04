"""The Camect integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr

from .camecthub import CamectHub
from .const import ATTR_CAMECT_MAKE, ATTR_CAMECT_MODEL, DOMAIN

PLATFORMS: list[Platform] = [Platform.CAMERA, Platform.SWITCH, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Camect integration from a config entry."""

    hub = CamectHub(hass, entry)
    if not await hub.async_initialize_hub(hass):
        return False

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={
            (DOMAIN, hub.id),
        },
        manufacturer=ATTR_CAMECT_MAKE,
        name=hub.info["name"],
        model=ATTR_CAMECT_MODEL,
        sw_version="1.0",
    )

    await hass.config_entries.async_forward_entry_setups(entry, [Platform.CAMERA])
    await hass.config_entries.async_forward_entry_setups(entry, [Platform.SWITCH])
    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform.BINARY_SENSOR]
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
