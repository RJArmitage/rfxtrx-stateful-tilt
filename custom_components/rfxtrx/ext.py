import logging

from .ext_louvolite_vogue_blind import LouvoliteVogueBlind
from .ext_somfy_venetian_blind import SomfyVenetianBlind

_LOGGER = logging.getLogger(__name__)


def create_cover_entity(device, device_id, entity_info, event=None):
    """Create a cover entitity of any of our supported types"""
    _LOGGER.info("Device ID " + str(device_id))
    _LOGGER.info("Info " + str(entity_info))

    if device_id[0] == '19' and device_id[1] == '13':
        _LOGGER.info("Detected a Louvolite Vogue vertical blind")
        return LouvoliteVogueBlind(device, device_id, entity_info)
    elif device_id[0] == '1a':
        _LOGGER.info("Detected a Somfy RFY blind")
        return SomfyVenetianBlind(device, device_id, entity_info)

    return None
