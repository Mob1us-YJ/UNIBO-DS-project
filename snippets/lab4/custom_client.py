import socket
import threading
import json
from snippets.lab4.example1_presentation import serialize, deserialize, Request, Response


class CustomClient:
    """A custom client class for MindRoll that properly manages network connections."""

    def __init__(self, server_address):
        self.server_address = server_address  # (IP, Port)
        self.sock = None
        self.connected = False
        self.lock = threading.Lock()  # Ensure thread safety

    def connect(self):
        """Establish a connection to the server."""
        if not self.connected:
            try:
                self.sock = socket.create_connection(self.server_address)  # Creates a TCP connection
                self.connected = True
                print(f"✅ Connected to server at {self.server_address}")
            except Exception as e:
                print(f"❌ Connection failed: {e}")

    def send_request(self, method, *args):
        """Send an RPC request to the server."""
        if not self.connected:
            self.connect()

        # Ensure valid JSON structure
        request = Request(method, args, {})
        serialized_request = json.dumps(request.__dict__, ensure_ascii=False) + "\n"  # Ensure message is properly terminated

        print(f"📤 Sending JSON request: {serialized_request.strip()}")  # 🔥 Debug JSON before sending

        try:
            with self.lock:
                self.sock.sendall(serialized_request.encode('utf-8'))  # Send request
                response_data = self.sock.recv(4096).decode('utf-8')  # Receive response
                
                print(f"📥 Received response: {response_data.strip()}")  # 🔥 Debug server response
                
                # Ensure response is a proper JSON object
                response_data = response_data.strip()
                if not response_data.startswith("{"):
                    print("❌ Received malformed JSON response. Attempting to fix...")
                    response_data = response_data[1:]  # Remove the first incorrect character

                if not response_data.strip():
                    print("❌ Server sent an empty response.")
                    return None

                response = deserialize(response_data)  # Deserialize response
                
                if isinstance(response, Response) and response.error:
                    print(f"❌ Server Error: {response.error}")
                return response
        except Exception as e:
            print(f"❌ Error during RPC request: {e}")
            return None


    def close(self):
        """Close the connection."""
        if self.sock:
            self.sock.close()
            self.connected = False
            print("❌ Connection closed")
