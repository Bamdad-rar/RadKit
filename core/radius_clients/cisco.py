import pyrad.packet
from core.radius_clients.base_client import BaseRadiusClient


class CiscoRadiusClient(BaseRadiusClient):
    """
    A RADIUS client for interacting with Cisco NAS devices.
    """
    def _create_auth_packet(self, username: str, password: str, **kwargs) -> pyrad.packet.Packet:
        """Creates a Cisco-style Access-Request packet."""
        
        req = self.client.CreateAuthPacket(
            code=pyrad.packet.AccessRequest,
            User_Name=username,
            NAS_Identifier=kwargs.get("nas_identifier", "cisco-simulator"),
        )

        req["User-Password"] = req.PwCrypt(password)
        req["NAS-IP-Address"] = kwargs.get("nas_ip_address", "127.0.0.1")
        req["Service-Type"] = "Framed-User"
        req["Framed-Protocol"] = "PPP"
        
        req["NAS-Port"] = kwargs.get("nas_port", 12345)
        req["NAS-Port-Id"] = kwargs.get("nas_port_id", "0/1/0/1")
        req["NAS-Port-Type"] = kwargs.get("nas_port_type", "Virtual")
        req["Calling-Station-Id"] = kwargs.get("calling_station_id", "00:1A:2B:3C:4D:5E")
        req["Acct-Session-Id"] = kwargs.get("acct_session_id", "cisco-session-1")
        
        req["Cisco-AVPair"] = "lcp:interface-config=rate-limit input 128000 8000 8000 conform-action transmit exceed-action drop"

        return req

    def _create_accounting_packet(self, username: str, accounting_packet_type: str, **kwargs) -> pyrad.packet.Packet:
        """Creates a Cisco-style Accounting-Request packet."""

        req = self.client.CreateAcctPacket(
            User_Name=username,
            NAS_Identifier=kwargs.get("nas_identifier", "cisco-simulator"),
        )
        
        req["Acct-Status-Type"] = accounting_packet_type
        req["NAS-IP-Address"] = kwargs.get("nas_ip_address", "127.0.0.1")
        req["Acct-Session-Id"] = kwargs.get("acct_session_id", "cisco-session-1")
        req["Calling-Station-Id"] = kwargs.get("calling_station_id", "00:1A:2B:3C:4D:5E")

        req["Cisco-Account-Info"] = "Q3f21;"
        
        if accounting_packet_type in ("Stop", "Alive"):
            req["Acct-Input-Octets"] = kwargs.get("acct_input_octets", "100000")
            req["Acct-Output-Octets"] = kwargs.get("acct_output_octets", "500000")
            req["Acct-Session-Time"] = kwargs.get("acct_session_time", "300")
        
        if accounting_packet_type == "Stop":
            req["Acct-Terminate-Cause"] = "User-Request"
            
        return req

