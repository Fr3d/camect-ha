"""Config flow for Camect integration."""
from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import camect
import requests
import urllib3
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_PORT, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import DOMAIN

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST, default="local.home.camect.com"): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_PORT, default="443"): str,
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host

    async def authenticate(self, username: str, password: str) -> bool:
        """Test if we can authenticate with the host."""
        return True


def resolve_local_camect_hostname() -> str:
    """
    Detect the hostname of the local Camect Hub(s).

    Camect's cloud service will return a list of all Camect Hubs
    running locally, so we'll pick the first one if one is found.
    If a user has multiple, they're likely a power user and can
    manually enter an alternate hostname if they want multiple Hubs in HomeAssistant.
    """
    resp = requests.get("https://local.home.camect.com/list.json", verify=False)
    if resp.status_code != 200 or "null" in str(resp.content):
        # The list API returns the literal text "null" if no local Camect Hubs exist
        raise Exception(
            f"Failed to detect 'local_https_url' for Camect Hub: [{resp.status_code}]"
        )
    json = resp.json()
    if json[0]["url"] is not None:
        return json[0]["url"]
    raise Exception(f"Failed to find first URL object in JSON response: {json}")


def prepend_scheme(url: str) -> str:
    """Add URL scheme to the URL passed in if not present."""
    urlobj = urlparse(url)
    if not urlobj.scheme:
        url = "https://" + url
    return url


def validate_hostname(url: str) -> str:
    """Validate and strip some bits that users might add if they copied the URL from a browser's address bar."""
    return str(urlparse(prepend_scheme(url)).hostname)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    hub_hostname = validate_hostname(data["host"])

    if hub_hostname in ("local.home.camect.com", "home.camect.com"):
        # To be helpful, we catch users using home.camect.com too because they're likely used to using that in a browser
        resolved_hostname = await hass.async_add_executor_job(
            resolve_local_camect_hostname
        )
        hub_hostname = validate_hostname(resolved_hostname)

    hub = await hass.async_add_executor_job(
        camect.Hub,
        f"{hub_hostname}:{data['port']}",
        data["username"],
        data["password"],
    )
    info = await hass.async_add_executor_job(hub.get_info)

    # Return info that you want to store in the config entry.
    return {"title": info["name"], "id": info["id"], "host": hub_hostname}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Camect."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            info = await validate_input(self.hass, user_input)
            await self.async_set_unique_id(info["id"])
            self._abort_if_unique_id_configured()
            user_input["host"] = info["host"]
        except requests.exceptions.Timeout as ex:
            errors["base"] = "cannot_connect"
            _LOGGER.exception("Timeout exception: %s", str(ex))
        except requests.exceptions.RequestException as ex:
            errors["base"] = "cannot_connect"
            _LOGGER.exception("Generic request exception: %s", str(ex))
        except Exception as ex:  # pylint: disable=broad-except
            exs = str(ex)
            if "401" in exs:
                errors["base"] = "invalid_auth"
                _LOGGER.exception("401 invalid auth exception: %s", str(ex))
            else:
                _LOGGER.exception("Unexpected exception: %s", str(ex))
                errors["base"] = "unknown"
        else:
            return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
