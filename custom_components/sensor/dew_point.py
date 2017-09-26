"""
Calculates dew point.
For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.mold_indicator/
"""
import logging
import math

import voluptuous as vol

from homeassistant.components.sensor import PLATFORM_SCHEMA
import homeassistant.util as util
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import track_state_change
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT, TEMP_CELSIUS, TEMP_FAHRENHEIT, CONF_NAME)
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

ATTR_DEWPOINT = 'Dew Point'

CONF_HUMIDITY = 'humidity_sensor'
CONF_TEMP = 'temp_sensor'

DEFAULT_NAME = 'Dew Point'

MAGNUS_K2 = 17.62
MAGNUS_K3 = 243.12

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_TEMP): cv.entity_id,
    vol.Required(CONF_HUMIDITY): cv.entity_id,
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up MoldIndicator sensor."""
    name = config.get(CONF_NAME, DEFAULT_NAME)
    temp_sensor = config.get(CONF_TEMP)
    humidity_sensor = config.get(CONF_HUMIDITY)

    add_devices([DewPoint(
        hass, name, temp_sensor, humidity_sensor)])


class DewPoint(Entity):
    """Represents a MoldIndication sensor."""

    def __init__(self, hass, name, temp_sensor, humidity_sensor):
        """Initialize the sensor."""
        self._state = None
        self._name = name
        self._temp_sensor = temp_sensor
        self._humidity_sensor = humidity_sensor
        self._is_metric = hass.config.units.is_metric

        self._temp = None
        self._hum = None

        track_state_change(hass, temp_sensor, self._sensor_changed)
        track_state_change(hass, humidity_sensor, self._sensor_changed)

        # Read initial state
        temp = hass.states.get(temp_sensor)
        hum = hass.states.get(humidity_sensor)

        if temp:
            self._temp = DewPoint._update_temp_sensor(temp)

        if hum:
            self._hum = DewPoint._update_hum_sensor(hum)

        self.update()

    @staticmethod
    def _update_temp_sensor(state):
        """Parse temperature sensor value."""
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        temp = util.convert(state.state, float)

        if temp is None:
            _LOGGER.error('Unable to parse sensor temperature: %s',
                          state.state)
            return None

        # convert to celsius if necessary
        if unit == TEMP_FAHRENHEIT:
            return util.temperature.fahrenheit_to_celsius(temp)
        elif unit == TEMP_CELSIUS:
            return temp
        else:
            _LOGGER.error("Temp sensor has unsupported unit: %s (allowed: %s, "
                          "%s)", unit, TEMP_CELSIUS, TEMP_FAHRENHEIT)

        return None

    @staticmethod
    def _update_hum_sensor(state):
        """Parse humidity sensor value."""
        unit = state.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
        hum = util.convert(state.state, float)

        if hum is None:
            _LOGGER.error('Unable to parse sensor humidity: %s',
                          state.state)
            return None

        if unit != '%':
            _LOGGER.error("Humidity sensor has unsupported unit: %s %s",
                          unit, " (allowed: %)")

        if hum > 100 or hum < 0:
            _LOGGER.error("Humidity sensor out of range: %s %s", hum,
                          " (allowed: 0-100%)")

        return hum

    def update(self):
        """Calculate latest state."""
        # check all sensors
        if None in (self._temp, self._hum):
            return

        # re-calculate dewpoint and mold indicator
        self._calc_dewpoint()

    def _sensor_changed(self, entity_id, old_state, new_state):
        """Handle sensor state changes."""
        if new_state is None:
            return

        if entity_id == self._temp_sensor:
            self._temp = DewPoint._update_temp_sensor(new_state)
        elif entity_id == self._humidity_sensor:
            self._hum = DewPoint._update_hum_sensor(new_state)

        self.update()
        self.schedule_update_ha_state()

    def _calc_dewpoint(self):
        """Calculate the dewpoint."""
        # Use magnus approximation to calculate the dew point
        alpha = MAGNUS_K2 * self._temp / (MAGNUS_K3 + self._temp)
        beta = MAGNUS_K2 * MAGNUS_K3 / (MAGNUS_K3 + self._temp)

        if self._hum == 0:
            self._state = -50  # not defined, assume very low value
        else:
            self._state = \
                MAGNUS_K3 * (alpha + math.log(self._hum / 100.0)) / \
                (beta - math.log(self._hum / 100.0))

        _LOGGER.debug("Dewpoint: %f " + TEMP_CELSIUS, self._state)

    @property
    def should_poll(self):
        """Return the polling state."""
        return False

    @property
    def name(self):
        """Return the name."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    @property
    def state(self):
        """Return the state of the entity."""
        return round(self._state, 2) if self._state is not None else None

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return {}

