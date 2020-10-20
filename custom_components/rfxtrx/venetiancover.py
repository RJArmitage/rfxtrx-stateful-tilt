"""Light support for switch entities."""
import logging
import asyncio
from typing import Any, Callable, Optional, Sequence, cast

from . import (
    CONF_AUTOMATIC_ADD,
    CONF_DATA_BITS,
    CONF_SIGNAL_REPETITIONS,
    DEFAULT_SIGNAL_REPETITIONS,
    SIGNAL_EVENT,
    RfxtrxCommandEntity,
)

from . import RFXtrx as rfxtrxmod

from .const import COMMAND_OFF_LIST, COMMAND_ON_LIST

from homeassistant.components import cover
from homeassistant.components.cover import (
    DEVICE_CLASS_BLIND,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_OPEN_TILT,
    SUPPORT_CLOSE_TILT,
    SUPPORT_STOP,
    SUPPORT_SET_POSITION,
    SUPPORT_SET_TILT_POSITION,
    ATTR_CURRENT_POSITION,
    ATTR_CURRENT_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
)
from homeassistant.const import (
    CONF_DEVICES,
    ATTR_ENTITY_ID,
    ATTR_ATTRIBUTION,
    CONF_ENTITY_ID,
    CONF_NAME,
    STATE_UNAVAILABLE,
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING)

from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.typing import (
    ConfigType,
    DiscoveryInfoType,
    HomeAssistantType,
)

TILT_POS_OPEN = 100
TILT_POS_HOME = 50
TILT_POS_CLOSED = 0
BLIND_POS_OPEN = 100
BLIND_POS_STOPPED = 50
BLIND_POS_CLOSED = 0

COMMAND_STOP = 0x00
COMMAND_UP = 0x01
COMMAND_DOWN = 0x03
COMMAND_SHORT_UP = 0x0F
COMMAND_SHORT_DOWN = 0x10
COMMAND_LONG_UP = 0x11
COMMAND_LONG_DOWN = 0x12


# mypy: allow-untyped-calls, allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Blinds Control"


class VenetianCover(RfxtrxCommandEntity, CoverEntity):
    # class VenetianCover(CoverEntity):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, signal_repetitions, event=None):
        """Initialzie a switch or light device."""
        super().__init__(device, device_id, 1, event)

        _LOGGER.info("Creating venetian cover, signal_repetitions param=",
                     str(signal_repetitions))

        if signal_repetitions < 1000:
            config = 3030101
        else:
            config = signal_repetitions

        config, self._euMode = divmod(config, 10)
        self._euMode = self._euMode > 0
        config, self._blindMySteps = divmod(config, 100)
        config, self._blindCloseSecs = divmod(config, 100)
        config, self._blindOpenSecs = divmod(config, 100)

        _LOGGER.info("New Venetian config," +
                     " config=" + str(signal_repetitions) +
                     " steps=" + str(self._blindMySteps) +
                     " openSecs=" + str(self._blindOpenSecs) +
                     " closeSecs=" + str(self._blindCloseSecs) +
                     " euMode=" + str(self._euMode))

    async def async_added_to_hass(self):
        """Restore device state."""
        _LOGGER.debug("Called async_added_to_hass")

        self._available = True
        self._tilt_position = TILT_POS_OPEN
        self._position = BLIND_POS_OPEN
        self._step = self._blindMySteps
        self._state = STATE_OPEN

        await super().async_added_to_hass()

        # if self._event is None:
        #     old_state = await self.async_get_last_state()
        #     if old_state is not None:
        #         self._state = old_state.state == STATE_OPEN

    @ property
    def available(self) -> bool:
        """Return true if light switch is on."""
        _LOGGER.debug("Returned available attribute = " + str(self._available))
        return self._available

    @ property
    def current_cover_tilt_position(self):
        """Return the brightness of this light between 0..255."""
        _LOGGER.debug(
            "Returned current_cover_tilt_position attribute = " + str(self._tilt_position))
        return self._tilt_position

    @property
    def current_cover_position(self):
        """Return the current_cover_position property."""
        _LOGGER.debug(
            "Returned current_cover_position attribute = " + str(self._position))
        return self._position

    @property
    def is_opening(self):
        """Return the is_opening property."""
        _LOGGER.debug("Returned is_opening attribute = " +
                      str(self._state == STATE_OPENING))
        return self._state == STATE_OPENING

    @property
    def is_closing(self):
        """Return the is_closing of the light."""
        _LOGGER.debug("Returned is_closing attribute = " +
                      str(self._state == STATE_CLOSING))
        return self._state == STATE_CLOSING

    @property
    def is_closed(self):
        """Return color is_closed min mireds."""
        _LOGGER.debug("Returned is_closed attribute = " +
                      str(self._state == STATE_CLOSED))
        return self._state == STATE_CLOSED

    @property
    def device_class(self):
        """Return the device class."""
        _LOGGER.debug("Returned device_class attribute")
        return DEVICE_CLASS_BLIND

    @property
    def supported_features(self):
        """Flag supported features."""
        _LOGGER.debug("Returned supported_features attribute")
        return SUPPORT_CLOSE | SUPPORT_OPEN | SUPPORT_STOP | SUPPORT_OPEN_TILT | SUPPORT_CLOSE_TILT | SUPPORT_SET_TILT_POSITION | SUPPORT_SET_POSITION

    @property
    def should_poll(self):
        """No polling needed for a RFXtrx switch."""
        return True

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return False

    # Requests to open the blind. In practice we do not open then blind, we will instead tilt to the
    # my position. If the blind is in motion then is ignored.

    async def async_open_cover(self, **kwargs):
        """Open the cover."""
        _LOGGER.debug("Invoked async_open_cover")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Opening blind by selecting my position...")
            await self.async_set_cover_my_position(**kwargs)

    # Requests to close the blind. If the blind is in motion then is ignored. Otherwise always close the blind so
    # that we can be sure the blind is closed.

    async def async_close_cover(self, **kwargs):
        """Close cover."""
        _LOGGER.debug("Invoked async_close_cover")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            # Do we need to wait?
            longOperation = self._state == STATE_OPEN or (
                self._state == STATE_CLOSED and self._position != BLIND_POS_CLOSED)

            self._state = STATE_CLOSING
            if longOperation:
                _LOGGER.info("Closing blind with a delay...")
                self._position = BLIND_POS_STOPPED
                self._tilt_position = TILT_POS_CLOSED
                self.schedule_update_ha_state(True)
            else:
                _LOGGER.info("Closing blind with no delay...")

            # close blind
            await self._async_send(self._device.send_close)

            if longOperation:
                _LOGGER.debug("Waiting blind close secs " +
                              str(self._blindCloseSecs))
                await asyncio.sleep(self._blindCloseSecs)

            # If the blind is still closing then we have finished. Otherwise assume we were interrupted
            if self._state == STATE_CLOSING:
                _LOGGER.info(
                    "Finished closing blind - setting blind to closed")

                self._state = STATE_CLOSED
                self._position = BLIND_POS_CLOSED
                self._tilt_position = TILT_POS_CLOSED
                self._step = 0
                self.schedule_update_ha_state(True)
            else:
                _LOGGER.info(
                    "Finished closing blind - blind is not closing so not setting to closed")

    # Requests to stop the blind. If the blind is not in motion then is ignored. Otherwise assume the blind
    # is in a mid position.

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        _LOGGER.debug("Invoked async_stop_cover, state=" + self._state)

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.info(
                "Blind is in motion - stopping blind and marking as partially closed")

            # Stop the blind
            await self._async_send(self._device.send_stop)

            self._state = STATE_CLOSED
            self._position = BLIND_POS_STOPPED
            self._tilt_position = TILT_POS_CLOSED
            self._step = 0
            self.async_write_ha_state()
        else:
            _LOGGER.debug("Blind is stationary - ignoring the request")

    # Requests to set the position of the blind. If the blind is in motion then is ignored. We will use this
    # to allow the blind to actually be opened. If the position is after the mid point then change into a close
    # command which will ensure the blind is closed. Otherwise set he state to OPENING and open the blind.
    # Then after a delay and marks as OPEN if the blind is still OPENING.

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _LOGGER.debug("Invoked async_set_cover_position")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        elif ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            if position < BLIND_POS_STOPPED:
                _LOGGER.debug(
                    "Position is before mid state - will close blind")
                await self.async_close_cover(**kwargs)
            else:
                _LOGGER.info(
                    "Position is after mid state - will open with a delay...")
                self._state = STATE_OPENING
                self._position = BLIND_POS_STOPPED
                self._tilt_position = TILT_POS_CLOSED
                self._step = 0
                # self.schedule_update_ha_state(True)
                self.schedule_update_ha_state(True)

                # Open blind
                await self._async_send(self._device.send_open)

                # Wait for blind to open and then set state open
                _LOGGER.debug("Waiting blind open secs " +
                              str(self._blindOpenSecs))
                await asyncio.sleep(self._blindOpenSecs)

                # If the blind is still opening then we have finished. Otherwise assume we were interrupted
                if self._state == STATE_OPENING:
                    _LOGGER.info(
                        "Finished opening blind - setting blind to open")
                    self._state = STATE_OPEN
                    self._position = BLIND_POS_OPEN
                    self._tilt_position = TILT_POS_OPEN
                    self._step = 0
                    self.schedule_update_ha_state(True)
                else:
                    _LOGGER.info(
                        "Finished opening blind - blind is not opening so not setting to open")
        else:
            _LOGGER.error("No position specified for set_cover_position")

    # Request to open the blind with a tilt

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        _LOGGER.debug("Invoked async_open_cover_tilt")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Opening blind by selecting my position...")
            await self.async_set_cover_my_position(**kwargs)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        _LOGGER.debug("Invoked async_close_cover_tilt")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Tilting by closing blind...")
            await self.async_close_cover(**kwargs)

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        _LOGGER.debug("Invoked async_set_cover_tilt_position")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        elif self._state == STATE_OPEN:
            _LOGGER.debug("Blind is open - switching to my position operation")
            await self.async_set_cover_my_position(**kwargs)
        elif self._state == STATE_CLOSED and self._position != BLIND_POS_CLOSED:
            _LOGGER.debug(
                "Blind is partially closed - switching to my position operation")
            await self.async_set_cover_my_position(**kwargs)
        else:
            if ATTR_TILT_POSITION in kwargs:
                self._tilt_position = kwargs[ATTR_TILT_POSITION]
            else:
                self._tilt_position = TILT_POS_HOME

            if self._tilt_position == TILT_POS_HOME:
                _LOGGER.debug(
                    "Mid position requested - switching to my position operation")
                await self.async_set_cover_my_position(**kwargs)
            elif self._tilt_position == 0:
                _LOGGER.debug(
                    "End position requested - switching to close operation")
                await self.async_close_cover(**kwargs)
            else:
                _LOGGER.info(
                    "Tilting to required position " + str(self._tilt_position))

                target = round(self._tilt_position / 50 * self._blindMySteps)
                steps = target - self._step

                _LOGGER.debug(
                    "Target = " + str(target) + ' from = ' + str(self._step) + " steps = " + str(steps))

                if (target == self._blindMySteps):
                    _LOGGER.debug(
                        "Tilt is to mid point - switching to my position operation")
                    await self.async_set_cover_my_position(**kwargs)
                else:
                    self._step = target

                    # Tilt blind
                    for step in range(abs(steps)):
                        if steps > 0:
                            await self._async_send(self._device.send_short_up)
                        else:
                            await self._async_send(self._device.send_short_down)

                    self.schedule_update_ha_state(True)

    async def async_set_cover_my_position(self, **kwargs):
        """Move the cover tilt to a preset position."""
        _LOGGER.debug("Invoked async_set_cover_my_position")
        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            longOperation = self._state == STATE_OPEN or (
                self._state == STATE_CLOSED and self._position != BLIND_POS_CLOSED)

            if longOperation:
                _LOGGER.info("Setting my position with a delay...")
                self._state = STATE_CLOSING
                self._position = BLIND_POS_STOPPED
                self._tilt_position = TILT_POS_CLOSED
                self.schedule_update_ha_state(True)
            else:
                _LOGGER.info("Setting my position with no delay...")

            # set my position blind
            await self._async_send(self._device.send_my)

            if longOperation:
                _LOGGER.debug("Waiting blind close secs " +
                              str(self._blindCloseSecs))
                await asyncio.sleep(self._blindCloseSecs)

                # If the blind is still opening then we have finished. Otherwise assume we were interrupted
                if self._state == STATE_CLOSING:
                    _LOGGER.info("Finished setting my position")
                    self._state = STATE_CLOSED
                    self._position = BLIND_POS_CLOSED
                    self._tilt_position = TILT_POS_HOME
                    self._step = self._blindMySteps
                    self.schedule_update_ha_state(True)
                else:
                    _LOGGER.info(
                        "Finished setting my position - blind is not closing so not setting to closed")
            else:
                _LOGGER.info("Finished setting my position")
                self._position = BLIND_POS_CLOSED
                self._tilt_position = TILT_POS_HOME
                self._step = self._blindMySteps
                self.schedule_update_ha_state(True)

    async def async_update(self):
        """Query the switch in this light switch and determine the state."""
        _LOGGER.debug("Invoked async_update")

    def _apply_event(self, event):
        """Apply command from rfxtrx."""
        _LOGGER.debug("Invoked _apply_event")
        super()._apply_event(event)
        # if event.values["Command"] in COMMAND_ON_LIST:
        #     self._state = True
        # elif event.values["Command"] in COMMAND_OFF_LIST:
        #     self._state = False

    @callback
    def _handle_event(self, event, device_id):
        """Check if event applies to me and update."""
        _LOGGER.debug("Invoked _handle_event")
        if device_id != self._device_id:
            return

        self._apply_event(event)

        self.async_write_ha_state()
