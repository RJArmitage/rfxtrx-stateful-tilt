"""Light support for switch entities."""
import logging
from typing import Any, Callable, Optional, Sequence, cast

from . import RfxtrxCommandEntity

from homeassistant.components.cover import (
    SUPPORT_CLOSE,
    SUPPORT_OPEN,
    SUPPORT_SET_POSITION,
    SUPPORT_STOP,
    SUPPORT_OPEN_TILT,
    SUPPORT_CLOSE_TILT,
    SUPPORT_SET_TILT_POSITION,
)


from homeassistant.core import callback

from .ext_abs_tilting_cover import AbstractTiltingCover

# mypy: allow-untyped-calls, allow-untyped-defs, no-check-untyped-defs

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Blinds Control"


class AbstractLiftingTiltingCover(AbstractTiltingCover):
    """Representation of a RFXtrx cover."""

    def __init__(self, device, device_id, midSteps, hasMid, syncMid, openSecs, closeSecs, event):
        super().__init__(device, device_id, midSteps,
                         hasMid, syncMid, openSecs, closeSecs, event)

    @property
    def current_cover_tilt_position(self):
        """Return the current tilt position property."""
        tilt = self._current_cover_tilt_position()
        _LOGGER.debug(
            "Returned current_cover_tilt_position attribute = " + str(tilt))
        return tilt

    @property
    def supported_features(self):
        """Flag supported features."""
        _LOGGER.debug("Returned supported_features attribute")
        return SUPPORT_CLOSE | SUPPORT_OPEN | SUPPORT_STOP | SUPPORT_OPEN_TILT | SUPPORT_CLOSE_TILT | SUPPORT_SET_TILT_POSITION | SUPPORT_SET_POSITION
