"""Config flow for YIWH Calendar integration."""
from __future__ import annotations

from typing import Any
import voluptuous as vol
import logging
from functools import partial

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError

from . import DOMAIN
from .scraper import YIWHScraper

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({})

def _validate_connection(scraper: YIWHScraper) -> tuple[list, list]:
    """Run the scraper in a separate thread."""
    return scraper.scrape_calendar()

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    _LOGGER.debug("Starting validation of YIWH Calendar input")
    scraper = YIWHScraper()
    
    try:
        _LOGGER.debug("Attempting to scrape calendar")
        # Run the blocking scraper in an executor
        candle_lighting, havdalah = await hass.async_add_executor_job(
            _validate_connection, scraper
        )
        
        if not candle_lighting and not havdalah:
            _LOGGER.error("No calendar events found in the response")
            raise CannotConnect("No calendar events found")
            
        _LOGGER.info("Successfully validated calendar connection")
        _LOGGER.debug("Found %d candle lighting times and %d havdalah times",
                     len(candle_lighting), len(havdalah))
        
    except ConnectionError as error:
        _LOGGER.error("Connection error: %s", str(error))
        raise CannotConnect(str(error)) from error
    except Exception as error:
        _LOGGER.exception("Unexpected error during calendar validation")
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
                _LOGGER.error("Connection failed: %s", str(error))
                errors["base"] = "cannot_connect"
            except UnknownError as error:
                _LOGGER.exception("Unknown error occurred")
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

