# Installation in homeassistant

To install this custom component in homeassistant, you must copy the `somfy_rts` folder in the folder `/config/custom_components/`. Installing the Visual Studio Code extension can greatly help you for this installation. Then you must edit `configuration.yaml` as follow:

```yaml
cover:
  - platform: somfy_rts
    name: cover_name_0
    ip_address: <ip_address>
    port: <port>

  - platform: somfy_rts
    name: cover_name_1
    ip_address: <ip_address>
    port: <port>
```

The IP adresses should be the same for each cover, and the same goes for the port.

Next, you must restart the homeassistant server.





