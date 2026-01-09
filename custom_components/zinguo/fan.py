"""Fan platform for Zinguo."""
import logging
from typing import Any, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util.percentage import (
    ordered_list_item_to_percentage,
    percentage_to_ordered_list_item,
)

from .const import DOMAIN
from .coordinator import ZinguoDataUpdateCoordinator # Import coordinator type

_LOGGER = logging.getLogger(__name__)

PRESET_MODES = ["Off", "Warming 1", "Warming 2", "Wind"]

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Zinguo fan platform."""
    # 从 hass.data 中获取协调器实例
    coordinator: ZinguoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    # 从协调器的 data 中获取设备信息
    device_info = coordinator.data # Assuming single device per entry

    # 创建风扇实体，传入协调器对象
    entity = ZinguoFan(coordinator, device_info)
    async_add_entities([entity])


class ZinguoFan(CoordinatorEntity, FanEntity):
    """Representation of a Zinguo fan."""

    def __init__(self, coordinator: ZinguoDataUpdateCoordinator, device_info: dict[str, Any]):
        """Initialize the fan."""
        super().__init__(coordinator)
        self._device_info = device_info
        self._attr_unique_id = f"{device_info['id']}_fan" # Construct unique_id
        self._attr_name = "Zinguo Fan"
        self._attr_preset_modes = PRESET_MODES
        self._attr_supported_features = FanEntityFeature.PRESET_MODE
        self._attr_device_info = {
            "identifiers": {(DOMAIN, device_info["id"])},
            "name": coordinator.name, # Use coordinator's determined name
            "manufacturer": "Zinguo",
            "model": device_info.get("device_model", "Unknown Model"),
            "sw_version": device_info.get("firmware_version", "Unknown Version"),
        }
        # Initialize state attributes
        self._current_preset_mode = "Off"


    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # 根据协调器的最新数据更新风扇状态
        device_status = self.coordinator.data # Get fresh data
        status_details = device_status.get('status', {}) # Adjust path if necessary

        # Determine current preset mode based on device status
        warming1_on = status_details.get('warming_switch_1', False)
        warming2_on = status_details.get('warming_switch_2', False)
        wind_on = status_details.get('wind_switch', False)

        if warming1_on and not warming2_on and not wind_on:
            self._current_preset_mode = "Warming 1"
        elif warming2_on and not warming1_on and not wind_on:
            self._current_preset_mode = "Warming 2"
        elif wind_on and not warming1_on and not warming2_on:
            self._current_preset_mode = "Wind"
        else:
            self._current_preset_mode = "Off" # Default or Off state

        self._attr_preset_mode = self._current_preset_mode
        self.async_write_ha_state() # Notify HA of state change


    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        _LOGGER.debug("Setting preset mode to: %s", preset_mode)
        if preset_mode not in PRESET_MODES:
             _LOGGER.warning("Invalid preset mode: %s", preset_mode)
             return

        # Define the control commands needed for each preset
        control_commands = {
            "Off": {"warming_switch_1": False, "warming_switch_2": False, "wind_switch": False},
            "Warming 1": {"warming_switch_1": True, "warming_switch_2": False, "wind_switch": False},
            "Warming 2": {"warming_switch_1": False, "warming_switch_2": True, "wind_switch": False},
            "Wind": {"warming_switch_1": False, "warming_switch_2": False, "wind_switch": True},
        }

        command_to_send = control_commands.get(preset_mode, {})
        if command_to_send:
            # 直接使用协调器发送控制命令
            await self.coordinator.send_control_command(command_to_send)
            # 状态更新由协调器的强制刷新处理
            # self._current_preset_mode = preset_mode # Don't set it here, let _handle_coordinator_update update it after refresh
        else:
            _LOGGER.warning("No command defined for preset mode: %s", preset_mode)


    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        # If no specific preset is given, default to one (e.g., Wind or Warming 1)
        target_preset = preset_mode or self.preset_modes[1] # Default to first non-off mode
        await self.async_set_preset_mode(target_preset)


    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        await self.async_set_preset_mode("Off")
