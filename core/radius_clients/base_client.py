from abc import ABC, abstractmethod
from typing import Any, Literal
from pathlib import Path

from pyrad.client import Client
from pyrad.dictionary import Dictionary
from pyrad.packet import Packet


ACCOUNTING_PACKET_TYPES = Literal["Start", "Alive", "Stop"]


class RadiusClientError(Exception):
    """Custom exception for RADIUS client errors."""
    pass


class BaseRadiusClient(ABC):
    """
    Abstract Base Class for a RADIUS client.
    This class provides the core logic for sending authentication and accounting
    packets. Subclasses must implement the packet creation methods to handle
    vendor-specific attributes.
    """

    def __init__(self, server: str, secret: str, dict_path: str | Path, logger, timeout: int = 3, retries: int = 3):
        self.logger = logger
        try:
            self.client = Client(
                server=server, secret=secret.encode("utf-8"), dict=Dictionary(dict_path), timeout=timeout, retries=retries
            )
        except FileNotFoundError as e:
            self.logger.error(f"RADIUS dictionary not found at path: {e.filename}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to initialize pyrad.client: {e}")
            raise

    @abstractmethod
    def _create_auth_packet(self, username: str, password: str, **kwargs) -> Packet:
        """Create a vendor-specific authentication packet."""
        raise NotImplementedError

    @abstractmethod
    def _create_accounting_packet(self, username: str, accounting_packet_type: str, **kwargs) -> Packet:
        """Create a vendor-specific accounting packet."""
        raise NotImplementedError

    def _send_accounting_request(self, username: str, accouting_packet_type: str, **kwargs) -> dict[str, Any]:
        """Sends an Accounting-Request and returns the server's reply."""
        self.logger.info(
            f"Sending Accounting-Request ({accouting_packet_type}) for user '{username}'"
        )
        try:
            request_packet = self._create_accounting_packet(
                username, accouting_packet_type, **kwargs
            )
            self.logger.debug(f"Request Packet: {request_packet}")
            reply_packet = self.client.SendPacket(request_packet)
            self.logger.info(
                f"Received reply for '{username}': Code={reply_packet.code}"
            )
            self.logger.debug(f"Reply Packet: {reply_packet}")
            return {"code": reply_packet.code, "attributes": dict(reply_packet)}
        except Exception as e:
            self.logger.error(
                f"Accounting request ({accouting_packet_type}) failed for '{username}': {e}"
            )
            raise RadiusClientError(f"Accounting request failed: {e}") from e

    def authenticate(self, username: str, password: str, **kwargs) -> dict[str, Any]:
        """Sends an Access-Request and returns the server's reply."""
        self.logger.info(f"Sending Access-Request for user '{username}'")
        try:
            request_packet = self._create_auth_packet(username, password, **kwargs)
            self.logger.debug(f"Request Packet: {request_packet}")
            reply_packet = self.client.SendPacket(request_packet)
            self.logger.info(f"Received reply for '{username}': Code={reply_packet.code}")
            self.logger.debug(f"Reply Packet: {reply_packet}")
            return {"code": reply_packet.code, "attributes": dict(reply_packet)}
        except Exception as e:
            self.logger.error(f"Authentication failed for '{username}': {e}")
            raise RadiusClientError(f"Authentication failed: {e}") from e

    def start(self, username: str, **kwargs) -> dict[str, Any]:
        """Sends an Accounting-Request with Acct-Status-Type=Start."""
        return self._send_accounting_request(username, "Start", **kwargs)

    def alive(self, username: str, **kwargs) -> dict[str, Any]:
        """Sends an Accounting-Request with Acct-Status-Type=Alive."""
        return self._send_accounting_request(username, "Alive", **kwargs)

    def stop(self, username: str, **kwargs) -> dict[str, Any]:
        """Sends an Accounting-Request with Acct-Status-Type=Stop."""
        return self._send_accounting_request(username, "Stop", **kwargs)

