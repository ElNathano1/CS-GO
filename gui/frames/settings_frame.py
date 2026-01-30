"""
Settings frame for the Go game application.

This module provides the settings interface where users can adjust sound preferences,
volume levels, and other application settings.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox

from gui.widgets import TopLevelWindow

if TYPE_CHECKING:
    from gui.app import App


class SettingsFrame(ttk.Frame):
    """
    Frame for application settings.

    Allows the user to adjust sound settings and other preferences.
    """

    def __init__(self, parent: ttk.Frame, app: "App"):
        """
        Initialize the settings frame.

        Args:
            parent (ttk.Frame): The parent frame.
            app (App): The main application instance.
        """

        super().__init__(parent)

        self.app = app
        loading = self.app.show_loading("Chargement des paramètres...")

        # Title
        title = ttk.Label(self, text="Paramètres", style="Title.TLabel")
        title.pack(pady=(20, 40))

        self.container = ttk.Frame(self)
        self.container.pack()

        # Ensure account panel is visible on this frame
        if hasattr(self.app, "account_panel") and self.app.account_panel:
            self.app.account_panel.lift()

        # Sound options frame
        main_option_frame = self.app.Frame(self.container, bg="black", bd=1)
        main_option_frame.pack(pady=20, fill=tk.X)
        option_frame = self.app.Frame(main_option_frame)
        option_frame.pack(pady=3, padx=3, fill=tk.X)

        option_frame.content_frame.grid_columnconfigure(0, weight=0)
        option_frame.content_frame.grid_columnconfigure(1, weight=1)
        option_frame.content_frame.grid_rowconfigure(0, weight=1)
        option_frame.content_frame.grid_rowconfigure(1, weight=1)
        option_frame.content_frame.grid_rowconfigure(2, weight=1)
        option_frame.content_frame.grid_rowconfigure(3, weight=1)

        # Volume controls
        self.master_volume_label = self.app.Label(
            option_frame.content_frame,
            image_path=self.app.sound_icon_path,
            image_size=(32, 32),
        )
        self.master_volume_label.grid(
            row=0, column=0, padx=(30, 10), pady=(20, 10), sticky="w"
        )
        self.master_volume_slider = ttk.Scale(
            option_frame.content_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["master_volume"]),
            takefocus=False,
        )
        self.master_volume_slider.grid(
            row=0, column=1, padx=(10, 30), pady=10, sticky="ew"
        )

        self.music_volume_label = self.app.Label(
            option_frame.content_frame,
            image_path=self.app.music_icon_path,
            image_size=(32, 32),
        )
        self.music_volume_label.grid(
            row=1, column=0, padx=(30, 10), pady=10, sticky="w"
        )
        self.music_volume_slider = ttk.Scale(
            option_frame.content_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["music_volume"]),
            takefocus=False,
        )
        self.music_volume_slider.grid(
            row=1, column=1, padx=(10, 30), pady=10, sticky="ew"
        )

        self.effects_volume_label = self.app.Label(
            option_frame.content_frame,
            image_path=self.app.effects_icon_path,
            image_size=(32, 32),
        )
        self.effects_volume_label.grid(
            row=2, column=0, padx=(30, 10), pady=(10, 20), sticky="w"
        )
        self.effects_volume_slider = ttk.Scale(
            option_frame.content_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            variable=tk.IntVar(value=self.app.preferences["effects_volume"]),
            takefocus=False,
        )
        self.effects_volume_slider.grid(
            row=2, column=1, padx=(10, 30), pady=(10, 20), sticky="ew"
        )

        # Store previous volume values for comparison
        self._old_master_volume = self.app.preferences["master_volume"]
        self._old_music_volume = self.app.preferences["music_volume"]
        self._old_effects_volume = self.app.preferences["effects_volume"]

        self.app.hide_loading(loading)

        # Rules button
        self.app.Button(
            self.container,
            overlay_path=self.app.rules_icon_path,
            hover_overlay_path=self.app.hovered_rules_icon_path,
            text="Règles du jeu",
            command=lambda: self._open_rules(),
            takefocus=False,
        ).pack(pady=(20, 10), padx=20)

        # Return to Lobby button
        self.app.Button(
            self.container,
            text="Retour",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_return,
            takefocus=False,
        ).pack(pady=(20, 20), padx=20)

        # Save settings when sliders or checkbox are changed
        self.master_volume_slider.config(command=lambda e: self._save_settings())
        self.music_volume_slider.config(command=lambda e: self._save_settings())
        self.effects_volume_slider.config(command=lambda e: self._save_settings())

    def _check_variable(self, slider: ttk.Scale) -> None:
        """
        Ensure the slider variable is an integer.
        Only updates icon if the new or old value is 0.

        Args:
            slider (ttk.Scale): The slider to check.
        """
        value = int(float(slider.get()))

        # Get old value for comparison
        if slider == self.master_volume_slider:
            old_value = self._old_master_volume
            label = self.master_volume_label
        elif slider == self.music_volume_slider:
            old_value = self._old_music_volume
            label = self.music_volume_label
        else:
            old_value = self._old_effects_volume
            label = self.effects_volume_label

        # Only run if new or old value is 0
        if value == 0:
            if slider == self.master_volume_slider:
                label.set_image(self.app.no_sound_icon_path)
            elif slider == self.music_volume_slider:
                label.set_image(self.app.no_music_icon_path)
            else:
                label.set_image(self.app.no_effects_icon_path)
        elif old_value == 0:
            # Reset to original icon if not muted
            if slider == self.master_volume_slider:
                label.set_image(self.app.sound_icon_path)
            elif slider == self.music_volume_slider:
                label.set_image(self.app.music_icon_path)
            else:
                label.set_image(self.app.effects_icon_path)

    def _save_settings(self) -> None:
        """
        Save the current settings to the application preferences.
        """

        # Save sound settings
        # self.app.preferences["sound_enabled"] = self.sound_enabled.get()
        self.app.preferences["master_volume"] = self.master_volume_slider.get()
        self.app.preferences["music_volume"] = self.music_volume_slider.get()
        self.app.preferences["effects_volume"] = self.effects_volume_slider.get()

        # Check slider values for icon updates
        self._check_variable(self.master_volume_slider)
        self._check_variable(self.music_volume_slider)
        self._check_variable(self.effects_volume_slider)

        # Update old values for next comparison
        self._old_master_volume = self.app.preferences["master_volume"]
        self._old_music_volume = self.app.preferences["music_volume"]
        self._old_effects_volume = self.app.preferences["effects_volume"]

        # Apply updated preferences
        self.app.apply_preferences()

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

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()
