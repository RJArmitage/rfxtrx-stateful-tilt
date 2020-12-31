import voluptuous as vol
import logging

from homeassistant import config_entries, exceptions
from homeassistant.components.rfxtrx.config_flow import ConfigFlow as OldConfigFlow
from homeassistant.components.rfxtrx.config_flow import OptionsFlow as OldOptionsFlow
from homeassistant.components.rfxtrx.binary_sensor import supported as binary_supported
from homeassistant.components.rfxtrx.cover import supported as cover_supported
from homeassistant.components.rfxtrx.light import supported as light_supported
from homeassistant.components.rfxtrx.switch import supported as switch_supported
from homeassistant.const import (
    CONF_COMMAND_OFF,
    CONF_COMMAND_ON,
    CONF_DEVICE_ID,
)
from homeassistant.core import callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.components.rfxtrx import (
    CONF_DATA_BITS,
    CONF_SIGNAL_REPETITIONS,
    get_device_id,
    DOMAIN
)
from homeassistant.components.rfxtrx.const import (
    CONF_DATA_BITS,
    CONF_FIRE_EVENT,
    CONF_OFF_DELAY,
    CONF_REPLACE_DEVICE,
    CONF_SIGNAL_REPETITIONS,
    DEVICE_PACKET_TYPE_LIGHTING4,
)
from homeassistant.components.rfxtrx.config_flow import (
    none_or_int,
)

from .ext.config_flow import(
    update_data_schema,
    update_device_options
)

_LOGGER = logging.getLogger(__name__)


class OptionsFlow(OldOptionsFlow):
    """Handle Rfxtrx options."""

    async def async_step_set_device_options(self, user_input=None):
        """Manage device options."""
        _LOGGER.info("Called async_step_set_device_options function")

        errors = {}
        if user_input is not None:
            device_id = get_device_id(
                self._selected_device_object.device,
                data_bits=user_input.get(CONF_DATA_BITS),
            )

            if CONF_REPLACE_DEVICE in user_input:
                await self._async_replace_device(user_input[CONF_REPLACE_DEVICE])

                devices = {self._selected_device_event_code: None}
                self.update_config_data(
                    global_options=self._global_options, devices=devices
                )

                return self.async_create_entry(title="", data={})

            try:
                command_on = none_or_int(user_input.get(CONF_COMMAND_ON), 16)
            except ValueError:
                errors[CONF_COMMAND_ON] = "invalid_input_2262_on"

            try:
                command_off = none_or_int(user_input.get(CONF_COMMAND_OFF), 16)
            except ValueError:
                errors[CONF_COMMAND_OFF] = "invalid_input_2262_off"

            try:
                off_delay = none_or_int(user_input.get(CONF_OFF_DELAY), 10)
            except ValueError:
                errors[CONF_OFF_DELAY] = "invalid_input_off_delay"

            if not errors:
                devices = {}
                device = {
                    CONF_DEVICE_ID: device_id,
                    CONF_FIRE_EVENT: user_input.get(CONF_FIRE_EVENT, False),
                    CONF_SIGNAL_REPETITIONS: user_input.get(CONF_SIGNAL_REPETITIONS, 1),
                }

                devices[self._selected_device_event_code] = device

                if off_delay:
                    device[CONF_OFF_DELAY] = off_delay
                if user_input.get(CONF_DATA_BITS):
                    device[CONF_DATA_BITS] = user_input[CONF_DATA_BITS]
                if command_on:
                    device[CONF_COMMAND_ON] = command_on
                if command_off:
                    device[CONF_COMMAND_OFF] = command_off

                update_device_options(device, user_input)

                self.update_config_data(
                    global_options=self._global_options, devices=devices
                )

                return self.async_create_entry(title="", data={})

        device_data = self._selected_device

        data_schema = {
            vol.Optional(
                CONF_FIRE_EVENT, default=device_data.get(
                    CONF_FIRE_EVENT, False)
            ): bool,
        }

        if binary_supported(self._selected_device_object):
            if device_data.get(CONF_OFF_DELAY):
                off_delay_schema = {
                    vol.Optional(
                        CONF_OFF_DELAY,
                        description={
                            "suggested_value": device_data[CONF_OFF_DELAY]},
                    ): str,
                }
            else:
                off_delay_schema = {
                    vol.Optional(CONF_OFF_DELAY): str,
                }
            data_schema.update(off_delay_schema)

        if (
            binary_supported(self._selected_device_object)
            or cover_supported(self._selected_device_object)
            or light_supported(self._selected_device_object)
            or switch_supported(self._selected_device_object)
        ):
            data_schema.update(
                {
                    vol.Optional(
                        CONF_SIGNAL_REPETITIONS,
                        default=device_data.get(CONF_SIGNAL_REPETITIONS, 1),
                    ): int,
                }
            )

        _LOGGER.info("Self " + str(self))
        _LOGGER.info("_selected_device_object " +
                     str(self._selected_device_object))
        _LOGGER.info(
            "p type" + str(self._selected_device_object.device.packettype))
        _LOGGER.info(
            "p subtype" + str(self._selected_device_object.device.subtype))
        update_data_schema(
            data_schema, self._selected_device_object, device_data)

        if (
            self._selected_device_object.device.packettype
            == DEVICE_PACKET_TYPE_LIGHTING4
        ):
            data_schema.update(
                {
                    vol.Optional(
                        CONF_DATA_BITS, default=device_data.get(
                            CONF_DATA_BITS, 0)
                    ): int,
                    vol.Optional(
                        CONF_COMMAND_ON,
                        default=hex(device_data.get(CONF_COMMAND_ON, 0)),
                    ): str,
                    vol.Optional(
                        CONF_COMMAND_OFF,
                        default=hex(device_data.get(CONF_COMMAND_OFF, 0)),
                    ): str,
                }
            )

        devices = {
            entry.id: entry.name_by_user if entry.name_by_user else entry.name
            for entry in self._device_entries
            if self._can_replace_device(entry.id)
        }

        if devices:
            data_schema.update(
                {
                    vol.Optional(CONF_REPLACE_DEVICE): vol.In(devices),
                }
            )

        return self.async_show_form(
            step_id="set_device_options",
            data_schema=vol.Schema(data_schema),
            errors=errors,
        )


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):

    async def async_step_user(self, user_input=None):
        """Step when user initializes a integration."""
        return OldConfigFlow().async_step_user(user_input)

    async def async_step_setup_network(self, user_input=None):
        """Step when setting up network configuration."""
        return OldConfigFlow().async_step_setup_network(user_input)

    async def async_step_setup_serial(self, user_input=None):
        """Step when setting up serial configuration."""
        return OldConfigFlow().async_step_setup_serial(user_input)

    async def async_step_setup_serial_manual_path(self, user_input=None):
        return OldConfigFlow().async_step_setup_serial_manual_path(user_input)

    async def async_step_import(self, import_config=None):
        """Handle the initial step."""
        return OldConfigFlow().async_step_import(import_config)

    async def async_validate_rfx(self, host=None, port=None, device=None):
        """Create data for rfxtrx entry."""
        return OldConfigFlow().async_validate_rfx(host, port, device)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Get the options flow for this handler."""
        _LOGGER.info("Called async_get_options_flow function")
        return OptionsFlow(config_entry)
