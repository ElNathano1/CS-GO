import json


def save_dictionnary(preferences: dict, filename: str) -> None:
    """
    Save a dictionary of preferences to a JSON file.

    Args:
        preferences (dict): Preferences to save
        filename (str): Name of the file to save to
    """
    with open(filename, "w") as f:
        json.dump(preferences, f, indent=2)


def load_dictionnary(filename: str) -> dict:
    """
    Load preferences from a JSON file.

    Args:
        filename (str): Name of the file to load

    Returns:
        dict: Loaded preferences
    """
    with open(filename, "r") as f:
        preferences = json.load(f)
    return preferences
