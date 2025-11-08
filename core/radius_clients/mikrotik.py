import pyrad.packet
from core.radius_clients.base_client import BaseRadiusClient
from typing import Literal

ACCOUNTING_PACKET_TYPES = Literal['Start', 'Alive', 'Stop']

class MikrotikRadiusClient(BaseRadiusClient):
    """
    A RADIUS client specifically for interacting with Mikrotik NAS devices.
    It implements the packet creation methods with standard attributes
    used by Mikrotik.
    """
    def _create_auth_packet(self, username: str, password: str, **kwargs) -> pyrad.packet.Packet:
        """Creates a Mikrotik-style Access-Request packet."""
        
        req = self.client.CreateAuthPacket(
            code=pyrad.packet.AccessRequest,
            User_Name=username,
            NAS_Identifier=kwargs.get("nas_identifier", "mikrotik-simulator"),
        )

        req["User-Password"] = req.PwCrypt(password)
        req["NAS-IP-Address"] = kwargs.get("nas_ip_address", "127.0.0.1")
        req["Service-Type"] = "Framed-User"
        req["Framed-Protocol"] = "PPP"
        
        req["NAS-Port"] = kwargs.get("nas_port", "50331950")
        req["NAS-Port-Type"] = kwargs.get("nas_port_type", "Virtual")
        req["Calling-Station-Id"] = kwargs.get("calling_station_id", "00:1B:44:11:3A:B7")
        req["Acct-Session-Id"] = kwargs.get("acct_session_id", "mikrotik-session-1")

        print(f"{req}")

        return req

    def _create_accounting_packet(self, username: str, accounting_packet_type: str, **kwargs) -> pyrad.packet.Packet:
        """Creates a Mikrotik-style Accounting-Request packet."""

        req = self.client.CreateAcctPacket(
            User_Name=username,
            NAS_Identifier=kwargs.get('nas_identifier', 'mikrotik-simulator'),
        )
        
        req["Acct-Status-Type"] = accounting_packet_type
        req["NAS-IP-Address"] = kwargs.get("nas_ip_address", "127.0.0.1")
        req["Service-Type"] = "Framed-User"
        
        # Add optional attributes from kwargs, with defaults
        req["Acct-Session-Id"] = kwargs.get("acct_session_id", "mikrotik-session-1")
        req["NAS-Port"] = kwargs.get("nas_port", "50331950")
        req["NAS-Port-Type"] = kwargs.get("nas_port_type", "Virtual")
        req["Calling-Station-Id"] = kwargs.get("calling_station_id", "00:1B:44:11:3A:B7")
        
        for key in ["acct_input_octets", "acct_output_octets", "acct_session_time"]:
            if key in kwargs:
                req[key.replace('_', '-').title()] = str(kwargs[key])

        if accounting_packet_type == "Stop":
            req["Acct-Terminate-Cause"] = "User-Request"
            
        return req

