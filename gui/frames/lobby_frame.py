"""
Lobby frame for the Go game application.

This module provides the main lobby interface where users can start new games,
access settings, view rules, and resume previous games.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

if TYPE_CHECKING:
    from gui.app import App
    from game.core import GoGame


class LobbyFrame(ttk.Frame):
    """
    Frame for initiating a lobby.

    Allows the user to start a new game, consult the game rules and go to parameters.
    """

    def __init__(self, parent: ttk.Frame, app: "App"):
        """
        Initialize the lobby frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """

        super().__init__(parent)

        self.app = app

        # Play background music if sound is not already playing
        if (
            self.app.sound_manager.is_enabled()
            and not self.app.sound_manager.is_playing("background_music")
        ):
            self.app.sound_manager.play_exclusive("background_music")

        # Title
        title = tk.Canvas(
            self,
            width=600,
            height=182,
            relief=tk.FLAT,
            bd=0,
            highlightthickness=0,
            bg="#1e1e1e",
        )
        title.create_image(
            0,
            0,
            image=app.cs_go_banner,
            anchor="nw",
        )
        title.pack(pady=40)

        # Menu frame
        main_menu_frame = self.app.Frame(self, bg="black", bd=1)
        main_menu_frame.pack(pady=20, padx=20)
        menu_frame = self.app.Frame(main_menu_frame)
        menu_frame.pack(pady=3, padx=3)

        # Buttons for menu options
        self.app.Button(
            menu_frame.content_frame,
            text="Continuer la partie",
            command=lambda: self._resume_game(game=self.app.current_game),  # type: ignore
            disabled=True if self.app.current_game is None else False,
            takefocus=False,
        ).pack(pady=(20, 10), fill=tk.X, padx=20)
        self.app.Button(
            menu_frame.content_frame,
            text="Nouvelle partie",
            command=lambda: self._open_game(),
            takefocus=False,
        ).pack(pady=10, fill=tk.X, padx=20)
        self.app.Button(
            menu_frame.content_frame,
            overlay_path=self.app.prefs_icon_path,
            hover_overlay_path=self.app.hovered_prefs_icon_path,
            text="Paramètres",
            command=lambda: self._open_settings(),
            takefocus=False,
        ).pack(pady=10, fill=tk.X, padx=20)
        self.app.Button(
            menu_frame.content_frame,
            overlay_path=self.app.rules_icon_path,
            hover_overlay_path=self.app.hovered_rules_icon_path,
            text="Règles du jeu",
            command=lambda: self._open_rules(),
            takefocus=False,
        ).pack(pady=10, fill=tk.X, padx=20)

        # Return to Desktop button
        self.app.Button(
            menu_frame.content_frame,
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            text="Retour au bureau",
            command=lambda: self.app.return_to_desktop(),
            takefocus=False,
        ).pack(pady=(10, 20), fill=tk.X, padx=20)

    def _open_game(self) -> None:
        """
        Open the game starting window.

        Args:
            game (GoGame, optional): The game instance to resume. Defaults to None.
        """
        from gui.frames.game_lobby_frame import GameLobbyFrame

        self.app.show_frame(lambda parent, app: GameLobbyFrame(parent, app))

    def _resume_game(self, game: "GoGame") -> None:
        """
        Resume an existing game.

        Args:
            game (GoGame): The game instance to resume.
        """
        from gui.frames.game_frame import GameFrame, SingleplayerGameFrame

        board_size = game.goban.size
        if not game.singleplayer:
            self.app.show_frame(
                lambda parent, app: GameFrame(parent, app, board_size, game)
            )
        else:
            self.app.show_frame(
                lambda parent, app: SingleplayerGameFrame(parent, app, board_size, game)
            )

    def _open_settings(self) -> None:
        """
        Open settings window.
        """
        from gui.frames.settings_frame import SettingsFrame

        self.app.show_frame(lambda parent, app: SettingsFrame(parent, app))

    def _open_rules(self) -> None:
        """
        Open game rules window.
        """

        rules_text = (
            "Règles du jeu de Go:\n\n"
            "1. Le jeu se joue sur une grille de 9x9, 13x13 ou 19x19 intersections.\n"
            "2. Deux joueurs (Noir et Blanc) placent alternativement des pierres sur les intersections.\n"
            "3. L'objectif est de contrôler le plus de territoire en encerclant des zones.\n"
            "4. Les pierres entourées sans libertés sont capturées et retirées du plateau.\n"
            "5. Le jeu se termine lorsque les deux joueurs passent consécutivement.\n"
            "6. Le score est calculé en fonction du territoire contrôlé et des pierres capturées.\n\n"
            "Pour plus de détails, consultez les règles officielles du jeu de Go."
        )

        messagebox.showinfo("Règles du jeu", rules_text)
