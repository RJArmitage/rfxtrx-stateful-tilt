"""Light support for switch entities."""
import logging
from typing import Any, Callable, Optional, Sequence, cast

from homeassistant.components.cover import (
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    ATTR_POSITION,
)

from homeassistant.const import (
    STATE_CLOSED
)

from homeassistant.core import callback

from .abs_tilting_cover import (
    AbstractTiltingCover,
    TILT_POS_CLOSED_MIN,
    TILT_POS_CLOSED_MAX,
    BLIND_POS_CLOSED
)

# mypy: allow-untyped-calls, allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Blinds Control"


class AbstractStaticTiltingCover(AbstractTiltingCover):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, midSteps, hasMid, syncMid, event):
        super().__init__(device, device_id, midSteps, hasMid, syncMid, 1, 1, event)

    async def async_added_to_hass(self):
        """Restore device state."""
        _LOGGER.debug("Called async_added_to_hass")

        await super().async_added_to_hass()

        self._blind_position = BLIND_POS_CLOSED
        self._state = STATE_CLOSED

        if self._event is None:
            old_state = await self.async_get_last_state()
            if old_state is not None:
                if 'current_position' in old_state.attributes:
                    _LOGGER.info("State = " + str(old_state))
                    self._tilt_position = self._tilt_to_steps(
                        old_state.attributes['current_position'])

                    _LOGGER.info("Recovered state=" + str(self._state) +
                                 " position=" + str(self._blind_position) +
                                 " tilt=" + str(self._tilt_position))

    @property
    def current_cover_position(self):
        """Return the current cover position property."""
        position = self._current_cover_tilt_position()
        _LOGGER.info(
            "Returned current_cover_position attribute = " + str(position))
        return position

    @property
    def is_closed(self):
        """Return the is_closed property."""
        if self.is_opening or self.is_closing:
            closed = False
        else:
            tilt = self._current_cover_tilt_position()
            closed = tilt <= TILT_POS_CLOSED_MIN or tilt >= TILT_POS_CLOSED_MAX

        _LOGGER.debug("Returned is_closed attribute = " + str(closed))
        return closed

    @property
    def supported_features(self):
        """Flag supported features."""
        _LOGGER.debug("Returned supported_features attribute")
        return SUPPORT_CLOSE | SUPPORT_OPEN | SUPPORT_SET_POSITION

    async def async_set_cover_position(self, **kwargs):
        """Move the cover to a specific position."""
        _LOGGER.info("Invoked async_set_cover_position")
        if ATTR_POSITION in kwargs:
            position = kwargs[ATTR_POSITION]
            await self.async_set_cover_tilt_position(tilt_position=position)
