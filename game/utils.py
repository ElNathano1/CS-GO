"""
Game persistence utilities for saving and loading Go games.

This module provides JSON-based serialization for GoGame instances,
allowing games to be saved and resumed later.
"""

import json
import numpy as np
from math import exp
from pyparsing import Literal

from game.core import GoGame


def game_to_dict(game: GoGame) -> dict:
    """
    Serialize a GoGame instance to a dict.
    """

    return {
        "size": game.goban.size,
        "board": game.goban.board.tolist(),
        "current_color": game.current_color,
        "black_passed": game.black_passed,
        "white_passed": game.white_passed,
        "nbr_moves": game.nbr_moves,
        "states": [state.tolist() for state in game.goban.states],
        "singleplayer": game.singleplayer,
    }


def game_from_dict(data: dict) -> GoGame:
    """
    Deserialize a GoGame instance from a dict.
    """

    game = GoGame(data["size"])
    game.goban.board = np.array(data["board"])
    game.current_color = data["current_color"]
    game.black_passed = data["black_passed"]
    game.white_passed = data["white_passed"]
    game.nbr_moves = data["nbr_moves"]
    game.goban.states = [np.array(state) for state in data["states"]]
    game.singleplayer = data["singleplayer"]
    return game

from config import EFG_K_FACTOR, EFG_EPSILON


def save_game(game: GoGame, filename: str) -> None:
    """
    Save a GoGame instance to a JSON file.

    Args:
        game (GoGame): GoGame instance to save
        filename (str): Name of the file to save to
    """

    data = game_to_dict(game)

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
    return game_from_dict(data)


def new_level(level_a: int, level_b: int, winner: Literal["A", "B", "NULL"]) -> tuple[int, int]:  # type: ignore
    """
    Calculate new player levels after a game using the EFG system.

    Args:
        level_a (int): Level of player A. The lowest level of both players.
        level_b (int): Level of player B. The highest level of both players.
        winner (Literal["A", "B", "NULL"]): Winner of the game, "NULL" for a draw.

    Returns:
        tuple[int, int]: New levels for player A and player B
    """

    D = level_b - level_a
    a = (1250 - level_a) / 6

    for threshold, K in sorted(EFG_K_FACTOR.items(), reverse=True):
        print(threshold, K)
        if level_a >= threshold:
            break
    for threshold, EPSILON in sorted(EFG_EPSILON.items(), reverse=True):
        if level_a >= threshold:
            break

    P_A = 1 / (exp(D / a) + 1)
    P_B = 1 - P_A

    if winner == "A":
        score_a, score_b = 1, 0
    elif winner == "B":
        score_a, score_b = 0, 1
    else:
        score_a, score_b = 0.5, 0.5

    new_level_a = level_a + K * (score_a - P_A + EPSILON / 2)
    new_level_b = level_b + K * (score_b - P_B + EPSILON / 2)

    return (
        min(max(round(new_level_a), -2950), 850),
        min(max(round(new_level_b), -2950), 850),
    )


if __name__ == "__main__":

    game = GoGame(9)
    game.take_move(2, 2)
    game.take_move(3, 3)

    save_game(game, "saved_game.csgogame")
    loaded_game = load_game("saved_game.csgogame")
    assert np.array_equal(game.goban.board, loaded_game.goban.board)
    assert game.current_color == loaded_game.current_color
    assert game.black_passed == loaded_game.black_passed
    assert game.white_passed == loaded_game.white_passed
    assert game.nbr_moves == loaded_game.nbr_moves
    assert all(
        np.array_equal(s1, s2)
        for s1, s2 in zip(game.goban.states, loaded_game.goban.states)
    )
