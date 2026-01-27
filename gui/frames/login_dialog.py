"""
Login / register dialog for user authentication.

This module provides the dialog interface for users to log in or register.
"""

from typing import TYPE_CHECKING
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.messagebox as messagebox

import requests
import asyncio
import httpx
import threading

if TYPE_CHECKING:
    from gui.app import App
from gui.widgets import TopLevelWindow

# API base URL
BASE_URL = "https://cs-go-production.up.railway.app"


class LoginFrame(ttk.Frame):
    """
    Dialog toplevel for login and register actions.

    Allows users to log in or create a new account.
    """

    def __init__(self, parent: tk.Widget, app: "App"):
        """
        Initializes the login dialog.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """

        super().__init__(parent)
        self.app = app

        # Title
        title = ttk.Label(
            self, text="Connexion", font=("Arial", 24, "bold"), background="#f0f0f0"
        )
        title.pack(pady=(40, 20))

        # Login frame
        login_frame = ttk.LabelFrame(self, padding=20)
        login_frame.pack(pady=20)

        # Username entry
        self.username_var = tk.StringVar()
        ttk.Label(
            login_frame,
            text="Nom d'utilisateur",
        ).pack(pady=(10, 5), fill=tk.X)
        self.username_entry = ttk.Entry(
            login_frame,
            textvariable=self.username_var,
            takefocus=False,
        )
        self.username_entry.pack(pady=(0, 10), fill=tk.X)

        # Password entry
        self.password_var = tk.StringVar()
        ttk.Label(
            login_frame,
            text="Mot de passe",
        ).pack(pady=(10, 5), fill=tk.X)
        self.password_entry = ttk.Entry(
            login_frame,
            textvariable=self.password_var,
            takefocus=False,
            show="*",
        )
        self.password_entry.pack(pady=(0, 10), fill=tk.X)

        # Login button
        self.login_button = self.app.Button(
            login_frame,
            text="Se connecter",
            command=self._login,
            takefocus=False,
        )
        self.login_button.pack(pady=10)

        # Error label
        self.error_label = ttk.Label(
            self,
            text="",
            foreground="red",
        )
        self.error_label.pack(pady=(0, 10), fill=tk.X)

        # Register button
        self.register_button = self.app.Button(
            self,
            text="S'inscrire",
            command=self._on_register,
            takefocus=False,
        )
        self.register_button.pack(pady=10)

    def _login(self) -> None:
        """
        Handle user login action.
        """

        username = self.username_var.get()
        password = self.password_var.get()

        self.login_button.set_disabled(True)

        thread = threading.Thread(
            target=lambda: asyncio.run(self._do_login(username, password))
        )
        thread.start()

    async def _do_login(self, username: str, password: str) -> None:
        """
        Authenticate a user with the backend API using async httpx.

        Args:
            username (str): The username of the user.
            password (str): The password of the user.
        """

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.post(
                    f"{BASE_URL}/auth/login",
                    params={"username": username, "password": password},
                )

                if response.status_code == 200:
                    data = response.json()
                    self.app.after(0, self._on_login_success, data)
                else:
                    self.app.after(0, self._on_login_error, "Identifiants incorrects")

        except Exception as e:
            self.app.after(0, self._on_login_error, str(e))

    def _on_login_success(self, data: dict) -> None:
        """Appelé dans le thread principal après succès."""
        self.app.token = data["token"]
        self.app.username = data["username"]

        # Import here to avoid circular dependency at module load time
        from gui.frames import LobbyFrame

        # Close dialog and show lobby
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

        self.app.preferences["auth_token"] = self.app.token
        self.app.show_frame(LobbyFrame)

    def _on_login_error(self, error: str) -> None:
        """Appelé dans le thread principal après erreur."""
        self.login_button.set_disabled(False)
        self._show_error(error)

        # Re-raise dialog above parent after messagebox closes
        dialog = self.winfo_toplevel()
        if isinstance(dialog, tk.Toplevel):
            dialog.lift()
            dialog.focus_set()

        # Reset entries and button for retry
        self.password_var.set("")
        self.username_var.set("")
        self.login_button.set_disabled(False)

    def _show_error(self, message: str) -> None:
        """
        Display an error message to the user.

        Args:
            message (str): The error message to display.
        """

        self.error_label.config(text=message)

    def _on_register(self) -> None:
        """
        Handle user registration action.
        """

        # Implementation of registration logic goes here
        pass
