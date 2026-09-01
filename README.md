### TLS / MQTT: Usage & systemd notes

To run victron-ble2mqtt with TLS-enabled MQTT connections, ensure the following in your settings TOML (see `edit-settings` for an interactive editor):

```toml
[mqtt.mqtt_tls]
enabled = true
ca_certs = "/etc/dreibein/tls/victron-mqtt-ca-chain.crt"
certfile = "/etc/dreibein/tls/victron-mqtt-client.crt"
keyfile = "/etc/dreibein/tls/victron-mqtt-client.key"
cert_reqs = 2
tls_version = 2
ciphers = ""
```

Notes:

- The CLI reads its settings from the XDG config directory (default: `~/.config/victron-ble2mqtt/victron-ble2mqtt.toml`). You can copy the example config into place or use `victron-ble2mqtt edit-settings`.
- If you run the service as root or want to place the config under `/root`, set `Environment="XDG_CONFIG_HOME=/root/.config"` in your systemd unit (see below).

Example systemd snippet to ensure the service finds the config under root:

```
[Service]
Environment="XDG_CONFIG_HOME=/root/.config"
ExecStart=/usr/bin/python3 -m victron_ble2mqtt publish-loop
```

Make sure the TLS files are readable by the service user and secure (private key permissions):

```
sudo chown root:victron /etc/dreibein/tls/*
sudo chmod 640 /etc/dreibein/tls/victron-mqtt-client.key
```
