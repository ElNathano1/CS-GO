"""
Core game logic for Go (Weiqi/Baduk).

This module contains the fundamental classes for implementing a Go game:
- Goban: The game board with all core Go rules (captures, ko, scoring)
- GoGame: Game state management (turns, passing, game end detection)

These classes handle all the game mechanics following standard Go rules,
including Chinese-style scoring.
"""

import numpy as np
from collections import deque
from typing import Set, Tuple, Dict, List


class Goban:
    """
    Represents a Go board (goban) and implements all core Go rules:
    - Stone placement
    - Chain and liberty detection
    - Captures
    - Ko rule (simple ko)
    - Territory detection
    - Scoring (Chinese-style)
    """

    EMPTY: int = 0
    BLACK: int = 1
    WHITE: int = 2

    def __init__(self, size: int):
        """
        Initialize an empty goban of given size.

        Args:
            size (int): Board size (e.g. 9, 13, 19)
        """
        self.size: int = size
        self.board: np.ndarray = np.zeros((size, size), dtype=int)

        # History of board states (used for ko rule)
        self.states: List[np.ndarray] = [self.board.copy()]

    # ======================
    # Basic utilities
    # ======================

    def _on_board(self, x: int, y: int) -> bool:
        """
        Check if coordinates are inside the board.

        Args:
            x (int): Row index
            y (int): Column index

        Returns:
            bool: True if inside the board
        """
        return 0 <= x < self.size and 0 <= y < self.size

    def _neighbours(self, x: int, y: int):
        """
        Yield all orthogonal neighbours of a board position.

        Args:
            x (int): Row index
            y (int): Column index

        Yields:
            tuple[int, int]: Valid neighbour coordinates
        """
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if self._on_board(nx, ny):
                yield nx, ny

    @staticmethod
    def opponent(color: int) -> int:
        """
        Return the opponent color.

        Args:
            color (int): Current color

        Returns:
            int: Opponent color
        """
        return Goban.BLACK if color == Goban.WHITE else Goban.WHITE

    # ======================
    # Chains and liberties
    # ======================

    def _chain_and_liberties(
        self, x: int, y: int
    ) -> Tuple[Set[Tuple[int, int]], Set[Tuple[int, int]]]:
        """
        Compute the chain and liberties of the stone at (x, y).

        Uses a BFS flood-fill starting from the given stone.

        Args:
            x (int): Row index
            y (int): Column index

        Returns:
            tuple:
                - set of (x, y) stones belonging to the chain
                - set of (x, y) liberties of the chain
        """
        color: int = self.board[x, y]
        assert color != self.EMPTY

        chain: Set[Tuple[int, int]] = set()
        liberties: Set[Tuple[int, int]] = set()
        visited: Set[Tuple[int, int]] = set()

        queue: deque[Tuple[int, int]] = deque([(x, y)])

        while queue:
            cx, cy = queue.popleft()
            if (cx, cy) in visited:
                continue

            visited.add((cx, cy))
            chain.add((cx, cy))

            for nx, ny in self._neighbours(cx, cy):
                if self.board[nx, ny] == self.EMPTY:
                    liberties.add((nx, ny))
                elif self.board[nx, ny] == color and (nx, ny) not in visited:
                    queue.append((nx, ny))

        return chain, liberties

    # ======================
    # Move legality (simulation)
    # ======================

    def possible_move(self, x: int, y: int, color: int) -> bool:
        """
        Check whether placing a stone at (x, y) is legal.

        Rules checked:
        - Position must be empty
        - Move must not be suicide (unless it captures)
        - Move must not violate the simple ko rule

        The board state is restored after simulation.

        Args:
            x (int): Row index
            y (int): Column index
            color (int): Stone color

        Returns:
            bool: True if the move is legal
        """
        if not self._on_board(x, y):
            return False
        if self.board[x, y] != self.EMPTY:
            return False

        # Save current board
        snapshot: np.ndarray = self.board.copy()

        # Play the stone temporarily
        self.board[x, y] = color
        opponent: int = self.opponent(color)
        captured_any: bool = False

        # Check opponent captures
        for nx, ny in self._neighbours(x, y):
            if self.board[nx, ny] == opponent:
                chain, liberties = self._chain_and_liberties(nx, ny)
                if not liberties:
                    self._remove_chain(chain)
                    captured_any = True

        # Check suicide
        _, liberties = self._chain_and_liberties(x, y)
        legal: bool = bool(liberties) or captured_any

        # Simple ko: compare only with position N-2
        if legal and len(self.states) >= 2:
            if np.array_equal(self.board, self.states[-2]):
                legal = False

        # Restore board
        self.board = snapshot
        return legal

    # ======================
    # Playing a move
    # ======================

    def play_move(self, x: int, y: int, color: int) -> tuple[bool, bool]:
        """
        Play a legal move and update the board state.

        Args:
            x (int): Row index
            y (int): Column index
            color (int): Stone color

        Returns:
            tuple[bool, bool]: Indicates if the move was played and if it was a capture
        """
        if not self.possible_move(x, y, color):
            return False, False

        self.board[x, y] = color
        opponent: int = self.opponent(color)

        # Remove captured opponent chains
        capture = False
        for nx, ny in self._neighbours(x, y):
            if self.board[nx, ny] == opponent:
                chain, liberties = self._chain_and_liberties(nx, ny)
                if not liberties:
                    self._remove_chain(chain)
                    capture = True

        # Save new board state (for ko)
        self.states.append(self.board.copy())
        return True, capture

    def _remove_chain(self, chain: Set[Tuple[int, int]]) -> None:
        """
        Remove all stones in a chain from the board.

        Args:
            chain (set): Set of (x, y) stones
        """
        for x, y in chain:
            self.board[x, y] = self.EMPTY

    # ======================
    # Territories
    # ======================

    def _calc_territories(self) -> Dict[int, List[Set[Tuple[int, int]]]]:
        """
        Detect all empty territories and assign them to a color if possible.

        A territory is assigned to a color if all bordering stones belong
        to that single color.

        Returns:
            dict:
                {
                    BLACK: [territory1, territory2, ...],
                    WHITE: [...]
                }
        """
        territories: Dict[int, List[Set[Tuple[int, int]]]] = {
            self.BLACK: [],
            self.WHITE: [],
        }

        visited: Set[Tuple[int, int]] = set()

        for x in range(self.size):
            for y in range(self.size):
                if self.board[x, y] != self.EMPTY or (x, y) in visited:
                    continue

                territory: Set[Tuple[int, int]] = set()
                border_colors: Set[int] = set()
                queue: deque[Tuple[int, int]] = deque([(x, y)])

                while queue:
                    cx, cy = queue.popleft()
                    if (cx, cy) in visited:
                        continue

                    visited.add((cx, cy))
                    territory.add((cx, cy))

                    for nx, ny in self._neighbours(cx, cy):
                        value = self.board[nx, ny]
                        if value == self.EMPTY and (nx, ny) not in visited:
                            queue.append((nx, ny))
                        elif value != self.EMPTY:
                            border_colors.add(value)

                if len(border_colors) == 1:
                    color = border_colors.pop()
                    territories[color].append(territory)

        return territories

    # ======================
    # Scoring
    # ======================

    def score(self) -> Dict[int, int]:
        """
        Compute the score using Chinese rules:
        - Stones on the board
        - Controlled territory intersections

        Returns:
            dict[int, int]: Score per color
        """
        score: Dict[int, int] = {
            self.BLACK: int(np.sum(self.board == self.BLACK)),  # type: ignore
            self.WHITE: int(np.sum(self.board == self.WHITE)),  # type: ignore
        }

        territories = self._calc_territories()

        for color in (self.BLACK, self.WHITE):
            for territory in territories[color]:
                score[color] += len(territory)

        return score

    # ======================
    # Display
    # ======================

    def __str__(self) -> str:
        """
        Return a human-readable board representation.

        Returns:
            str: Board as ASCII grid
        """
        symbols = {self.EMPTY: ".", self.BLACK: "X", self.WHITE: "O"}
        return "\n".join(
            " ".join(symbols[value] for value in row) for row in self.board
        )


class GoGame:
    """
    Manages a Go game:
    - Player turns
    - Passing
    - Game end detection
    - Score access
    """

    def __init__(self, size: int):
        """
        Initialize a new Go game.

        Args:
            size (int): Board size
        """
        self.goban: Goban = Goban(size)
        self.current_color: int = Goban.BLACK
        self.black_passed: bool = False
        self.white_passed: bool = False
        self.nbr_moves: int = 0

        self.singleplayer: bool = False

    def copy(self) -> "GoGame":
        """
        Create a deep copy of the current game state.

        Returns:
            GoGame: A new GoGame instance with the same state
        """

        new_game = GoGame(self.goban.size)
        new_game.goban.board = self.goban.board.copy()
        new_game.goban.states = [state.copy() for state in self.goban.states]
        new_game.current_color = self.current_color
        new_game.black_passed = self.black_passed
        new_game.white_passed = self.white_passed
        new_game.nbr_moves = self.nbr_moves

        return new_game

    def set_singleplayer(self) -> None:
        """
        Check if the game is in singleplayer mode against an AI.

        Args:
            ai_color (int): Color assigned to the AI
            ai_id (int): ID of the AI player
        """

        self.singleplayer = True

    def switch_player(self) -> None:
        """Switch the active player."""
        self.current_color = (
            Goban.WHITE if self.current_color == Goban.BLACK else Goban.BLACK
        )

    def take_move(self, x: int, y: int) -> tuple[bool, bool]:
        """
        Attempt to play a move for the current player.

        Args:
            x (int): Row index
            y (int): Column index

        Returns:
            tuple[bool, bool]: Indicates if the move was successful and if it was a capture
        """
        successfull, capture = self.goban.play_move(x, y, self.current_color)
        if successfull:
            self.nbr_moves += 1
            self.black_passed = False
            self.white_passed = False
            self.switch_player()
            return True, capture
        return False, False

    def pass_move(self) -> None:
        """
        Pass the current player's turn.
        """
        if self.current_color == Goban.BLACK:
            self.black_passed = True
        else:
            self.white_passed = True

        self.nbr_moves += 1
        self.switch_player()

    def game_over(self) -> bool:
        """
        Determine if the game is over.

        Returns:
            bool: True if both players passed consecutively
        """
        return self.black_passed and self.white_passed

    def get_score(self) -> Dict[int, int]:
        """
        Get the current score.

        Returns:
            dict[int, int]: Score per color
        """
        return self.goban.score()

    def get_winner(self) -> int | None:
        """
        Determine the winner.

        Returns:
            int | None: Winning color, or None if tie
        """
        score = self.get_score()
        if score[Goban.BLACK] > score[Goban.WHITE]:
            return Goban.BLACK
        if score[Goban.WHITE] > score[Goban.BLACK]:
            return Goban.WHITE
        return None
