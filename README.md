# HomeAssistant Dewpoint Sensor

Dewpoint sensor for HomeAssistant.

To add a dew point sensor to your configuration, add the following template to your ```sensors``` section:


```  - platform: dew_point
    temp_sensor: sensor.temperature_sensor_xxxxxx
    humidity_sensor: sensor.humidity_yyyyyy
    name: Dew Point
```

