import logging
from homeassistant.components.rfxtrx.cover import RfxtrxCover
from homeassistant.components.rfxtrx import CONF_SIGNAL_REPETITIONS

from .louvolite_vogue_blind import LouvoliteVogueBlind
from .somfy_venetian_blind import SomfyVenetianBlind

from .const import (
    DEVICE_PACKET_TYPE_RFY,

    DEVICE_PACKET_TYPE_BLINDS1,
    DEVICE_PACKET_SUBTYPE_BLINDST19
)

_LOGGER = logging.getLogger(__name__)


def create_cover_entity(device, device_id, entity_info, event=None):
    """Create a cover entitity of any of our supported types"""
    _LOGGER.info("Device ID " + str(device_id))
    _LOGGER.info("Info " + str(entity_info))

    if device_id[0] == DEVICE_PACKET_TYPE_BLINDS1 and device_id[1] == DEVICE_PACKET_SUBTYPE_BLINDST19:
        _LOGGER.info("Detected a Louvolite Vogue vertical blind")
        return LouvoliteVogueBlind(device, device_id, entity_info)
    elif device_id[0] == DEVICE_PACKET_TYPE_RFY:
        _LOGGER.info("Detected a Somfy RFY blind")
        return SomfyVenetianBlind(device, device_id, entity_info)
    else:
        return RfxtrxCover(device, device_id, entity_info[CONF_SIGNAL_REPETITIONS])
