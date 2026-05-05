"""Config flow for Home Panel HACS integration."""
import logging
import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback

from .const import DOMAIN, DEFAULT_NAME

_LOGGER = logging.getLogger(__name__)

class HomePanelHacsConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Home Panel HACS."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.host = None
        self.port = 80
        self.name = DEFAULT_NAME

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            self.host = user_input[CONF_HOST]
            return self.async_create_entry(title=self.name, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_HOST): str,
            }),
            errors=errors
        )

    async def async_step_zeroconf(self, discovery_info: zeroconf.ZeroconfServiceInfo):
        """Handle zeroconf discovery."""
        self.host = discovery_info.host
        if discovery_info.port:
            self.port = discovery_info.port
        if discovery_info.name:
            self.name = discovery_info.name.split(".")[0]

        _LOGGER.info("Discovered HomePanel via mDNS at %s:%s", self.host, self.port)

        # set unique id to the host or a mac address if provided.
        await self.async_set_unique_id(self.host)
        self._abort_if_unique_id_configured()

        self.context.update({
            "title_placeholders": {"name": self.name}
        })

        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(self, user_input=None):
        """Confirm discovery and configure MQTT on the device."""
        errors = {}

        if user_input is not None:
            mqtt_server = user_input.get("mqtt_server")

            # Send HTTP request to ESP32 to configure MQTT
            try:
                url = f"http://{self.host}:{self.port}/api/config"
                payload = {
                    "mqtt_server": mqtt_server,
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=payload, timeout=10) as resp:
                        if resp.status == 200:
                            _LOGGER.info("Successfully configured HomePanel MQTT server to %s.", mqtt_server)
                            data = {
                                CONF_HOST: self.host,
                                "mqtt_server": mqtt_server
                            }
                            return self.async_create_entry(title=self.name, data=data)
                        else:
                            _LOGGER.error("Failed to configure device, HTTP status: %s", resp.status)
                            errors["base"] = "cannot_connect"
            except Exception as e:
                _LOGGER.error("Error communicating with HomePanel: %s", e)
                errors["base"] = "cannot_connect"

        schema = vol.Schema({
            vol.Required("mqtt_server", default=""): str,
        })

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": self.name},
            data_schema=schema,
            errors=errors
        )
