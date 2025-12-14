"""Config flow for YIWH Calendar integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN
from .hebcal import HebCal

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({})

def _validate_connection(scraper: HebCal) -> tuple[list, list]:
    """Run the scraper in a separate thread."""
    return scraper.scrape()

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    _LOGGER.debug("YIWeHa: Starting validation of YIWeHa Calendar input")
    scraper = HebCal("06117")
    
    try:
        _LOGGER.debug("YIWeHa: Attempting to scrape calendar")
        # Run the blocking scraper in an executor
        candle_lighting, havdalah = await hass.async_add_executor_job(
            _validate_connection, scraper
        )
        
        if not candle_lighting and not havdalah:
            _LOGGER.error("YIWeHa: No calendar events found in the response")
            raise CannotConnect("YIWeHa: No calendar events found")
            
        _LOGGER.debug("YIWeHa: Successfully validated calendar connection")
        _LOGGER.debug("YIWeHa: Found %d candle lighting times and %d havdalah times",
                     len(candle_lighting), len(havdalah))
        
    except ConnectionError as error:
        _LOGGER.error("YIWeHa: Connection error: %s", str(error))
        raise CannotConnect(str(error)) from error
    except Exception as error:
        _LOGGER.exception("YIWeHa: Unexpected error during calendar validation")
        raise UnknownError from error

    return {"title": "Young Israel West Hartford Calendar"}

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for YIWH Calendar."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnect as error:
                _LOGGER.error("YIWeHa: Connection failed: %s", str(error))
                errors["base"] = "cannot_connect"
            except UnknownError as error:
                _LOGGER.exception("YIWeHa: Unknown error occurred")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class UnknownError(HomeAssistantError):
    """Error to indicate an unknown error occurred."""

