"""Platform for fan integration."""
from typing import Any, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PRESET_MODES, PRESET_MODE_OFF, PRESET_MODE_COOL, PRESET_MODE_HEAT_LOW, PRESET_MODE_HEAT_HIGH
from . import ZinguoDataUpdateCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Zinguo fan based on a config entry."""
    coordinator: ZinguoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([ZinguoFan(coordinator)], True)

class ZinguoFan(FanEntity):
    """Representation of a Zinguo fan with heating."""
    
    def __init__(self, coordinator):
        """Initialize the fan."""
        self._coordinator = coordinator
        self._attr_name = f"{coordinator.name} Fan"
        self._attr_unique_id = f"{coordinator.mac}_fan"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, coordinator.mac)},
            "name": coordinator.name,
            "manufacturer": "Zinguo",
            "model": "Smart Bathroom Fan",
        }
        
        # Fan features
        self._attr_supported_features = (
            FanEntityFeature.PRESET_MODE |
            FanEntityFeature.TURN_ON |
            FanEntityFeature.TURN_OFF
        )
        
        # Preset modes
        self._attr_preset_modes = PRESET_MODES
    
    @property
    def is_on(self):
        """Return true if fan is on."""
        if self._coordinator.data:
            wind_on = self._coordinator.data.get("windSwitch") == 1
            heater1_on = self._coordinator.data.get("warmingSwitch1") == 1
            heater2_on = self._coordinator.data.get("warmingSwitch2") == 1
            return wind_on or heater1_on or heater2_on
        return False
    
    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode."""
        if not self._coordinator.data:
            return PRESET_MODE_OFF
            
        wind_on = self._coordinator.data.get("windSwitch") == 1
        heater1_on = self._coordinator.data.get("warmingSwitch1") == 1
        heater2_on = self._coordinator.data.get("warmingSwitch2") == 1
        
        if not wind_on:
            return PRESET_MODE_OFF
        elif heater1_on:
            return PRESET_MODE_HEAT_LOW
        elif heater2_on:
            return PRESET_MODE_HEAT_HIGH
        else:
            return PRESET_MODE_COOL
    
    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        if preset_mode is None:
            # Default to cool mode
            preset_mode = PRESET_MODE_COOL
        
        await self.async_set_preset_mode(preset_mode)
    
    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        payload = {
            "warmingSwitch1": 0,
            "warmingSwitch2": 0,
            "windSwitch": 0,
            "turnOffAll": 1
        }
        await self._coordinator.send_control_command(payload)
    
    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        if preset_mode == PRESET_MODE_OFF:
            await self.async_turn_off()
        elif preset_mode == PRESET_MODE_COOL:
            payload = {
                "warmingSwitch1": 0,
                "warmingSwitch2": 0,
                "windSwitch": 1,
                "turnOffAll": 0
            }
        elif preset_mode == PRESET_MODE_HEAT_LOW:
            payload = {
                "warmingSwitch1": 1,
                "warmingSwitch2": 0,
                "windSwitch": 1,
                "turnOffAll": 0
            }
        elif preset_mode == PRESET_MODE_HEAT_HIGH:
            payload = {
                "warmingSwitch1": 0,
                "warmingSwitch2": 1,
                "windSwitch": 1,
                "turnOffAll": 0
            }
        else:
            raise ValueError(f"Invalid preset mode: {preset_mode}")
        
        await self._coordinator.send_control_command(payload)
    
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
