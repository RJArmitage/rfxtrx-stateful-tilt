"""Light support for switch entities."""
from custom_components.save.venetiancovertiltsimulate import TILT_POS_CLOSED, TILT_POS_OPEN
import logging
import asyncio
from typing import Any, Callable, Optional, Sequence, cast

from . import RfxtrxCommandEntity

from homeassistant.components.cover import (
    DEVICE_CLASS_BLIND,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_OPEN_TILT,
    SUPPORT_CLOSE_TILT,
    SUPPORT_STOP,
    SUPPORT_SET_POSITION,
    SUPPORT_SET_TILT_POSITION,
    ATTR_POSITION,
    ATTR_TILT_POSITION,
    CoverEntity,
)

from homeassistant.const import (
    STATE_CLOSED,
    STATE_CLOSING,
    STATE_OPEN,
    STATE_OPENING)

from homeassistant.core import callback

# Values returned for blind position in various states
BLIND_POS_OPEN = 100
BLIND_POS_STOPPED = 50
BLIND_POS_WILLOPEN = 75
BLIND_POS_TILTED = 1
BLIND_POS_CLOSED = 0

# Values returned for tilt position in various states
TILT_POS_BLIND_OPEN = 100
TILT_POS_MID = 50
TILT_POS_STOPPED = 25
TILT_POS_BLIND_CLOSED = 0


# mypy: allow-untyped-calls, allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Blinds Control"


# Represents a cover entity that has slats - either vertical or horizontal. Thios differs from a cover in that:
# - Opening the blind tilts the slats to allow light. Not moving the blind out of the window
# - Closing the blind requires the blind to be fully lowered into the window and the slats to be in a tilted position
#
# Properties:
#   Config:
#     _blindMaxSteps - number of steps to tilt the blind from fully tilted to the mid position
#     _blindMidSteps - number of steps to tilt the blind from fully tilted to the mid position
#     _supportmidCommand - Boolean - TRUE if the blind has an explicit command for the mid position
#     _syncmidPos - boolean - TRUE if we should send a "mid" position command each time we cross the mid position
#     _blindCloseSecs - number of seconds to wait for the blind to fully close from fully open position
#     _blindOpenSecs - number of seconds to wait for the blind to fully open from fully closed position
#   State:
#     _blind_position - reported position of the blind
#     _tilt_step - step posiotion of the tilt - related to the _tilt_position
#     _state - what the blind is curfrently doing - STATE_OPEN/STATE_OPENING/STATE_CLOSED/STATE_CLOSING
#
class SlattedCover(RfxtrxCommandEntity, CoverEntity):
    # class VenetianCover(CoverEntity):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, signal_repetitions, event=None):
        super().__init__(device, device_id, 1, event)

        _LOGGER.info("Creating slatted cover with tilt control, signal_repetitions param=",
                     str(signal_repetitions))

        if signal_repetitions < 1000:
            config = 3030101
        else:
            config = signal_repetitions

        config, self._syncmidPos = divmod(config, 10)
        self._syncmidPos = self._syncmidPos > 0
        config, self._blindMidSteps = divmod(config, 100)
        config, self._blindCloseSecs = divmod(config, 100)
        config, self._blindOpenSecs = divmod(config, 100)

        self._blindMaxSteps = int(self._blindMidSteps * 2)
        self._supportmidCommand = True

        _LOGGER.info("New slatted config," +
                     " config=" + str(signal_repetitions) +
                     " midSteps=" + str(self._blindMidSteps) +
                     " maxSteps=" + str(self._blindMaxSteps) +
                     " openSecs=" + str(self._blindOpenSecs) +
                     " closeSecs=" + str(self._blindCloseSecs) +
                     " syncmidPos=" + str(self._syncmidPos))

    async def async_added_to_hass(self):
        """Restore device state."""
        _LOGGER.debug("Called async_added_to_hass")

        self._available = True
        self._blind_position = BLIND_POS_OPEN
        self._tilt_step = self._blindMidSteps
        self._state = STATE_OPEN

        await super().async_added_to_hass()

        # if self._event is None:
        #     old_state = await self.async_get_last_state()
        #     if old_state is not None:
        #         self._state = old_state.state == STATE_OPEN

    @ property
    def available(self) -> bool:
        """Return true if device is available - not sure what makes it unavailable."""
        _LOGGER.debug("Returned available attribute = " + str(self._available))
        return self._available

    @ property
    def current_cover_tilt_position(self):
        """Return the current tilt position property."""
        if self._tilt_position == 0:
            tilt = TILT_POS_CLOSED
        elif self._tilt_position == self._blindMidSteps:
            tilt = TILT_POS_MID
        elif self._tilt_position >= self._blindMaxSteps:
            tilt = TILT_POS_OPEN
        else:
            tilt = TILT_POS_OPEN / self._blindMaxSteps

        _LOGGER.debug(
            "Returned current_cover_tilt_position attribute = " + str(tilt))
        return tilt

    @property
    def current_cover_position(self):
        """Return the current cover position property."""
        if self._blind_position == BLIND_POS_CLOSED and self._tilt_position > 0:
            position = BLIND_POS_TILTED
        elif self._blind_position == BLIND_POS_CLOSED or self._blind_position == BLIND_POS_OPEN:
            position = self._blind_position
        else:
            position = BLIND_POS_STOPPED
        _LOGGER.debug(
            "Returned current_cover_position attribute = " + str(position))
        return position

    @property
    def is_opening(self):
        """Return the is_opening property."""
        opening = self._state == STATE_OPENING
        _LOGGER.debug("Returned is_opening attribute = " + str(opening))
        return opening

    @property
    def is_closing(self):
        """Return the is_closing property."""
        closing = self._state == STATE_CLOSING
        _LOGGER.debug("Returned is_closing attribute = " + str(closing))
        return closing

    @property
    def is_closed(self):
        """Return the is_closed property."""
        closed = self._state == STATE_CLOSED
        _LOGGER.debug("Returned is_closed attribute = " + str(closed))
        return closed

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
    # mid position. If the blind is in motion then is ignored.

    async def async_open_cover(self, **kwargs):
        """Open the cover by selecting the mid position."""
        _LOGGER.debug("Invoked async_open_cover")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Opening blind by selecting mid position...")
            await self._async_set_cover_mid_position()

    # Requests to close the blind. If the blind is in motion then is ignored. Otherwise always close the blind so
    # that we can be sure the blind is closed.

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.debug("Invoked async_close_cover")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            # We need to wait if either the blind is open or it is closed but not in the closed position
            isLong = self._state == STATE_OPEN or (
                self._state == STATE_CLOSED and self._blind_position != BLIND_POS_CLOSED)

            self._state = STATE_CLOSING
            if isLong:
                _LOGGER.info("Closing blind with a delay...")
                self._blind_position = BLIND_POS_STOPPED
                self._tilt_position = 0
                self.async_write_ha_state()
                # self.schedule_update_ha_state(True)
            else:
                _LOGGER.info("Closing blind with no delay...")

            # close blind
            await self._async_close_blind()

            if isLong:
                _LOGGER.debug("Waiting blind close secs " +
                              str(self._blindCloseSecs))
                await asyncio.sleep(self._blindCloseSecs)

            # If the blind is still closing then we have finished. Otherwise assume we were interrupted
            if self._state == STATE_CLOSING:
                _LOGGER.info(
                    "Finished closing blind - setting blind to closed")

                self._state = STATE_CLOSED
                self._blind_position = BLIND_POS_CLOSED
                self._tilt_position = 0
                self.async_write_ha_state()
                # self.schedule_update_ha_state(True)
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
            await self._async_stop_blind()

            self._state = STATE_CLOSED
            self._blind_position = BLIND_POS_STOPPED
            self._tilt_position = 0
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
                    "Requested position is before mid state - will close blind...")
                await self.async_close_cover(**kwargs)
            elif position < BLIND_POS_WILLOPEN:
                _LOGGER.debug(
                    "Requested position is before open state - will select mid position...")
                await self._async_set_cover_mid_position(**kwargs)
            else:
                _LOGGER.info(
                    "Requested position is after open state - will open with a delay...")
                self._state = STATE_OPENING
                self._blind_position = BLIND_POS_STOPPED
                self._tilt_position = 0
                self.async_write_ha_state()
                # self.schedule_update_ha_state(True)

                # Open blind
                await self._async_open_blind()

                # Wait for blind to open and then set state open
                _LOGGER.debug("Waiting blind open secs " +
                              str(self._blindOpenSecs))
                await asyncio.sleep(self._blindOpenSecs)

                # If the blind is still opening then we have finished. Otherwise assume we were interrupted
                if self._state == STATE_OPENING:
                    _LOGGER.info(
                        "Finished opening blind - setting blind to open")
                    self._state = STATE_OPEN
                    self._blind_position = BLIND_POS_OPEN
                    self._tilt_position = self._blindMaxSteps
                    self.async_write_ha_state()
                    # self.schedule_update_ha_state(True)
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
            _LOGGER.debug("Opening blind by selecting mid position...")
            await self._async_set_cover_mid_position()

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        _LOGGER.debug("Invoked async_close_cover_tilt")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Tilting by closing blind...")
            await self.async_close_cover(**kwargs)

    async def async_set_cover_tilt_to_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        _LOGGER.debug("Invoked async_set_cover_tilt_position")

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        elif self._state == STATE_OPEN:
            _LOGGER.debug(
                "Blind is open - switching to mid position operation")
            await self._async_set_cover_mid_position()
        elif self._state == STATE_CLOSED and self._blind_position != BLIND_POS_CLOSED:
            _LOGGER.debug(
                "Blind is partially closed - switching to mid position operation")
            await self._async_set_cover_mid_position()
        else:
            if ATTR_TILT_POSITION in kwargs:
                tilt_position = kwargs[ATTR_TILT_POSITION]
            else:
                tilt_position = TILT_POS_MID

            if tilt_position == TILT_POS_MID:
                _LOGGER.debug(
                    "mid position requested - switching to mid position operation")
                await self._async_set_cover_mid_position(**kwargs)
            elif tilt_position == 0:
                _LOGGER.debug(
                    "End position requested - switching to close operation")
                await self.async_close_cover(**kwargs)
            else:
                target = round(tilt_position / TILT_POS_MID *
                               self._blindMidSteps)
                steps = target - self._tilt_position

                _LOGGER.info(
                    "Tilting to required position; position=" + str(tilt_position) +
                    " target=" + str(target) +
                    " from=" + str(self._tilt_position) +
                    " steps=" + str(steps))

                if (target == self._blindMidSteps):
                    _LOGGER.debug(
                        "Tilt is to mid point - switching to mid position operation")
                    await self._async_set_cover_mid_position()
                else:
                    if self._syncmidPos:
                        if steps < 0 and target < self._blindMidSteps and self._tilt_step > self._blindMidSteps:
                            steps = steps + \
                                (self._tilt_step - self._blindMidSteps)
                            _LOGGER.info(
                                "Tilt crosses mid point from high - syncing mid position; steps remaining=" + str(steps))
                            await self._async_set_cover_mid_position()
                        elif steps > 0 and target > self._blindMidSteps and self._tilt_step < self._blindMidSteps:
                            steps = steps - \
                                (self._blindMidSteps - self._tilt_step)
                            _LOGGER.info(
                                "Tilt crosses mid point from low - syncing mid position; steps remaining=" + str(steps))
                            await self._async_set_cover_mid_position()

                    self._tilt_step = target

                    # Tilt blind
                    for step in range(abs(steps)):
                        if steps > 0:
                            await self._async_tilt_blind_forward()
                        else:
                            await self._async_tilt_blind_back()

                    self.async_write_ha_state()
                    # self.schedule_update_ha_state(True)

    async def _async_set_cover_mid_position(self):
        """Move the cover tilt to a preset position."""
        _LOGGER.debug("Invoked _async_set_cover_mid_position")
        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            longOperation = self._state == STATE_OPEN or (
                self._state == STATE_CLOSED and self._blind_position != BLIND_POS_CLOSED)

            if longOperation:
                _LOGGER.info("Setting mid position with a delay...")
                self._state = STATE_CLOSING
                self._blind_position = BLIND_POS_STOPPED
                self._tilt_position = 0
                self.async_write_ha_state()
                # self.schedule_update_ha_state(True)
            else:
                _LOGGER.info("Setting mid position with no delay...")

            # set mid position blind
            await self._async_set_cover_mid_position()

            if longOperation:
                _LOGGER.debug("Waiting blind close secs " +
                              str(self._blindCloseSecs))
                await asyncio.sleep(self._blindCloseSecs)

                # If the blind is still opening then we have finished. Otherwise assume we were interrupted
                if self._state == STATE_CLOSING:
                    _LOGGER.info("Finished setting mid position")
                    self._state = STATE_CLOSED
                    self._blind_position = BLIND_POS_CLOSED
                    self._tilt_position = self._blindMidSteps
                    self.async_write_ha_state()
                    # self.schedule_update_ha_state(True)
                else:
                    _LOGGER.info(
                        "Finished setting mid position - blind is not closing so not setting to closed")
            else:
                _LOGGER.info("Finished setting mid position")
                self._blind_position = BLIND_POS_CLOSED
                self._tilt_position = self._blindMidSteps
                self.async_write_ha_state()
                # self.schedule_update_ha_state(True)

    # Handle updates from cover device

    async def async_update(self):
        """Query the switch in this light switch and determine the state."""
        _LOGGER.debug("Invoked async_update")

    def _apply_event(self, event):
        """Apply command from rfxtrx."""
        _LOGGER.debug("Invoked _apply_event")
        super()._apply_event(event)

    @callback
    def _handle_event(self, event, device_id):
        """Check if event applies to me and update."""
        _LOGGER.debug("Invoked _handle_event")
        if device_id != self._device_id:
            return

        self._apply_event(event)

        self.async_write_ha_state()

    # Implementations for device specific actions

    async def _async_close_blind(self):
        """Callback to open the blind"""
        await self._async_send(self._device.send_close)

    async def _async_open_blind(self):
        """Callback to open the blind"""
        await self._async_send(self._device.send_open)

    async def _async_stop_blind(self):
        """Callback to open the blind"""
        await self._async_send(self._device.send_stop)

    async def _async_tilt_blind_to_mid(self):
        """Callback to open the blind"""

    async def _async_tilt_blind_forward(self):
        """Callback to open the blind"""

    async def _async_tilt_blind_back(self):
        """Callback to open the blind"""
