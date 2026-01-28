"""
GUI frames package for the Go game application.

This package contains all the frame classes that make up the different
screens and views of the application.

Available frames:
    - LobbyFrame: Main menu/lobby screen
    - SettingsFrame: Game settings and preferences
    - GameLobbyFrame: Pre-game setup and player selection
    - GameFrame: Main game board and play interface
    - SingleplayerGameFrame: Game frame specialized for single-player mode
"""

from .lobby_frame import LobbyFrame
from .settings_frame import SettingsFrame
from .local_lobby_frame import LocalLobbyFrame
from .game_frame import GameFrame, SingleplayerGameFrame

__all__ = [
    "LobbyFrame",
    "SettingsFrame",
    "LocalLobbyFrame",
    "GameFrame",
    "SingleplayerGameFrame",
]
