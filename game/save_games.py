import json
import numpy as np

from game.game_classes import GoGame


def save_game(game: GoGame, filename: str) -> None:
    """
    Save a GoGame instance to a JSON file.

    Args:
        game (GoGame): GoGame instance to save
        filename (str): Name of the file to save to
    """

    data = {
        "size": game.goban.size,
        "board": game.goban.board.tolist(),
        "current_color": game.current_color,
        "black_passed": game.black_passed,
        "white_passed": game.white_passed,
        "nbr_moves": game.nbr_moves,
        "states": [state.tolist() for state in game.goban.states],
        "singleplayer": game.singleplayer,
        "ai_color": game.ai_color,
        "ai_id": game.ai_id,
    }

    with open(filename, "w") as f:
        json.dump(data, f, indent=2)


def load_game(filename: str) -> GoGame:
    """
    Load a GoGame instance from a JSON file.

    Args:
        filename (str): Name of the file to load

    Returns:
        GoGame: Loaded game
    """

    with open(filename, "r") as f:
        data = json.load(f)

    # Recréer la partie
    game = GoGame(data["size"])
    game.goban.board = np.array(data["board"])
    game.current_color = data["current_color"]
    game.black_passed = data["black_passed"]
    game.white_passed = data["white_passed"]
    game.nbr_moves = data["nbr_moves"]
    game.goban.states = [np.array(state) for state in data["states"]]
    game.singleplayer = data["singleplayer"]
    game.ai_color = data["ai_color"]
    game.ai_id = data["ai_id"]

    return game


if __name__ == "__main__":

    game = GoGame(9)
    game.take_move(2, 2)
    game.take_move(3, 3)

    save_game(game, "saved_game.csgogame")
    loaded_game = load_game("saved_game.csgogame")

    print("Original Game:")
    print(game.goban.__str__())
    print("size:", game.goban.size)
    print("current_color:", game.current_color)
    print("black_passed:", game.black_passed)
    print("white_passed:", game.white_passed)
    print("nbr_moves:", game.nbr_moves)
    print(
        "states:",
        len(game.goban.states),
    )

    print("Loaded Game:")
    print(loaded_game.goban.__str__())
    print("size:", loaded_game.goban.size)
    print("current_color:", loaded_game.current_color)
    print("black_passed:", loaded_game.black_passed)
    print("white_passed:", loaded_game.white_passed)
    print("nbr_moves:", loaded_game.nbr_moves)
    print("states:", len(loaded_game.goban.states))
    assert np.array_equal(game.goban.board, loaded_game.goban.board)
    assert game.current_color == loaded_game.current_color
    assert game.black_passed == loaded_game.black_passed
    assert game.white_passed == loaded_game.white_passed
    assert game.nbr_moves == loaded_game.nbr_moves
    assert all(
        np.array_equal(s1, s2)
        for s1, s2 in zip(game.goban.states, loaded_game.goban.states)
    )
