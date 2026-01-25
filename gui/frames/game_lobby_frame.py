"""
Game lobby frame for the Go game application.

This module provides the game setup interface where users can select
board size and game mode (single player vs multiplayer) before starting a game.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk

if TYPE_CHECKING:
    from gui.app import App


class GameLobbyFrame(ttk.Frame):
    """
    Frame for game lobby before starting a game.

    Allows the user to select game options before starting the game.
    """

    def __init__(self, parent: ttk.Frame, app: "App"):
        """
        Initialize the game lobby frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """

        super().__init__(parent)

        self.app = app

        self.board_size = tk.IntVar(value=19)
        self.multiplayer = tk.BooleanVar(value=True)
        self.ai = None

        # Title
        title = ttk.Label(
            self, text="Game Lobby", font=("Arial", 24, "bold"), background="#f0f0f0"
        )
        title.pack(pady=(40, 20))

        # Number of players selection frame
        player_frame = ttk.LabelFrame(self, padding=20)
        player_frame.pack(pady=20)

        # Buttons for number of players
        ttk.Radiobutton(
            player_frame,
            text="Un joueur (contre IA)",
            variable=self.multiplayer,
            value=False,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        ttk.Radiobutton(
            player_frame,
            text="Deux joueurs (local)",
            variable=self.multiplayer,
            value=True,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)

        # Board size selection frame
        size_frame = ttk.LabelFrame(self, padding=20)
        size_frame.pack(pady=20)

        # Buttons for different board sizes
        ttk.Radiobutton(
            size_frame,
            text="9x9",
            variable=self.board_size,
            value=9,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        ttk.Radiobutton(
            size_frame,
            text="13x13",
            variable=self.board_size,
            value=13,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)
        ttk.Radiobutton(
            size_frame,
            text="19x19",
            variable=self.board_size,
            value=19,
            takefocus=False,
        ).pack(pady=10, fill=tk.X)

        # Start Game button
        self.app.Button(
            self,
            text="Démarrer la partie",
            command=self._start_game,
            takefocus=False,
        ).pack(pady=20)

        # Return to Lobby button
        self.app.Button(
            self,
            text="Retour au Lobby",
            overlay_path=self.app.return_icon_path,
            command=self._return_to_lobby,
            takefocus=False,
        ).pack(pady=20)

    def _start_game(self) -> None:
        """
        Start a new game with the selected board size.

        Args:
            board_size (int): The size of the board (9, 13, or 19).
            multiplayer (bool): Whether the game is multiplayer. Defaults to True.
            ai (int | None): The AI difficulty level if applicable. Defaults to None.
        """
        from gui.frames.game_frame import GameFrame, SingleplayerGameFrame

        if self.multiplayer.get():
            self.app.show_frame(
                lambda parent, app: GameFrame(parent, app, self.board_size.get())
            )

        if not self.multiplayer.get():
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(
                    parent, app, self.board_size.get()
                )
            )

    def _return_to_lobby(self) -> None:
        """
        Return to the lobby frame.
        """
        from gui.frames.lobby_frame import LobbyFrame

        self.app.show_frame(LobbyFrame)
