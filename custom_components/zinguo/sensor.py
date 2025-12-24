"""Platform for sensor integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from . import ZinguoDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zinguo sensors based on a config entry."""
    coordinator: ZinguoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    sensors = [
        TemperatureSensor(coordinator),
        OnlineStatusSensor(coordinator),
    ]
    
    async_add_entities(sensors, True)

class TemperatureSensor(SensorEntity):
    """Representation of a Zinguo temperature sensor."""
    
    def __init__(self, coordinator):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._attr_name = f"{coordinator.name} Temperature"
        self._attr_unique_id = f"{coordinator.mac}_temperature"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.mac)},
            "name": coordinator.name,
            "manufacturer": "Zinguo",
            "model": "Smart Bathroom Fan",
        }
        self._attr_native_unit_of_measurement = "°C"
        self._attr_device_class = "temperature"
    
    @property
    def native_value(self):
        """Return the temperature value."""
        if self._coordinator.data:
            temp = self._coordinator.data.get("temperature")
            if temp is not None:
                try:
                    return float(temp)
                except (ValueError, TypeError):
                    return None
        return None
    
    @property
    def available(self):
        """Return if entity is available."""
        return self._coordinator.data is not None
    
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )
    
    async def async_update(self):
        """Update the entity."""
        await self._coordinator.async_request_refresh()

class OnlineStatusSensor(SensorEntity):
    """Representation of a Zinguo online status sensor."""
    
    def __init__(self, coordinator):
        """Initialize the sensor."""
        self._coordinator = coordinator
        self._attr_name = f"{coordinator.name} Online Status"
        self._attr_unique_id = f"{coordinator.mac}_online"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.mac)},
            "name": coordinator.name,
            "manufacturer": "Zinguo",
            "model": "Smart Bathroom Fan",
        }
        self._attr_device_class = None
    
    @property
    def native_value(self):
        """Return the online status."""
        if self._coordinator.data:
            online = self._coordinator.data.get("online")
            return "Online" if online == 1 else "Offline"
        return "Unknown"
    
    @property
    def available(self):
        """Return if entity is available."""
        return True
    
    async def async_added_to_hass(self):
        """When entity is added to hass."""
        self.async_on_remove(
            self._coordinator.async_add_listener(self.async_write_ha_state)
        )
    
    async def async_update(self):
        """Update the entity."""
        await self._coordinator.async_request_refresh()
