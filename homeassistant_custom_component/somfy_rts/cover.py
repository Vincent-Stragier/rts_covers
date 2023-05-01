from .somfy_rts import RTSSomfyRollingShutter
import voluptuous as vol

from pprint import pformat

import logging

import homeassistant.helpers.config_validation as config_validation
from homeassistant.components.cover import (
    CoverEntity,
    CoverDeviceClass,
    CoverEntityFeature,
    PLATFORM_SCHEMA,
    STATE_OPEN,
    STATE_CLOSED,
)

from homeassistant.const import CONF_NAME, CONF_IP_ADDRESS, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger("somfy_rts")

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): config_validation.string,
        vol.Required(CONF_IP_ADDRESS): config_validation.string,
        vol.Required(CONF_PORT): config_validation.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up Somfy RTS rolling shutter."""
    _LOGGER.info(pformat(config))

    cover = {
        "name": config[CONF_NAME],
        "ip_address": config[CONF_IP_ADDRESS],
        "port": config[CONF_PORT]
    }

    add_entities([SomfyRTSCover(cover)])


class SomfyRTSCover(CoverEntity):
    """Representation of a Somfy RTS rolling shutter."""

    def __init__(self, cover):
        """Initialize a Somfy RTS rolling shutter."""
        _LOGGER.info(pformat(cover))
        self._name = cover.get('name')
        self._ip_address = cover.get('ip_address')
        self._port = cover.get('port')
        self._cover = RTSSomfyRollingShutter(
            self._ip_address,
            self._port,
            self._name
        )
        self._attr_device_class = CoverDeviceClass.SHUTTER
        self._attr_supported_features = (
            CoverEntityFeature.OPEN |
            CoverEntityFeature.CLOSE |
            CoverEntityFeature.STOP
        )
        self._state = None

    def open_cover(self, **kwargs):
        """Open the rolling shutter."""
        self._cover.up()
        self._state = STATE_OPEN

    def close_cover(self, **kwargs):
        """Close the rolling shutter."""
        self._cover.down()
        self._state = STATE_CLOSED

    def stop_cover(self, **kwargs):
        """Stop the rolling shutter."""
        self._cover.stop()
        self._state = None

    @property
    def is_closed(self):
        return self._state is not STATE_OPEN

    @property
    def name(self):
        return self._name
