"""Platform for fan integration."""
from typing import Any, Optional

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_OFF,
    STATE_ON,
    Platform, # 导入 Platform 以确保 entity_id 构建方式的一致性
)

from .const import DOMAIN
from .coordinator import ZinguoDataUpdateCoordinator
from .api import ZinguoAPI # 确保导入 API 类
import logging

_LOGGER = logging.getLogger(__name__)

# 定义预设模式
PRESET_MODE_OFF = "off"
PRESET_MODE_COOLING = "cooling" # 或者叫 "wind"
PRESET_MODE_WARMING_LOW = "warming_low" # 暖风低档
PRESET_MODE_WARMING_HIGH = "warming_high" # 暖风高档

class ZinguoFan(FanEntity):
    """Representation of a Zinguo fan."""

    def __init__(self, coordinator: ZinguoDataUpdateCoordinator, device_info: dict, api: ZinguoAPI):
        """Initialize the fan."""
        self.coordinator = coordinator
        self._device_info = device_info
        self._api = api # 保留 API 实例引用
        # 修改 unique_id，使其与最佳实践下的 switch unique_id 保持一致
        # 假设 switch.py 中的 unique_id 是 f"{device_info['id']}_warming_switch_1"
        # 那么这里的 fan unique_id 应该也类似，但为了区别，加上 fan 标识
        # 例如，如果 switch 的 unique_id 是 device_id_warming_switch_1
        # 那么 fan 的 unique_id 可以是 device_id_fan
        self._attr_unique_id = f"{device_info['id']}_fan"
        self._attr_name = device_info.get("name", "Zinguo Fan")
        self._attr_available = True
        # 支持预设模式
        self._attr_supported_features = FanEntityFeature.PRESET_MODE
        # 更新预设模式
        self._attr_preset_modes = [
            PRESET_MODE_OFF,
            PRESET_MODE_COOLING,
            PRESET_MODE_WARMING_LOW,
            PRESET_MODE_WARMING_HIGH
        ]
        # 初始化状态
        self._state = False # 默认关闭
        self._preset_mode = PRESET_MODE_OFF
        # 假设初始状态可以通过设备信息获取，或者从协调器获取
        # self._update_state_from_coordinator()

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        # 根据协调器状态或设备在线状态判断
        return self.coordinator.last_update_success and self._device_info.get('online', True)

    @property
    def preset_mode(self) -> Optional[str]:
        """Return the current preset mode."""
        return self._preset_mode

    @property
    def is_on(self) -> bool:
        """Return true if the entity is on."""
        return self._state

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        # 当协调器更新数据时，这里需要根据最新的设备状态来更新风扇自身的状态
        # 这是一个复杂点，需要根据 API 返回的状态来推断风扇当前模式
        # 假设设备信息中包含了各个开关的状态
        device_data = self.coordinator.data.get(self._device_info['id'])
        if device_data:
            # 示例：假设 API 返回的设备状态中有 'warmingSwitch1', 'warmingSwitch2', 'wind'
            # 需要根据这些开关的状态反推出风扇的 preset_mode 和 is_on
            switch1_state = device_data.get('warmingSwitch1', STATE_OFF)
            switch2_state = device_data.get('warmingSwitch2', STATE_OFF)
            wind_state = device_data.get('wind', STATE_OFF)

            if wind_state == STATE_ON:
                new_preset = PRESET_MODE_COOLING
                new_state = True
            elif switch1_state == STATE_ON and switch2_state == STATE_ON:
                new_preset = PRESET_MODE_WARMING_HIGH
                new_state = True
            elif switch1_state == STATE_ON and switch2_state == STATE_OFF:
                new_preset = PRESET_MODE_WARMING_LOW
                new_state = True
            else: # 所有相关开关都关了
                new_preset = PRESET_MODE_OFF
                new_state = False

            # 只有状态真正发生变化时才更新
            if self._preset_mode != new_preset or self._state != new_state:
                self._preset_mode = new_preset
                self._state = new_state
                self.async_write_ha_state() # 通知 HA 状态已更新
                _LOGGER.debug(f"Fan state updated via coordinator: is_on={self._state}, preset_mode={self._preset_mode}")

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set the preset mode of the fan."""
        _LOGGER.debug(f"Setting fan preset mode to: {preset_mode}")

        # --- 构建正确的开关实体 ID ---
        # 基于最佳实践，假设 switch.py 中的 unique_id 为 f"{device_info['id']}_warming_switch_1"
        # 那么 hass 生成的 entity_id 就是 f"switch.{DOMAIN}_{device_info['id']}_warming_switch_1"
        device_id = self._device_info['id']
        switch1_entity_id = f"switch.{DOMAIN}_{device_id}_warming_switch_1"
        switch2_entity_id = f"switch.{DOMAIN}_{device_id}_warming_switch_2"
        wind_entity_id = f"switch.{DOMAIN}_{device_id}_wind_switch"

        # --- 关闭所有相关的开关 ---
        await self.hass.services.async_call(
            domain='switch',
            service='turn_off',
            target={'entity_id': [switch1_entity_id, switch2_entity_id, wind_entity_id]}, # 关闭所有相关开关
            blocking=True # 等待服务调用完成
        )
        _LOGGER.debug(f"Turned off all related switches: {[switch1_entity_id, switch2_entity_id, wind_entity_id]}")

        # --- 根据模式开启相应的开关 ---
        if preset_mode == PRESET_MODE_OFF:
            self._state = False
            self._preset_mode = PRESET_MODE_OFF
            _LOGGER.debug("Fan set to OFF.")
        elif preset_mode == PRESET_MODE_COOLING:
            # 开启吹风开关
            await self.hass.services.async_call(
                domain='switch',
                service='turn_on',
                target={'entity_id': wind_entity_id},
                blocking=True
            )
            self._state = True
            self._preset_mode = PRESET_MODE_COOLING
            _LOGGER.debug(f"Fan set to COOLING, turned on {wind_entity_id}.")
        elif preset_mode == PRESET_MODE_WARMING_LOW:
            # 开启暖风开关1
            await self.hass.services.async_call(
                domain='switch',
                service='turn_on',
                target={'entity_id': switch1_entity_id},
                blocking=True
            )
            self._state = True
            self._preset_mode = PRESET_MODE_WARMING_LOW
            _LOGGER.debug(f"Fan set to WARMING_LOW, turned on {switch1_entity_id}.")
        elif preset_mode == PRESET_MODE_WARMING_HIGH:
            # 开启暖风开关1和开关2
            await self.hass.services.async_call(
                domain='switch',
                service='turn_on',
                target={'entity_id': [switch1_entity_id, switch2_entity_id]},
                blocking=True
            )
            self._state = True
            self._preset_mode = PRESET_MODE_WARMING_HIGH
            _LOGGER.debug(f"Fan set to WARMING_HIGH, turned on {switch1_entity_id} and {switch2_entity_id}.")
        else:
            _LOGGER.error(f"Unknown preset mode: {preset_mode}")
            return

        # 状态更新应由协调器轮询或开关实体自身状态变化触发的更新来完成。
        # 如果协调器更新频率较高，可以在此处立即更新本地状态，但这可能导致短暂不一致。
        # 如果协调器更新较慢，可以取消注释下面两行，立即更新UI状态。
        # self._state = self._preset_mode != PRESET_MODE_OFF
        # self.async_write_ha_state()


    async def async_turn_on(
        self,
        percentage: Optional[int] = None,
        preset_mode: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Turn on the fan."""
        # 如果指定了预设模式，则使用该模式；否则，默认为上次的模式或低档暖风
        mode_to_use = preset_mode or self._preset_mode or PRESET_MODE_WARMING_LOW
        _LOGGER.debug(f"Fan turn_on called, using preset_mode: {mode_to_use}")
        await self.async_set_preset_mode(mode_to_use)


    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn off the fan."""
        _LOGGER.debug("Fan turn_off called.")
        await self.async_set_preset_mode(PRESET_MODE_OFF)

# ... 其他方法 (speed, oscillation, direction) ...
# 如果你想保留速度控制等功能，需要相应地实现 speed_list, percentage, set_percentage, etc.
# 但根据你的需求，使用 preset_mode 已经足够。

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> bool:
    """Set up the Zinguo fan platform."""
    coordinator: ZinguoDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]
    api: ZinguoAPI = hass.data[DOMAIN][entry.entry_id]["api"]

    entities = []
    for device_info in coordinator.data.values():
        # 创建风扇实体
        entities.append(ZinguoFan(coordinator, device_info, api))

    async_add_entities(entities)
    return True