"""
AI players for the Go game.

This module contains various AI implementations for playing Go:
- Player: Base class for all players (human and AI)
- Martin: Simple random-move AI (easy difficulty)
- TrueAI: Base class for lookahead AI players
- Leo: Intermediate AI with basic strategy (medium difficulty)
- Magnus: Advanced AI with deeper lookahead (hard difficulty)
- TruePlayer: Human player class

AI players use different strategies and search depths to provide
varying levels of challenge for human players.
"""

import numpy as np
import sys
from pathlib import Path
from typing import Literal

import random as rd

# Add parent directory to path to import goban
sys.path.insert(0, str(Path(__file__).parent.parent))
from game.core import Goban, GoGame


class Player:
    """
    A class representing a player in the Go game.

    Attributes:
        id (int): The unique identifier of the player. Negative for AI players.
        name (str): The name of the player.
        level (int): The skill level of the player.

        goban (Goban): The current state of the Go board.
        color (str): The color assigned to the player (Goban.BLACK or Goban.WHITE).
    """

    def __init__(self, id: int | str, name: str, level: int, game: GoGame, color: int):
        """
        Initializes the player.

        Args:
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to the player (Goban.BLACK or Goban.WHITE).
        """

        self.id = id
        self.name = name
        self.level = level

        self.game = game
        self.color = color

        self.opponent_color = Goban.BLACK if color == Goban.WHITE else Goban.WHITE

    def __str__(self) -> str:
        return f"Player {self.id} - {self.name} (Level {self.level})"


class Martin(Player):
    """
    A class representing the AI opponent, "Martin", to play against the user.

    Attributes:
        game (GoGame): The current state of the Go board.
        color (int): The color assigned to Martin (Goban.BLACK or Goban.WHITE).
        resign_threshold (int): The score difference threshold for Martin to resign.
        resign_probability (float): The probability that Martin will resign whatever the score is.
        opponent_color (int): The color of Martin's opponent.
    """

    def __init__(
        self,
        game: GoGame,
        color: int,
        resign_threshold: int = 50,
        resign_probability: float = 0.0001,
        pass_probability: float = 0.5,
    ):
        """
        Initializes the AI opponent.

        Args:
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to Martin (Goban.BLACK or Goban.WHITE).
            resign_threshold (int): The score difference threshold for Martin to resign.
            resign_probability (float): The probability for Martin to resign whatever the score is.
            pass_probability (float): The probability for Martin to pass after the player have already passed.
        """

        super().__init__(id=-1, name="Martin", level=0, game=game, color=color)
        self.resign_threshold = resign_threshold
        self.resign_probability = resign_probability
        self.pass_probability = pass_probability

    def __str__(self) -> str:
        return "-- LEVEL 0 --\nMartin: Enthousiastic Amateur\nA player that plays random moves with a small chance to pass or resign."

    def choose_move(self) -> tuple[int, int] | Literal["pass", "resign"]:
        """
        Chooses a random move among the possible moves.

        Returns:
            tuple[int, int] | Literal["pass", "resign"]: The chosen move as (x, y), or "pass" or "resign" if no moves are possible.
        """

        # Random chance to resign
        if rd.random() < self.resign_probability:
            return "resign"

        # Check score to decide to resign
        score = self.game.get_score()
        if score[self.opponent_color] - score[self.color] > self.resign_threshold:
            return "resign"

        # If the opponent just passed, random chance to pass
        if (self.game.black_passed and self.color == Goban.WHITE) or (
            self.game.white_passed and self.color == Goban.BLACK
        ):
            if rd.random() < self.pass_probability:
                return "pass"

        # Getting all empty positions on the board
        empty_positions = np.argwhere(self.game.goban.board == Goban.EMPTY)

        valid = False
        while not valid and len(empty_positions) > 0:
            random_position = empty_positions[np.random.choice(len(empty_positions))]

            # Check if the move is valid
            temp_game = self.game.copy()
            valid, _ = temp_game.take_move(random_position[0], random_position[1])

            empty_positions = np.delete(
                empty_positions,
                np.where((empty_positions == random_position).all(axis=1)),
                axis=0,
            )

        if valid:
            return (random_position[0], random_position[1])
        else:
            return "pass"


class TrueAI(Player):
    """
    A placeholder class for a more advanced AI opponent, that can look ahead few moves to pick the best one.

    Attributes:
        id (int): The unique identifier of the player. Negative for AI players.
        name (str): The name of the player.
        level (int): The skill level of the player.*

        game (GoGame): The current state of the Go board.
        color (int): The color assigned to the TrueAI (Goban.BLACK or Goban.WHITE).
    """

    def __init__(self, id: int, name: str, level: int, game: GoGame, color: int):
        """
        Initializes the advanced AI opponent.

        Args:
            id (int): The unique identifier of the AI.
            name (str): The name of the AI.
            level (int): The skill level of the AI.
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to the TrueAI (Goban.BLACK or Goban.WHITE).
        """

        super().__init__(id=id, name=name, level=level, game=game, color=color)

    def __str__(self) -> str:
        return f"-- LEVEL {self.level} --\nTrueAI: {self.name}\nA player that uses advanced strategies to play Go."

    def choose_move(
        self, nbr_moves: int
    ) -> tuple[int, int] | Literal["pass", "resign"]:
        """
        Chooses the best move among the possible moves by simulating each one using alpha-beta pruning.

        Args:
            nbr_moves (int): The number of moves to look ahead.

        Returns:
            tuple[int, int] | Literal["pass", "resign"]: The chosen move as (x, y), or "pass" if no moves are possible.
        """

        def look_ahead(
            game: GoGame, depth: int, maximizing_player: bool, alpha: float, beta: float
        ) -> float:
            """
            A recursive minimax function with alpha-beta pruning to evaluate board positions.
            Alpha-beta pruning eliminates branches that cannot affect the final decision,
            significantly reducing computation time without changing the result.

            Args:
                game (GoGame): The current state of the Go board.
                depth (int): Remaining depth to explore (0 = evaluation node).
                maximizing_player (bool): True if the current player is the AI (maximizing), False if opponent (minimizing).
                alpha (float): The best score the maximizing player can guarantee so far.
                beta (float): The best score the minimizing player can guarantee so far.

            Returns:
                float: The evaluation of the board state (score difference for AI).
            """

            # BASE CASE: If depth is 0, evaluate the current board position
            if depth == 0:
                score = game.get_score()
                return score[self.color] - score[self.opponent_color]

            # Get all empty positions where a move can be played
            empty_positions = np.argwhere(game.goban.board == Goban.EMPTY)

            # MAXIMIZING PLAYER (AI's turn): Try to maximize the score
            if maximizing_player:
                max_eval = -float("inf")

                for position in empty_positions:
                    x, y = position
                    temp_game = game.copy()
                    valid_move, _ = temp_game.take_move(x, y)

                    # Skip invalid moves
                    if not valid_move:
                        continue

                    # Recursively evaluate this move (opponent's turn next)
                    eval = look_ahead(temp_game, depth - 1, False, alpha, beta)
                    max_eval = max(max_eval, eval)

                    # ALPHA-BETA PRUNING: Update alpha and prune if possible
                    alpha = max(alpha, eval)
                    if beta <= alpha:
                        # Beta cutoff: opponent won't allow this branch, so stop exploring
                        break

                return max_eval

            # MINIMIZING PLAYER (Opponent's turn): Try to minimize the AI's score
            else:
                min_eval = float("inf")

                for position in empty_positions:
                    x, y = position
                    temp_game = game.copy()
                    valid_move, _ = temp_game.take_move(x, y)

                    # Skip invalid moves
                    if not valid_move:
                        continue

                    # Recursively evaluate this move (AI's turn next)
                    eval = look_ahead(temp_game, depth - 1, True, alpha, beta)
                    min_eval = min(min_eval, eval)

                    # ALPHA-BETA PRUNING: Update beta and prune if possible
                    beta = min(beta, eval)
                    if beta <= alpha:
                        # Alpha cutoff: AI won't allow this branch, so stop exploring
                        break

                return min_eval

        # STEP 1: Get all empty positions on the board
        empty_positions = np.argwhere(self.game.goban.board == Goban.EMPTY)

        # If no positions are available, pass the turn
        if len(empty_positions) == 0:
            return "pass"

        # STEP 2: Initialize variables to track the best move
        best_move = None
        best_score = -float("inf")
        _score = self.game.get_score()
        current_score = _score[self.color] - _score[self.opponent_color]

        # STEP 3: Evaluate each possible move
        for position in empty_positions:
            x, y = position

            # Create a copy of the game to simulate the move
            temp_game = self.game.copy()
            valid_move, _ = temp_game.take_move(x, y)

            # Skip invalid moves
            if not valid_move:
                continue

            # STEP 4: Use look_ahead with alpha-beta pruning to evaluate this move
            # Start with alpha = -infinity and beta = +infinity
            score = look_ahead(temp_game, nbr_moves, False, -float("inf"), float("inf"))

            # STEP 5: Keep track of the move with the best evaluation
            if score > best_score:
                best_score = score
                best_move = [(x, y)]
            elif score == best_score and best_move is None:
                continue
            elif score == best_score:
                best_move.append((x, y))  # type: ignore

        # STEP 6: Return the best move found, or "pass" if no valid moves exist
        if best_score - current_score <= 0 and current_score > 0:
            return "pass"

        if best_move is None:
            return "pass"

        return best_move[rd.randint(0, len(best_move) - 1)]


class Leo(TrueAI):
    """
    A class representing the AI opponent, "Leo", to play against the user.

    Attributes:
        game (GoGame): The current state of the Go board.
        color (int): The color assigned to Leo (Goban.BLACK or Goban.WHITE).
    """

    def __init__(self, game: GoGame, color: int):
        """
        Initializes the AI opponent.

        Args:
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to Leo (Goban.BLACK or Goban.WHITE).
        """

        super().__init__(id=-2, name="Leo", level=1, game=game, color=color)

    def __str__(self) -> str:
        return "-- LEVEL 1 --\nLeo: Casual Player\nA player that analyses all possible moves to pick the directly best one."

    def choose_move(self) -> tuple[int, int] | Literal["pass", "resign"]:
        """
        Chooses the best move among the possible moves by simulating each one.

        Returns:
            tuple[int, int] | Literal["pass", "resign"]: The chosen move as (x, y), or "pass" if no moves are possible.
        """

        return super().choose_move(nbr_moves=2)


class Magnus(TrueAI):
    """
    A class representing the AI opponent, "Magnus", to play against the user.

    Attributes:
        game (GoGame): The current state of the Go board.
        color (int): The color assigned to Magnus (Goban.BLACK or Goban.WHITE).
    """

    def __init__(self, game: GoGame, color: int):
        """
        Initializes the AI opponent.

        Args:
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to Magnus (Goban.BLACK or Goban.WHITE).
        """

        super().__init__(id=-3, name="Magnus", level=2, game=game, color=color)

    def __str__(self) -> str:
        return "-- LEVEL 2 --\nMagnus: Strategic Player\nA player that analyses several moves ahead to pick the best one."

    def choose_move(self) -> tuple[int, int] | Literal["pass", "resign"]:
        """
        Chooses the best move among the possible moves by simulating each one using look-ahead.

        Returns:
            tuple[int, int] | Literal["pass", "resign"]: The chosen move as (x, y), or "pass" if no moves are possible.
        """

        return super().choose_move(nbr_moves=4)


class TruePlayer(Player):
    """
    A class representing a human player.

    Attributes:
        game (GoGame): The current state of the Go board.
        color (int): The color assigned to the TruePlayer (Goban.BLACK or Goban.WHITE).
    """

    def __init__(self, id: int | str, name: str, level: int, game: GoGame, color: int):
        """
        Initializes the human player.

        Args:
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to the TruePlayer (Goban.BLACK or Goban.WHITE).
        """

        super().__init__(id=id, name=name, level=level, game=game, color=color)

    def __str__(self) -> str:
        return f"-- HUMAN PLAYER --\n{self.name}: Human Player\nA human player playing against the AI."
