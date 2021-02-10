# What is this?

This component replaces the built-in integration for RFXTRX covers. It adds "stateful tilt" to the basic capabilities. This is only available for blinds that support it. All other RFXTRX operations fall back on the in-built support from Home Assistant.
<br><br>

# Why does it exist? Do I need it?

You possibly don't - it's intended to satisfy a specific requirement.

I have a number of venetian blinds which use Somfy motors. Now for me the whole point of venetian blinds is to provide more control over the light in my home while maintaining provacy as best I can. I want some specific capabilities that the base Home Assistant RFXTRX cover support doesnt give me. Note that this is an opnionated list. These are the facilities that I expect from the way I want to use venetian blinds:

- I want to fully get the benefit of the tilt functions of my blinds. I want to be able to tilt the blind to any position that the blind supports. I have installed venetian blinds to control the light in my house and my privacy. Simply being able to be open or closed doesn't cut it.

- I want to get full scripting support. I should be able to tell the blind to tilt to 70% say and have the blind "know" that it is currently tilted to 30% so needs to step 7 positions to get to 70% tilted. This also makes support via Alexa better as I can tell the blind to tilt to 80% or whatever.

- The concept of "opening" and "closing" the blinds should relate to tilting the blind and not lifting. To me an open venetian blind is one that is tilted to open - not one that is lifted. A closed blind is both dropped and tully tilted closed.

- Privacy is key. I want to be certain that the blinds will only attempt to lift if they are explicitly told to. In particular if using Alexa integration, if Alexa is told to "open" the blind it should do this by tilting the blind to open and not by lifting the blind.

- I want to be able to control my blinds using Somfy groups as well as individually. Somfy motors have the ability to assign a single channel on their controller to more than one blind. This means that to control all those blinds only a single instruction is sent. Now, it is possible to do something similar in Home Assistant by creating a cover group. But that's missing the point of the Somfy function. It would mean that each operation would be sent seperately to each blind in the group. That's irritating to me as all the blinds start and stop moving seperately with a sort of ripple effect. I have 5 blinds in a bay window and this looks untidy!

- I want the blind icon in Home Assistant to clue me about privacy. If the blind is tilted to anything other than fully closed then it should show the blind as open. Eventually an icon that shows intermediate positions would be nice but that's for the future.

So, if you have one or more of those requirements then maybe this component will be useful for you. If not then you should continue with the existing built-in Home Assistant RFXTRX integration.
<br><br>

# Which blinds are supported

This implementation only supports two types of blinds. It is fully compatible with everying else that RFXTRX supports but uses the existing RFXTRX functionality:

- **_Venetian blinds_** using **_Somfy_** battery and mains-powered RTS motors such as **Sonesse** and **Lift & Tilt** motors.

- **_Vertical blinds_** using **_Louvolite Vogue_** battery powered motors. Note that this requires RFXTRX firmware 1044 or better.

Why only those blinds? Simply because those are the ones I have so those are the ones I can test against. I also have Somfy roller blinds which are controlled by the original Home Assistant integration.
<br><br>

# Limitations

1. The supported blind motors do not report their state. This means that, for example, if I open a blind in Home Assistant and then close it using the blind's own controller, the Home Assistant won't know and will still show it as open. The component does its best to synchronise when it can. So if was then later told to close then the blind would remain closed and then be up to date again.

2. At present the full tilt support does not work. The RFXTRX documentation says that you can perform a tilt by sending either a 0.5 sec or 2 sec up or down operation depending if you are in EU or US mode. However this simply does not work on my blinds and always either lifts or closes the blind. I suspect the information is out of date for modern motors (my blinds are very new). If better support is added to the RFXTRX firmware then support will be added to this component. At the moment this component simulates an intermediate tilt position operation.
   <br><br>

# Installing and uninstalling

Simply copy the contents of the custom_components/rfxtrx folder to the config/custom_components/rfxtrx folder of your home assistant and then restart. If you don't already use the RFXTRX integration then you should add it from the integrations page as usual. If you want to get rid of the new component then simply delete the config/custom_components/rfxtrx folder and restart home assistant.
<br><br>

# Usage

Simply add blinds using the standard RFXTRX integration options dialog. The component will automatically detect if you select a supported blind type. The dialog will then show additional options:

## Somfy Venetian Blinds

These options are only available when the venetian blind mode is set to "US" or "EU". Note that Somfy venetian blinds have a "my" position which would normally be set to the blind mid position (ie. fully tilted open). Hence a Somfy venetian blind has three directly supported states - fully lifted, fully closed and tilted open.

At the moment the component does not support the full tilt operations that the motor is capable of. Instead it supports tilting to the mid point (50%) along with an extra tilt before and after this point (25% and 75%). The extra positions are provided by tilting up or down from the mid point for a number of milliseconds. Set whatever works for you in the configuration.

- **Open time (secs)** - Number of seconds that the blind requires to completely lift. Allow the time for the worst case which would be to lift from fully tilted upward.
- **Close time (secs)** - Number of seconds that the blind requires to complely close when fuly lifted.
- **Mid open/close time (secs)** - Number of seconds that the blind requires to tilt to its mid point (the "my" position). Allow the time for the worst case which would be to tilt to the mid position from fully tilted upward as the blind will normally first tilt to closed and then tilt to the mid point.
- **Lower tilt time from midpoint (ms)** - The component simulates a 25% tilt operation by tilting to the mid point and then closing the blind for this number of milliseconds. This is not ideal and will be removed if better tilt support is added to RFXTRX.
- **Upper tilt time from midpoint (ms)** - The component simulates a 75% tilt operation by tilting to the mid point and then lifting the blind for this number of milliseconds. Again this will be removed if better tilt support is added to RFXTRX.

At present the blind is able to provide three open tilt positions. The Somfy motor can do better than this and if better support is added to RFXTRX then the component will provide it.

Note that the open and close times are important as a Somfy motor reacts differently to a "stop" command if the blind is in motion or stationary. The component will only accept the "stop" command if it believes the blind is in motion. The mid time is important as the component needs to know how long to allow the blind to reach the mid position before it then tries to tilt to another position. This makes the tilt operation more reliable.

The Somfy blind will not lift the blind if instructed to open. Instead it will use the tilt to mid operation to tilt the blind open. Similarly a close command will tilt to closed. This also takes into account if the blind is currently lifted. So, an open or close instruction will always protect privacy by ensuring the blind is tilted as necessary. To lift the blind set the cover position to more than 50% using cover.set_cover_position or the position slider in Lovelace. Using Alexa you can lift the blind using something like "Alexa, set office blind to 100%"

## Lovolite Vogue Vertical Blinds

The Louvolite Vogue vertical blinds motor allows the blinds to be tilted to 0, 45, 90, 135 and 180 degrees. These are positions 0%, 25%, 50%, 75% and 100%. 0% and 100% are both fully closed. 50% is fully open. Closing the blind will tilt to 0%. Opening the blind tilts to 50%.

- **Open time (secs)** - Number of seconds that the blind requires to complely open to 50%. Allow the time for the worst case which would be that the blind starts fully closed.
- **Close time (secs)** - Number of seconds that the blind requires to complely close. Allow the time for the worst case which would be that the blind is tilted to the opposite close position.
- **Mid open/close time (secs)** -

## Service Operations

The component adds three new scripting operations:

- **rfxtrx.decrease_cover_tilt** - This operation is intended for button handlers and decreases the amount of tilt by one "step". It can be used in two ways:

  1. If your button sends an event each time it is clicked then use with no parameters to decrease the tilt amount each time the button is clicked. If the blind is fully tilted then nothing happens.
  2. If your button sends a "hold" event when held and then a "release" event when released then add a "repeat_automatically" parameter. In this case the blind will keep stepping until either fully stepped or a "cover.stop_cover_tilt" operation is called.

- **rfxtrx.increase_cover_tilt** - This operation is intended for button handlers and increases the amount of tilt by one "step". It can be used in two ways:

  1. If your button sends an event each time it is clicked then use with no parameters to increase the tilt amount each time the button is clicked. If the blind is fully tilted then nothing happens.
  2. If your button sends a "hold" event when held and then a "release" event when released then add a "repeat_automatically" parameter. In this case the blind will keep stepping until either fully stepped or a "cover.stop_cover_tilt" operation is called.

- **rfxtrx.update_cover_position** - Sets the internal state of the position and tilt position of the blind. This is intended to be used when defining a Somfy group device. In this case the tilt states of any blinds in the Somfy group would be wrong. To solve this simply create an automation to update the states of the indivisual blinds in the group when the group device changes. For example this automation updates the 5 individual blinds that make up Somfy group cover.living_room whenever the group tilt position changes:

```
    - alias: "Living Room sync blind state"
      description: "Sync the tilt of individual blinds with group blind"
      trigger:
      - platform: state
        entity_id: cover.living_room
        attribute: current_tilt_position
      action:
      - service: rfxtrx.update_cover_position
        data:
          position: '{{ state_attr("cover.living_room", "current_position") }}'
          tilt_position: '{{ state_attr("cover.living_room", "current_tilt_position") }}'
        entity_id:
        - cover.living_room_1
        - cover.living_room_2
        - cover.living_room_3
        - cover.living_room_4
        - cover.living_room_5
      mode: single
```
