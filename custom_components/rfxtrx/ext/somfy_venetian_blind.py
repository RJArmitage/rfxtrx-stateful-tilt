import logging
import asyncio

from homeassistant.const import (
    STATE_OPENING,
    STATE_CLOSING)

from homeassistant.components.rfxtrx import CONF_SIGNAL_REPETITIONS

from .abs_tilting_cover import AbstractTiltingCover, BLIND_POS_CLOSED
from .const import (
    CONF_CLOSE_SECONDS,
    CONF_OPEN_SECONDS,
    CONF_STEPS_MID,
    CONF_SYNC_SECONDS,
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

# Event 071a000001010101 Office
# Event 071a000001020101 Front
# Event 071a000001030101 Back
# Event 071a000001060101 Living 1
# Event 071a000001060201 Living 2
# Event 071a000001060301 Living 3
# Event 071a000001060401 Living 4
# Event 071a000001060501 Living 5
# Event 071a00000106ff01 Living all


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
                         False,  # Do not lift on open
                         entity_info[CONF_SYNC_MID],  # Sync on mid point
                         entity_info[CONF_OPEN_SECONDS],  # Open time
                         entity_info[CONF_CLOSE_SECONDS],  # Close time
                         entity_info[CONF_SYNC_SECONDS],  # Sync time ms
                         500  # Ms for each step
                         )

        self._tiltPos1Sec = entity_info[CONF_TILT_POS1_MS] / 1000
        self._tiltPos2Sec = entity_info[CONF_TILT_POS2_MS] / 1000

    async def _async_tilt_blind_to_step(self, steps, target):
        _LOGGER.info("SOMFY VENETIAN TILTING BLIND")
        if target == 0:
            await self._async_set_cover_position(BLIND_POS_CLOSED)
        elif target == 1:
            # If not already closed then close first
            if steps != -1:
                _LOGGER.info("Tilt blind to mid")
                await self._async_tilt_blind_to_mid_step()
            _LOGGER.info("Close blind")
            await self._async_send(self._device.send_command, CMD_CLOSE)
            _LOGGER.info("Wait... " + str(self._tiltPos1Sec))
            await asyncio.sleep(self._tiltPos1Sec)
            _LOGGER.info("Stop")
            await self._async_send(self._device.send_command, CMD_STOP)
        elif target == 2:
            await self._async_tilt_blind_to_mid_step()
            await self._async_send(self._device.send_command, CMD_STOP)
        elif target == 3:
            # If not already at mid point then move first
            if steps != 1:
                _LOGGER.info("Tilt blind to mid")
                await self._async_tilt_blind_to_mid_step()
            _LOGGER.info("Open blind")
            await self._async_send(self._device.send_command, CMD_OPEN)
            _LOGGER.info("Wait... " + str(self._tiltPos2Sec))
            await asyncio.sleep(self._tiltPos2Sec)
            _LOGGER.info("Stop")
            await self._async_send(self._device.send_command, CMD_STOP)
        elif target == 4:
            await self._async_set_cover_position(BLIND_POS_CLOSED)

        return target

    # Replace with action to close blind
    async def _async_do_close_blind(self):
        """Callback to close the blind"""
        _LOGGER.info("SOMFY VENETIAN CLOSING BLIND")
        await self._set_state(STATE_CLOSING, BLIND_POS_CLOSED, self._tilt_step)
        await self._async_send(self._device.send_command, CMD_CLOSE)

    # Replace with action to open blind
    async def _async_do_open_blind(self):
        """Callback to open the blind"""
        _LOGGER.info("SOMFY VENETIAN OPENING BLIND")
        await self._async_send(self._device.send_command, CMD_OPEN)

    async def _async_do_tilt_blind_to_mid(self):
        """Callback to tilt the blind to mid"""
        _LOGGER.info("SOMFY VENETIAN TILTING BLIND TO MID")
        await self._set_state(STATE_OPENING, BLIND_POS_CLOSED, self._tilt_step)
        await self._async_send(self._device.send_command, CMD_STOP)
        return self._blindSyncSecs
