import json


class Request:
    """ Represents an RPC request. """

    def __init__(self, name, args=None, metadata=None):
        self.name = name
        self.args = args if args else []
        self.metadata = metadata if metadata else {}

    def to_dict(self):
        """ Converts request data to a dictionary for serialization. """
        return {
            "name": self.name,
            "args": self.args,
            "metadata": self.metadata
        }

    @staticmethod
    def from_dict(data):
        """ Creates a Request object from a dictionary. """
        return Request(
            name=data["name"],
            args=data.get("args", []),
            metadata=data.get("metadata", {})
        )


class Response:
    """ Represents an RPC response. """

    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error

    def to_dict(self):
        """ Converts response data to a dictionary for serialization. """
        return {
            "result": self.result,
            "error": self.error
        }

    @staticmethod
    def from_dict(data):
        """ Creates a Response object from a dictionary. """
        return Response(
            result=data.get("result"),
            error=data.get("error")
        )


def serialize(obj):
    """ Serializes an object into a JSON string. """
    return json.dumps(obj.to_dict())


def deserialize(json_string):
    """ Deserializes a JSON string into a Request or Response object. """
    try:
        data = json.loads(json_string)
        if "name" in data:
            return Request.from_dict(data)
        elif "result" in data or "error" in data:
            return Response.from_dict(data)
        else:
            raise ValueError("Invalid JSON format")
    except json.JSONDecodeError:
        raise ValueError("Failed to parse JSON")


class MindRollGameState:
    """ Represents the current game state for MindRoll. """

    def __init__(self, players=None, current_turn=None, called_number=None, winner=None):
        self.players = players if players else {}  # { "player1": { "dice_number": 4, "dice_color": "red", "score": 0 } }
        self.current_turn = current_turn  # Name of the player whose turn it is
        self.called_number = called_number  # Last called number
        self.winner = winner  # Name of the winning player

    def to_dict(self):
        """ Converts the game state to a dictionary for serialization. """
        return {
            "players": self.players,
            "current_turn": self.current_turn,
            "called_number": self.called_number,
            "winner": self.winner
        }

    @staticmethod
    def from_dict(data):
        """ Creates a MindRollGameState object from a dictionary. """
        return MindRollGameState(
            players=data.get("players", {}),
            current_turn=data.get("current_turn"),
            called_number=data.get("called_number"),
            winner=data.get("winner")
        )


def serialize_game_state(game_state):
    """ Serializes the game state into a JSON string. """
    return json.dumps(game_state.to_dict())


def deserialize_game_state(json_string):
    """ Deserializes a JSON string into a MindRollGameState object. """
    try:
        data = json.loads(json_string)
        return MindRollGameState.from_dict(data)
    except json.JSONDecodeError:
        raise ValueError("Failed to parse game state JSON")


# Example usage for testing
if __name__ == "__main__":
    # Creating a sample request
    request = Request("join_room", ["room1", "Alice"])
    serialized_request = serialize(request)
    print("Serialized Request:", serialized_request)

    deserialized_request = deserialize(serialized_request)
    print("Deserialized Request:", deserialized_request.to_dict())

    # Creating a sample response
    response = Response("Player joined successfully")
    serialized_response = serialize(response)
    print("Serialized Response:", serialized_response)

    deserialized_response = deserialize(serialized_response)
    print("Deserialized Response:", deserialized_response.to_dict())

    # Creating a sample game state
    game_state = MindRollGameState(
        players={
            "Alice": {"dice_number": 4, "dice_color": "red", "score": 1},
            "Bob": {"dice_number": 6, "dice_color": "blue", "score": 0}
        },
        current_turn="Bob",
        called_number=10,
        winner=None
    )

    serialized_game_state = serialize_game_state(game_state)
    print("Serialized Game State:", serialized_game_state)

    deserialized_game_state = deserialize_game_state(serialized_game_state)
    print("Deserialized Game State:", deserialized_game_state.to_dict())
