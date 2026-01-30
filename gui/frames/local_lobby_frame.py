"""
Game lobby frame for the Go game application.

This module provides the game setup interface where users can select
board size and game mode (single player vs multiplayer) before starting a game.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk

from game.core import Goban
from gui.frames.game_frame import GameFrame, SingleplayerGameFrame
from gui.utils import random_username
from player.ai import Martin, Player

from game.core import GoGame

if TYPE_CHECKING:
    from gui.app import App


class LocalLobbyFrame(ttk.Frame):
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
        loading = self.app.show_loading("Chargement du lobby local...")

        self.board_size = tk.IntVar(value=19)
        self.multiplayer = tk.BooleanVar(value=True)
        self.ai = None

        # Title
        title = ttk.Label(self, text="Game Lobby", style="Title.TLabel")
        title.pack(pady=40)

        self.container = ttk.Frame(self)
        self.container.pack()

        # Ensure account panel is visible on this frame
        if hasattr(self.app, "account_panel") and self.app.account_panel:
            self.app.account_panel.lift()

        # Number of players selection frame
        main_player_frame = self.app.Frame(self.container, bg="black", bd=1)
        main_player_frame.pack(pady=20, fill=tk.X)
        player_frame = self.app.Frame(main_player_frame)
        player_frame.pack(pady=3, padx=3, fill=tk.X)

        # Buttons for number of players
        ttk.Radiobutton(
            player_frame.content_frame,
            text="Un joueur (contre IA)",
            variable=self.multiplayer,
            value=False,
            takefocus=False,
        ).pack(padx=30, pady=(20, 10), fill=tk.X)
        ttk.Radiobutton(
            player_frame.content_frame,
            text="Deux joueurs (local)",
            variable=self.multiplayer,
            value=True,
            takefocus=False,
        ).pack(padx=30, pady=(10, 20), fill=tk.X)

        # Board size selection frame
        main_size_frame = self.app.Frame(self.container, bg="black", bd=1)
        main_size_frame.pack(pady=20, fill=tk.X)
        size_frame = self.app.Frame(main_size_frame)
        size_frame.pack(pady=3, padx=3, fill=tk.X)

        # Buttons for different board sizes
        ttk.Radiobutton(
            size_frame.content_frame,
            text="9x9",
            variable=self.board_size,
            value=9,
            takefocus=False,
        ).pack(padx=30, pady=(20, 10), fill=tk.X)
        ttk.Radiobutton(
            size_frame.content_frame,
            text="13x13",
            variable=self.board_size,
            value=13,
            takefocus=False,
        ).pack(padx=30, pady=10, fill=tk.X)
        ttk.Radiobutton(
            size_frame.content_frame,
            text="19x19",
            variable=self.board_size,
            value=19,
            takefocus=False,
        ).pack(padx=30, pady=(10, 20), fill=tk.X)

        self.app.Button(
            self.container,
            text="Continuer la partie",
            command=lambda: self._resume_game(game=self.app.current_game),  # type: ignore
            state=tk.DISABLED if self.app.current_game is None else tk.NORMAL,
            takefocus=False,
        ).pack(pady=(20, 10))

        # Start Game button
        self.app.Button(
            self.container,
            text="Démarrer la partie",
            command=self._start_game,
            takefocus=False,
        ).pack(pady=10)

        # Return to Lobby button
        self.app.Button(
            self.container,
            text="Retour au Lobby",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._return_to_lobby,
            takefocus=False,
        ).pack(pady=(10, 20))

        self.app.hide_loading(loading)

    def _resume_game(self, game: "GoGame") -> None:
        """
        Resume an existing game.

        Args:
            game (GoGame): The game instance to resume.
        """

        board_size = game.goban.size
        if not game.singleplayer:
            self.app.show_frame(
                lambda parent, app: GameFrame(
                    parent,
                    app,
                    board_size,
                    Player(
                        self.app.account_profile_photo["text"].strip(),
                        self.app.get_profile_photo(),
                        color=Goban.BLACK,
                        level=-1,
                    ),
                    Player(
                        random_username(),
                        self.app._get_default_profile_photo(),
                        color=Goban.WHITE,
                        level=-1,
                    ),
                    game,
                )
            )
        else:
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(
                    parent,
                    app,
                    board_size,
                    Martin(game, Goban.BLACK),
                    Player(
                        self.app.account_profile_photo["text"].strip(),
                        self.app.get_profile_photo(),
                        color=Goban.WHITE,
                        level=-1,
                    ),
                    game,
                )
            )

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
            game = GoGame(self.board_size.get())
            self.app.show_frame(
                lambda parent, app: GameFrame(
                    parent,
                    app,
                    self.board_size.get(),
                    Player(
                        self.app.account_profile_photo["text"].strip(),
                        self.app.get_profile_photo(),
                        color=Goban.BLACK,
                        level=-1,
                    ),
                    Player(
                        random_username(),
                        self.app._get_default_profile_photo(),
                        color=Goban.WHITE,
                        level=-1,
                    ),
                    game,
                )
            )

        if not self.multiplayer.get():
            game = GoGame(self.board_size.get())
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(
                    parent,
                    app,
                    self.board_size.get(),
                    Martin(game, Goban.BLACK),
                    Player(
                        self.app.account_profile_photo["text"].strip(),
                        self.app.get_profile_photo(),
                        color=Goban.WHITE,
                        level=-1,
                    ),
                    game,
                )
            )

    def _return_to_lobby(self) -> None:
        """
        Return to the lobby frame.
        """
        from gui.frames.lobby_frame import LobbyFrame

        self.app.show_frame(LobbyFrame)
