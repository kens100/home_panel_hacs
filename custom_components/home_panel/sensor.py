"""Support for Home Panel sensors."""
import logging
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Home Panel sensors from config entry."""
    entry_data = hass.data[DOMAIN][entry.entry_id]
    name = entry_data["name"]

    entities = [
        HomePanelTemperatureSensor(hass, entry, name),
        HomePanelHumiditySensor(hass, entry, name),
        HomePanelDoorSignalSensor(hass, entry, name),
    ]

    async_add_entities(entities)


class HomePanelBaseSensor(SensorEntity):
    """Base class for Home Panel sensors."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_name: str, name_suffix: str, key: str) -> None:
        """Initialize the sensor."""
        self._hass = hass
        self._entry = entry
        self._entry_name = entry_name
        self._key = key
        
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name_suffix
        self.entity_id = f"sensor.home_panel_{key}"

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.unique_id or self._entry.entry_id)},
            "name": self._entry_name,
            "manufacturer": "kens100",
            "model": "Home Panel ESP32",
            "sw_version": "1.0.0",
        }

    @property
    def native_value(self):
        """Return the state of the sensor."""
        return self._hass.data[DOMAIN][self._entry.entry_id].get(self._key)

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{DOMAIN}_{self._entry.entry_id}_update_{self._key}",
                self._async_update_state,
            )
        )

    @callback
    def _async_update_state(self, value) -> None:
        """Update the sensor state."""
        self._hass.data[DOMAIN][self._entry.entry_id][self._key] = value
        self.async_write_ha_state()


class HomePanelTemperatureSensor(HomePanelBaseSensor):
    """Temperature sensor."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = "°C"
    _attr_icon = "mdi:thermometer"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_name: str) -> None:
        """Initialize temperature sensor."""
        super().__init__(hass, entry, entry_name, "Temperature", "temperature")


class HomePanelHumiditySensor(HomePanelBaseSensor):
    """Humidity sensor."""

    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_native_unit_of_measurement = "%"
    _attr_icon = "mdi:water-percent"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_name: str) -> None:
        """Initialize humidity sensor."""
        super().__init__(hass, entry, entry_name, "Humidity", "humidity")


class HomePanelDoorSignalSensor(HomePanelBaseSensor):
    """Door signal sensor."""

    _attr_icon = "mdi:gesture-tap-button"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, entry_name: str) -> None:
        """Initialize door signal sensor."""
        super().__init__(hass, entry, entry_name, "Door Signal", "door_signal")
