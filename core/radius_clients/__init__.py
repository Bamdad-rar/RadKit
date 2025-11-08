from pathlib import Path
from core.radius_clients.base_client import BaseRadiusClient
from core.radius_clients.mikrotik import MikrotikRadiusClient
from core.radius_clients.cisco import CiscoRadiusClient
from core.radius_clients.fortigate import FortinetRadiusClient

_CLIENT_MAP = {
    "mikrotik": MikrotikRadiusClient,
    "cisco": CiscoRadiusClient,
    "fortigate": FortinetRadiusClient,
}

def get_radius_client(vendor: str, server: str, secret: str, dict_path: str | Path, logger) -> BaseRadiusClient:
    """
    Factory function to get a RADIUS client for a specific vendor.

    Args:
        vendor (str): The vendor name (e.g., 'mikrotik').

    Returns:
        An instance of a BaseRadiusClient subclass.
    """
    client_class = _CLIENT_MAP.get(vendor.lower())
    if not client_class:
        raise ValueError(f"Unknown RADIUS vendor '{vendor}'. Available: {list(_CLIENT_MAP.keys())}")
    return client_class(server, secret, dict_path, logger)
