import dataclasses
import sys

from cli_base.systemd.data_classes import BaseSystemdServiceInfo, BaseSystemdServiceTemplateContext
from ha_services.mqtt4homeassistant.data_classes import MqttSettings


@dataclasses.dataclass
class MqttTlsSettings:
    """
    TLS/SSL configuration for MQTT connection.
    """

    enabled: bool = False  # Enable TLS/SSL
    ca_certs: str = ''  # Path to CA certificate file
    certfile: str = ''  # Path to client certificate file (optional)
    keyfile: str = ''  # Path to client private key file (optional)
    cert_reqs: int = 2  # Certificate requirements (0=none, 1=optional, 2=required) - default CERT_REQUIRED
    tls_version: int = 2  # TLS version (1.2, 1.3) - Python ssl module constants
    ciphers: str = ''  # Cipher suite specification (optional)


@dataclasses.dataclass
class SystemdServiceTemplateContext(BaseSystemdServiceTemplateContext):
    """
    Context values for the systemd service file content.
    """

    verbose_service_name: str = 'victron-ble2mqtt'
    exec_start: str = f'{sys.argv[0]} publish-loop'


@dataclasses.dataclass
class SystemdServiceInfo(BaseSystemdServiceInfo):
    """
    Information for systemd helper functions.
    """

    template_context: SystemdServiceTemplateContext = dataclasses.field(default_factory=SystemdServiceTemplateContext)


@dataclasses.dataclass
class UserSettings:
    """
    Victron-BLE -> MQTT - settings

    Note: Insert at least our "device_keys" and your MQTT settings.

    See README for more information.
    """

    device_name: str = 'Victron'
    publish_throttle_seconds: int = 1  # Minimum time between publishing messages to MQTT, in seconds.

    # Add device keys here:
    device_keys: list[str] = dataclasses.field(default_factory=list)

    # Information about the MQTT server:
    mqtt: dataclasses = dataclasses.field(default_factory=MqttSettings)

    # TLS/SSL configuration for MQTT:
    mqtt_tls: dataclasses = dataclasses.field(default_factory=MqttTlsSettings)

    systemd: dataclasses = dataclasses.field(default_factory=SystemdServiceInfo)
