import logging
from homeassistant.components.rfxtrx import CONF_SIGNAL_REPETITIONS

from .abs_tilting_cover import (
    AbstractTiltingCover,
    BLIND_POS_CLOSED)

from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING)

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

DEVICE_TYPE = "Vogue Vertical"

CMD_CLOSE_CW = 0x00
CMD_CLOSE_CCW = 0x01
CMD_45_DEGREES = 0x02
CMD_90_DEGREES = 0x03
CMD_135_DEGREES = 0x04

# Event 0919130400A1DB010000


class LouvoliteVogueBlind(AbstractTiltingCover):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, entity_info, event=None):
        device.type_string = DEVICE_TYPE
        super().__init__(device, device_id,
                         entity_info[CONF_SIGNAL_REPETITIONS], event,
                         2,  #  2 steps to mid point
                         True,  # Supports mid point
                         False,  # Does not support lift
                         False,  # Do not lift on open
                         False,  # Does not require sync on mid point
                         entity_info[CONF_OPEN_SECONDS],  # Open time
                         entity_info[CONF_CLOSE_SECONDS],  # Close time
                         entity_info[CONF_SYNC_SECONDS],  # Sync time ms
                         2000  # Ms for each step
                         )
        _LOGGER.info("Create Louvolite Vogue tilting blind " + str(device_id))

    async def _async_tilt_blind_to_step(self, steps, target):
        _LOGGER.info("LOUVOLITE TILTING BLIND")
        if target == 0:
            movement = STATE_CLOSING
            command = CMD_CLOSE_CCW
        elif target == 1:
            movement = STATE_OPENING
            command = CMD_45_DEGREES
        elif target == 2:
            movement = STATE_OPENING
            command = CMD_90_DEGREES
        elif target == 3:
            movement = STATE_OPENING
            command = CMD_135_DEGREES
        else:
            movement = STATE_CLOSING
            command = CMD_CLOSE_CW

        await self._set_state(movement, BLIND_POS_CLOSED, self._tilt_step)
        await self._async_send(self._device.send_command, command)
        await self._wait_and_set_state(self._blindSyncSecs, movement, STATE_CLOSED, BLIND_POS_CLOSED, target)
        return target

    # Replace with action to close blind
    async def _async_do_close_blind(self):
        """Callback to close the blind"""
        _LOGGER.info("LOUVOLITE CLOSING BLIND")
        await self._set_state(STATE_CLOSING, BLIND_POS_CLOSED, self._tilt_step)
        await self._async_send(self._device.send_command, CMD_CLOSE_CCW)
        return self._blindCloseSecs

    # Replace with action to open blind
    async def _async_do_open_blind(self):
        """Callback to open the blind"""
        _LOGGER.info("LOUVOLITE OPENING BLIND")
        await self._set_state(STATE_OPENING, BLIND_POS_CLOSED, self._tilt_step)
        await self._async_send(self._device.send_command, CMD_90_DEGREES)
        return self._blindSyncSecs

    async def _async_do_tilt_blind_to_mid(self):
        """Callback to tilt the blind to mid"""
        _LOGGER.info("LOUVOLITE TILTING BLIND TO MID")
        await self._set_state(STATE_OPENING, BLIND_POS_CLOSED, self._tilt_step)
        await self._async_send(self._device.send_command, CMD_90_DEGREES)
        return self._blindOpenSecs
