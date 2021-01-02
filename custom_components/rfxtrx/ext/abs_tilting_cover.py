"""Light support for switch entities."""
import logging
import asyncio
import time
from typing import Any, Callable, Optional, Sequence, cast

from .. import RfxtrxCommandEntity

from homeassistant.components.cover import (
    DEVICE_CLASS_BLIND,
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_OPEN_TILT,
    SUPPORT_CLOSE_TILT,
    SUPPORT_STOP_TILT,
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
BLIND_POS_TILTED_MAX = 99
BLIND_POS_STOPPED = 50
BLIND_POS_TILTED_MIN = 1
BLIND_POS_CLOSED = 0

# Values returned for tilt position in various states
TILT_POS_CLOSED_MAX = 100
TILT_POS_OPEN = 50
TILT_POS_STOPPED = 25
TILT_POS_CLOSED_MIN = 0


# mypy: allow-untyped-calls, allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Blinds Control"

AUTO_STEP_CLICK_SEC = 2
COMMAND_DEBOUNCE_SEC = 0.5


# Represents a cover entity that has slats - either vertical or horizontal. Thios differs from a cover in that:
# - Opening the blind tilts the slats to allow light. Not moving the blind out of the window
# - Closing the blind requires the blind to be fully lowered into the window and the slats to be in a tilted position
#
# Properties:
#   Config:
#     _blindMaxSteps - number of steps to tilt the blind from fully tilted to the mid position
#     _blindMidSteps - number of steps to tilt the blind from fully tilted to the mid position
#     _hasMidCommand - Boolean - TRUE if the blind has an explicit command for the mid position
#     _syncMidPos - boolean - TRUE if we should send a "mid" position command each time we cross the mid position
#     _blindCloseSecs - number of seconds to wait for the blind to fully close from fully open position
#     _blindOpenSecs - number of seconds to wait for the blind to fully open from fully closed position
#   State:
#     _blind_position - reported position of the blind
#     _tilt_step - step posiotion of the tilt - related to the _tilt_position
#     _state - what the blind is curfrently doing - STATE_OPEN/STATE_OPENING/STATE_CLOSED/STATE_CLOSING
#
class AbstractTiltingCover(RfxtrxCommandEntity, CoverEntity):
    """Representation of a RFXtrx cover supporting tilt and, optionally, lift."""

    def __init__(self, device, device_id, signal_repetitions, event, midSteps, hasMid, hasLift, syncMid, openSecs, closeSecs, stepMs):
        self._syncMidPos = syncMid
        self._hasMidCommand = hasMid
        self._hasLift = hasLift
        self._blindMidSteps = midSteps
        self._blindCloseSecs = closeSecs
        self._blindOpenSecs = openSecs
        self._blindStepMs = stepMs
        self._blindMaxSteps = int(self._blindMidSteps * 2)

        super().__init__(device, device_id, signal_repetitions, event)

        _LOGGER.info("New tilting cover config," +
                     " signal_repetitions=" + str(signal_repetitions) +
                     " midSteps=" + str(self._blindMidSteps) +
                     " maxSteps=" + str(self._blindMaxSteps) +
                     " openSecs=" + str(self._blindOpenSecs) +
                     " closeSecs=" + str(self._blindCloseSecs) +
                     " stepMs=" + str(self._blindStepMs) +
                     " hasLift=" + str(self._hasLift) +
                     " hasMidCommand=" + str(self._hasMidCommand) +
                     " syncMidPos=" + str(self._syncMidPos))

    async def async_added_to_hass(self):
        """Restore device state."""
        _LOGGER.debug("Called async_added_to_hass")

        self._blind_position = BLIND_POS_OPEN
        self._tilt_position = 0
        self._state = STATE_OPEN
        self._lastStopTime = time.time()
        self._autoStepActive = False
        self._autoStepDirection = 0
        self._lastCommandTime = time.time()

        await super().async_added_to_hass()

        if self._event is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                if 'current_tilt_position' in old_state.attributes:
                    _LOGGER.info("State = " + str(old_state))
                    self._blind_position = old_state.attributes['current_position']
                    tilt = old_state.attributes['current_tilt_position']
                    if not(self._hasLift) or self._blind_position <= BLIND_POS_TILTED_MAX:
                        self._state = STATE_CLOSED
                        self._blind_position = BLIND_POS_CLOSED
                        self._tilt_position = self._tilt_to_steps(tilt)
                    else:
                        self._state = STATE_OPEN
                        self._blind_position = BLIND_POS_OPEN
                        self._tilt_position = self._blindMidSteps

                    _LOGGER.info("Recovered state=" + str(self._state) +
                                 " position=" + str(self._blind_position) +
                                 " tilt=" + str(self._tilt_position))

    @property
    def available(self) -> bool:
        """Return true if device is available - not sure what makes it unavailable."""
        return True

    @property
    def current_cover_tilt_position(self):
        """Return the current tilt position property."""
        if self._tilt_position == 0:
            tilt = TILT_POS_CLOSED_MIN
        elif self._tilt_position == self._blindMidSteps:
            tilt = TILT_POS_OPEN
        elif self._tilt_position >= self._blindMaxSteps:
            tilt = TILT_POS_CLOSED_MAX
        else:
            tilt = self._steps_to_tilt(self._tilt_position)

        _LOGGER.debug(
            "Returned current_cover_tilt_position attribute = " + str(tilt))
        return tilt

    @property
    def current_cover_position(self):
        """Return the current cover position property."""
        if self._blind_position == BLIND_POS_CLOSED:
            if self._tilt_position == 0:
                position = BLIND_POS_CLOSED
            else:
                position = BLIND_POS_TILTED_MIN
        elif self._blind_position == BLIND_POS_OPEN:
            position = BLIND_POS_OPEN
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
        closed = self._state == STATE_CLOSED and self._tilt_position == 0
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
        return SUPPORT_CLOSE | SUPPORT_OPEN | SUPPORT_STOP | SUPPORT_OPEN_TILT | SUPPORT_CLOSE_TILT | SUPPORT_STOP_TILT | SUPPORT_SET_TILT_POSITION | SUPPORT_SET_POSITION

    @property
    def should_poll(self):
        """No polling needed for a RFXtrx switch."""
        return False

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return False

    # Requests to open the blind. In practice we do not open then blind, we will instead tilt to the
    # mid position. If the blind is in motion then is ignored.

    async def async_open_cover(self, **kwargs):
        """Open the cover by selecting the mid position."""
        _LOGGER.info("Invoked async_open_cover")

        if self._blind_is_in_motion():
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Opening blind by selecting mid position...")
            await self._async_set_cover_mid_position()

    # Requests to close the blind. If the blind is in motion then is ignored. Otherwise always close the blind so
    # that we can be sure the blind is closed.

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.info("Invoked async_close_cover")

        if self._blind_is_in_motion():
            _LOGGER.info("Blind is in motion - will ignore request")
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
        _LOGGER.info("Invoked async_stop_cover")

        if not self._hasLift:
            _LOGGER.info("Blind does not lift - ignoring the request")
        elif self._blind_is_in_motion():
            _LOGGER.info(
                "Blind is in motion - stopping blind and marking as partially closed")

            # Stop the blind
            await self._async_stop_blind()

            self._state = STATE_OPEN
            self._blind_position = BLIND_POS_STOPPED
            self._tilt_position = 0
            self.async_write_ha_state()
        else:
            _LOGGER.info("Blind is stationary - ignoring the request")

    # Requests to set the position of the blind. If the blind is in motion then is ignored. We will use this
    # to allow the blind to actually be opened. If the position is after the mid point then change into a close
    # command which will ensure the blind is closed. Otherwise set he state to OPENING and open the blind.
    # Then after a delay and marks as OPEN if the blind is still OPENING.

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _LOGGER.info("Invoked async_set_cover_position")

        if self._blind_is_in_motion():
            _LOGGER.info("Blind is in motion - will ignore request")
        elif self._ignore_bounce():
            _LOGGER.info("Duplicate command - will ignore request")
        elif ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            if position < BLIND_POS_STOPPED:
                _LOGGER.info(
                    "Requested position is before mid state - will close blind...")
                await self.async_close_cover(**kwargs)
            elif position <= BLIND_POS_TILTED_MAX:
                _LOGGER.info(
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
        _LOGGER.info("Invoked async_open_cover_tilt")

        if self._autoStepActive:
            self._autoStepDirection = 1
            if (time.time() - self._lastStopTime) < AUTO_STEP_CLICK_SEC:
                _LOGGER.info("Auto tilting open_cover_tilt...")
                while self._autoStepDirection > 0 and self._autoStepActive and self._tilt_position < self._blindMaxSteps:
                    await self._async_set_cover_tilt_position(self._tilt_position + self._autoStepDirection)
                    if self._tilt_position < self._blindMaxSteps:
                        await asyncio.sleep(self._blindStepMs / 1000)
            else:
                _LOGGER.info("Disabled auto advance of cover_tilt")
            self._autoStepActive = False
        elif self._tilt_position < self._blindMaxSteps:
            await self._async_set_cover_tilt_position(self._tilt_position + 1)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        _LOGGER.info("Invoked async_close_cover_tilt")

        if self._autoStepActive:
            self._autoStepDirection = -1
            if (time.time() - self._lastStopTime) < AUTO_STEP_CLICK_SEC:
                _LOGGER.info("Auto tilting close_cover_tilt...")
                while self._autoStepDirection < 0 and self._autoStepActive and self._tilt_position > 0:
                    await self._async_set_cover_tilt_position(self._tilt_position + self._autoStepDirection)
                    if self._tilt_position > 0:
                        await asyncio.sleep(self._blindStepMs / 1000)
            else:
                _LOGGER.info("Disabled auto advance of cover_tilt")
            self._autoStepActive = False
        elif self._tilt_position > 0:
            await self._async_set_cover_tilt_position(self._tilt_position - 1)
        else:
            await self.async_close_cover(**kwargs)

    async def async_stop_cover_tilt(self, **kwargs):
        """Stop the cover."""
        _LOGGER.info("Invoked async_stop_cover_tilt")

        lastStop = self._lastStopTime
        now = time.time()
        self._lastStopTime = now

        self._autoStepActive = (now - lastStop) < AUTO_STEP_CLICK_SEC
        if self._autoStepActive:
            _LOGGER.info("Enabled auto advance of cover_tilt")
            self._autoStepDirection = 0
        else:
            _LOGGER.info("Disabled auto advance of cover_tilt")

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        _LOGGER.info("Invoked async_set_cover_tilt_position")

        if self._blind_is_in_motion():
            _LOGGER.info("Blind is in motion - will ignore request")
        elif self._ignore_bounce():
            _LOGGER.info("Duplicate command - will ignore request")
        elif self._state == STATE_OPEN:
            _LOGGER.info(
                "Blind is open - switching to mid position operation")
            await self._async_set_cover_mid_position()
        elif self._state == STATE_CLOSED and self._blind_position != BLIND_POS_CLOSED:
            _LOGGER.info(
                "Blind is partially closed - switching to mid position operation")
            await self._async_set_cover_mid_position()
        else:
            if ATTR_TILT_POSITION in kwargs:
                tilt_position = kwargs[ATTR_TILT_POSITION]
            else:
                tilt_position = TILT_POS_OPEN

            if tilt_position == self._blindMidSteps:
                _LOGGER.info(
                    "Tilt is to mid point - switching to mid position operation")
                await self._async_set_cover_mid_position()
            else:
                await self._async_set_cover_tilt_position(self._tilt_to_steps(tilt_position))

    async def _async_set_cover_tilt_position(self, tilt_position, syncMidPos=True):
        """Move the cover tilt to a specific position."""
        _LOGGER.info("Invoked _async_set_cover_tilt_position")

        if self._blind_is_in_motion():
            _LOGGER.info("Blind is in motion - will ignore request")
        elif self._state == STATE_OPEN:
            _LOGGER.info(
                "Blind is open - switching to mid position operation")
            await self._async_set_cover_mid_position()
        elif self._state == STATE_CLOSED and self._blind_position != BLIND_POS_CLOSED:
            _LOGGER.info(
                "Blind is partially closed - switching to mid position operation")
            await self._async_set_cover_mid_position()
        else:
            steps = tilt_position - self._tilt_position

            _LOGGER.info(
                "Tilting to required position; " +
                " target=" + str(tilt_position) +
                " from=" + str(self._tilt_position) +
                " steps=" + str(steps))

            if steps != 0:
                if self._syncMidPos and syncMidPos:
                    if steps < 0 and tilt_position < self._blindMidSteps and self._tilt_position > self._blindMidSteps:
                        steps = steps + \
                            (self._tilt_position - self._blindMidSteps)
                        _LOGGER.info(
                            "Tilt crosses mid point from high - syncing mid position; steps remaining=" + str(steps))
                        await self._async_set_cover_mid_position()
                    elif steps > 0 and tilt_position > self._blindMidSteps and self._tilt_position < self._blindMidSteps:
                        steps = steps - \
                            (self._blindMidSteps - self._tilt_position)
                        _LOGGER.info(
                            "Tilt crosses mid point from low - syncing mid position; steps remaining=" + str(steps))
                        await self._async_set_cover_mid_position()
                self._tilt_position = await self._async_tilt_blind_to_step(steps, tilt_position)

            self.async_write_ha_state()

    async def _async_set_cover_mid_position(self):
        """Move the cover tilt to a preset position."""
        _LOGGER.info("Invoked _async_set_cover_mid_position")

        if self._blind_is_in_motion():
            _LOGGER.info("Blind is in motion - will ignore request")
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
            await self._async_tilt_blind_to_mid()

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

    # Helper functions

    def _ignore_bounce(self):
        last = self._lastCommandTime
        self._lastCommandTime = time.time()
        return (self._lastCommandTime - last) <= COMMAND_DEBOUNCE_SEC

    def _blind_is_in_motion(self):
        return self._state == STATE_OPENING or self._state == STATE_CLOSING

    def _tilt_to_steps(self, tilt):
        steps = min(round(tilt / 50 * self._blindMidSteps),
                    self._blindMaxSteps)
        return steps

    def _steps_to_tilt(self, steps):
        tilt = min(round(steps / self._blindMidSteps * 50), 100)
        return tilt

    async def _async_send_command(self, cmd):
        """Send a command to the blind"""
        _LOGGER.info("LOW-LEVEL SENDING BLIND COMMAND - " + str(cmd))
        await self._async_send(self._device.send_command, cmd)

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

    # --------------------------------------------------------------------------------
    # Implementations for device specific actions

    # Replace this function if stepping the slats is not a linear operation
    async def _async_tilt_blind_to_step(self, steps, target):
        # Tilt blind
        for step in range(abs(steps)):
            if steps > 0:
                await self._async_tilt_blind_forward()
            else:
                await self._async_tilt_blind_back()
        return target

    # Replace with action to close blind
    async def _async_close_blind(self):
        """Callback to close the blind"""
        _LOGGER.info("LOW-LEVEL CLOSING BLIND")
        # await self._async_send(self._device.send_close)

    # Replace with action to open blind
    async def _async_open_blind(self):
        """Callback to open the blind"""
        _LOGGER.info("LOW-LEVEL OPENING BLIND")
        # await self._async_send(self._device.send_open)

    # Replace with action to stop blind
    async def _async_stop_blind(self):
        """Callback to stop the blind"""
        _LOGGER.info("LOW-LEVEL STOPPING BLIND")
        # await self._async_send(self._device.send_stop)

    # Replace with action to tilt blind to mid position
    async def _async_tilt_blind_to_mid(self):
        """Callback to tilt the blind to mid"""
        _LOGGER.info("LOW-LEVEL TILTING BLIND TO MID")

    # Replace with action to tilt blind forward one step
    async def _async_tilt_blind_forward(self):
        """Callback to tilt the blind forward"""
        _LOGGER.info("LOW-LEVEL TILTING BLIND FORWARD")

    # Replace with action to tilt blind backward one step
    async def _async_tilt_blind_back(self):
        """Callback to tilt the blind backward"""
        _LOGGER.info("LOW-LEVEL TILTING BLIND BACKWARD")
