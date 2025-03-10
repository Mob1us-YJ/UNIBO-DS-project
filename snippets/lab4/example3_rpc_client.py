from snippets.lab3 import Client
from snippets.lab4.users import Token
from snippets.lab4.example1_presentation import serialize, deserialize, Request, Response
import traceback


class MindRollClient(Client):
    def __init__(self, server_address):
        super().__init__(server_address, self.__on_connection_event)
        self.token = None  # Store authentication token
        self.connected = False  # Track connection status

    def connect(self):
        """Establishes a connection if not already connected."""
        if not self.connected:
            print(f"🔗 Connecting to server at {self.server_address}...")
            try:
                super().connect()  # Call parent class connect (if exists)
                self.connected = True
                print("✅ Connection established!")
            except AttributeError:
                print("❌ Error: `connect()` method not found in parent class.")
            except Exception as e:
                print(f"❌ Failed to connect: {e}")

    def __on_connection_event(self, event, connection, error):
        """Handles connection events."""
        match event:
            case 'connect':
                connection.callback = self.__on_message_event
                self.connected = True  # Mark connection as established
            case 'error':
                traceback.print_exception(error)
                self.connected = False
            case 'close':
                print("❌ Connection closed")
                self.connected = False

    def __on_message_event(self, event, payload, connection, error):
        """Handles messages received from the server."""
        match event:
            case 'message':
                try:
                    response = deserialize(payload)
                    assert isinstance(response, Response)
                    if response.error:
                        print(f"❌ Error: {response.error}")
                    else:
                        print(f"✅ Response: {response.result}")
                except Exception as e:
                    traceback.print_exc()
                    print("❌ Failed to parse response")
                finally:
                    connection.close()
            case 'error':
                traceback.print_exception(error)
            case 'close':
                print("❌ Message connection closed")

    def send_request(self, method, *args):
        """Send an RPC request with authentication if available."""
        self.connect()  # Ensure connection before sending request
        metadata = {"token": self.token} if self.token else {}
        request = Request(method, args, metadata)
        self.send(serialize(request))

    def authenticate(self, token):
        """Set the authentication token."""
        if isinstance(token, Token):
            self.token = token.token  # Store only the token string
            print("✅ Authentication successful!")
        else:
            print("❌ Invalid token format!")

    def create_room(self, room_id):
        """Create a new game room."""
        print(f"🏠 Creating room: {room_id}")
        self.send_request("create_room", room_id)

    def join_room(self, room_id, player_name):
        """Join an existing game room."""
        print(f"👤 {player_name} is joining room: {room_id}")
        self.send_request("join_room", room_id, player_name)

    def call_number(self, room_id, player_name, number):
        """Player calls a number."""
        print(f"🎲 {player_name} calls number {number} in room {room_id}")
        self.send_request("call_number", room_id, player_name, number)

    def reveal_result(self, room_id, player_name):
        """Player reveals the result."""
        print(f"📢 {player_name} is revealing the result in room {room_id}")
        self.send_request("reveal_result", room_id, player_name)

    def get_game_state(self, room_id):
        """Retrieve the current game state."""
        print(f"📊 Fetching game state for room {room_id}")
        self.send_request("get_game_state", room_id)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 3:
        print("Usage: python example3_rpc_client.py <server_ip> <server_port>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])

    client = MindRollClient((server_ip, server_port))

    print("\n=== MindRoll Client Ready ===")
    print("Commands: create_room, join_room, call_number, reveal_result, get_game_state, exit")

    while True:
        try:
            command = input("\nEnter command: ").strip().split()
            if not command:
                continue

            cmd, *params = command

            if cmd == "create_room" and len(params) == 1:
                client.create_room(params[0])

            elif cmd == "join_room" and len(params) == 2:
                client.join_room(params[0], params[1])

            elif cmd == "call_number" and len(params) == 3:
                client.call_number(params[0], params[1], int(params[2]))

            elif cmd == "reveal_result" and len(params) == 2:
                client.reveal_result(params[0], params[1])

            elif cmd == "get_game_state" and len(params) == 1:
                client.get_game_state(params[0])

            elif cmd == "exit":
                print("Exiting client...")
                break

            else:
                print("❌ Invalid command or parameters!")

        except KeyboardInterrupt:
            print("\nClient shutting down.")
            break
        except Exception as e:
            traceback.print_exc()
            print("❌ An error occurred.")
