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
from gui.widgets import TopLevelWindow, TexturedButton

# API base URL
from config import BASE_URL


class AISelectorFrame(ttk.Frame):
    """
    Dialog toplevel for AI selection actions.

    Allows users to select an AI for the game.
    """

    def __init__(
        self, parent: tk.Widget, app: "App", ai_selector_button: TexturedButton
    ):
        """
        Initializes the AI selector dialog.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """

        super().__init__(parent)
        self.app = app
        self.ai_selector_button = ai_selector_button
        self._login_timeout_handle = None
        loading = self.app.show_loading("Chargement...")

        # Create canvas and scrollbar for scrollable content
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(30, 20))

        canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        scrollable_window = canvas.create_window(
            (0, 0), window=scrollable_frame, anchor="n"
        )
        canvas.configure(yscrollcommand=scrollbar.set)

        def _on_canvas_configure(event):
            canvas.itemconfig(scrollable_window, width=event.width)
            canvas.coords(scrollable_window, event.width / 2, 0)

        canvas.bind("<Configure>", _on_canvas_configure)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                # Canvas has been destroyed, binding will be cleaned up
                pass

        self._mousewheel_binding = self.bind_all("<MouseWheel>", _on_mousewheel)

        # AI selection frame
        main_ai_frame = self.app.Frame(scrollable_frame, bg="black", bd=1)
        main_ai_frame.pack(pady=20, fill=tk.X, padx=20)
        ai_frame = self.app.Frame(main_ai_frame)
        ai_frame.pack(pady=3, padx=3, fill=tk.X)

        # Martin
        self.app.Label(
            ai_frame,
            text="Débutant (coups aléatoires)",
        ).pack(pady=(20, 5), padx=20)
        self.martin_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.martin_icon_path,
            hover_overlay_path=self.app.hovered_martin_icon_path,
            text="Martin",
            command=lambda: self._select_ai("Martin"),
            takefocus=False,
        )
        self.martin_button.pack(pady=(5, 10), padx=20)

        # Amina
        self.app.Label(
            ai_frame,
            text="Novice (-2950 FFG)",
        ).pack(pady=(10, 5), padx=20)
        self.amina_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.amina_icon_path,
            hover_overlay_path=self.app.hovered_amina_icon_path,
            text="Amina",
            command=lambda: self._select_ai("Amina"),
            takefocus=False,
        )
        self.amina_button.pack(pady=(5, 10), padx=20)

        # Léo
        self.app.Label(
            ai_frame,
            text="Intermédiaire (-2000 FFG)",
        ).pack(pady=(10, 5), padx=20)
        self.leo_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.leo_icon_path,
            hover_overlay_path=self.app.hovered_leo_icon_path,
            text="Léo",
            command=lambda: self._select_ai("Léo"),
            takefocus=False,
        )
        self.leo_button.pack(pady=(5, 10), padx=20)

        # Sofia
        self.app.Label(
            ai_frame,
            text="Confirmée (-1050 FFG)",
        ).pack(pady=(10, 5), padx=20)
        self.sofia_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.sofia_icon_path,
            hover_overlay_path=self.app.hovered_sofia_icon_path,
            text="Sofia",
            command=lambda: self._select_ai("Sofia"),
            takefocus=False,
        )
        self.sofia_button.pack(pady=(5, 10), padx=20)

        # Ravi
        self.app.Label(
            ai_frame,
            text="Expert (-100 FFG)",
        ).pack(pady=(10, 5), padx=20)
        self.ravi_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.ravi_icon_path,
            hover_overlay_path=self.app.hovered_ravi_icon_path,
            text="Ravi",
            command=lambda: self._select_ai("Ravi"),
            takefocus=False,
        )
        self.ravi_button.pack(pady=(5, 10), padx=20)

        # Ada
        self.app.Label(
            ai_frame,
            text="Grande Maître (850 FFG)",
        ).pack(pady=(10, 5), padx=20)
        self.ada_button = self.app.Button(
            ai_frame,
            overlay_path=self.app.ada_icon_path,
            hover_overlay_path=self.app.hovered_ada_icon_path,
            text="Ada",
            command=lambda: self._select_ai("Ada"),
            takefocus=False,
        )
        self.ada_button.pack(pady=(5, 10), padx=20)

        # Return button
        self.return_button = self.app.Button(
            self,
            text="Retour",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_return,
            takefocus=False,
        )
        self.return_button.pack(pady=(10, 20), padx=20, side=tk.BOTTOM)

        self.app.hide_loading(loading)

    def _select_ai(self, ai_name: str) -> None:
        """
        Handle AI selection action.

        Args:
            ai_name (str): The name of the selected AI.
        """

        # Set selected AI in the main app
        self.ai_selector_button.configure(
            text=ai_name,
            overlay_path=getattr(
                self.app, f"hovered_{ai_name.lower().replace('é', 'e')}_icon_path"
            ),
            hover_overlay_path=getattr(
                self.app, f"hovered_{ai_name.lower().replace('é', 'e')}_icon_path"
            ),
        )

        # Clean up mousewheel binding
        if self._mousewheel_binding:
            self.unbind_all("<MouseWheel>")

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()


class RegisterFrame(ttk.Frame):
    """
    Dialog toplevel for login and register actions.

    Allows users to log in or create a new account.
    """

    def __init__(self, parent: tk.Widget, app: "App"):
        """
        Initializes the register dialog.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """

        super().__init__(parent)
        self.app = app
        loading = self.app.show_loading("Chargement...")
        self._mousewheel_binding = None  # Store binding ID for cleanup

        # Title
        title = ttk.Label(self, text="Inscription", style="Title.TLabel")
        title.pack(pady=(20, 40))

        # Create canvas and scrollbar for scrollable content
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 20))

        canvas = tk.Canvas(canvas_frame, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                # Canvas has been destroyed, binding will be cleaned up
                pass

        self._mousewheel_binding = self.bind_all("<MouseWheel>", _on_mousewheel)

        # Register frame
        main_register_frame = self.app.Frame(scrollable_frame, bg="black", bd=1)
        main_register_frame.pack(pady=20, fill=tk.X, padx=20)
        register_frame = self.app.Frame(main_register_frame)
        register_frame.pack(pady=3, padx=3, fill=tk.X)

        # Username entry
        self.username_var = tk.StringVar()
        self.app.Label(
            register_frame,
            text="Nom d'utilisateur",
        ).pack(pady=(20, 5), padx=20)
        self.username_entry = ttk.Entry(
            register_frame,
            textvariable=self.username_var,
            font=("Skranji", 14),
            takefocus=True,
        )
        self.username_entry.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Name entry
        self.name_var = tk.StringVar()
        self.app.Label(
            register_frame,
            text="Nom d'affichage",
        ).pack(pady=(20, 5), padx=20)
        self.name_entry = ttk.Entry(
            register_frame,
            textvariable=self.name_var,
            font=("Skranji", 14),
            takefocus=True,
        )
        self.name_entry.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Password entry
        self.password_var = tk.StringVar()
        self.app.Label(
            register_frame,
            text="Mot de passe",
        ).pack(pady=(10, 5), padx=20)
        self.password_entry = ttk.Entry(
            register_frame,
            textvariable=self.password_var,
            font=("Skranji", 14),
            takefocus=True,
            show="*",
        )
        self.password_entry.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Confirm password entry
        self.confirm_password_var = tk.StringVar()
        self.app.Label(
            register_frame,
            text="Confirmer le mot de passe",
        ).pack(pady=(10, 5), padx=20)
        self.confirm_password_entry = ttk.Entry(
            register_frame,
            textvariable=self.confirm_password_var,
            font=("Skranji", 14),
            takefocus=True,
            show="*",
        )
        self.confirm_password_entry.pack(pady=(0, 10), padx=20, fill=tk.X)

        # Register button
        self.register_button = self.app.Button(
            register_frame,
            text="S'inscrire",
            overlay_path=self.app.register_icon_path,
            hover_overlay_path=self.app.hovered_register_icon_path,
            command=self._handle_register,
            takefocus=False,
        )
        self.register_button.pack(pady=(10, 20), padx=20)

        # Bottom section (outside scrollable area)
        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=20, pady=(0, 20))

        # Error label
        self.error_label = ttk.Label(
            bottom_frame,
            text="",
            style="Error.TLabel",
        )
        self.error_label.pack(pady=(0, 10), fill=tk.X)

        # Login button
        self.login_button = ttk.Button(
            bottom_frame,
            text="Déjà un compte ? Se connecter",
            command=self._on_login,
            takefocus=False,
            cursor="hand2",
            padding=0,
        )
        self.login_button.pack(pady=10)

        # Return button
        self.return_button = self.app.Button(
            bottom_frame,
            text="Retour",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_return,
            takefocus=False,
        )
        self.return_button.pack(pady=10, padx=20, side=tk.BOTTOM)

        # Bind Enter key to register
        self.bind("<Return>", lambda event: self._handle_register())
        self.username_entry.bind("<Return>", lambda event: self._handle_register())
        self.name_entry.bind("<Return>", lambda event: self._handle_register())
        self.password_entry.bind("<Return>", lambda event: self._handle_register())
        self.confirm_password_entry.bind(
            "<Return>", lambda event: self._handle_register()
        )

        # Bind Tab key to navigate between entries
        self.username_entry.bind(
            "<Tab>", lambda e: (self.name_entry.focus_set(), "break")[1]
        )
        self.name_entry.bind(
            "<Tab>", lambda e: (self.password_entry.focus_set(), "break")[1]
        )
        self.password_entry.bind(
            "<Tab>", lambda e: (self.confirm_password_entry.focus_set(), "break")[1]
        )
        self.confirm_password_entry.bind(
            "<Tab>", lambda e: (self.username_entry.focus_set(), "break")[1]
        )

        self.app.hide_loading(loading)

    def _handle_register(self) -> None:
        """
        Handle user registration action.
        """

        username = self.username_var.get()
        name = self.name_var.get()
        password = self.password_var.get()
        confirm_password = self.confirm_password_var.get()

        # Check if all fields are filled
        if username == "" or name == "" or password == "" or confirm_password == "":
            if username == "":
                self.username_entry.configure(style="Error.TEntry")
            if name == "":
                self.name_entry.configure(style="Error.TEntry")
            if password == "":
                self.password_entry.configure(style="Error.TEntry")
            if confirm_password == "":
                self.confirm_password_entry.configure(style="Error.TEntry")
            self._show_error("Veuillez remplir tous les champs.")
            return

        # Check if username is only alphanumeric
        if not username.isalnum() or username != username.lower():
            self.username_entry.configure(style="Error.TEntry")
            self._show_error("Le nom d'utilisateur doit être alphanumérique.")
            return

        # Check if username is already taken
        try:
            response = requests.get(
                f"{BASE_URL}/users/{username}",
                timeout=5,
            )
            if response.status_code == 200:
                self.username_entry.configure(style="Error.TEntry")
                self._show_error("Le nom d'utilisateur est déjà pris.")
                return

        except Exception as e:
            self._show_error(
                f"Erreur lors de la vérification du nom d'utilisateur : {e}"
            )
            return

        # Check if passwords match
        if password != confirm_password:
            self.password_entry.configure(style="Error.TEntry")
            self.confirm_password_entry.configure(style="Error.TEntry")
            self._show_error("Les mots de passe ne correspondent pas.")
            return

        # Check is password length is at least 8 characters, and contains at least:
        # - One number,
        # - One lowercase letter,
        # - One uppercase letter,
        # - One special character
        if (
            len(password) < 8
            or not any(c.isdigit() for c in password)
            or not any(c.islower() for c in password)
            or not any(c.isupper() for c in password)
            or not any(c in "!@#$%^&*()-_=+[{]}\\|;:'\",<.>/?`~" for c in password)
        ):
            self.password_entry.configure(style="Error.TEntry")
            self.confirm_password_entry.configure(style="Error.TEntry")
            self._show_error(
                "Le mot de passe doit contenir au moins 8 caractères, "
                "dont une majuscule, une minuscule, un chiffre et un caractère spécial."
            )
            return

        self.username_entry.configure(style="TEntry")
        self.password_entry.configure(style="TEntry")
        self.confirm_password_entry.configure(style="TEntry")
        self.register_button.config(state=tk.DISABLED)

        thread = threading.Thread(
            target=lambda: asyncio.run(self._do_register(username, name, password))
        )
        thread.start()

    async def _do_register(self, username: str, name: str, password: str) -> None:
        """
        Authenticate a user with the backend API using async httpx.

        Args:
            username (str): The username of the user.
            name (str): The name of the user.
            password (str): The password of the user.
        """

        try:
            async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
                # Create user account
                response = await client.post(
                    f"{BASE_URL}/users/",
                    json={
                        "username": username,
                        "name": name,
                        "password": password,
                    },
                )

                if response.status_code != 200:
                    self.app.after(
                        0,
                        self._on_register_error,
                        "Erreur lors de la création du compte.",
                    )
                    return

                # Login with new account
                response = await client.post(
                    f"{BASE_URL}/auth/login",
                    json={"username": username, "password": password},
                )

                if response.status_code != 200:
                    response = await client.post(
                        f"{BASE_URL}/auth/login",
                        params={"username": username, "password": password},
                    )

                if response.status_code == 200:
                    data = response.json()
                    self.app.after(0, self._on_register_success, data)
                else:
                    self.app.after(
                        0, self._on_register_error, "Identifiants incorrects"
                    )

        except Exception as e:
            self.app.after(0, self._on_register_error, str(e))

    def _on_register_success(self, data: dict) -> None:
        """Appelé dans le thread principal après succès."""
        self.app.token = data["token"]
        self.app.username = data["username"]

        # Fetch full user data to get the name
        self.app._fetch_user_data()

        # Mark user as connected in database
        self.app._mark_user_connected()

        # Notify that username and profile photo have been updated
        self.app.notify_username_updated()
        self.app.notify_profile_photo_updated()

        # Import here to avoid circular dependency at module load time
        from gui.frames import LobbyFrame

        # Close dialog and show lobby
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

        self.app.preferences["auth_token"] = self.app.token
        self.app.show_frame_with_loading(LobbyFrame, "Chargement du lobby...")

    def _on_register_error(self, error: str) -> None:
        """Appelé dans le thread principal après erreur."""
        self.register_button.config(state=tk.NORMAL)
        self.username_entry.configure(style="Error.TEntry")
        self.name_entry.configure(style="Error.TEntry")
        self.password_entry.configure(style="Error.TEntry")
        self.confirm_password_entry.configure(style="Error.TEntry")
        self._show_error(error)

        # Re-raise dialog above parent after messagebox closes
        dialog = self.winfo_toplevel()
        if isinstance(dialog, tk.Toplevel):
            dialog.lift()
            dialog.focus_set()

        # Reset entries and button for retry
        self.password_var.set("")
        self.username_var.set("")
        self.register_button.config(state=tk.NORMAL)

    def _show_error(self, message: str) -> None:
        """
        Display an error message to the user.

        Args:
            message (str): The error message to display.
        """

        self.error_label.config(text=message)

    def _on_login(self) -> None:
        """
        Switch to login frame.
        """
        # Get the parent container (dialog body_frame)
        parent = self.master

        # Destroy current frame
        self.destroy()

        # Create and pack the LoginFrame
        login_frame = LoginFrame(parent, self.app)  # type: ignore
        login_frame.pack(fill=tk.BOTH, expand=True)

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """
        # Clean up mousewheel binding
        if self._mousewheel_binding:
            self.unbind_all("<MouseWheel>")

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()
