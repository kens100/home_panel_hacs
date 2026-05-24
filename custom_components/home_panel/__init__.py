"""The Home Panel HACS integration."""
import logging

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import mqtt
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_TEMPERATURE_TOPIC,
    CONF_HUMIDITY_TOPIC,
    CONF_DOOR_SIGNAL_TOPIC,
    CONF_DOOR_STATE_TOPIC,
    DEFAULT_TEMPERATURE_TOPIC,
    DEFAULT_HUMIDITY_TOPIC,
    DEFAULT_DOOR_SIGNAL_TOPIC,
    DEFAULT_DOOR_STATE_TOPIC,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor"]

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Home Panel HACS integration."""
    _LOGGER.info("Initializing Home Panel HACS")

    async def set_state_service(call):
        """Handle the service call to set home panel state."""
        state = call.data.get("state", "unknown")
        _LOGGER.info("Home Panel state changed to: %s", state)
        hass.bus.async_fire(f"{DOMAIN}_state_update", {"state": state})
        hass.states.async_set(f"{DOMAIN}.status", state)

    hass.services.async_register(DOMAIN, "set_state", set_state_service)

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Panel from a config entry."""
    _LOGGER.info("Setting up Home Panel from config entry: %s", entry.entry_id)

    name = entry.data.get(CONF_NAME, DOMAIN)
    temperature_topic = entry.data.get(CONF_TEMPERATURE_TOPIC, DEFAULT_TEMPERATURE_TOPIC)
    humidity_topic = entry.data.get(CONF_HUMIDITY_TOPIC, DEFAULT_HUMIDITY_TOPIC)
    door_signal_topic = entry.data.get(CONF_DOOR_SIGNAL_TOPIC, DEFAULT_DOOR_SIGNAL_TOPIC)
    door_state_topic = entry.data.get(CONF_DOOR_STATE_TOPIC, DEFAULT_DOOR_STATE_TOPIC)

    # Initialize data structure for this entry
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "name": name,
        "temperature": None,
        "humidity": None,
        "door_signal": None,
        "door_state": None,
        "door": None,
        "subscriptions": [],
    }

    # Define robust callbacks supporting both old and new HA MQTT signatures
    @callback
    def temperature_message_received(*args, **kwargs):
        """Handle temperature MQTT message."""
        if len(args) == 1:
            msg = args[0]
            payload = getattr(msg, "payload", msg)
        else:
            payload = args[2]

        try:
            value = float(payload)
            hass.data[DOMAIN][entry.entry_id]["temperature"] = value
            async_dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_update_temperature", value)
        except ValueError:
            _LOGGER.warning("Invalid temperature value: %s", payload)

    @callback
    def humidity_message_received(*args, **kwargs):
        """Handle humidity MQTT message."""
        if len(args) == 1:
            msg = args[0]
            payload = getattr(msg, "payload", msg)
        else:
            payload = args[2]

        try:
            value = float(payload.rstrip("%"))
            hass.data[DOMAIN][entry.entry_id]["humidity"] = value
            async_dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_update_humidity", value)
        except ValueError:
            _LOGGER.warning("Invalid humidity value: %s", payload)

    @callback
    def door_signal_message_received(*args, **kwargs):
        """Handle door signal MQTT message."""
        if len(args) == 1:
            msg = args[0]
            payload = getattr(msg, "payload", msg)
        else:
            payload = args[2]

        signal_value = payload.lower()
        hass.data[DOMAIN][entry.entry_id]["door_signal"] = signal_value
        async_dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_update_door_signal", signal_value)
        update_door_state(hass, entry.entry_id)

    @callback
    def door_state_message_received(*args, **kwargs):
        """Handle door state MQTT message."""
        if len(args) == 1:
            msg = args[0]
            payload = getattr(msg, "payload", msg)
        else:
            payload = args[2]

        state_value = payload.lower()
        hass.data[DOMAIN][entry.entry_id]["door_state"] = "on" if state_value == "open" else "off"
        async_dispatcher_send(hass, f"{DOMAIN}_{entry.entry_id}_update_door_state", hass.data[DOMAIN][entry.entry_id]["door_state"])
        update_door_state(hass, entry.entry_id)

    # Subscribe to MQTT topics
    sub1 = await mqtt.async_subscribe(hass, temperature_topic, temperature_message_received)
    sub2 = await mqtt.async_subscribe(hass, humidity_topic, humidity_message_received)
    sub3 = await mqtt.async_subscribe(hass, door_signal_topic, door_signal_message_received)
    sub4 = await mqtt.async_subscribe(hass, door_state_topic, door_state_message_received)

    hass.data[DOMAIN][entry.entry_id]["subscriptions"].extend([sub1, sub2, sub3, sub4])

    # Forward entry setup to platforms
    try:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except AttributeError:
        # Fallback for older Home Assistant versions
        for platform in PLATFORMS:
            hass.async_create_task(
                hass.config_entries.async_forward_entry_setup(entry, platform)
            )

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    try:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    except AttributeError:
        # Fallback for older Home Assistant versions
        import asyncio
        unload_ok = all(
            await asyncio.gather(
                *[
                    hass.config_entries.async_forward_entry_unload(entry, platform)
                    for platform in PLATFORMS
                ]
            )
        )
    
    if unload_ok:
        entry_data = hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry_data and "subscriptions" in entry_data:
            for unsubscribe in entry_data["subscriptions"]:
                unsubscribe()
    
    return unload_ok

def update_door_state(hass: HomeAssistant, entry_id: str):
    """Update combined door state based on available sensors."""
    entry_data = hass.data[DOMAIN][entry_id]
    
    door_state_value = entry_data.get("door_state")
    door_signal_value = entry_data.get("door_signal")

    if door_state_value is not None:
        final_state = door_state_value
        _LOGGER.info("Door state from sensor: %s", door_state_value)
    elif door_signal_value is not None:
        final_state = "on" if door_signal_value == "clicked" else "off"
        _LOGGER.info("Door state from signal: %s", door_signal_value)
    else:
        final_state = "unavailable"

    entry_data["door"] = final_state
    async_dispatcher_send(hass, f"{DOMAIN}_{entry_id}_update_door", final_state)