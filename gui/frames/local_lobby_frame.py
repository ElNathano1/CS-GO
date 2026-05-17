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
from player.ai import KatagoAI, Martin, Amina, Leo, Sofia, Ravi, Ada, Player

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
        self._loading = self.app.show_loading("Chargement du lobby local...")

        self.board_size = tk.IntVar(value=19)
        self.multiplayer = tk.BooleanVar(value=True)
        self.ai = None
        self.after(0, self._build_step_1)

    def _build_step_1(self) -> None:
        # Title
        title = ttk.Label(self, text="Game Lobby", style="Title.TLabel")
        title.pack(pady=40)

        self.container = ttk.Frame(self)
        self.container.pack()

        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_columnconfigure(1, weight=1)

        # Ensure account panel is visible on this frame
        if hasattr(self.app, "account_panel") and self.app.account_panel:
            self.app.account_panel.lift()

        self.after(0, self._build_step_2)

    def _build_step_2(self) -> None:
        # Number of players selection frame
        main_player_frame = self.app.Frame(self.container, bg="black", bd=1)
        main_player_frame.grid(row=0, column=0, pady=20, padx=5, sticky="nes")
        player_frame = self.app.Frame(main_player_frame)
        player_frame.pack(pady=3, padx=3, fill=tk.BOTH, expand=True)

        # Buttons for number of players
        self.multiplayer_button = self.app.Button(
            player_frame.content_frame,
            overlay_path=self.app.multiplayer_icon_path,
            hover_overlay_path=self.app.hovered_multiplayer_icon_path,
            text="Deux joueurs",
            command=lambda: self._select_player("multiplayer"),
            takefocus=False,
        )
        self.multiplayer_button.pack(padx=30, pady=(20, 10), fill=tk.BOTH)
        self.singleplayer_button = self.app.Button(
            player_frame.content_frame,
            overlay_path=self.app.singleplayer_icon_path,
            hover_overlay_path=self.app.hovered_singleplayer_icon_path,
            text="Un joueur",
            command=lambda: self._select_player("singleplayer"),
            takefocus=False,
        )
        self.singleplayer_button.pack(padx=30, pady=10, fill=tk.BOTH)
        self._select_player("multiplayer")

        # Button to select AI difficulty (only visible in singleplayer mode)
        self.ai_button = self.app.Button(
            player_frame.content_frame,
            overlay_path=self.app.singleplayer_icon_path,
            hover_overlay_path=self.app.hovered_singleplayer_icon_path,
            text="Un joueur",
            command=lambda: self._select_player("singleplayer"),
            takefocus=False,
        )

        self.after(0, self._build_step_3)

    def _build_step_3(self) -> None:
        # Board size selection frame
        main_size_frame = self.app.Frame(self.container, bg="black", bd=1)
        main_size_frame.grid(row=0, column=1, pady=20, padx=5, sticky="nws")
        size_frame = self.app.Frame(main_size_frame)
        size_frame.pack(pady=3, padx=3, fill=tk.BOTH, expand=True)

        # Buttons for different board sizes
        self.nine_button = self.app.Button(
            size_frame.content_frame,
            overlay_path=self.app.untoggle_icon_path,
            hover_overlay_path=self.app.hovered_untoggle_icon_path,
            text="9 × 9  ",
            width=150,
            command=lambda: self._select_size(9),
            takefocus=False,
        )
        self.nine_button.pack(padx=30, pady=(20, 10), fill=tk.X)
        self.thirteen_button = self.app.Button(
            size_frame.content_frame,
            overlay_path=self.app.untoggle_icon_path,
            hover_overlay_path=self.app.hovered_untoggle_icon_path,
            text="13 × 13",
            width=150,
            command=lambda: self._select_size(13),
            takefocus=False,
        )
        self.thirteen_button.pack(padx=30, pady=10, fill=tk.X)
        self.nineteen_button = self.app.Button(
            size_frame.content_frame,
            overlay_path=self.app.toggle_icon_path,
            hover_overlay_path=self.app.hovered_toggle_icon_path,
            text="19 × 19",
            width=150,
            command=lambda: self._select_size(19),
            takefocus=False,
        )
        self.nineteen_button.pack(padx=30, pady=(10, 20), fill=tk.X)

        self.after(0, self._build_step_4)

    def _build_step_4(self) -> None:
        self.app.Button(
            self,
            text="Continuer la partie",
            command=lambda: self._resume_game(game=self.app.current_game),  # type: ignore
            state=tk.DISABLED if self.app.current_game is None else tk.NORMAL,
            takefocus=False,
        ).pack(pady=(20, 10))

        # Start Game button
        self.app.Button(
            self,
            text="Démarrer la partie",
            command=self._start_game,
            takefocus=False,
        ).pack(pady=10)

        # Return to Lobby button
        self.app.Button(
            self,
            text="Retour au Lobby",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._return_to_lobby,
            takefocus=False,
        ).pack(pady=(10, 20))

        self.app.hide_loading(self._loading)

    def _select_player(self, mode: str) -> None:
        """
        Emulates the behavior of radiobuttons for player mode selection.

        Args:
            mode (str): The game mode to select ("singleplayer" or "multiplayer").
        """

        if mode == "singleplayer":
            self.multiplayer.set(False)
            self.multiplayer_button.configure(
                overlay_path=self.app.multiplayer_icon_path,
                hover_overlay_path=self.app.hovered_multiplayer_icon_path,
            )
            self.singleplayer_button.configure(
                overlay_path=self.app.hovered_singleplayer_icon_path,
                hover_overlay_path=self.app.hovered_singleplayer_icon_path,
            )
        elif mode == "multiplayer":
            self.multiplayer.set(True)
            self.multiplayer_button.configure(
                overlay_path=self.app.hovered_multiplayer_icon_path,
                hover_overlay_path=self.app.hovered_multiplayer_icon_path,
            )
            self.singleplayer_button.configure(
                overlay_path=self.app.singleplayer_icon_path,
                hover_overlay_path=self.app.hovered_singleplayer_icon_path,
            )

    def _select_size(self, size: int) -> None:
        """
        Emulates the behavior of radiobuttons

        Args:
            size (int): The size of the board to select (9, 13, or 19).
        """

        self.board_size.set(size)

        match size:
            case 9:
                self.nine_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )
                self.thirteen_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.nineteen_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
            case 13:
                self.nine_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.thirteen_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )
                self.nineteen_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
            case 19:
                self.nine_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.thirteen_button.configure(
                    overlay_path=self.app.untoggle_icon_path,
                    hover_overlay_path=self.app.hovered_untoggle_icon_path,
                )
                self.nineteen_button.configure(
                    overlay_path=self.app.toggle_icon_path,
                    hover_overlay_path=self.app.hovered_toggle_icon_path,
                )

    def _resume_game(self, game: "GoGame") -> None:
        """
        Resume an existing game.

        Args:
            game (GoGame): The game instance to resume.
        """

        board_size = game.goban.size
        if not game.singleplayer:
            display_name = self.app._get_display_name()
            self.app.show_frame(
                lambda parent, app: GameFrame(
                    parent,
                    app,
                    board_size,
                    Player(
                        display_name,
                        self.app.get_profile_photo(display_name.split(" ")[0]),
                        color=Goban.BLACK,
                        level=-3000,
                    ),
                    Player(
                        random_username(),
                        self.app._get_default_profile_photo(),
                        color=Goban.WHITE,
                        level=-3000,
                    ),
                    game,
                ),
                show_social_panel=False,
            )
        else:
            print("Resuming singleplayer game...")
            display_name = self.app._get_display_name()
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(
                    parent,
                    app,
                    board_size,
                    KatagoAI("Test", game, Goban.BLACK, -1750),
                    Player(
                        display_name,
                        self.app.get_profile_photo(display_name.split(" ")[0]),
                        color=Goban.WHITE,
                        level=-3000,
                    ),
                    game,
                ),
                show_social_panel=False,
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
            display_name = self.app._get_display_name()
            game = GoGame(self.board_size.get())
            self.app.show_frame(
                lambda parent, app: GameFrame(
                    parent,
                    app,
                    self.board_size.get(),
                    Player(
                        display_name,
                        self.app.get_profile_photo(display_name.split(" ")[0]),
                        color=Goban.BLACK,
                        level=-3000,
                    ),
                    Player(
                        random_username(),
                        self.app._get_default_profile_photo(),
                        color=Goban.WHITE,
                        level=-3000,
                    ),
                    game,
                ),
                show_social_panel=False,
            )

        if not self.multiplayer.get():
            display_name = self.app._get_display_name()
            game = GoGame(self.board_size.get())
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(
                    parent,
                    app,
                    self.board_size.get(),
                    KatagoAI("Test", game, Goban.BLACK, -1750),
                    Player(
                        display_name,
                        self.app.get_profile_photo(display_name.split(" ")[0]),
                        color=Goban.WHITE,
                        level=-3000,
                    ),
                    game,
                ),
                show_social_panel=False,
            )

    def _return_to_lobby(self) -> None:
        """
        Return to the lobby frame.
        """
        from gui.frames.lobby_frame import LobbyFrame

        self.app.show_frame_with_loading(LobbyFrame, "Chargement du lobby...")
