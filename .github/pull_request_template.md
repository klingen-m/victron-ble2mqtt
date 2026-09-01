---
title: Add TLS support and documentation for MQTT TLS
body: |
  Implement TLS setup for MQTT client in `victron_ble2mqtt/cli_app/mqtt.py` using `ssl.SSLContext` with a fallback to `Client.tls_set` for older paho-mqtt versions.

  Added example TLS configuration file `victron-ble2mqtt/victron-ble2mqtt.toml` and updated `README.md` with TLS usage notes and systemd guidance (XDG_CONFIG_HOME).

  Testing instructions and troubleshooting tips included.

  Please review the mapping of `cert_reqs` / `tls_version` numeric values to Python's `ssl` constants and validate file permissions for private keys.

---
head: tls-support
base: main
