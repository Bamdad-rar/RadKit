import logging
import time
from flask import Flask, jsonify, render_template, request
from . import get_radius_client
from .base_client import RadiusClientError
from pyrad.packet import Packet

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, template_folder='templates', static_folder='static')


def format_packet_attributes(packet: Packet) -> dict:
    """Format packet attributes for better display."""
    formatted = {}
    for key, value in packet.items():
        if isinstance(value, list):
            formatted_values = []
            for v in value:
                if isinstance(v, bytes):
                    try:
                        formatted_values.append(v.decode('utf-8'))
                    except:
                        formatted_values.append(v.hex())
                else:
                    formatted_values.append(str(v))
            formatted[key] = formatted_values if len(formatted_values) > 1 else formatted_values[0]
        elif isinstance(value, bytes):
            try:
                formatted[key] = value.decode('utf-8')
            except:
                formatted[key] = value.hex()
        else:
            formatted[key] = str(value)
    return formatted


def packet_to_string(packet: Packet, title: str = "Packet") -> str:
    """Convert a packet to a formatted string."""
    lines = [
        f"{'='*60}",
        f"{title}",
        f"{'='*60}",
        f"Code: {packet.code}",
        f"ID: {packet.id}",
        f"Authenticator: {packet.authenticator.hex() if packet.authenticator else 'N/A'}",
        f"\nAttributes:",
    ]
    
    formatted_attrs = format_packet_attributes(packet)
    for key, value in formatted_attrs.items():
        if isinstance(value, list):
            lines.append(f"  {key}:")
            for v in value:
                lines.append(f"    - {v}")
        else:
            lines.append(f"  {key}: {value}")
    
    return '\n'.join(lines)


@app.route('/')
def index():
    """Serves the main HTML page."""
    return render_template('index.html')


@app.route('/api/test_connection', methods=['POST'])
def test_connection():
    """Test connection to RADIUS server."""
    data = request.json
    try:
        server = data.get('server', '127.0.0.1')
        secret = data.get('secret', 'secret')
        vendor = data.get('vendor', 'mikrotik')
        
        client = get_radius_client(vendor, server, secret)
        start_time = time.time()
        
        try:
            client.authenticate('test_connection', 'test_password')
        except:
            pass
            
        response_time = (time.time() - start_time) * 1000
        
        return jsonify({
            "success": True,
            "message": f"Connection successful! Response time: {response_time:.2f}ms",
            "response_time": response_time
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }), 400


@app.route('/api/get_defaults/<vendor>', methods=['GET'])
def get_defaults(vendor: str):
    """Returns the default Attribute-Value Pairs (AVPs) for a given vendor."""
    try:
        client = get_radius_client(vendor)
        defaults = client.get_default_avps()
        return jsonify(defaults)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500


@app.route('/api/preview_packet', methods=['POST'])
def preview_packet():
    """Creates and returns a string representation of a RADIUS packet without sending it."""
    data = request.json
    try:
        username = data['username']
        password = data['password']
        vendor = data['vendor']
        command = data['command']
        avps = data['avps']
        server = data.get('server', '127.0.0.1')
        secret = data.get('secret', 'secret')

        client = get_radius_client(vendor, server, secret)
        packet: Packet
        
        if command == 'auth':
            packet = client._create_auth_packet(username, password, **avps)
            title = "ACCESS-REQUEST PACKET"
        elif command in ['start', 'alive', 'stop']:
            status_type = command.capitalize()
            packet = client._create_accounting_packet(username, status_type, **avps)
            title = f"ACCOUNTING-REQUEST PACKET ({status_type})"
        else:
            return jsonify({"error": f"Unknown command for preview: {command}"}), 400

        packet_details = packet_to_string(packet, title)
        return jsonify({"packet_details": packet_details})

    except Exception as e:
        return jsonify({"error": f"Failed to generate packet preview: {e}"}), 500


@app.route('/api/execute_step', methods=['POST'])
def execute_step():
    """Receives and executes a SINGLE RADIUS command step."""
    data = request.json
    log_entry = ""
    success = True
    
    try:
        username = data['username']
        password = data['password']
        vendor = data['vendor']
        command = data['command']
        avps = data['avps']
        server = data.get('server', '127.0.0.1')
        secret = data.get('secret', 'secret')

        client = get_radius_client(vendor, server, secret)
        
        request_packet = None
        if command == 'auth':
            request_packet = client._create_auth_packet(username, password, **avps)
        elif command in ['start', 'alive', 'stop']:
            status_type = command.capitalize()
            request_packet = client._create_accounting_packet(username, status_type, **avps)
        
        if request_packet:
            log_entry += packet_to_string(request_packet, f"REQUEST: {command.upper()}")
            log_entry += "\n\n"
        
        log_entry += f"Sending {command.upper()} request to {server}...\n"
        
        start_time = time.time()
        reply_packet = None
        
        if command == 'auth':
            request_pkt = client._create_auth_packet(username, password, **avps)
            reply_packet = client.client.SendPacket(request_pkt)
        elif command == 'start':
            request_pkt = client._create_accounting_packet(username, "Start", **avps)
            reply_packet = client.client.SendPacket(request_pkt)
        elif command == 'alive':
            request_pkt = client._create_accounting_packet(username, "Alive", **avps)
            reply_packet = client.client.SendPacket(request_pkt)
        elif command == 'stop':
            request_pkt = client._create_accounting_packet(username, "Stop", **avps)
            reply_packet = client.client.SendPacket(request_pkt)
        else:
            log_entry += f"Unknown command: {command}\n"
            success = False
            
        response_time = (time.time() - start_time) * 1000
        
        if reply_packet:
            log_entry += packet_to_string(reply_packet, f"REPLY: {command.upper()}")
            log_entry += f"\n\n⏱️  Response time: {response_time:.2f}ms\n"
            
            if command == 'auth':
                if reply_packet.code == 2:
                    log_entry += "✅ Authentication SUCCESSFUL\n"
                elif reply_packet.code == 3:
                    log_entry += "❌ Authentication REJECTED\n"
                    success = False
                else:
                    log_entry += f"⚠️  Unexpected reply code: {reply_packet.code}\n"
            else:
                if reply_packet.code == 5:
                    log_entry += "✅ Accounting packet ACKNOWLEDGED\n"
                else:
                    log_entry += f"⚠️  Unexpected reply code: {reply_packet.code}\n"

    except RadiusClientError as e:
        log_entry += f"\n❌ RADIUS Client Error: {e}\n"
        success = False
    except Exception as e:
        log_entry += f"\n❌ Backend Execution Error: {e}\n"
        import traceback
        log_entry += f"\nTraceback:\n{traceback.format_exc()}\n"
        success = False
        
    return jsonify({"log": log_entry, "success": success})


if __name__ == '__main__':
    app.run(debug=True, port=5001)
