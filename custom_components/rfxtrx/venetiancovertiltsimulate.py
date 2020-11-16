"""Light support for switch entities."""
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

TILT_POS_OPEN = 100
TILT_POS_HOME = 50
TILT_POS_STOPPED = 25
TILT_POS_CLOSED = 0
BLIND_POS_OPEN = 100
BLIND_POS_STOPPED = 50
BLIND_POS_WILLOPEN = 75
BLIND_POS_TILTED = 1
BLIND_POS_CLOSED = 0

TILT_STEP_CLOSED = 0
TILT_STEP_DOWN = 1
TILT_STEP_HOME = 2
TILT_STEP_UP = 3

# mypy: allow-untyped-calls, allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Blinds Control"


class VenetianCoverTiltSimulate(RfxtrxCommandEntity, CoverEntity):
    # class VenetianCover(CoverEntity):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, signal_repetitions, event=None):
        """Initialzie a switch or light device."""
        super().__init__(device, device_id, 1, event)

        _LOGGER.info("Creating venetian cover with tilt simulation, signal_repetitions param=",
                     str(signal_repetitions))

        if signal_repetitions < 1000:
            # Default 40 secs up and down, 5 secs full tilt to my, 4 secs full tilt to close, 3.15 secs tilt down, 1.35 secs tilt up
            config = 404050406327
        else:
            config = signal_repetitions

        # tilt info OOCCMMTTUUDD
        # OO: Secs to open blind completely
        # CC: Secs to close blind completely
        # MM: Deci-Secs to move from fully filted up to my position
        # TT: Deci-Secs to move from fully tilted up to fully closed
        # UU: Deci-Secs to move from fully closed to up tilted
        # DD: Deci-Secs to move from fully closed to down tilted
    
        config, self._tiltToDownPosSecs = divmod(config, 100)
        config, self._tiltToUpPosSecs = divmod(config, 100)
        config, self._fullTiltToCloseSecs = divmod(config, 100)
        config, self._fullTiltToHomeSecs = divmod(config, 100)
        config, self._openToCloseSecs = divmod(config, 100)
        config, self._closeToOpenSecs = divmod(config, 100)

        self._tiltToDownPosSecs = self._tiltToDownPosSecs / 20 # Time to tilt up to down tilt position
        self._tiltToUpPosSecs = self._tiltToUpPosSecs / 20 # Time to tilt up to up tilt position
        self._fullTiltToCloseSecs = self._fullTiltToCloseSecs / 10 # Time for tilt from up to fully closed
        self._fullTiltToHomeSecs = self._fullTiltToHomeSecs / 10 # Time to tilt from up to my tilt 

        _LOGGER.info("New Venetian config," +
                     " config=" + str(signal_repetitions) +
                     " tiltToDownPosSecs=" + str(self._tiltToDownPosSecs) +
                     " tiltToUpPosSecs=" + str(self._tiltToUpPosSecs) +
                     " fullTiltToCloseSecs=" + str(self._fullTiltToCloseSecs) +
                     " fullTiltToHomeSecs=" + str(self._fullTiltToHomeSecs) +
                     " openSecs=" + str(self._closeToOpenSecs) +
                     " closeSecs=" + str(self._openToCloseSecs))

    async def async_added_to_hass(self):
        """Restore device state."""
        _LOGGER.debug("Called async_added_to_hass")

        self._available = True
        self._state = STATE_OPEN
        self._stateUnknown = True
        self._tiltStep = TILT_STEP_CLOSED

        await super().async_added_to_hass()

        if self._event is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                if 'current_tilt_position' in old_state.attributes:
                    _LOGGER.info("State " + str(old_state))
                    position = old_state.attributes['current_position']
                    tilt = old_state.attributes['current_tilt_position']
                    if position <= 10:
                        self._state = STATE_CLOSED
                        self._stateUnknown = False
                        self._tiltStep = int(tilt // 25)
                    elif position >= 90:
                        self._state = STATE_OPEN
                        self._stateUnknown = False

                    _LOGGER.info("New state=" + str(self._state) +
                                " tiltStep=" + str(self._tiltStep))

    @property
    def available(self) -> bool:
        """Return true if device is available - not sure what makes it unavailable."""
        _LOGGER.debug("Returned available attribute = " + str(self._available))
        return self._available

    @property
    def current_cover_tilt_position(self):
        """Return the current tilt position property."""
        if self._stateUnknown:
            position = TILT_POS_CLOSED
        elif self._state == STATE_OPEN:
            position = TILT_POS_OPEN
        elif self._state == STATE_OPENING or self._state == STATE_CLOSING:
            position = TILT_POS_CLOSED
        else:
            if self._tiltStep == TILT_STEP_CLOSED:
                position = TILT_POS_CLOSED
            elif self._tiltStep == TILT_STEP_HOME:
                position = TILT_POS_HOME
            else:
                position = self._tiltStep * 25

        _LOGGER.debug("Returned current_cover_tilt_position attribute = " + str(position))
        return position

    @property
    def current_cover_position(self):
        """Return the current cover position property."""
        if self._stateUnknown:
            position = BLIND_POS_STOPPED
        elif self._state == STATE_CLOSED:
            if self._tiltStep == TILT_STEP_CLOSED:
                position = BLIND_POS_CLOSED
            else:
                position = BLIND_POS_TILTED
        elif self._state == STATE_OPEN:
            position = BLIND_POS_OPEN
        else:
            position = BLIND_POS_STOPPED

        _LOGGER.debug("Returned current_cover_position attribute = " + str(position))
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
        return DEVICE_CLASS_BLIND

    @property
    def supported_features(self):
        """Flag supported features."""
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
        """Open the cover by selecting the my position."""
        _LOGGER.debug("Invoked async_open_cover")

        if self.should_ignore_action():
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Opening blind by selecting my position...")
            await self.async_set_cover_my_position(**kwargs)

    # Requests to close the blind. If the blind is in motion then is ignored. Otherwise always close the blind so
    # that we can be sure the blind is closed.

    async def async_close_cover(self, **kwargs):
        """Close the cover."""
        _LOGGER.debug("Invoked async_close_cover")

        if self.should_ignore_action():
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            state = self._state
            self._state = STATE_CLOSING
            self._stateUnknown = True
            self.async_write_ha_state()

            _LOGGER.info("Closing blind...")
            await self._async_send(self._device.send_close)
            await self._async_send(self._device.send_close)

            if state != STATE_CLOSED:
                _LOGGER.debug("Waiting blind close secs " + str(self._openToCloseSecs))
                await asyncio.sleep(self._openToCloseSecs)
            else:
                _LOGGER.debug("Waiting blind full tilt to closed secs " + str(self._fullTiltToCloseSecs))
                await asyncio.sleep(self._fullTiltToCloseSecs)

            # If the blind is still closing then we have finished. Otherwise assume we were interrupted
            if self._state == STATE_CLOSING:
                _LOGGER.info("Finished closing blind - setting blind to closed")

                self._state = STATE_CLOSED
                self._stateUnknown = False
                self._tiltStep = TILT_STEP_CLOSED
                self.async_write_ha_state()
            else:
                _LOGGER.info("Finished closing blind - blind is not closing so not setting to closed")

    # Requests to stop the blind. If the blind is not in motion then is ignored. Otherwise assume the blind
    # is in a mid position.

    async def async_stop_cover(self, **kwargs):
        """Stop the cover."""
        _LOGGER.debug("Invoked async_stop_cover, state=" + self._state)

        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            _LOGGER.info("Blind is in motion - stopping blind and marking as partially closed")

            # Stop the blind
            await self._async_send(self._device.send_stop)

            # Now we don't know eher we are!
            self._state = STATE_OPEN
            self._stateUnknown = True
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

        if self.should_ignore_action():
            _LOGGER.debug("Blind is in motion - will ignore request")
        elif ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            if position < BLIND_POS_STOPPED:
                _LOGGER.debug("Requested position is before mid state - will close blind...")
                await self.async_close_cover(**kwargs)
            elif position < BLIND_POS_WILLOPEN:
                _LOGGER.debug("Requested position is before open state - will select my position...")
                await self.async_set_cover_my_position(**kwargs)
            else:
                _LOGGER.info("Requested position is after open state - will open with a delay...")
                self._state = STATE_OPENING
                self._stateUnknown = True
                self.async_write_ha_state()

                # Open blind
                await self._async_send(self._device.send_open)
                await self._async_send(self._device.send_open)

                # Wait for blind to open and then set state open
                _LOGGER.debug("Waiting blind open secs " + str(self._closeToOpenSecs))
                await asyncio.sleep(self._closeToOpenSecs)

                # If the blind is still opening then we have finished. Otherwise assume we were interrupted
                if self._state == STATE_OPENING:
                    _LOGGER.info("Finished opening blind - setting blind to open")

                    self._state = STATE_OPEN
                    self._stateUnknown = False
                    self.async_write_ha_state()
                else:
                    _LOGGER.info("Finished opening blind - blind is not opening so not setting to open")
        else:
            _LOGGER.error("No position specified for set_cover_position")

    # Request to open the blind with a tilt

    async def async_open_cover_tilt(self, **kwargs):
        """Open the cover tilt."""
        _LOGGER.debug("Invoked async_open_cover_tilt")

        if self.should_ignore_action():
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Opening blind by selecting my position...")
            await self.async_set_cover_my_position(**kwargs)

    async def async_close_cover_tilt(self, **kwargs):
        """Close the cover tilt."""
        _LOGGER.debug("Invoked async_close_cover_tilt")

        if self.should_ignore_action():
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            _LOGGER.debug("Tilting by closing blind...")
            await self.async_close_cover(**kwargs)

    async def async_set_cover_tilt_position(self, **kwargs):
        """Move the cover tilt to a specific position."""
        _LOGGER.debug("Invoked async_set_cover_tilt_position")

        if self.should_ignore_action():
            _LOGGER.debug("Blind is in motion - will ignore request")
        elif self._state == STATE_OPEN:
            _LOGGER.debug("Blind is open - switching to my position operation")
            await self.async_set_cover_my_position(**kwargs)
        elif self._stateUnknown:
            _LOGGER.debug("Blind position is unknown - switching to my position operation")
            await self.async_set_cover_my_position(**kwargs)
        else:
            if ATTR_TILT_POSITION in kwargs:
                tiltPosition = kwargs[ATTR_TILT_POSITION]
            else:
                tiltPosition = TILT_POS_HOME

            if tiltPosition <= 5:
                tiltStep = TILT_POS_CLOSED
            elif tiltPosition <= 40:
                tiltStep = TILT_STEP_DOWN
            elif tiltPosition <= 60:
                tiltStep = TILT_STEP_HOME
            else:
                tiltStep = TILT_STEP_UP

            if tiltStep == self._tiltStep:
                _LOGGER.debug("Current tilt position requested - will ignore request")
            elif tiltStep == TILT_STEP_HOME:
                _LOGGER.debug("My position requested - switching to my position operation")
                await self.async_set_cover_my_position(**kwargs)
            elif tiltStep == TILT_STEP_CLOSED:
                _LOGGER.debug("End position requested - switching to close operation")
                await self.async_close_cover(**kwargs)
            else:
                state = self._state
                self._state = STATE_OPENING
                self.async_write_ha_state()

                _LOGGER.debug("Closing blind before set position operation...")
                await self._async_send(self._device.send_close)
                if state == STATE_CLOSED and self._tiltStep == TILT_STEP_CLOSED:
                    _LOGGER.debug("Skipping wait for close operation as we are closed")
                else:
                    _LOGGER.debug("Waiting for close secs " + str(self._fullTiltToCloseSecs))
                    await asyncio.sleep(self._fullTiltToCloseSecs)

                # If the blind is still opening then we need to do the next step. Otherwise assume we were interrupted
                if self._state == STATE_OPENING:
                    _LOGGER.info("Attempting to open blind to tilt position...")
                    await self._async_send(self._device.send_open)
                    await self._async_send(self._device.send_open)

                    if tiltStep == TILT_STEP_DOWN:
                        _LOGGER.debug("Waiting blind down tilt secs " + str(self._tiltToDownPosSecs))
                        await asyncio.sleep(self._tiltToDownPosSecs)
                    elif tiltStep == TILT_STEP_UP:
                        _LOGGER.debug("Waiting blind up tilt secs " + str(self._tiltToUpPosSecs))
                        await asyncio.sleep(self._tiltToUpPosSecs)

                    # If the blind is still opening then we need to do the next step. Otherwise assume we were interrupted
                    if self._state == STATE_OPENING:
                        _LOGGER.debug("Stopping blind at near position")
                        await self._async_send(self._device.send_stop)

                # If the blind is still opening then we have finished. Otherwise assume we were interrupted
                if self._state == STATE_OPENING:
                    _LOGGER.info("Finished setting tilt position")
                    self._state = STATE_CLOSED
                    self._stateUnknown = False
                    self._tiltStep = tiltStep
                    self.async_write_ha_state()
                else:
                    _LOGGER.info("Finished setting tilt position - blind is not opening so not setting to tilted")

    async def async_set_cover_my_position(self, **kwargs):
        """Move the cover tilt to a preset position."""
        _LOGGER.debug("Invoked async_set_cover_my_position")

        if self.should_ignore_action():
            _LOGGER.debug("Blind is in motion - will ignore request")
        else:
            # set my position blind
            _LOGGER.info("Setting my position with a delay...")
            state = self._state
            self._state = STATE_OPENING
            self.async_write_ha_state()
            await self._async_send(self._device.send_my)

            if self._stateUnknown or state != STATE_CLOSED:
                _LOGGER.debug("Waiting blind close secs " + str(self._openToCloseSecs))
                await asyncio.sleep(self._openToCloseSecs)
            else:
                _LOGGER.debug("Waiting blind tilt secs " + str(self._fullTiltToHomeSecs))
                await asyncio.sleep(self._fullTiltToHomeSecs)

            # If the blind is still opening then we have finished. Otherwise assume we were interrupted
            if self._state == STATE_OPENING:
                _LOGGER.info("Finished setting my position")
                self._state = STATE_CLOSED
                self._stateUnknown = False
                self._tiltStep = TILT_STEP_HOME
                self.async_write_ha_state()
            else:
                _LOGGER.info("Finished setting my position - blind is not closing so not setting to closed")

    def should_ignore_action(self):
        """"Should the action be ignored"""
        if self._state == STATE_OPENING or self._state == STATE_CLOSING:
            return True
        else:
            return False

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
