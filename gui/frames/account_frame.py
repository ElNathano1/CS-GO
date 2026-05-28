"""
Login / register dialog for user authentication.

This module provides the dialog interface for users to log in or register.
"""

from pathlib import Path
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable
from io import BytesIO
import tkinter as tk
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog

import requests
import asyncio
import httpx
import threading
from PIL import Image, ImageTk

if TYPE_CHECKING:
    from gui.app import App
from gui.widgets import TopLevelWindow, TexturedButton, clear_image_cache

# API base URL
from config import BASE_URL, BASE_FOLDER_PATH


class AccountFrame(ttk.Frame):
    """
    Dialog toplevel for managing account.

    Allows users to:
    - Change account details (e.g., name, password, profile_photo).
    - Log out.
    """

    def __init__(self, parent: tk.Widget, app: "App"):
        """
        Initializes the account management dialog.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """

        self.ui = app.ui
        self.S = app.S

        super().__init__(parent)
        self.app = app
        loading = self.app.show_loading("Chargement...")

        # Logout button
        self.logout_button = ttk.Button(
            self,
            image=self.app.hovered_logout_icon,
            command=self._on_logout,
            takefocus=False,
            cursor="hand2",
        )
        self.logout_button.pack(pady=self.S((18, 0)), padx=self.S(20), anchor=tk.NW)

        # Create canvas and scrollbar for scrollable content
        canvas_frame = ttk.Frame(self)
        canvas_frame.pack(
            fill=tk.BOTH, expand=True, padx=self.S(20), pady=self.S((30, 20))
        )

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

        # Account information
        title = ttk.Label(
            scrollable_frame, text="Informations du compte", style="SubTitle.TLabel"
        )
        title.pack(pady=0)

        # Account management frame
        main_account_frame = self.app.Frame(scrollable_frame, bg="black", bd=1)
        main_account_frame.pack(pady=self.S(20), fill=tk.X, padx=self.S(20))
        account_frame = self.app.Frame(main_account_frame)
        account_frame.pack(pady=self.S(3), padx=self.S(3), fill=tk.X)

        self.download_profile_picture()

        # Change profile picture button
        self.change_profile_picture_button = TexturedButton(
            account_frame,
            texture_path=self.profile_picture_path,
            hover_overlay_path=self.app.edit_picture_banner_path,
            overlay_padding=0,
            command=self._on_change_profile_picture,
            width=self.S(240),
            height=self.S(240),
            bd=self.S(2),
            relief=tk.FLAT,
            bg="black",
            takefocus=False,
        )
        self.change_profile_picture_button.pack(pady=self.S((20, 10)), padx=self.S(10))

        # Change name entry
        self.name_var = tk.StringVar(value=self.app.name)
        self.app.Label(
            account_frame,
            text="Changer le nom d'affichage",
        ).pack(pady=self.S((10, 5)), padx=self.S(20))
        self.name_entry = ttk.Entry(
            account_frame,
            textvariable=self.name_var,
            font=("Skranji", 14),
            takefocus=True,
            state=tk.NORMAL if self.app.password else tk.DISABLED,
        )
        self.name_entry.pack(pady=self.S((0, 10)), padx=self.S(20), fill=tk.X)

        # Change password entry
        self.password_var = tk.StringVar(
            value=self.app.password if self.app.password else ""
        )
        self.app.Label(
            account_frame,
            text="Changer le mot de passe",
        ).pack(pady=self.S((10, 5)), padx=self.S(20))
        self.password_entry = ttk.Entry(
            account_frame,
            textvariable=self.password_var,
            takefocus=True,
            font=self.ui.font(("Skranji", 14)),  # type: ignore
            show="*",
            state=tk.NORMAL if self.app.password else tk.DISABLED,
        )
        self.password_entry.pack(pady=self.S((0, 10)), padx=self.S(20), fill=tk.X)

        # Edit account button
        self.edit_account_button = self.app.Button(
            account_frame,
            text="Sauvegarder" if self.app.password else "Éditer le compte",
            overlay_path=(
                self.app.save_icon_path
                if self.app.password
                else self.app.edit_icon_path
            ),
            hover_overlay_path=(
                self.app.hovered_save_icon_path
                if self.app.password
                else self.app.hovered_edit_icon_path
            ),
            command=self._on_edit_account,
            takefocus=False,
            state=(
                tk.DISABLED
                if (
                    self.app.password
                    and self.app.name == self.name_var.get()
                    and self.app.password == self.password_var.get()
                )
                else tk.NORMAL
            ),
        )
        self.edit_account_button.pack(pady=self.S((10, 20)), padx=self.S(20))

        # Account statistics
        title = ttk.Label(
            scrollable_frame, text="Statistiques du compte", style="SubTitle.TLabel"
        )
        title.pack(pady=0)

        # Account statistics frame
        main_statistics_frame = self.app.Frame(scrollable_frame, bg="black", bd=1)
        main_statistics_frame.pack(pady=self.S(20), fill=tk.X, padx=self.S(20))
        statistics_frame = self.app.Frame(main_statistics_frame)
        statistics_frame.pack(pady=3, padx=3, fill=tk.X)
        self.statistics_frame = statistics_frame

        statistics_frame.columnconfigure(0, weight=1)
        statistics_frame.columnconfigure(1, weight=1)
        statistics_frame.rowconfigure(0, weight=1)
        statistics_frame.rowconfigure(1, weight=1)

        self.account_statistics = {}
        thread = threading.Thread(target=self._load_statistics_worker, daemon=True)
        thread.start()

        # Number of games played
        self.app.Label(
            statistics_frame,
            text="Nombre de parties jouées",
        ).grid(row=0, column=0, pady=self.S(10), padx=self.S(20), sticky="nw")
        self.games_played_label = self.app.Label(
            statistics_frame,
            text=self.account_statistics.get("games_played", "0"),
        )
        self.games_played_label.grid(
            row=0, column=1, pady=self.S(10), padx=self.S((0, 20)), sticky="ne"
        )

        # View of the 3 last games played with the result and the opponent's name
        self.draw_recent_games(statistics_frame)

        # Number of wins
        self.app.Label(
            statistics_frame,
            text="Nombre de victoires",
        ).grid(
            row=1, column=0, pady=self.S((10, 20)), padx=self.S((20, 0)), sticky="nw"
        )
        self.games_won_label = self.app.Label(
            statistics_frame,
            text=self.account_statistics.get("games_won", "0"),
        )
        self.games_won_label.grid(
            row=1, column=1, pady=self.S((10, 20)), padx=self.S((0, 20)), sticky="ne"
        )

        # Return button
        self.return_button = self.app.Button(
            self,
            text="Retour",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_return,
            takefocus=False,
        )
        self.return_button.pack(pady=self.S((0, 20)), padx=self.S((20, 0)), anchor=tk.S)

        # Bind Enter key to login
        self.bind("<Return>", lambda event: self._on_edit_account())
        self.name_entry.bind("<Return>", lambda event: self._on_edit_account())
        self.password_entry.bind("<Return>", lambda event: self._on_edit_account())

        # Bind Tab key to navigate between entries
        self.name_entry.bind(
            "<Tab>", lambda e: (self.password_entry.focus_set(), "break")[1]
        )
        self.password_entry.bind(
            "<Tab>", lambda e: (self.name_entry.focus_set(), "break")[1]
        )

        self.app.hide_loading(loading)

        self.name_entry.bind("<KeyRelease>", self._update_button)
        self.password_entry.bind("<KeyRelease>", self._update_button)

    def _update_button(self, e):
        """
        Update state of self.edit_account_button when we change the name or the password of the user.
        """

        if (
            self.name_var.get() != self.app.name
            or self.password_var.get() != self.app.password
        ):
            self.edit_account_button.config(state=tk.NORMAL)
        else:
            self.edit_account_button.config(state=tk.DISABLED)

    def _on_edit_account(self):
        """
        Give permission to modify the information of the account.
        Check if the user logged in manually or automatically. If automatically,
        open login dialog to login manually.
        """

        if self.app.password:
            self._on_save_account()

        else:
            self.app._show_login_dialog()
            self._on_return()

    def _on_save_account(self):
        """
        Save the new account information (name and password) to the backend API.
        """

        try:
            response = requests.post(
                f"{BASE_URL}/users/{self.app.username}/change_name",
                params={"new_name": self.name_entry.get()},
                timeout=5,
            )
            print(response)
            if response.status_code == 200:
                messagebox.showinfo(
                    "Succès", "Informations du compte mises à jour avec succès."
                )
                self.app.name = self.name_entry.get()  # type: ignore
            else:
                messagebox.showerror(
                    "Erreur", "Échec de la mise à jour des informations du compte."
                )

            response = requests.post(
                f"{BASE_URL}/users/{self.app.username}/change_password",
                params={
                    "old_password": self.app.password,
                    "new_password": self.password_entry.get(),
                },
                timeout=5,
            )
            if response.status_code == 200:
                messagebox.showinfo(
                    "Succès", "Informations du compte mises à jour avec succès."
                )
                self.app.password = self.password_entry.get()  # type: ignore
            else:
                messagebox.showerror(
                    "Erreur", "Échec de la mise à jour des informations du compte."
                )

        except Exception as e:
            messagebox.showerror(
                "Erreur",
                "Une erreur est survenue lors de la mise à jour des informations du compte.",
            )

    def download_profile_picture(self) -> None:
        """
        Download the user's profile picture from the backend API and save it locally.
        """

        self.profile_picture_path = (
            Path(BASE_FOLDER_PATH)
            / "gui"
            / "images"
            / "profiles"
            / "current_profile_picture.webp"
        )
        default_profile_path = (
            Path(BASE_FOLDER_PATH)
            / "gui"
            / "images"
            / "profiles"
            / "default_profile_photo.png"
        )
        target_size = self.ui.image_size((236, 236)) or (236, 236)

        try:
            response = requests.get(
                f"{BASE_URL}/users/{self.app.username}/profile-picture",
                timeout=5,
            )
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content)).convert("RGBA")
            else:
                image = Image.open(default_profile_path).convert("RGBA")

            image = image.resize(target_size, Image.Resampling.LANCZOS)
            image.save(self.profile_picture_path, format="WEBP")

        except Exception:
            try:
                image = Image.open(default_profile_path).convert("RGBA")
                image = image.resize(target_size, Image.Resampling.LANCZOS)
                image.save(self.profile_picture_path, format="WEBP")
            except Exception:
                self.profile_picture_path = default_profile_path

    def _on_change_profile_picture(self) -> None:
        """
        Handle change profile picture action.
        """

        new_profile_picture = filedialog.askopenfilename(
            title="Sélectionner une nouvelle photo de profil",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp")],
        )
        if not new_profile_picture:
            return

        try:
            picture = Image.open(new_profile_picture).convert("RGBA")
        except Exception:
            return

        dialog = TopLevelWindow(self.app, width=835, height=560)
        frame = UploadProfilePictureFrame(
            dialog.body_frame,
            self.app,
            picture,
            on_complete=self._on_profile_picture_uploaded,
        )
        frame.pack(fill=tk.BOTH, expand=True)
        dialog.show(wait=False)

    def _on_profile_picture_uploaded(self, picture_path: Path) -> None:
        """
        Refresh the local profile picture preview after a successful upload.
        """

        self.profile_picture_path = picture_path
        clear_image_cache(picture_path)
        self.change_profile_picture_button.configure(texture_path=picture_path)
        self.app.notify_profile_photo_updated()

    async def fetch_account_statistics(self) -> None:
        """
        Fetch the user's account statistics from the backend API.
        """

        try:
            async with httpx.AsyncClient(verify=False) as client:
                response = await client.get(f"{BASE_URL}/games/{self.app.username}")
                if response.status_code == 200:
                    data = response.json()
                    self.account_statistics = {
                        "games_played": len(data),
                        "games_won": sum(
                            1
                            for game in data
                            if game.get("result") == "1-0"
                            and game.get("black_player").get("username")
                            == self.app.username
                            or game.get("result") == "0-1"
                            and game.get("white_player").get("username")
                            == self.app.username
                        ),
                        "recent_games": data[:3],
                    }

                else:
                    pass

        except Exception as e:
            pass

    def _load_statistics_worker(self) -> None:
        asyncio.run(self.fetch_account_statistics())
        self.app.after(0, self._refresh_statistics_ui)

    def _refresh_statistics_ui(self) -> None:
        if not self.winfo_exists():
            return

        self.games_played_label.set_text(
            str(self.account_statistics.get("games_played", "0"))
        )
        self.games_won_label.set_text(
            str(self.account_statistics.get("games_won", "0"))
        )

        for child in self.statistics_frame.grid_slaves():
            row = int(child.grid_info().get("row", 0))
            if row >= 2:
                child.grid_forget()
        self.draw_recent_games(self.statistics_frame)

    def draw_recent_games(self, parent: tk.Widget) -> None:
        """
        Draw a list of the user's 3 most recent games with the result and opponent's name.
        """

        if not self.account_statistics:
            return

        for i in range(len(self.account_statistics.get("recent_games", []))):
            game = self.account_statistics["recent_games"][i]
            color = (
                "blancs"
                if game.get("white_player").get("username") == self.app.username
                else "noirs"
            )
            result = game.get("result", "N/A")
            opponent = (
                game.get("black_player").get("name")
                if game.get("white_player").get("username") == self.app.username
                else game.get("white_player").get("name")
            )
            frame = tk.Frame(
                parent,
                bg=(
                    "green"
                    if result == "1-0"
                    and color == "noirs"
                    or result == "0-1"
                    and color == "blancs"
                    else "red" if result in ["1-0", "0-1"] else "#f6a90d"
                ),
                bd=0,
                relief=tk.FLAT,
            )
            game_label = ttk.Label(
                frame,
                text=f"{"Gagné" if result == "1-0" and color == "noirs" or result == "0-1" and color == "blancs" else "Perdu"} avec les {color} contre {opponent} !",
                font=("Skranji", 8),
                background="#1e1e1e" if color == "noirs" else "white",
                foreground="white" if color == "noirs" else "black",
                anchor=tk.CENTER,
            )
            game_label.pack(
                fill=tk.BOTH,
                expand=True,
                padx=self.S(2),
                pady=self.S(2),
                ipadx=self.S(5),
                ipady=self.S(5),
            )
            frame.grid(
                row=2 + i,
                column=0,
                columnspan=2,
                sticky="ew",
                padx=self.S(20),
                pady=(
                    self.S((0, 20))
                    if i == len(self.account_statistics.get("recent_games", [])) - 1
                    else self.S((0, 10))
                ),
            )

    def _on_logout(self) -> None:
        """
        Handle logout action to log the user out and return to the login screen.
        """

        self.app._logout()
        self._on_return()

    def _on_return(self) -> None:
        """
        Handle return action to go back to the previous frame.
        """

        # Close dialog
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()


class UploadProfilePictureFrame(ttk.Frame):
    """
    Frame to upload a new profile picture for the user.
    Allows users to select an image file from their computer and upload it as their new profile picture.

    Allows users to:
    - Select an image file from their computer.
    - Crop and preview the selected image.
    - Upload the new profile picture to the backend API.
    """

    def __init__(
        self,
        parent: tk.Widget,
        app: "App",
        picture: Image.Image,
        on_complete: Callable[[Path], None] | None = None,
    ):
        """
        Initializes the upload profile picture frame.

        Args:
            parent: The container in which this frame is placed (e.g., dialog body)
            app (App): The main application instance.
        """
        self.ui = app.ui
        self.S = app.S

        super().__init__(parent)
        self.app = app
        self.original_image = picture.convert("RGBA")
        self.on_complete = on_complete

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.crop_size = self.S(496)
        self.canvas_size = self.S(500)
        self._drag_start: tuple[int, int] | None = None

        self.canvas = tk.Canvas(
            self,
            width=self.canvas_size,
            height=self.canvas_size,
            bg="#1e1e1e",
            highlightthickness=0,
        )
        self.canvas.grid(
            row=0, column=0, pady=self.S(20), padx=self.S(20), sticky="news"
        )

        button_row = ttk.Frame(self)
        button_row.grid(row=0, column=1, pady=self.S(20), padx=self.S(20), sticky="n")

        self.error_label = ttk.Label(button_row, text="", style="Error.TLabel")
        self.error_label.pack(pady=self.S((0, 10)))

        self.upload_button = self.app.Button(
            button_row,
            text="Importer",
            overlay_path=self.app.save_icon_path,
            hover_overlay_path=self.app.hovered_save_icon_path,
            command=self._on_upload,
            takefocus=False,
        )
        self.upload_button.pack(pady=self.S((10, 0)))

        self.change_picture_button = self.app.Button(
            button_row,
            text="Changer de photo",
            overlay_path=self.app.upload_icon_path,
            hover_overlay_path=self.app.hovered_upload_icon_path,
            command=self._on_change_picture,
            takefocus=False,
        )
        self.change_picture_button.pack(pady=self.S((10, 0)))

        self.cancel_button = self.app.Button(
            button_row,
            text="Annuler",
            overlay_path=self.app.return_icon_path,
            hover_overlay_path=self.app.hovered_return_icon_path,
            command=self._on_cancel,
            takefocus=False,
        )
        self.cancel_button.pack(pady=self.S(10))

        self._init_canvas_image()

        self.canvas.bind("<ButtonPress-1>", self._start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._end_drag)
        self.canvas.bind("<MouseWheel>", self._on_zoom)

    def _init_canvas_image(self) -> None:
        """
        Prepare the canvas image and crop overlay.
        """

        min_scale = max(
            self.crop_size / self.original_image.width,
            self.crop_size / self.original_image.height,
        )
        self._min_scale = min_scale
        self._max_scale = min_scale * 4
        self._scale = min_scale

        self.crop_left = (self.canvas_size - self.crop_size) / 2
        self.crop_top = (self.canvas_size - self.crop_size) / 2
        self.crop_right = self.crop_left + self.crop_size
        self.crop_bottom = self.crop_top + self.crop_size

        self._display_size = (0, 0)
        self._image_id: int | None = None
        self._render_image(center=(self.canvas_size / 2, self.canvas_size / 2))

        self.crop_rect = self.canvas.create_rectangle(
            self.crop_left,
            self.crop_top,
            self.crop_right,
            self.crop_bottom,
            outline="white",
            width=2,
        )

    def _render_image(self, center: tuple[float, float] | None = None) -> None:
        """
        Render the scaled image in the canvas.
        """

        display_width = max(1, int(self.original_image.width * self._scale))
        display_height = max(1, int(self.original_image.height * self._scale))
        self._display_size = (display_width, display_height)
        resized = self.original_image.resize(
            (display_width, display_height), Image.Resampling.LANCZOS
        )
        self._photo = ImageTk.PhotoImage(resized)

        if center is None and self._image_id is not None:
            coords = self.canvas.coords(self._image_id)
            center = (coords[0], coords[1])
        elif center is None:
            center = (self.canvas_size / 2, self.canvas_size / 2)

        center = self._clamp_center(center[0], center[1])

        if self._image_id is None:
            self._image_id = self.canvas.create_image(
                center[0], center[1], image=self._photo
            )
        else:
            self.canvas.itemconfig(self._image_id, image=self._photo)
            self.canvas.coords(self._image_id, center[0], center[1])

        self.canvas.image = self._photo  # type: ignore
        if hasattr(self, "crop_rect"):
            self.canvas.tag_raise(self.crop_rect)

    def _clamp_center(self, cx: float, cy: float) -> tuple[float, float]:
        """
        Keep the image covering the crop square.
        """

        half_w = self._display_size[0] / 2
        half_h = self._display_size[1] / 2

        min_cx = self.crop_right - half_w
        max_cx = self.crop_left + half_w
        if min_cx > max_cx:
            min_cx = max_cx = (min_cx + max_cx) / 2

        min_cy = self.crop_bottom - half_h
        max_cy = self.crop_top + half_h
        if min_cy > max_cy:
            min_cy = max_cy = (min_cy + max_cy) / 2

        cx = min(max(cx, min_cx), max_cx)
        cy = min(max(cy, min_cy), max_cy)
        return cx, cy

    def _start_drag(self, event) -> None:
        self._drag_start = (event.x, event.y)

    def _on_drag(self, event) -> None:
        if not self._drag_start or self._image_id is None:
            return

        dx = event.x - self._drag_start[0]
        dy = event.y - self._drag_start[1]
        cx, cy = self.canvas.coords(self._image_id)
        cx, cy = self._clamp_center(cx + dx, cy + dy)
        self.canvas.coords(self._image_id, cx, cy)
        self._drag_start = (event.x, event.y)

    def _end_drag(self, event) -> None:
        self._drag_start = None

    def _on_zoom(self, event) -> None:
        if self._image_id is None:
            return

        direction = 1 if event.delta > 0 else -1
        factor = 1.08 if direction > 0 else 0.92
        new_scale = min(max(self._scale * factor, self._min_scale), self._max_scale)
        if new_scale == self._scale:
            return
        self._scale = new_scale
        self._render_image()

    def _on_cancel(self) -> None:
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

    def _on_upload(self) -> None:
        if getattr(self, "_uploading", False):
            return
        self._set_upload_state(True)
        thread = threading.Thread(target=self._upload_worker, daemon=True)
        thread.start()

    def _set_upload_state(self, uploading: bool) -> None:
        self._uploading = uploading
        state = tk.DISABLED if uploading else tk.NORMAL
        self.upload_button.config(state=state)
        self.cancel_button.config(state=state)
        if uploading:
            self.error_label.config(text="Envoi en cours...")

    def _upload_worker(self) -> None:
        try:
            if not self.app.username:
                raise ValueError("Utilisateur non connecté.")

            cropped = self._get_cropped_image()
            buffer = BytesIO()
            cropped.save(buffer, format="WEBP")
            buffer.seek(0)

            response = requests.post(
                f"{BASE_URL}/users/{self.app.username}/profile-picture",
                files={
                    "file": (
                        "profile_picture.webp",
                        buffer.getvalue(),
                        "image/webp",
                    )
                },
                timeout=10,
            )

            if response.status_code not in (200, 201):
                raise ValueError("Erreur lors de l'envoi de l'image.")

            output_path = (
                Path(BASE_FOLDER_PATH)
                / "gui"
                / "images"
                / "profiles"
                / "current_profile_picture.webp"
            )
            output_path.parent.mkdir(parents=True, exist_ok=True)
            cropped.save(output_path, format="WEBP")

            self.app.after(0, lambda: self._on_upload_success(output_path))

        except Exception as exc:
            self.app.after(0, lambda: self._on_upload_error(str(exc)))

    def _on_upload_success(self, output_path: Path) -> None:
        self._set_upload_state(False)
        if self.on_complete:
            self.on_complete(output_path)
        dialog = self.winfo_toplevel()
        if isinstance(dialog, TopLevelWindow):
            dialog.close()

    def _on_upload_error(self, message: str) -> None:
        self._set_upload_state(False)
        self.error_label.config(text=message)

    def _get_cropped_image(self) -> Image.Image:
        if self._image_id is None:
            return self.original_image

        cx, cy = self.canvas.coords(self._image_id)
        display_w, display_h = self._display_size
        display_left = cx - display_w / 2
        display_top = cy - display_h / 2

        crop_left = (self.crop_left - display_left) / self._scale
        crop_top = (self.crop_top - display_top) / self._scale
        crop_right = (self.crop_right - display_left) / self._scale
        crop_bottom = (self.crop_bottom - display_top) / self._scale

        crop_left = max(0, min(self.original_image.width, crop_left))
        crop_top = max(0, min(self.original_image.height, crop_top))
        crop_right = max(0, min(self.original_image.width, crop_right))
        crop_bottom = max(0, min(self.original_image.height, crop_bottom))

        cropped = self.original_image.crop(
            (
                int(round(crop_left)),
                int(round(crop_top)),
                int(round(crop_right)),
                int(round(crop_bottom)),
            )
        )
        return cropped.resize(
            (self.crop_size, self.crop_size), Image.Resampling.LANCZOS
        )

    def _on_change_picture(self) -> None:
        """
        Change the picture file to edit
        """

        new_profile_picture = filedialog.askopenfilename(
            title="Sélectionner une nouvelle photo de profil",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.webp")],
        )
        if not new_profile_picture:
            return

        try:
            picture = Image.open(new_profile_picture).convert("RGBA")
        except Exception:
            return

        self.original_image = picture.convert("RGBA")
        self._init_canvas_image()
