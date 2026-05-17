# Home Panel State Recorder (HACS Integration)

This is a basic Home Assistant custom integration (HACS) designed to record your home_panel's opening and closing states. 

## Features
- Provides a custom service (`home_panel_hacs.set_state`) to update the home_panel status.
- Automatically creates and updates a dummy entity `home_panel_hacs.status`.
- Fires an internal Home Assistant event `home_panel_hacs_state_update` whenever the state changes.

## Directory Structure
```
home_panel_hacs/
├── hacs.json (Needed for HACS compatibility)
├── README.md
└── custom_components
    └── home_panel_hacs
        ├── __init__.py (Main integration code)
        ├── const.py    (Constants)
        ├── manifest.json (Integration metata)
        └── services.yaml (Service definitions for UI)
```

## Installation via HACS
1. Open HACS in Home Assistant.
2. Click the 3 dots in the top right corner and select **Custom repositories**.
3. Add the URL of this repository and select **Integration** as the category.
4. Click **Download**.
5. Restart Home Assistant.

## Usage
Add the following to your `configuration.yaml`:

```yaml
home_panel_hacs:
```

Once restarted, you can use the service `home_panel_hacs.set_state` in the Developer Tools -> Services, or via Automations. 

Example Service Call:
```yaml
service: home_panel_hacs.set_state
data:
  state: "open"
```

You can then trigger automations off the state of `home_panel_hacs.status` or by listening to the `home_panel_hacs_state_update` event.
It can use for hacs
