"""
AI players for the Go game.

This module contains various AI implementations for playing Go:
- Player: Base class for all players (human and AI)
- Martin: Simple random-move AI (easy difficulty)
- TrueAI: Base class for lookahead AI players
- Leo: Intermediate AI with basic strategy (medium difficulty)
- Magnus: Advanced AI with deeper lookahead (hard difficulty)

AI players use different strategies and search depths to provide
varying levels of challenge for human players.
"""

import numpy as np
import sys
from pathlib import Path
from typing import Literal
from PIL import Image, ImageTk

import subprocess
import threading
import queue
import time

import random as rd

from game.utils import game_from_dict
from game.core import Goban, GoGame
from game.utils import ffg_points_to_katago, transform_coordinates

from config import (
    BASE_FOLDER_PATH,
    KATAGO_EXECUTABLE_PATH,
    KATAGO_MODEL_PATH,
    KATAGO_HUMAN_MODEL_PATH,
    KATAGO_HUMAN_CONFIG_PATH,
)


class Player:
    """
    A class representing a player in the Go game.

    Attributes:
        name (str): The name of the player.
        level (int): The skill level of the player.
        goban (Goban): The current state of the Go board.
        color (str): The color assigned to the player (Goban.BLACK or Goban.WHITE).
    """

    def __init__(
        self, name: str, profile_photo: ImageTk.PhotoImage, level: int, color: int
    ):
        """
        Initializes the player.

        Args:
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to the player (Goban.BLACK or Goban.WHITE).
        """

        self.name = name
        self.level = level
        self.color = color
        self.profile_photo = profile_photo

        self.opponent_color = Goban.BLACK if color == Goban.WHITE else Goban.WHITE

    def __str__(self) -> str:
        return f"Player {self.name} (playing {'white' if self.color == Goban.WHITE else 'black'})"


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
        resign_probability: float = 0.0001,
        pass_probability: float = 0.5,
    ):
        """
        Initializes the AI opponent.

        Args:
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to Martin (Goban.BLACK or Goban.WHITE).
            resign_probability (float): The probability for Martin to resign whatever the score is.
            pass_probability (float): The probability for Martin to pass after the player have already passed.
        """

        images_dir = Path(BASE_FOLDER_PATH) / "gui" / "images" / "profiles"
        default_photo_path = images_dir / "martin_profile_photo.png"

        if default_photo_path.exists():
            profile_photo = ImageTk.PhotoImage(
                Image.open(default_photo_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        else:
            # Create a blank image if default not found
            blank_image = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
            profile_photo = ImageTk.PhotoImage(blank_image)

        super().__init__(
            name="Martin", color=color, profile_photo=profile_photo, level=-2950
        )
        self.game = game

        self.resign_probability = resign_probability
        self.pass_probability = pass_probability

    def __str__(self) -> str:
        return (
            f"Player Martin (playing {'white' if self.color == Goban.WHITE else 'black'})\n"
            "Martin (level -2950): Enthousiastic Amateur\n"
            "A player that plays random moves with a small chance to pass or resign."
        )

    def choose_move(self) -> tuple[int, int] | Literal["pass", "resign"]:
        """
        Chooses a random move among the possible moves.

        Returns:
            tuple[int, int] | Literal["pass", "resign"]: The chosen move as (x, y), or "pass" or "resign" if no moves are possible.
        """

        # Random chance to resign
        if rd.random() < self.resign_probability:
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
        name (str): The name of the player.
        level (int): The skill level of the player.
        game (GoGame): The current state of the Go board.
        color (int): The color assigned to the TrueAI (Goban.BLACK or Goban.WHITE).
    """

    def __init__(self, name: str, game: GoGame, color: int, level: int):
        """
        Initializes the advanced AI opponent.

        Args:
            id (int): The unique identifier of the AI.
            name (str): The name of the AI.
            level (int): The skill level of the AI.
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to the TrueAI (Goban.BLACK or Goban.WHITE).
        """

        images_dir = Path(BASE_FOLDER_PATH) / "gui" / "images" / "profiles"
        default_photo_path = images_dir / f"{name.lower()}_profile_photo.png"

        if default_photo_path.exists():
            profile_photo = ImageTk.PhotoImage(
                Image.open(default_photo_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        else:
            # Create a blank image if default not found
            blank_image = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
            profile_photo = ImageTk.PhotoImage(blank_image)

        super().__init__(
            name=name, color=color, profile_photo=profile_photo, level=level
        )
        self.game = game
        self.profile_photo = profile_photo

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

        return _true_ai_choose_move(self.game, self.color, nbr_moves)


def _true_ai_choose_move(
    game: GoGame, color: int, nbr_moves: int
) -> tuple[int, int] | Literal["pass", "resign"]:
    opponent_color = Goban.BLACK if color == Goban.WHITE else Goban.WHITE

    def look_ahead(
        game: GoGame, depth: int, maximizing_player: bool, alpha: float, beta: float
    ) -> float:
        if depth == 0:
            score = game.get_score()
            return score[color] - score[opponent_color]

        empty_positions = np.argwhere(game.goban.board == Goban.EMPTY)

        if maximizing_player:
            max_eval = -float("inf")
            for position in empty_positions:
                x, y = position
                temp_game = game.copy()
                valid_move, _ = temp_game.take_move(x, y)
                if not valid_move:
                    continue
                eval = look_ahead(temp_game, depth - 1, False, alpha, beta)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break
            return max_eval

        min_eval = float("inf")
        for position in empty_positions:
            x, y = position
            temp_game = game.copy()
            valid_move, _ = temp_game.take_move(x, y)
            if not valid_move:
                continue
            eval = look_ahead(temp_game, depth - 1, True, alpha, beta)
            min_eval = min(min_eval, eval)
            beta = min(beta, eval)
            if beta <= alpha:
                break
        return min_eval

    empty_positions = np.argwhere(game.goban.board == Goban.EMPTY)
    if len(empty_positions) == 0:
        return "pass"

    best_move = None
    best_score = -float("inf")
    _score = game.get_score()
    current_score = _score[color] - _score[opponent_color]

    for position in empty_positions:
        x, y = position
        temp_game = game.copy()
        valid_move, _ = temp_game.take_move(x, y)
        if not valid_move:
            continue
        score = look_ahead(temp_game, nbr_moves, False, -float("inf"), float("inf"))
        if score > best_score:
            best_score = score
            best_move = [(x, y)]
        elif score == best_score and best_move is not None:
            best_move.append((x, y))

    if best_score - current_score <= 0 and current_score > 0:
        return "pass"

    if best_move is None:
        return "pass"

    return best_move[rd.randint(0, len(best_move) - 1)]


def compute_ai_move(
    game_state: dict,
    ai_kind: str,
    color: int,
    resign_threshold: int = 50,
    resign_probability: float = 0.0001,
    pass_probability: float = 0.5,
) -> tuple[int, int] | Literal["pass", "resign"]:
    """
    Compute an AI move in a headless context (safe for multiprocessing).
    """
    game = game_from_dict(game_state)

    if ai_kind == "Martin":
        # Random AI (Martin)
        opponent_color = Goban.BLACK if color == Goban.WHITE else Goban.WHITE
        if rd.random() < resign_probability:
            return "resign"

        score = game.get_score()
        if score[opponent_color] - score[color] > resign_threshold:
            return "resign"

        if (game.black_passed and color == Goban.WHITE) or (
            game.white_passed and color == Goban.BLACK
        ):
            if rd.random() < pass_probability:
                return "pass"

        empty_positions = np.argwhere(game.goban.board == Goban.EMPTY)
        valid = False
        while not valid and len(empty_positions) > 0:
            random_position = empty_positions[np.random.choice(len(empty_positions))]
            temp_game = game.copy()
            valid, _ = temp_game.take_move(random_position[0], random_position[1])
            empty_positions = np.delete(
                empty_positions,
                np.where((empty_positions == random_position).all(axis=1)),
                axis=0,
            )

        if valid:
            return (random_position[0], random_position[1])
        return "pass"

    if ai_kind == "Leo":
        return _true_ai_choose_move(game, color, 2)

    if ai_kind == "Magnus":
        return _true_ai_choose_move(game, color, 4)

    return _true_ai_choose_move(game, color, 2)


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

        super().__init__(name="Leo", game=game, color=color, level=-2850)

    def __str__(self) -> str:
        return (
            f"Player Leo (playing {'white' if self.color == Goban.WHITE else 'black'})\n"
            "Leo (level -2850): Casual Player\n"
            "A player that analyses all possible moves to pick the directly best one."
        )

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

        super().__init__(name="Magnus", game=game, color=color, level=-2750)

    def __str__(self) -> str:
        return (
            f"Player Magnus (playing {'white' if self.color == Goban.WHITE else 'black'})\n"
            "Magnus (level -2750): Strategic Player\n"
            "A player that analyses several moves ahead to pick the best one."
        )

    def choose_move(self) -> tuple[int, int] | Literal["pass", "resign"]:
        """
        Chooses the best move among the possible moves by simulating each one using look-ahead.

        Returns:
            tuple[int, int] | Literal["pass", "resign"]: The chosen move as (x, y), or "pass" if no moves are possible.
        """

        return super().choose_move(nbr_moves=4)


class KatagoAI(Player):
    """
    A class representing the AI opponent using KataGo.

    Attributes:
        name (str): The name of the player.
        level (int): The skill level of the player.
        game (GoGame): The current state of the Go board.
        color (int): The color assigned to the TrueAI (Goban.BLACK or Goban.WHITE).
    """

    def __init__(
        self,
        name: str,
        game: GoGame,
        color: int,
        level: int,
        katago_path: str = str(KATAGO_EXECUTABLE_PATH),
        model_path: str = str(KATAGO_MODEL_PATH),
        human_model_path: str = str(KATAGO_HUMAN_MODEL_PATH),
        human_example_path: str = str(KATAGO_HUMAN_CONFIG_PATH),
    ):
        """
        Initializes the KataGo AI opponent.

        Args:
            id (int): The unique identifier of the AI.
            name (str): The name of the AI.
            level (int): The skill level of the AI.
            game (GoGame): The current state of the Go board.
            color (int): The color assigned to the TrueAI (Goban.BLACK or Goban.WHITE).
        """

        images_dir = Path(BASE_FOLDER_PATH) / "gui" / "images" / "profiles"
        default_photo_path = images_dir / f"{name.lower()}_profile_photo.png"

        if default_photo_path.exists():
            profile_photo = ImageTk.PhotoImage(
                Image.open(default_photo_path).resize(
                    (32, 32), Image.Resampling.LANCZOS
                )
            )
        else:
            # Create a blank image if default not found
            blank_image = Image.new("RGBA", (32, 32), (255, 255, 255, 0))
            profile_photo = ImageTk.PhotoImage(blank_image)

        super().__init__(
            name=name, color=color, profile_photo=profile_photo, level=level
        )
        self.game = game
        self.profile_photo = profile_photo

        # Change level in KataGo config if needed
        katago_level = f"preaz_{ffg_points_to_katago(level)}"
        self.set_level(katago_level)

        self.process = subprocess.Popen(
            [
                katago_path,
                "gtp",
                "-model",
                model_path,
                "-human-model",
                human_model_path,
                "-config",
                human_example_path,
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )

        self.q = queue.Queue()
        self.stderr_lines = []
        threading.Thread(
            target=self._reader, args=(self.process.stdout, self.q), daemon=True
        ).start()
        threading.Thread(target=self._stderr_reader, daemon=True).start()

        self._wait_for_ready(timeout=120.0)
        self._send(f"boardsize {self.game.goban.size}", timeout=60.0)
        self._send("clear_board")

        # Reconstruct goban state in Katago is needed
        if self.game.nbr_moves > 0:
            self.reconstruct_goban()

    def _reader(self, stream, out_queue):
        for line in stream:
            out_queue.put(line.rstrip("\n"))

    def _stderr_reader(self):
        if not self.process.stderr:
            return
        for line in self.process.stderr:
            self.stderr_lines.append(line.rstrip("\n"))

    def _send(self, cmd: str, timeout: float = 10.0) -> str:
        if not self.process.stdin or self.process.poll() is not None:
            raise RuntimeError("KataGo process not running")

        self.process.stdin.write(cmd + "\n")
        self.process.stdin.flush()

        # GTP responses end with an empty line
        lines = []
        end_time = None if timeout is None else (time.time() + timeout)
        while True:
            remaining = None if end_time is None else max(0.0, end_time - time.time())
            if remaining is not None and remaining == 0.0:
                extra = ""
                exit_code = self.process.poll()
                if exit_code is not None:
                    extra = f" (KataGo exited with code {exit_code})"
                stderr_tail = "\n".join(self.stderr_lines[-20:])
                if stderr_tail:
                    extra += f"\nKataGo stderr (tail):\n{stderr_tail}"
                raise TimeoutError(
                    f"Timeout waiting for KataGo response to: {cmd}{extra}"
                )
            try:
                line = self.q.get(
                    timeout=0.1 if remaining is None else min(0.1, remaining)
                )
            except queue.Empty:
                continue

            if line == "":
                break
            lines.append(line)

        if not lines:
            return ""

        header = lines[0]
        body = "\n".join(line.lstrip() for line in lines[1:]).strip()
        if header.startswith("="):
            return (header[1:].strip() + ("\n" + body if body else "")).strip()
        if header.startswith("?"):
            raise RuntimeError(
                (header[1:].strip() + ("\n" + body if body else "")).strip()
            )
        return "\n".join(lines).strip()

    def _genmove(self, color: str, timeout: float = 60.0) -> str:
        return self._send(f"genmove {color}", timeout=timeout)

    def _play(self, color: str, move: str, timeout: float = 10.0) -> str:
        return self._send(f"play {color} {move}", timeout=timeout)

    def _wait_for_ready(self, timeout: float = 120.0) -> None:
        try:
            self._send("name", timeout=timeout)
        except TimeoutError as exc:
            extra = ""
            exit_code = self.process.poll()
            if exit_code is not None:
                extra = f" (KataGo exited with code {exit_code})"
            stderr_tail = "\n".join(self.stderr_lines[-20:])
            if stderr_tail:
                extra += f"\nKataGo stderr (tail):\n{stderr_tail}"
            raise TimeoutError(f"Timeout waiting for KataGo to start{extra}") from exc

    def set_level(
        self,
        profile: str,
        cfg_path: Path = KATAGO_HUMAN_CONFIG_PATH,
    ) -> None:
        lines = cfg_path.read_text().splitlines()
        new_lines = []

        for line in lines:
            if line.strip().startswith("humanSLProfile"):
                new_lines.append(f"humanSLProfile = {profile}")
            else:
                new_lines.append(line)

        cfg_path.write_text("\n".join(new_lines))

    def reconstruct_goban(self) -> None:
        """
        Reconstruct the current goban state in Katago by sending all moves played so far.
        """
        for x in range(self.game.goban.size):
            for y in range(self.game.goban.size):
                if self.game.goban.board[x, y] == Goban.BLACK:
                    self._play("black", transform_coordinates((x, y)))  # type: ignore
                elif self.game.goban.board[x, y] == Goban.WHITE:
                    self._play("white", transform_coordinates((x, y)))  # type: ignore
                else:
                    continue  # No move found (should not happen)

    def extract_last_move(self) -> str | None:
        """
        To make Katago work, we need to send the other palyer's moves. Compare self.game.goban with previous states to determine
        the latest move.

        Returns:
            (str | None): Last move on str form, None if last move was pass or does not exist.
        """

        # If opponent pass on last turn
        if (
            self.game.black_passed
            if self.color == Goban.WHITE
            else self.game.white_passed
        ):
            return None

        # Checking if last move does not exist (need at least 2 states to compare)
        if len(self.game.goban.states) < 2:
            return None

        last_state = self.game.goban.states[-2]
        current_sate = self.game.goban.board

        # Checking what new stone of opponent color is set
        last_move = None
        for x in range(self.game.goban.size):
            for y in range(self.game.goban.size):
                if (
                    current_sate[x, y] == Goban.BLACK
                    if self.color == Goban.WHITE
                    else Goban.WHITE
                ) and (last_state[x, y] != current_sate[x, y]):
                    last_move = x, y
                    break
            if last_move is not None:
                break

        if last_move is None:
            return None

        return transform_coordinates(last_move)  # type: ignore

    def choose_move(self) -> tuple[int, int] | Literal["pass", "resign"]:
        """
        Chooses the best move using Katago implementation.

        Returns:
            tuple[int, int] | Literal["pass", "resign"]: The chosen move as (x, y), or "pass" if no moves are possible.
        """

        # If there is a last move, meaning the other player moved before
        last_move = self.extract_last_move()
        if last_move is not None:
            opponent_color = "black" if self.color == Goban.WHITE else "white"
            self._play(opponent_color, last_move)

        move = self._genmove("black" if self.color == Goban.BLACK else "white")

        if move in ["resign", "pass"]:
            return move  # type: ignore
        else:
            transformed = transform_coordinates(move)  # type: ignore
            return transformed  # type: ignore

    def close(self) -> None:
        try:
            self._send("quit", timeout=2.0)
        except Exception:
            pass
        if self.process.poll() is None:
            self.process.terminate()
