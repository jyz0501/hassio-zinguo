"""The Zinguo integration."""
import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ZinguoDataUpdateCoordinator # 导入协调器

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.FAN, Platform.SENSOR]

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Zinguo from a config entry."""
    _LOGGER.debug("Setting up Zinguo integration for entry: %s", entry.entry_id)

    # 创建协调器实例
    coordinator = ZinguoDataUpdateCoordinator(
        hass=hass,
        username=entry.data["username"],
        password=entry.data["password"]
    )

    # 将协调器实例存储到 hass.data 中
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # 初始化协调器（首次刷新）
    await coordinator.async_config_entry_first_refresh()

    # 加载平台
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unloaded
