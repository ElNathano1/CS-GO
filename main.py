from gui.gui_classes import *
from gui.save_preferences import save_dictionnary, load_dictionnary

import os
import sys
from pathlib import Path

# Add parent directory to path to import goban
sys.path.insert(0, str(Path(__file__).parent.parent))


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
            "fullscreen": True,
        }
        save_dictionnary(preferences, "preferences.prefs")
        return preferences


def load_current_game() -> GoGame | None:
    """
    Load a saved game if it exists.

    Returns:
        GoGame | None: Loaded game or None if no saved game exists
    """

    from game.save_games import load_game

    if os.path.exists("saves/autosave.csgogame"):
        return load_game("saves/autosave.csgogame")
    return None


if __name__ == "__main__":
    preferences = load_preferences()
    app = App(preferences=preferences, current_game=load_current_game())
    app.mainloop()
