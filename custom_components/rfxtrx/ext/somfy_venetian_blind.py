import logging
from homeassistant.components.rfxtrx import CONF_SIGNAL_REPETITIONS

from .abs_tilting_cover import AbstractTiltingCover
from .const import (
    CONF_CLOSE_SECONDS,
    CONF_OPEN_SECONDS,
    CONF_STEPS_MID,
    CONF_SYNC_MID
)

_LOGGER = logging.getLogger(__name__)

DEVICE_TYPE = "Somfy Venetian"

CMD_CLOSE_CW = 0x00
CMD_CLOSE_CCW = 0x01
CMD_45_DEGREES = 0x02
CMD_90_DEGREES = 0x03
CMD_135_DEGREES = 0x04

# Event 071a000001010101


class SomfyVenetianBlind(AbstractTiltingCover):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, entity_info, event=None):
        device.type_string = DEVICE_TYPE
        super().__init__(device, device_id,
                         entity_info[CONF_SIGNAL_REPETITIONS], event,
                         entity_info[CONF_STEPS_MID],  # steps to mid point
                         True,  # Supports mid point
                         True,  # Supports lift
                         entity_info[CONF_SYNC_MID],  # Sync on mid point
                         entity_info[CONF_OPEN_SECONDS],  # Open time
                         entity_info[CONF_CLOSE_SECONDS],  # Close time
                         500  # Ms for each step
                         )

    async def _async_tilt_blind_to_step(self, steps, target):
        _LOGGER.info("SOMFY VENETIAN TILTING BLIND")
        # if target == 0:
        #     await self._async_send(self._device.send_close)
        # elif target == 1:
        #     await self._async_send(self._device.send_stop)
        # elif target == 2:
        #     await self._async_send(self._device.send_close)

        return target

    # Replace with action to close blind
    async def _async_close_blind(self):
        """Callback to close the blind"""
        _LOGGER.info("SOMFY VENETIAN CLOSING BLIND")
        # await self._async_send(self._device.send_close)

    # Replace with action to open blind
    async def _async_open_blind(self):
        """Callback to open the blind"""
        _LOGGER.info("SOMFY VENETIAN OPENING BLIND")
        # await self._async_send(self._device.send_open)

    async def _async_tilt_blind_to_mid(self):
        """Callback to tilt the blind to mid"""
        _LOGGER.info("SOMFY VENETIAN TILTING BLIND TO MID")
        # await self._async_send(self._device.send_stop)
