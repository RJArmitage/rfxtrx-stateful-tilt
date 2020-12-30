import logging
from homeassistant.components.rfxtrx.cover import *
from homeassistant.components.rfxtrx.cover import (
    CONF_DEVICES,
    supported,
)
from homeassistant.components.rfxtrx import (
    CONF_DATA_BITS,
    get_device_id,
    get_rfx_object,
)

from . import create_cover_entity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass,
    config_entry,
    async_add_entities,
):
    """Set up config entry."""
    _LOGGER.info("Called overridden async_setup_entry")

    discovery_info = config_entry.data
    device_ids = set()

    entities = []
    for packet_id, entity_info in discovery_info[CONF_DEVICES].items():
        event = get_rfx_object(packet_id)
        if event is None:
            _LOGGER.error("Invalid device: %s", packet_id)
            continue
        if not supported(event):
            continue

        device_id = get_device_id(
            event.device, data_bits=entity_info.get(CONF_DATA_BITS)
        )
        if device_id in device_ids:
            continue
        device_ids.add(device_id)

        entity = create_cover_entity(event.device, device_id, entity_info)
        # if entity is None:
        # entity = RfxtrxCover(
        #     event.device, device_id, entity_info[CONF_SIGNAL_REPETITIONS]
        # )
        entities.append(entity)

    async_add_entities(entities)
