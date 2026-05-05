"""The Home Panel HACS integration."""
import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType
from homeassistant.config_entries import ConfigEntry
from homeassistant.components import mqtt

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

DATA_CONFIG = f"{DOMAIN}_config"
DATA_DOOR_STATE = f"{DOMAIN}_door_state"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Home Panel HACS integration."""
    _LOGGER.info("Initializing Home Panel HACS")

    hass.data.setdefault(DATA_CONFIG, {})
    hass.data.setdefault(DATA_DOOR_STATE, {"signal": None, "state": None})

    async def set_state_service(call):
        """Handle the service call to set home panel state."""
        state = call.data.get("state", "unknown")
        _LOGGER.info("Home Panel state changed to: %s", state)
        hass.bus.async_fire(f"{DOMAIN}_state_update", {"state": state})
        hass.states.async_set("home_panel_hacs.status", state)

    hass.services.async_register(DOMAIN, "set_state", set_state_service)

    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Home Panel from a config entry."""
    _LOGGER.info("Setting up Home Panel from config entry")

    name = entry.data.get(CONF_NAME, DOMAIN)
    temperature_topic = entry.data.get(CONF_TEMPERATURE_TOPIC, DEFAULT_TEMPERATURE_TOPIC)
    humidity_topic = entry.data.get(CONF_HUMIDITY_TOPIC, DEFAULT_HUMIDITY_TOPIC)
    door_signal_topic = entry.data.get(CONF_DOOR_SIGNAL_TOPIC, DEFAULT_DOOR_SIGNAL_TOPIC)
    door_state_topic = entry.data.get(CONF_DOOR_STATE_TOPIC, DEFAULT_DOOR_STATE_TOPIC)

    hass.data[DATA_CONFIG] = {
        "name": name,
        "temperature_topic": temperature_topic,
        "humidity_topic": humidity_topic,
        "door_signal_topic": door_signal_topic,
        "door_state_topic": door_state_topic,
    }

    sub1 = await mqtt.async_subscribe(hass, temperature_topic, temperature_message_received)
    sub2 = await mqtt.async_subscribe(hass, humidity_topic, humidity_message_received)
    sub3 = await mqtt.async_subscribe(hass, door_signal_topic, door_signal_message_received)
    sub4 = await mqtt.async_subscribe(hass, door_state_topic, door_state_message_received)

    hass.data.setdefault(f"{DOMAIN}_subscriptions", [])
    hass.data[f"{DOMAIN}_subscriptions"].extend([sub1, sub2, sub3, sub4])

    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    subs = hass.data.get(f"{DOMAIN}_subscriptions", [])
    for sub_unsubscribe in subs:
        sub_unsubscribe()
    hass.data.pop(f"{DOMAIN}_subscriptions", None)
    
    return True


def temperature_message_received(hass, topic, payload, qos):
    """Handle temperature MQTT message."""
    try:
        value = float(payload)
        config = hass.data[DATA_CONFIG]
        name = config["name"]
        hass.states.async_set(
            "sensor.home_panel_temperature",
            value,
            {"unit_of_measurement": "°C", "friendly_name": f"{name} Temperature", "icon": "mdi:thermometer"},
        )
    except ValueError:
        _LOGGER.warning("Invalid temperature value: %s", payload)


def humidity_message_received(hass, topic, payload, qos):
    """Handle humidity MQTT message."""
    try:
        value = float(payload.rstrip("%"))
        config = hass.data[DATA_CONFIG]
        name = config["name"]
        hass.states.async_set(
            "sensor.home_panel_humidity",
            value,
            {"unit_of_measurement": "%", "friendly_name": f"{name} Humidity", "icon": "mdi:water-percent"},
        )
    except ValueError:
        _LOGGER.warning("Invalid humidity value: %s", payload)


def door_signal_message_received(hass, topic, payload, qos):
    """Handle door signal MQTT message."""
    config = hass.data[DATA_CONFIG]
    name = config["name"]

    signal_value = payload.lower()
    hass.data[DATA_DOOR_STATE]["signal"] = signal_value

    hass.states.async_set(
        "sensor.home_panel_door_signal",
        signal_value,
        {"friendly_name": f"{name} Door Signal", "icon": "mdi:gesture-tap-button"},
    )

    update_door_state(hass)


def door_state_message_received(hass, topic, payload, qos):
    """Handle door state MQTT message."""
    config = hass.data[DATA_CONFIG]
    name = config["name"]

    state_value = payload.lower()
    hass.data[DATA_DOOR_STATE]["state"] = state_value

    hass.states.async_set(
        "binary_sensor.home_panel_door_state",
        "on" if state_value == "open" else "off",
        {"friendly_name": f"{name} Door State", "device_class": "door"},
    )

    update_door_state(hass)


def update_door_state(hass):
    """Update door state based on available sensors."""
    config = hass.data[DATA_CONFIG]
    name = config["name"]
    door_data = hass.data[DATA_DOOR_STATE]

    door_state_value = door_data.get("state")
    door_signal_value = door_data.get("signal")

    if door_state_value is not None:
        final_state = "on" if door_state_value == "open" else "off"
        _LOGGER.info("Door state from sensor: %s", door_state_value)
    elif door_signal_value is not None:
        final_state = "on" if door_signal_value == "clicked" else "off"
        _LOGGER.info("Door state from signal: %s", door_signal_value)
    else:
        final_state = "unavailable"

    hass.states.async_set(
        "binary_sensor.home_panel_door",
        final_state,
        {"friendly_name": f"{name} Door", "device_class": "door"},
    )