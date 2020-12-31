import voluptuous as vol
import logging

from homeassistant.components.rfxtrx.cover import supported as cover_supported

from .const import (
    DEF_CLOSE_SECONDS,
    DEF_OPEN_SECONDS,
    DEF_SUPPORTS_MID,
    DEF_STEPS_MID,
    DEF_SYNC_MID,
    CONF_CLOSE_SECONDS,
    CONF_OPEN_SECONDS,
    CONF_SUPPORTS_MID,
    CONF_STEPS_MID,
    CONF_SYNC_MID,
    DEVICE_PACKET_TYPE_RFY
)

_LOGGER = logging.getLogger(__name__)


def update_device_options(device, user_input):
    device[CONF_SUPPORTS_MID] = user_input.get(
        CONF_SUPPORTS_MID, DEF_SUPPORTS_MID)
    device[CONF_SYNC_MID] = user_input.get(
        CONF_SYNC_MID, DEF_SYNC_MID)
    device[CONF_STEPS_MID] = user_input.get(
        CONF_STEPS_MID, DEF_STEPS_MID)
    device[CONF_OPEN_SECONDS] = user_input.get(CONF_OPEN_SECONDS,
                                               DEF_OPEN_SECONDS)
    device[CONF_CLOSE_SECONDS] = user_input.get(CONF_CLOSE_SECONDS,
                                                DEF_CLOSE_SECONDS)


def update_data_schema(data_schema, device_object, device_data):
    if (cover_supported(device_object)):
        if device_object.device.packettype == DEVICE_PACKET_TYPE_RFY:
            # Add Somfy RFY tilt options
            data_schema.update(
                {
                    vol.Optional(
                        CONF_SUPPORTS_MID,
                        default=device_data.get(
                            CONF_SUPPORTS_MID, DEF_SUPPORTS_MID)
                    ): bool,
                    vol.Optional(
                        CONF_SYNC_MID,
                        default=device_data.get(CONF_SYNC_MID, DEF_SYNC_MID),
                    ): bool,
                    vol.Optional(
                        CONF_STEPS_MID,
                        default=device_data.get(CONF_STEPS_MID, DEF_STEPS_MID),
                    ): int,
                    vol.Optional(
                        CONF_OPEN_SECONDS,
                        default=device_data.get(
                            CONF_OPEN_SECONDS, DEF_OPEN_SECONDS),
                    ): int,
                    vol.Optional(
                        CONF_CLOSE_SECONDS,
                        default=device_data.get(
                            CONF_CLOSE_SECONDS, DEF_CLOSE_SECONDS),
                    ): int,
                }
            )
