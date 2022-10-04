[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)

As a learning exercise, I have written a more featureful Home Assistant integration for the [Camect Hub](https://camect.com/).

It provides fully-fledged devices and entities for the hub, its cameras, and motion detection alerts, making it much easier and quicker to setup automations for these events.

Many thanks to the Camect team for providing something I could learn from with their [original Home Assistant code](https://github.com/camect/home-assistant-integration), and for their [camect-py](https://github.com/camect/camect-py) library.

I suggest treating this as beta quality for now. It's been working great for me for a few weeks, however YMMV 😊

## Features ##
- Fully visible and configurable within Home Assistant
  - ![HA Integrations](https://github.com/Fr3d/camect-ha/blob/main/ha_integrations.png?raw=true)
- Hub mode control (Normal or At Home)
  - ![Hub mode](https://github.com/Fr3d/camect-ha/blob/main/ha_hub_mode.png?raw=true)
- Full devices for each camera
  - ![Camera device](https://github.com/Fr3d/camect-ha/blob/main/ha_camera_device.png?raw=true)
- Motion sensors within each camera's device
- Detected object attribute within each camera
- Individual camera alert control
- Automatic addition of cameras added to the Hub
- Appropriate device statuses of cameras and switches if a camera goes offline
- Continues to receive events from Camect's event bus to utilise within Home Assistant
- *Should* support multiple hubs (however I've not yet been able to verify this as I only own one)

## Requirements ##
- Home Assistant 2022.9 or later
- A Camect Hub device
- Administrative access to your Hub
- Network access between Home Assistant and your Hub

## Installation ##
If you have the original Camect integration installed, you'll need to archive or delete it from your Home Assistant `custom_components` directory, remove the configuration lines from `configuration.yaml`, and clean up the orphaned camera entities from Home Assistant.

### HACS ###
Using [HACS](https://hacs.xyz/) to install is the recommended method. Add the URL for this repo as a custom repository, and then install it using the Explore & Download button.

Ensure you pick the correct repo, as there's a similar one for the original Camect team's code. Look for this repo's description; "**Camect Hub integration for Home Assistant / HACS**".

### Manual Installation ###
Copy `custom_components/camect` from this repo into your Home Assistant `/config/custom_components` directory.

If you install it manually you *might* need to add one line to your `configuration.yaml` before Home Assistant will detect it:
```yaml
camect:
```

## Configuration ##

1. Add a local account (not a "cloud" account like Google) to your Hub for the integration to authenticate with.
   1. At the time of writing, the API only works for users granted Administrator privileges.
   2. ![Add local Camect Hub user](https://github.com/Fr3d/camect-ha/blob/main/add_ha_user.png?raw=true)
2. Once the integration is installed in Home Assistant, add the integration from your Settings -> Integrations page and search for Camect.
3. Fill in the username and password you setup above.
   1. Most people won't need to change the URL as `local.home.camect.com` provides a redirects to the Hub running in your home.
   2. ![Camect HA Config](https://github.com/Fr3d/camect-ha/blob/main/ha_configuration.png?raw=true)
4. Assuming it successfully connects after submitting the form, the integration will ask you to set the areas (rooms) for the Hub and every camera it finds.

