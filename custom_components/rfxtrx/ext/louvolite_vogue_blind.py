import logging
from homeassistant.components.rfxtrx import CONF_SIGNAL_REPETITIONS

from .abs_tilting_cover import AbstractTiltingCover

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
                         False,  # Does not require sync on mid point
                         1,  # Dummy opening time
                         1,  # Dummy close time
                         2000  # Ms for each step
                         )

    async def _async_tilt_blind_to_step(self, steps, target):
        _LOGGER.info("LOUVOLITE TILTING BLIND")
        if target == 0:
            await self._async_send(self._device.send_command, CMD_CLOSE_CCW)
        elif target == 1:
            await self._async_send(self._device.send_command, CMD_45_DEGREES)
        elif target == 2:
            await self._async_send(self._device.send_command, CMD_90_DEGREES)
        elif target == 3:
            await self._async_send(self._device.send_command, CMD_135_DEGREES)
        elif target == 4:
            await self._async_send(self._device.send_command, CMD_CLOSE_CW)

        return target

    # Replace with action to close blind
    async def _async_close_blind(self):
        """Callback to close the blind"""
        _LOGGER.info("LOUVOLITE CLOSING BLIND")
        await self._async_send(self._device.send_command, CMD_CLOSE_CCW)

    # Replace with action to open blind
    async def _async_open_blind(self):
        """Callback to open the blind"""
        _LOGGER.info("LOUVOLITE OPENING BLIND")
        await self._async_send(self._device.send_command, CMD_90_DEGREES)

    async def _async_tilt_blind_to_mid(self):
        """Callback to tilt the blind to mid"""
        _LOGGER.info("LOUVOLITE TILTING BLIND TO MID")
        await self._async_send(self._device.send_command, CMD_90_DEGREES)
