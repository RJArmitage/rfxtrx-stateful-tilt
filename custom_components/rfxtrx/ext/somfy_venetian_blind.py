import logging
import asyncio
from homeassistant.components.rfxtrx import CONF_SIGNAL_REPETITIONS

from .abs_tilting_cover import AbstractTiltingCover
from .const import (
    CONF_CLOSE_SECONDS,
    CONF_OPEN_SECONDS,
    CONF_STEPS_MID,
    CONF_SYNC_MID,
    CONF_TILT_POS1_MS,
    CONF_TILT_POS2_MS
)

_LOGGER = logging.getLogger(__name__)

DEVICE_TYPE = "Somfy Venetian"

CMD_STOP = 0x00
CMD_OPEN = 0x01
CMD_CLOSE = 0x03
CMD_OPEN05SEC = 0x0f
CMD_CLOSE05SEC = 0x10
CMD_OPEN2SEC = 0x11
CMD_CLOSE2SEC = 0x12

CMD_SYNC_DELAY = 4.0

# Event 071a000001010101 Office
# Event 071a000001020101 Front
# Event 071a000001030101 Back
# Event 071a000001060101 Living 1
# Event 071a000001060201 Living 2
# Event 071a000001060301 Living 3
# Event 071a000001060401 Living 4
# Event 071a000001060501 Living 5


class SomfyVenetianBlind(AbstractTiltingCover):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, entity_info, event=None):
        device.type_string = DEVICE_TYPE
        super().__init__(device, device_id,
                         entity_info[CONF_SIGNAL_REPETITIONS], event,
                         # entity_info[CONF_STEPS_MID],  # steps to mid point
                         2,
                         True,  # Supports mid point
                         True,  # Supports lift
                         entity_info[CONF_SYNC_MID],  # Sync on mid point
                         entity_info[CONF_OPEN_SECONDS],  # Open time
                         entity_info[CONF_CLOSE_SECONDS],  # Close time
                         500  # Ms for each step
                         )

        self._tiltPos1Sec = entity_info[CONF_TILT_POS1_MS] / 1000
        self._tiltPos2Sec = entity_info[CONF_TILT_POS2_MS] / 1000

    async def _async_tilt_blind_to_step(self, steps, target):
        _LOGGER.info("SOMFY VENETIAN TILTING BLIND")
        if target == 0:
            await self._async_send(self._device.send_command, CMD_CLOSE)
        elif target == 1:
            # If not already closed then close first
            if steps != -1:
                _LOGGER.info("Tilt blind to mid")
                await self._async_send(self._device.send_command, CMD_STOP)
                _LOGGER.info("Wait...")
                await asyncio.sleep(CMD_SYNC_DELAY)
            _LOGGER.info("Close blind")
            await self._async_send(self._device.send_command, CMD_CLOSE)
            _LOGGER.info("Wait..." + str(self._tiltPos1Sec))
            await asyncio.sleep(self._tiltPos1Sec)
            _LOGGER.info("Stop")
            await self._async_send(self._device.send_command, CMD_STOP)
        elif target == 2:
            await self._async_send(self._device.send_command, CMD_STOP)
        elif target == 3:
            # If not already at mid point then move first
            if steps != 1:
                _LOGGER.info("Tilt blind to mid")
                await self._async_send(self._device.send_command, CMD_STOP)
                _LOGGER.info("Wait...")
                await asyncio.sleep(CMD_SYNC_DELAY)
            _LOGGER.info("Open blind")
            await self._async_send(self._device.send_command, CMD_OPEN)
            _LOGGER.info("Wait..." + str(self._tiltPos2Sec))
            await asyncio.sleep(self._tiltPos2Sec)
            _LOGGER.info("Stop")
            await self._async_send(self._device.send_command, CMD_STOP)
        # elif target == 4:
        #     await self._async_send(self._device.send_command, CMD_STOP)

        return target

    # Replace with action to close blind
    async def _async_close_blind(self):
        """Callback to close the blind"""
        _LOGGER.info("SOMFY VENETIAN CLOSING BLIND")
        await self._async_send(self._device.send_command, CMD_CLOSE)

    # Replace with action to open blind
    async def _async_open_blind(self):
        """Callback to open the blind"""
        _LOGGER.info("SOMFY VENETIAN OPENING BLIND")
        await self._async_send(self._device.send_command, CMD_OPEN)

    async def _async_tilt_blind_to_mid(self):
        """Callback to tilt the blind to mid"""
        _LOGGER.info("SOMFY VENETIAN TILTING BLIND TO MID")
        await self._async_send(self._device.send_command, CMD_STOP)
