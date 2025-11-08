import pyrad.packet
from core.radius_clients.base_client import BaseRadiusClient

class FortinetRadiusClient(BaseRadiusClient):
    """
    A RADIUS client for simulating requests from a FortiGate NAS device.
    """
    def _create_auth_packet(self, username: str, password: str, **kwargs) -> pyrad.packet.Packet:
        """
        Creates a FortiGate-style Access-Request packet.
        
        Includes standard attributes plus Fortinet VSAs for context.
        """
        req = self.client.CreateAuthPacket(
            code=pyrad.packet.AccessRequest,
            User_Name=username,
            NAS_Identifier="FortiGate-Test-NAS",
        )

        req["User-Password"] = req.PwCrypt(password)
        req["NAS-IP-Address"] = kwargs.get("nas_ip_address", "127.0.0.1")
        req["Calling-Station-Id"] = kwargs.get("calling_station_id", "00:09:0F:0B:01:01")
        req["Acct-Session-Id"] = kwargs.get("acct_session_id", "fortinet-session-1")
        
        req["Fortinet-Vdom-Name"] = kwargs.get("vdom_name", "root")
        req["Fortinet-Interface-Name"] = kwargs.get("interface_name", "port1")

        return req

    def _create_accounting_packet(self, username: str, accounting_packet_type: str, **kwargs) -> pyrad.packet.Packet:
        """
        Creates a FortiGate-style Accounting-Request packet.
        
        Includes standard accounting attributes plus Fortinet VSAs.
        """
        req = self.client.CreateAcctPacket(
            User_Name=username,
            NAS_Identifier="FortiGate-Test-NAS",
        )
        
        req["Acct-Status-Type"] = accounting_packet_type
        req["NAS-IP-Address"] = kwargs.get("nas_ip_address", "127.0.0.1")
        req["Acct-Session-Id"] = kwargs.get("acct_session_id", "fortinet-session-1")
        req["Calling-Station-Id"] = kwargs.get("calling_station_id", "00:09:0F:0B:01:01")

        req["Fortinet-Vdom-Name"] = kwargs.get("vdom_name", "root")
        req["Fortinet-Interface-Name"] = kwargs.get("interface_name", "port1")
        
        if "client_ip" in kwargs:
            req["Fortinet-Client-IP-Address"] = kwargs["client_ip"]

        if accounting_packet_type in ("Stop", "Alive"):
            req["Acct-Input-Octets"] = str(kwargs.get("acct_input_octets", 0))
            req["Acct-Output-Octets"] = str(kwargs.get("acct_output_octets", 0))
            req["Acct-Session-Time"] = str(kwargs.get("acct_session_time", 0))
        
        if accounting_packet_type == "Stop":
            req["Acct-Terminate-Cause"] = "User-Request"
            
        return req

