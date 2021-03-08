import logging
import asyncio
from homeassistant.const import (
    STATE_OPENING,
    STATE_CLOSING
)
from homeassistant.components.rfxtrx import CONF_SIGNAL_REPETITIONS
from homeassistant.components.rfxtrx.const import (
    CONF_VENETIAN_BLIND_MODE,
    CONST_VENETIAN_BLIND_MODE_EU,
    CONST_VENETIAN_BLIND_MODE_US
)
from .abs_tilting_cover import (
    AbstractTiltingCover,
    BLIND_POS_CLOSED
)
from .const import (
    CONF_CLOSE_SECONDS,
    CONF_OPEN_SECONDS,
    CONF_STEPS_MID,
    CONF_SYNC_SECONDS,
    CONF_SYNC_MID,
    CONF_TILT_POS1_MS,
    CONF_TILT_POS2_MS,
    DEF_CLOSE_SECONDS,
    DEF_OPEN_SECONDS, DEF_STEPS_MID,
    DEF_SYNC_SECONDS,
    DEF_TILT_POS1_MS,
    DEF_TILT_POS2_MS
)

_LOGGER = logging.getLogger(__name__)

DEVICE_TYPE = "Somfy Venetian"

CMD_SOMFY_STOP = 0x00
CMD_SOMFY_UP = 0x01
CMD_SOMFY_DOWN = 0x03
CMD_SOMFY_UP05SEC = 0x0f
CMD_SOMFY_DOWN05SEC = 0x10
CMD_SOMFY_UP2SEC = 0x11
CMD_SOMFY_DOWN2SEC = 0x12

# Event 071a000001010101 Office
# Event 071a000001020101 Front
# Event 071a000001030101 Back
# Event 071a000001060101 Living 1
# Event 071a000001060201 Living 2
# Event 071a000001060301 Living 3
# Event 071a000001060401 Living 4
# Event 071a000001060501 Living 5
# Event 071a00000106ff01 Living all
# Event 071a000002010101 Kitchen


class SomfyVenetianBlind(AbstractTiltingCover):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, entity_info, event=None):
        device.type_string = DEVICE_TYPE
        super().__init__(device, device_id,
                         entity_info[CONF_SIGNAL_REPETITIONS], event,
                         # entity_info.get(CONF_STEPS_MID, DEF_STEPS_MID),  # steps to mid point
                         2,  # Currently support 2 steps to mid point
                         True,  # Supports mid point
                         True,  # Supports lift
                         False,  # Do not lift on open
                         False,  # Sync on mid point
                         entity_info.get(CONF_OPEN_SECONDS,
                                         DEF_OPEN_SECONDS),  # Open time
                         entity_info.get(CONF_CLOSE_SECONDS,
                                         DEF_CLOSE_SECONDS),  # Close time
                         entity_info.get(CONF_SYNC_SECONDS,
                                         DEF_SYNC_SECONDS),  # Sync time ms
                         500  # Ms for each step
                         )

        self._venetian_blind_mode = entity_info.get(CONF_VENETIAN_BLIND_MODE)
        self._tiltPos1Sec = entity_info.get(
            CONF_TILT_POS1_MS, DEF_TILT_POS1_MS) / 1000
        self._tiltPos2Sec = entity_info.get(
            CONF_TILT_POS2_MS, DEF_TILT_POS2_MS) / 1000

    @property
    def icon(self):
        """Return the icon property."""
        icon = "mdi:window-shutter" if self.is_closed else "mdi:window-shutter-open"
        _LOGGER.debug("Returned icon attribute = " + icon)
        return icon

    # Handle tilting a somfy blind. At present this is done by simulating a tilt using
    # an open or close followed by a delay. This needs to be replaced by a number of
    # tilt operations when supported by RFXCOM

    async def _async_tilt_blind_to_step(self, steps, target):
        """Callback to tilt the blind to some position"""
        _LOGGER.info("SOMFY VENETIAN TILTING BLIND")
        if target == 0:
            await self._async_set_cover_position(BLIND_POS_CLOSED)

        elif target == 1:
            # If not already at mid point then move first
            if steps != -1:
                await self._async_tilt_blind_to_mid_step()

            await self._async_somfy_blind_down()
            await asyncio.sleep(self._tiltPos1Sec)
            await self._async_send(self._device.send_command, CMD_SOMFY_STOP)

        elif target == 2:
            await self._async_tilt_blind_to_mid_step()

        elif target == 3:
            # If not already at mid point then move first
            if steps != 1:
                await self._async_tilt_blind_to_mid_step()

            await self._async_somfy_blind_up()
            await asyncio.sleep(self._tiltPos2Sec)
            await self._async_send(self._device.send_command, CMD_SOMFY_STOP)

        elif target == 4:
            await self._async_set_cover_position(BLIND_POS_CLOSED)

        return target

    async def _async_do_close_blind(self):
        """Callback to close a Somfy blind"""
        _LOGGER.info("SOMFY VENETIAN CLOSING BLIND")
        await self._set_state(STATE_CLOSING, BLIND_POS_CLOSED, self._tilt_step)
        await self._async_somfy_blind_down()

    async def _async_do_open_blind(self):
        """Callback to open a Somfy blind"""
        _LOGGER.info("SOMFY VENETIAN OPENING BLIND")
        await self._async_somfy_blind_up()

    async def _async_do_tilt_blind_to_mid(self):
        """Callback to tilt a Somfy blind to mid"""
        _LOGGER.info("SOMFY VENETIAN TILTING BLIND TO MID")
        await self._set_state(STATE_OPENING, BLIND_POS_CLOSED, self._tilt_step)
        await self._async_send(self._device.send_command, CMD_SOMFY_STOP)
        return self._blindSyncSecs

    async def _async_somfy_blind_down(self):
        """Callback to move a Somfy venetian blind down - varies between regions"""
        if self._venetian_blind_mode == CONST_VENETIAN_BLIND_MODE_US:
            await self._async_send(self._device.send_command, CMD_SOMFY_DOWN05SEC)
        elif self._venetian_blind_mode == CONST_VENETIAN_BLIND_MODE_EU:
            await self._async_send(self._device.send_command, CMD_SOMFY_DOWN2SEC)
        else:
            _LOGGER.warn("Unexpected DOWN command for a none-EU/US device")
            await self._async_send(self._device.send_command, CMD_SOMFY_DOWN)

    async def _async_somfy_blind_up(self):
        """Callback to move a Somfy venetian blind up - varies between regions"""
        if self._venetian_blind_mode == CONST_VENETIAN_BLIND_MODE_US:
            await self._async_send(self._device.send_command, CMD_SOMFY_UP05SEC)
        elif self._venetian_blind_mode == CONST_VENETIAN_BLIND_MODE_EU:
            await self._async_send(self._device.send_command, CMD_SOMFY_UP2SEC)
        else:
            _LOGGER.warn("Unexpected UP command for a none-EU/US device")
            await self._async_send(self._device.send_command, CMD_SOMFY_UP)
