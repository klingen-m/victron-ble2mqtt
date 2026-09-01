"""
    CLI for usage
"""

import asyncio
import logging
import time
import ssl

from bleak import AdvertisementData, BLEDevice
from cli_base.cli_tools.verbosity import setup_logging
from cli_base.toml_settings.api import TomlSettings
from cli_base.tyro_commands import TyroVerbosityArgType
from ha_services.mqtt4homeassistant.mqtt import get_connected_client
from rich import print
from victron_ble.scanner import BaseScanner

from victron_ble2mqtt.cli_app import app
from victron_ble2mqtt.cli_app.settings import get_settings
from victron_ble2mqtt.mqtt import VictronMqttDeviceHandler
from victron_ble2mqtt.user_settings import UserSettings
from victron_ble2mqtt.victron_ble_utils import DeviceHandler


logger = logging.getLogger(__name__)


def _setup_mqtt_tls(mqtt_client, tls_settings):
    """
    Configure TLS/SSL for MQTT client connection.

    This uses an SSLContext when available and falls back to the older
    tls_set(...) API if necessary.
    """
    if not tls_settings.enabled:
        return

    # Maps from numeric config values to ssl module constants
    CERT_REQS_MAP = {
        0: ssl.CERT_NONE,
        1: ssl.CERT_OPTIONAL,
        2: ssl.CERT_REQUIRED,
    }

    TLS_VERSION_MAP = {
        1: ssl.TLSVersion.TLSv1,
        2: ssl.TLSVersion.TLSv1_2,
        3: ssl.TLSVersion.TLSv1_3,
    }

    try:
        ca_certs = tls_settings.ca_certs if getattr(tls_settings, 'ca_certs', None) else None
        certfile = tls_settings.certfile if getattr(tls_settings, 'certfile', None) else None
        keyfile = tls_settings.keyfile if getattr(tls_settings, 'keyfile', None) else None
        cert_reqs = CERT_REQS_MAP.get(getattr(tls_settings, 'cert_reqs', 2), ssl.CERT_REQUIRED)
        tls_version_cfg = getattr(tls_settings, 'tls_version', None)
        tls_version = TLS_VERSION_MAP.get(tls_version_cfg) if tls_version_cfg is not None else None
        ciphers = tls_settings.ciphers if getattr(tls_settings, 'ciphers', None) else None

        # Build SSLContext for a secure connection
        # If ca_certs is None, create_default_context will use system CA bundle
        context = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH, cafile=ca_certs)
        context.verify_mode = cert_reqs

        if certfile and keyfile:
            context.load_cert_chain(certfile=certfile, keyfile=keyfile)

        if tls_version is not None:
            # Set minimum_version to the requested TLS version (modern API)
            try:
                context.minimum_version = tls_version
            except Exception:
                # If the runtime does not support TLSVersion enum assignment,
                # we simply ignore and rely on defaults.
                pass

        if ciphers:
            context.set_ciphers(ciphers)

        # Use the modern API when available
        if hasattr(mqtt_client, 'tls_set_context'):
            mqtt_client.tls_set_context(context)
        else:
            # Fallback for older paho versions: tls_set with parameters
            mqtt_client.tls_set(
                ca_certs=ca_certs,
                certfile=certfile,
                keyfile=keyfile,
                cert_reqs=cert_reqs,
                tls_version=None,  # leave to ssl context; older API expects PROTOCOL_* constants
                ciphers=ciphers,
            )

        # Ensure certificate verification is enforced when requested
        if cert_reqs == ssl.CERT_REQUIRED:
            try:
                mqtt_client.tls_insecure_set(False)
            except Exception:
                # If the client does not provide tls_insecure_set, ignore
                pass

        logger.info('TLS/SSL enabled for MQTT connection')
    except Exception as e:
        logger.error(f'Failed to configure TLS for MQTT: {e}')
        raise


@app.command
def publish_loop(verbosity: TyroVerbosityArgType):
    """
    Publish MQTT messages in endless loop (Entrypoint from systemd)
    """
    setup_logging(verbosity=verbosity)

    toml_settings: TomlSettings = get_settings()
    user_settings: UserSettings = toml_settings.get_user_settings(debug=verbosity > 1)

    keys = user_settings.device_keys
    print(f'Use device {len(keys)} device keys.')

    class MqttPublisher(BaseScanner):
        def __init__(
            self,
            *,
            keys: list[str],
            user_settings: UserSettings,
        ):
            super().__init__()
            self.device_handler = DeviceHandler(keys)
            self.victron_mqtt_handler = VictronMqttDeviceHandler(user_settings=user_settings)

            self.mqtt_client = get_connected_client(settings=user_settings.mqtt, verbosity=verbosity)
            
            # Configure TLS if enabled
            _setup_mqtt_tls(self.mqtt_client, user_settings.mqtt_tls)
            
            self.mqtt_client.loop_start()

            self.rssi_info = {}

            self.next_publish = 0

        def _detection_callback(self, device: BLEDevice, advertisement: AdvertisementData):
            self.rssi_info[device.address] = advertisement.rssi
            return super()._detection_callback(device, advertisement)

        def callback(self, ble_device: BLEDevice, raw_data: bytes, advertisement: AdvertisementData):
            logger.debug(f'Received data from {ble_device.address.lower()}: {raw_data.hex()}')
            logger.debug('advertisement: %r', advertisement)

            if generic_device := self.device_handler.get_generic_device(ble_device, raw_data):
                if time.monotonic() < self.next_publish:
                    logger.debug(f'Skipping publish for {ble_device.name} ({ble_device.address}) due to throttle.')
                    return

                self.victron_mqtt_handler.publish(
                    ble_device=ble_device,
                    raw_data=raw_data,
                    generic_device=generic_device,
                    rssi=self.rssi_info.get(ble_device.address),
                    mqtt_client=self.mqtt_client,
                )
                self.next_publish = time.monotonic() + user_settings.publish_throttle_seconds
            else:
                logger.warning(f'Unsupported: {ble_device.name} ({ble_device.address})')

    async def scan(*, keys: list[str], user_settings: UserSettings):
        scanner = MqttPublisher(
            keys=keys,
            user_settings=user_settings,
        )
        await scanner.start()

    loop = asyncio.get_event_loop()
    asyncio.ensure_future(
        scan(
            keys=keys,
            user_settings=user_settings,
        )
    )
    loop.run_forever()
