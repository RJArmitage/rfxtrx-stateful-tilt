import logging
import voluptuous as vol
from homeassistant.components.rfxtrx.cover import RfxtrxCover
from homeassistant.components.rfxtrx import CONF_SIGNAL_REPETITIONS
from homeassistant.helpers import config_validation as cv, entity_platform


from homeassistant.components.cover import (
    DEVICE_CLASS_BLIND,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_OPEN_TILT,
    SUPPORT_CLOSE_TILT,
    SUPPORT_STOP_TILT,
    SUPPORT_STOP,
    SUPPORT_SET_POSITION,
    SUPPORT_SET_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION)


from .louvolite_vogue_blind import LouvoliteVogueBlind
from .somfy_venetian_blind import SomfyVenetianBlind

from .const import (
    DEVICE_PACKET_TYPE_RFY,

    DEVICE_PACKET_TYPE_BLINDS1,
    DEVICE_PACKET_SUBTYPE_BLINDST19,

    ATTR_AUTO_REPEAT,
    SVC_UPDATE_POSITION,
    SVC_INCREASE_TILT,
    SVC_DECREASE_TILT
)

_LOGGER = logging.getLogger(__name__)


async def async_define_sync_services():
    platform = entity_platform.current_platform.get()

    platform.async_register_entity_service(
        SVC_UPDATE_POSITION,
        {
            vol.Required(ATTR_POSITION): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            ),
            vol.Required(ATTR_TILT_POSITION): vol.All(
                vol.Coerce(int), vol.Range(min=0, max=100)
            )
        },
        "async_update_cover_position",
        [SUPPORT_SET_POSITION | SUPPORT_SET_TILT_POSITION],
    )

    platform.async_register_entity_service(
        SVC_INCREASE_TILT,
        {
            vol.Optional(ATTR_AUTO_REPEAT, default=False): bool
        },
        "async_increase_cover_tilt",
        [SUPPORT_SET_TILT_POSITION],
    )

    platform.async_register_entity_service(
        SVC_DECREASE_TILT,
        {
            vol.Optional(ATTR_AUTO_REPEAT, default=False): bool
        },
        "async_decrease_cover_tilt",
        [SUPPORT_SET_TILT_POSITION],
    )


def create_cover_entity(device, device_id, entity_info, event=None):
    """Create a cover entitity of any of our supported types"""
    _LOGGER.info("Device ID " + str(device_id))
    _LOGGER.info("Info " + str(entity_info))

    if int(device_id[0], 16) == DEVICE_PACKET_TYPE_BLINDS1 and int(device_id[1], 16) == DEVICE_PACKET_SUBTYPE_BLINDST19:
        _LOGGER.info("Detected a Louvolite Vogue vertical blind")
        return LouvoliteVogueBlind(device, device_id, entity_info)
    elif int(device_id[0], 16) == DEVICE_PACKET_TYPE_RFY and device_id[2][0:2] == "01":
        _LOGGER.info("Detected a Somfy RFY blind")
        return SomfyVenetianBlind(device, device_id, entity_info)
    else:
        _LOGGER.info("Created default cover X" + device_id[2][0:2] + "X")
        return RfxtrxCover(device, device_id, entity_info[CONF_SIGNAL_REPETITIONS])
