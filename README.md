# What is this?

This component replaces the built-in integration for RFXTRX covers. It adds "stateful tilt" to the basic capabilities. This is only available for blinds that support it. All other RFXTRX operations fall back on the in-built support from Home Assistant.
<br><br>

# Why does it exist? Do I need it?

You possibly don't - it's intended to satisfy a specific requirement.

I have a number of venetian blinds which use Somfy motors. Now for me the whole point of venetian blinds is to provide more control over the light in my home while maintaining provacy as best I can. I want some specific capabilities that the base Home Assistant RFXTRX cover support doesnt give me:

- I want to separate the concept of "lifting" the blind from the concept of "tilting" the blind.

- The concept of "opening" and "closing" the blinds should relate to tilting the blind and not lifting. An open venetian blind is one that is tilted to open - not one that is lifted. A closed blind is both dropped and tully tilted closed.

- Privacy is key. I want to be certain that the blinds will only attempt to lift if they are explicitly told to. In particular if using Alexa integration, if Alexa is told to "open" the blind it should do this by tilting the blind to open and not by lifting the blind.

- I want to be able to control my blinds using Somfy groups as well as individually. Somfy motors have the ability to assign a single channel on their controller to more than one blind. This means that to control all those blinds only a single instruction is sent. Now, it is possible to do something similar in Home Assistant by creating a cover group. But that's missing the point of the Somfy function. It would mean that each operation would be sent seperately to each blind in the group. That's irritating to me as all the blinds start and stop moving seperately. It looks untidy!

So, if you have one or more of those requirements then maybe this component will be useful for you. If not then you should continue with the existing built-in Home Assistant RFXTRX integration.
<br><br>

# Which blinds are supported

This implementation only supports two types of blinds:

- _Venetian blinds_ using **_Somfy_** battery and mains-powered RTS motors such as **Sonesse** and **Lift & Tilt** motors.

- _Vertical blinds_ using **_Louvolite Vogue_** battery powered motors

Why only those blinds? Simply because those are the ones I have so those are the ones I can test against. I also have Somfy roller blinds which are controlled by the original Home Assistant integration.
<br><br>

# Limitations

The supported blind motors do not report their state. This means that, for example, if I open a blind in Home Assistant and then close it using the blind's own controller, the Home Assistant won't know and will still show it as open.

At present the full tilt support does not work. The RFXCOM documentation says that you can perform a tilt by sending either a 0.5 sec or 2 sec up or down operastion. However this does not work on my blinds and always either lifts or closes the blind. I suspect the information is out of date for modern motors. If better support is added to the RFXCOM firmware then support will be added to this component. At the momewnt this component simulates a tilt position operation.
<br><br>

# Installing and uninstalling

Simply copy the contents of the custom_components/rfxtrx folder to the custom_components/rfxtrx folder of your home assistant and then restart. If you already use the RFXTRX integration then you should add it from the integrations page. If you wasmnt to get rid of the new component then simply delete the custom_components/rfxtrx folder and restart home assistant.
<br><br>

# Usage

Simply add blinds using the standard RFXTRX integration options dialog. The component will automatically detect if you select a supported blind type. The dialog will then show additional options:

## Somfy Venetian Blinds

These options are only available when the Venetian blind mode is set to "US" or "EU". Note that Somfy venetian blinds have a "my" position which would normally be set to the blind mid position (ie. fully tilted open). Hence a Somfy venetian blind has three "goto" positions - fully lifted, fully closed and tilted open.

At the moment the component does not support full tilt operations. Instead it supports tilting to the mid point (position 2) along with an extra tilt before and after this point (positions 1 and 3). The extra positions are provided by tilting up or down from the mid point for a number of milliseconds. Set whatever works for you in the configuration.

- **Open time (secs)** - Number of seconds that the blind requires to completely lift. Allow the time for the worst case which would be to lift from fully tilted upward.
- **Close time (secs)** - Number of seconds that the blind requires to complely close when fuly lifted.
- **Mid open/close time (secs)** - Number of seconds that the blind requires to tilt to its mid point (the "my" position). Allow the time for the worst case which would be to tilt to the mid position from fully tilted upward as the blind will normally first tilt to closed and then tilt to the mid point.
- **Lower tilt time from midpoint (ms)** -
- **Upper tilt time from midpoint (ms)** -

## Lovolite Vogue Vertical Blinds

The Louvolite Vogue vertical blinds motor allows the blinds to be tilted to 0, 45, 90, 135 and 180 degrees. 0 and 180 degrees are fully closed and 90 degrees is fully open.

- **Open time (secs)** -
- **Close time (secs)** - Number of seconds that the blind requires to complely close. Allow the time for the worst case which would be that the blind is tilted to the oposite close position.
- **Mid open/close time (secs)** -
