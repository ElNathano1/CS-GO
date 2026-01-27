from gui.app import *
from gui.utils import (
    save_preferences as save_dictionnary,
    load_preferences as load_dictionnary,
)
from game.core import GoGame

import os
import sys
from pathlib import Path

import requests

# Add parent directory to path to import goban
sys.path.insert(0, str(Path(__file__).parent.parent))


BASE_URL = "https://cs-go-production.up.railway.app"


def load_preferences() -> dict:
    """
    Load user preferences from a configuration file or database.
    For demonstration purposes, we return a hardcoded dictionary.
    """

    if os.path.exists("preferences.prefs"):
        return load_dictionnary("preferences.prefs")

    else:
        preferences = {
            "sound_enabled": True,
            "master_volume": 100,
            "music_volume": 100,
            "effects_volume": 100,
            "stay_logged_in": True,
            "auth_token": None,
        }
        save_dictionnary(preferences, "preferences.prefs")
        return preferences


def load_current_game() -> GoGame | None:
    """
    Load a saved game if it exists.

    Returns:
        GoGame | None: Loaded game or None if no saved game exists
    """

    from game.utils import load_game

    if os.path.exists("saves/autosave.csgogame"):
        return load_game("saves/autosave.csgogame")
    return None


if __name__ == "__main__":
    preferences = load_preferences()
    app = App(preferences=preferences, current_game=load_current_game())
    app.mainloop()
