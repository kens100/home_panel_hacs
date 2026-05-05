"""Constants for the home_panel_hacs integration."""
import voluptuous as vol
import homeassistant.helpers.config_validation as cv

DOMAIN = "home_panel_hacs"
CONF_NAME = "name"
DEFAULT_NAME = "Home Panel HACS"

CONF_TEMPERATURE_TOPIC = "temperature_topic"
CONF_HUMIDITY_TOPIC = "humidity_topic"
CONF_DOOR_SIGNAL_TOPIC = "door_signal_topic"
CONF_DOOR_STATE_TOPIC = "door_state_topic"

DEFAULT_TEMPERATURE_TOPIC = "home_panel/temperature"
DEFAULT_HUMIDITY_TOPIC = "home_panel/humidity"
DEFAULT_DOOR_SIGNAL_TOPIC = "home_panel/door_signal"
DEFAULT_DOOR_STATE_TOPIC = "home_panel/door_state"

CONFIG_SCHEMA = vol.Schema({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_TEMPERATURE_TOPIC, default=DEFAULT_TEMPERATURE_TOPIC): cv.string,
    vol.Optional(CONF_HUMIDITY_TOPIC, default=DEFAULT_HUMIDITY_TOPIC): cv.string,
    vol.Optional(CONF_DOOR_SIGNAL_TOPIC, default=DEFAULT_DOOR_SIGNAL_TOPIC): cv.string,
    vol.Optional(CONF_DOOR_STATE_TOPIC, default=DEFAULT_DOOR_STATE_TOPIC): cv.string,
})
