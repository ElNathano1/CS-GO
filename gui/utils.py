"""
Utility functions for the GUI.

This module provides helper functions for common operations like
saving and loading preferences to/from JSON files.
"""

import json
from pathlib import Path

from config import LOCAL_USERNAMES


def save_preferences(preferences: dict, filename: str | Path) -> None:
    """
    Save a dictionary of preferences to a JSON file.

    Args:
        preferences (dict): Dictionary containing preference key-value pairs
        filename (str | Path): Path to the JSON file to save to

    Raises:
        IOError: If the file cannot be written
        TypeError: If preferences is not a dictionary
    """
    if not isinstance(preferences, dict):
        raise TypeError("Preferences must be a dictionary")

    filepath = Path(filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(preferences, f, indent=2, ensure_ascii=False)


def load_preferences(filename: str | Path) -> dict:
    """
    Load preferences from a JSON file.

    Args:
        filename (str | Path): Path to the JSON file to load from

    Returns:
        dict: Dictionary containing the loaded preferences

    Raises:
        FileNotFoundError: If the file does not exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    filepath = Path(filename)

    if not filepath.exists():
        raise FileNotFoundError(f"Preferences file not found: {filepath}")

    with open(filepath, "r", encoding="utf-8") as f:
        preferences = json.load(f)

    return preferences


def random_username() -> str:
    """
    Generate a random username.

    Returns:
        str: A randomly generated username
    """
    import random
    import string

    adjectives = random.choice(LOCAL_USERNAMES["adjectives"])
    noun, genre = random.choice(LOCAL_USERNAMES["nouns"])

    return f"{noun} {adjectives[genre]}"


# Legacy function names for backwards compatibility
save_dictionnary = save_preferences
load_dictionnary = load_preferences
