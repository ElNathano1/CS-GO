"""
Sound management system for the Go game application.

This module provides a centralized sound manager that handles loading,
playing, and controlling game sound effects and music using pygame.mixer.
"""

from pathlib import Path
import pygame


class SoundManager:
    """
    Manager for game sounds and music.

    Handles loading and playing sound effects for various game events.
    Uses pygame.mixer for cross-platform audio support.
    Falls back gracefully if pygame is not available.

    Attributes:
        enabled (bool): Whether sound is currently enabled
        volume (float): Master volume level (0.0 to 1.0)
        sounds (dict): Dictionary mapping event names to pygame.mixer.Sound objects
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize the sound manager.

        Args:
            enabled (bool): Whether to enable sounds (default: True)
        """
        self.enabled = enabled
        self.volume = 0.7
        self.sounds = {}

        if self.enabled:
            try:
                pygame.mixer.init()
                self._load_sounds()
            except Exception as e:
                self.enabled = False

    def _load_sounds(self) -> None:
        """
        Load all sound files from the sounds directory.

        This method attempts to load sound files for various game events.
        If a file is not found, it continues without error to allow
        the game to run even with missing sound files.
        """
        sounds_dir = Path(__file__).parent / "sounds"

        # Define sound files for different game events
        sound_files = {
            "background_music": "background_music.wav",
            "click_effect": "click.wav",
            "game_start_music": "game_start.wav",
            "stone_placed_effect": "stone_place.wav",
            "pass_effect": "pass.wav",
            "game_over_music": "game_over.wav",
            "invalid_move_effect": "invalid.wav",
            "capture_effect": "capture.wav",
            "resign_music": "resign.wav",
        }

        for event_name, filename in sound_files.items():
            sound_path = sounds_dir / filename
            try:
                if sound_path.exists():
                    self.sounds[event_name] = pygame.mixer.Sound(str(sound_path))
                    self.sounds[event_name].set_volume(self.volume)
            except Exception as e:
                pass

    def play(self, event: str) -> None:
        """
        Play a sound effect for a game event.

        Args:
            event (str): The event name (e.g., 'stone_placed', 'pass', 'game_over')
        """
        if not self.enabled or event not in self.sounds:
            return

        try:
            self.sounds[event].play()
        except Exception as e:
            return

    def play_exclusive(self, event: str) -> None:
        """
        Play a sound effect, stopping any currently playing sounds first.

        Args:
            event (str): The event name (e.g., 'stone_placed', 'pass', 'game_over')
        """
        if not self.enabled or event not in self.sounds:
            return

        try:
            pygame.mixer.stop()  # Stop all currently playing sounds
            self.sounds[event].play()
        except Exception as e:
            return

    def stop(self, event: str) -> None:
        """
        Stop a specific sound effect.

        Args:
            event (str): The event name of the sound to stop
        """
        if not self.enabled or event not in self.sounds:
            return

        try:
            self.sounds[event].stop()
        except Exception as e:
            return

    def stop_all(self) -> None:
        """
        Stop all currently playing sounds.
        """
        if not self.enabled or not self.sounds:
            return

        try:
            for sound in self.sounds.values():
                sound.stop()
        except Exception as e:
            return

    def set_volume(self, volume: float) -> None:
        """
        Set the master volume level for all sounds.

        Args:
            volume (float): Volume level between 0.0 (silent) and 1.0 (full volume)
        """
        self.volume = max(0.0, min(1.0, volume))
        for sound in self.sounds.values():
            sound.set_volume(self.volume)

    def toggle(self) -> None:
        """
        Toggle sound on/off.
        """
        self.enabled = not self.enabled

    def is_enabled(self) -> bool:
        """
        Check if sound is currently enabled.

        Returns:
            bool: True if sound is enabled, False otherwise
        """
        return self.enabled

    def is_playing(self, event: str) -> bool:
        """
        Check if a specific sound is currently playing.

        Args:
            event (str): The event name to check

        Returns:
            bool: True if the sound is currently playing, False otherwise
        """
        if not self.enabled or event not in self.sounds:
            return False

        try:
            return self.sounds[event].get_volume() > 0 and pygame.mixer.get_busy()
        except Exception as e:
            return False
