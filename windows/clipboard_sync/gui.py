"""Tkinter desktop interface for manual Clipboard Sync on Windows."""

from __future__ import annotations

import platform
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from tkinter import ttk
from typing import Callable, Literal

from clipboard_sync.clipboard import read_text, write_text
from clipboard_sync.config import AppConfig, load_config
from clipboard_sync.state import AppState, StateStore
from clipboard_sync.supabase_client import (
    AuthenticationRequiredError,
    ClipboardItem,
    SupabaseSync,
)


LIGHT_COLORS = {
    "background": "#f3f7fc",
    "surface": "#ffffff",
    "field": "#f1f5fb",
    "surface_border": "#dce6f2",
    "primary": "#2563eb",
    "primary_active": "#1d4ed8",
    "accent": "#06b6d4",
    "text": "#10213d",
    "muted": "#64748b",
    "success": "#15803d",
    "success_background": "#ecfdf3",
    "error": "#b42318",
    "error_background": "#fef3f2",
    "info": "#1d4ed8",
    "info_background": "#eff6ff",
    "disabled": "#94a3b8",
}

DARK_COLORS = {
    "background": "#0b1220",
    "surface": "#111c2e",
    "field": "#1c293d",
    "surface_border": "#263852",
    "primary": "#60a5fa",
    "primary_active": "#3b82f6",
    "accent": "#22d3ee",
    "text": "#f8fafc",
    "muted": "#94a3b8",
    "success": "#4ade80",
    "success_background": "#102b23",
    "error": "#f87171",
    "error_background": "#351a20",
    "info": "#60a5fa",
    "info_background": "#122640",
    "disabled": "#64748b",
}

# Keep one shared mapping so existing widgets and tests can continue importing COLORS.
COLORS = LIGHT_COLORS.copy()

FeedbackKind = Literal["info", "success", "error"]


def system_uses_dark_mode() -> bool:
    """Return the Windows app-theme preference, defaulting safely to light mode."""

    if platform.system() != "Windows":
        return False
    try:
        import winreg

        path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            apps_use_light_theme, _value_type = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return int(apps_use_light_theme) == 0
    except (OSError, TypeError, ValueError):
        return False


class RoundedPanel(tk.Canvas):
    """Canvas-backed container with a genuinely rounded background."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        fill: str | None = None,
        background: str | None = None,
        radius: int = 22,
        padding: tuple[int, int] = (22, 18),
        expand_y: bool = False,
    ) -> None:
        fill = fill or COLORS["surface"]
        background = background or COLORS["background"]
        super().__init__(
            parent,
            background=background,
            borderwidth=0,
            highlightthickness=0,
            height=1,
        )
        self.fill = fill
        self.radius = radius
        self.padding_x, self.padding_y = padding
        self.expand_y = expand_y
        self.content = tk.Frame(self, background=fill, borderwidth=0)
        self._content_window = self.create_window(
            self.padding_x,
            self.padding_y,
            anchor="nw",
            window=self.content,
        )
        self.bind("<Configure>", self._redraw)
        self.content.bind("<Configure>", self._resize_to_content)
        self.after_idle(self._sync_height)

    def set_fill(self, fill: str) -> None:
        self.fill = fill
        self.content.configure(background=fill)
        self._draw_shape(self.winfo_width(), self.winfo_height())

    def _resize_to_content(self, _event: tk.Event[tk.Misc]) -> None:
        self._sync_height()

    def _sync_height(self) -> None:
        required_height = self.content.winfo_reqheight() + (self.padding_y * 2)
        if int(float(self.cget("height"))) != required_height:
            self.configure(height=required_height)

    def _redraw(self, event: tk.Event[tk.Misc]) -> None:
        content_width = max(1, event.width - (self.padding_x * 2))
        content_options = {"width": content_width}
        if self.expand_y:
            content_options["height"] = max(1, event.height - (self.padding_y * 2))
        self.itemconfigure(self._content_window, **content_options)
        self.coords(self._content_window, self.padding_x, self.padding_y)
        self._draw_shape(event.width, event.height)

    def _draw_shape(self, width: int, height: int) -> None:
        self.delete("rounded-background")
        radius = max(1, min(self.radius, width // 2, height // 2))
        diameter = radius * 2
        options = {"fill": self.fill, "outline": "", "tags": "rounded-background"}
        self.create_rectangle(radius, 0, width - radius, height, **options)
        self.create_rectangle(0, radius, width, height - radius, **options)
        self.create_arc(0, 0, diameter, diameter, start=90, extent=90, **options)
        self.create_arc(width - diameter, 0, width, diameter, start=0, extent=90, **options)
        self.create_arc(0, height - diameter, diameter, height, start=180, extent=90, **options)
        self.create_arc(
            width - diameter,
            height - diameter,
            width,
            height,
            start=270,
            extent=90,
            **options,
        )
        self.tag_lower("rounded-background")


class ScrollableFrame(ttk.Frame):
    """Vertically scroll content when the app is used on a shorter display."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent, style="App.TFrame")
        self.canvas = tk.Canvas(
            self,
            background=COLORS["background"],
            borderwidth=0,
            highlightthickness=0,
        )
        self.inner = ttk.Frame(self.canvas, style="App.TFrame")
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self._size_sync_pending = False
        self.canvas.pack(fill="both", expand=True)
        self.inner.bind("<Configure>", self._schedule_size_sync)
        self.canvas.bind("<Configure>", self._schedule_size_sync)
        self.canvas.bind("<Enter>", lambda _event: self.canvas.bind_all("<MouseWheel>", self._scroll))
        self.canvas.bind("<Leave>", lambda _event: self.canvas.unbind_all("<MouseWheel>"))

    def _schedule_size_sync(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self._size_sync_pending:
            return
        self._size_sync_pending = True
        self.after_idle(self._sync_inner_size)

    def _sync_inner_size(self) -> None:
        self._size_sync_pending = False
        width = max(1, self.canvas.winfo_width())
        height = max(self.canvas.winfo_height(), self.inner.winfo_reqheight())
        self.canvas.itemconfigure(self._window, width=width, height=height)
        self.canvas.configure(scrollregion=(0, 0, width, height))

    def _scroll(self, event: tk.Event[tk.Misc]) -> None:
        if event.delta:
            self.canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")


class DesktopController:
    """Share the working CLI services with the desktop interface."""

    def __init__(
        self,
        *,
        store: StateStore | None = None,
        config_loader: Callable[[], AppConfig] = load_config,
        sync_factory: Callable[[AppConfig], SupabaseSync] = SupabaseSync,
        clipboard_reader: Callable[[], str] = read_text,
        clipboard_writer: Callable[[str], None] = write_text,
    ) -> None:
        self.store = store or StateStore()
        self.config_loader = config_loader
        self.sync_factory = sync_factory
        self.clipboard_reader = clipboard_reader
        self.clipboard_writer = clipboard_writer
        self.state = self.store.load()
        self.sync: SupabaseSync | None = None

    @property
    def is_logged_in(self) -> bool:
        return self.state.is_logged_in

    def login(self, email: str, password: str, device_name: str) -> AppState:
        previous_state = self.store.load()
        sync = self.sync_factory(self.config_loader())
        state = sync.sign_in(email.strip(), password)
        state.client_device_key = previous_state.client_device_key
        sync.use_session(state)
        sync.ensure_windows_device(state, device_name)
        self.store.save(state)
        self.sync = sync
        self.state = state
        return state

    def restore(self, device_name: str) -> AppState:
        sync = self.sync_factory(self.config_loader())
        self.sync = sync
        self._use_saved_session()
        sync.ensure_windows_device(self.state, device_name)
        self.store.save(self.state)
        return self.state

    def push(self, device_name: str, content: str | None = None) -> str:
        sync = self._require_sync()
        self._use_saved_session()
        sync.ensure_windows_device(self.state, device_name)
        self.store.save(self.state)
        if content is None:
            content = self.clipboard_reader()
        sync.push_clipboard_text(self.state, content)
        return content

    def pull(self) -> ClipboardItem | None:
        sync = self._require_sync()
        self._use_saved_session()
        return sync.pull_latest_clipboard_text()

    def copy_to_clipboard(self, content: str) -> str:
        self.clipboard_writer(content)
        return content

    def logout(self) -> None:
        self.state = self.store.clear_session()
        self.sync = None

    def _require_sync(self) -> SupabaseSync:
        if self.sync is None:
            raise AuthenticationRequiredError("You are not logged in. Sign in first.")
        return self.sync

    def _use_saved_session(self) -> None:
        sync = self._require_sync()
        try:
            sync.use_session(self.state)
        except AuthenticationRequiredError:
            self.state = self.store.clear_session()
            self.sync = None
            raise
        self.store.save(self.state)


class ClipboardSyncWindow(tk.Tk):
    """Branded, keyboard-friendly desktop shell for the manual sync flow."""

    def __init__(self, controller: DesktopController | None = None) -> None:
        super().__init__()
        self.dark_mode = system_uses_dark_mode()
        COLORS.clear()
        COLORS.update(DARK_COLORS if self.dark_mode else LIGHT_COLORS)
        self.controller = controller or DesktopController()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clipboard-sync")
        self.device_name = default_device_name()
        self.email = tk.StringVar(value=self.controller.state.user_email or "")
        self.password = tk.StringVar()
        self.account = tk.StringVar(value="Not signed in")
        self.feedback = tk.StringVar(value="Ready to sync.")
        self.feedback_icon = tk.StringVar(value="i")
        self.feedback_kind: FeedbackKind = "info"
        self.last_pushed_text: str | None = None
        self.latest_pulled_text: str | None = None
        self.busy = False
        self._fit_job: str | None = None
        self._fit_when_mapped = False
        self._theme_job: str | None = None
        self._rounded_panels: list[RoundedPanel] = []
        self._field_panels: list[RoundedPanel] = []
        self._app_icon: tk.PhotoImage | None = None
        self._brand_icon: tk.PhotoImage | None = None

        self.title("Clipboard Sync")
        self.geometry("540x785")
        self.minsize(540, 630)
        self.configure(background=COLORS["background"])
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.bind("<Return>", self._handle_return)
        self.bind("<Map>", self._handle_window_map, add="+")

        self._load_branding()
        self._configure_style()
        self._build_ui()
        self._theme_job = self.after(1500, self._check_system_theme)

        if self.controller.is_logged_in:
            self._show_session(self.controller.state.user_email or "Saved account")
            self._run(
                "Restoring your session…",
                lambda: self.controller.restore(self.device_name),
                lambda state: self._session_ready(state, "Device ready."),
            )
        else:
            self._show_login()

    def _load_branding(self) -> None:
        icon_path = Path(__file__).with_name("assets") / "app_icon.png"
        if not icon_path.exists():
            return
        try:
            self._app_icon = tk.PhotoImage(file=str(icon_path))
            self._brand_icon = self._app_icon.subsample(16, 16)
            self.iconphoto(True, self._app_icon)
        except tk.TclError:
            self._app_icon = None
            self._brand_icon = None

    def _configure_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("App.TFrame", background=COLORS["background"])
        style.configure(
            "Card.TFrame",
            background=COLORS["surface"],
            bordercolor=COLORS["surface_border"],
            borderwidth=1,
            relief="solid",
        )
        style.configure("HeaderIcon.TLabel", background=COLORS["background"])
        style.configure(
            "Title.TLabel",
            background=COLORS["background"],
            foreground=COLORS["text"],
            font=("Segoe UI", 24, "bold"),
        )
        style.configure(
            "Subtitle.TLabel",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 12),
        )
        style.configure(
            "PageSection.TLabel",
            background=COLORS["background"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 11, "bold"),
        )
        style.configure(
            "Section.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            font=("Segoe UI", 13, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            font=("Segoe UI", 11),
        )
        style.configure(
            "Muted.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["muted"],
            font=("Segoe UI", 10),
        )
        style.configure(
            "Account.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["text"],
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "AccountCheck.TLabel",
            background=COLORS["surface"],
            foreground=COLORS["success"],
            font=("Segoe UI Symbol", 14, "bold"),
        )
        style.configure(
            "App.TEntry",
            padding=(10, 9),
            fieldbackground=COLORS["surface"],
            foreground=COLORS["text"],
            insertcolor=COLORS["text"],
            bordercolor=COLORS["surface_border"],
            lightcolor=COLORS["surface_border"],
            darkcolor=COLORS["surface_border"],
        )
        style.map(
            "App.TEntry",
            bordercolor=[("focus", COLORS["primary"])],
            lightcolor=[("focus", COLORS["primary"])],
            darkcolor=[("focus", COLORS["primary"])],
        )
        style.configure(
            "Primary.TButton",
            background=COLORS["primary"],
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=2,
            focuscolor=COLORS["accent"],
            font=("Segoe UI", 11, "bold"),
            padding=(16, 9),
        )
        style.map(
            "Primary.TButton",
            background=[("active", COLORS["primary_active"]), ("disabled", COLORS["disabled"])],
            foreground=[("disabled", "#eef2f7")],
        )
        style.configure(
            "Secondary.TButton",
            background=COLORS["surface"],
            foreground=COLORS["primary"],
            bordercolor=COLORS["primary"],
            borderwidth=1,
            focusthickness=2,
            focuscolor=COLORS["accent"],
            font=("Segoe UI", 10, "bold"),
            padding=(16, 10),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", COLORS["info_background"]), ("disabled", "#f8fafc")],
            foreground=[("disabled", COLORS["disabled"])],
        )
        style.configure(
            "Copy.TButton",
            background=COLORS["info_background"],
            foreground=COLORS["primary"],
            borderwidth=0,
            focusthickness=2,
            focuscolor=COLORS["accent"],
            font=("Segoe UI", 11, "bold"),
            padding=(16, 9),
        )
        style.map(
            "Copy.TButton",
            background=[("active", COLORS["field"]), ("disabled", COLORS["field"])],
            foreground=[("disabled", COLORS["disabled"])],
        )
        style.configure(
            "Link.TButton",
            background=COLORS["surface"],
            foreground=COLORS["primary"],
            borderwidth=0,
            font=("Segoe UI", 10, "bold"),
            padding=(0, 8),
            anchor="w",
        )
        style.map(
            "Link.TButton",
            background=[("active", COLORS["surface"])],
            foreground=[("active", COLORS["primary_active"]), ("disabled", COLORS["disabled"])],
        )
        style.configure(
            "Danger.TButton",
            background=COLORS["surface"],
            foreground=COLORS["error"],
            borderwidth=0,
            font=("Segoe UI", 10),
            padding=(0, 8),
            anchor="w",
        )
        style.map(
            "Danger.TButton",
            background=[("active", COLORS["surface"])],
            foreground=[("disabled", COLORS["disabled"])],
        )
        style.configure(
            "AppDanger.TButton",
            background=COLORS["background"],
            foreground=COLORS["error"],
            borderwidth=0,
            font=("Segoe UI", 11),
            padding=(12, 7),
        )
        style.map(
            "AppDanger.TButton",
            background=[("active", COLORS["background"])],
            foreground=[("disabled", COLORS["disabled"])],
        )
        style.configure(
            "App.Horizontal.TProgressbar",
            background=COLORS["accent"],
            troughcolor=COLORS["info_background"],
            borderwidth=0,
            thickness=4,
        )
        self._configure_feedback_style("info")

    def _configure_feedback_style(self, kind: FeedbackKind) -> None:
        background = COLORS[f"{kind}_background"]
        foreground = COLORS[kind]
        style = ttk.Style(self)
        style.configure("Feedback.TFrame", background=background)
        style.configure(
            "FeedbackIcon.TLabel",
            background=background,
            foreground=foreground,
            font=("Segoe UI", 10, "bold"),
        )
        style.configure(
            "Feedback.TLabel",
            background=background,
            foreground=foreground,
            font=("Segoe UI", 9),
        )

    def _check_system_theme(self) -> None:
        self._theme_job = None
        dark_mode = system_uses_dark_mode()
        if dark_mode != self.dark_mode:
            self.dark_mode = dark_mode
            self._apply_theme()
        self._theme_job = self.after(1500, self._check_system_theme)

    def _apply_theme(self) -> None:
        COLORS.clear()
        COLORS.update(DARK_COLORS if self.dark_mode else LIGHT_COLORS)
        self.configure(background=COLORS["background"])
        self._configure_style()
        self.scroller.canvas.configure(background=COLORS["background"])

        for panel in self._rounded_panels:
            if panel is self.feedback_panel:
                panel.configure(background=COLORS["background"])
            elif panel in self._field_panels:
                panel.configure(background=COLORS["surface"])
                panel.set_fill(COLORS["field"])
            else:
                panel.configure(background=COLORS["background"])
                panel.set_fill(COLORS["surface"])

        text_options = {
            "background": COLORS["field"],
            "foreground": COLORS["text"],
            "insertbackground": COLORS["text"],
            "selectbackground": COLORS["primary"],
            "selectforeground": "#ffffff",
        }
        self.push_input.configure(**text_options)
        display_options = text_options | {
            "foreground": COLORS["text"] if self.latest_pulled_text is not None else COLORS["muted"]
        }
        self.pulled_display.configure(**display_options)
        self._set_feedback(self.feedback.get(), kind=self.feedback_kind)
        self._set_native_title_bar()

    def _set_native_title_bar(self) -> None:
        """Ask supported Windows versions to match the app's current theme."""

        if platform.system() != "Windows" or not self.winfo_ismapped():
            return
        try:
            import ctypes

            window_handle = ctypes.windll.user32.GetParent(self.winfo_id())
            enabled = ctypes.c_int(1 if self.dark_mode else 0)
            for attribute in (20, 19):
                result = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    window_handle,
                    attribute,
                    ctypes.byref(enabled),
                    ctypes.sizeof(enabled),
                )
                if result == 0:
                    break
        except (AttributeError, OSError):
            return

    def _build_ui(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.shell = ttk.Frame(self, style="App.TFrame", padding=(30, 20, 30, 20))
        self.shell.grid(row=0, column=0, sticky="nsew")
        self.shell.columnconfigure(0, weight=1)
        self.shell.rowconfigure(1, weight=1)

        self._build_header(self.shell)
        self.scroller = ScrollableFrame(self.shell)
        self.scroller.grid(row=1, column=0, sticky="nsew")
        self.content = self.scroller.inner
        self.content.columnconfigure(0, weight=1)
        self.content.rowconfigure(0, weight=1)

        self.login_card = self._card(self.content)
        self._build_login_card(self.login_card.content)
        self.session_content = ttk.Frame(self.content, style="App.TFrame")
        self.session_content.columnconfigure(0, weight=1)
        self._build_session_content(self.session_content)

        self.feedback_panel = RoundedPanel(
            self.content,
            fill=COLORS["info_background"],
            radius=18,
            padding=(14, 8),
        )
        self._rounded_panels.append(self.feedback_panel)
        self.feedback_panel.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        self.feedback_frame = self.feedback_panel.content
        self.feedback_frame.columnconfigure(1, weight=1)
        self.feedback_icon_label = tk.Label(
            self.feedback_frame,
            textvariable=self.feedback_icon,
            background=COLORS["info_background"],
            foreground=COLORS["info"],
            font=("Segoe UI", 10, "bold"),
            width=2,
            anchor="center",
        )
        self.feedback_icon_label.grid(row=0, column=0, sticky="n", padx=(0, 4))
        self.feedback_label = tk.Label(
            self.feedback_frame,
            textvariable=self.feedback,
            background=COLORS["info_background"],
            foreground=COLORS["info"],
            font=("Segoe UI", 9),
            wraplength=500,
            justify="left",
            anchor="w",
        )
        self.feedback_label.grid(row=0, column=1, sticky="ew")
        self.progress = ttk.Progressbar(
            self.feedback_frame,
            mode="indeterminate",
            style="App.Horizontal.TProgressbar",
        )
        self.logout_button = ttk.Button(
            self.content,
            text="Log Out",
            style="AppDanger.TButton",
            command=self._logout,
            takefocus=True,
        )
        self.logout_button.grid(row=2, column=0, sticky="ew", pady=(8, 2))

    def _build_header(self, parent: ttk.Frame) -> None:
        self.header = ttk.Frame(parent, style="App.TFrame")
        self.header.grid(row=0, column=0, sticky="ew", pady=(0, 14))
        self.header.columnconfigure(0, weight=1)
        ttk.Label(self.header, text="Clipboard Sync", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )

    def _card(
        self,
        parent: tk.Misc,
        *,
        radius: int = 22,
        padding: tuple[int, int] = (22, 18),
        expand_y: bool = False,
    ) -> RoundedPanel:
        card = RoundedPanel(parent, radius=radius, padding=padding, expand_y=expand_y)
        self._rounded_panels.append(card)
        card.content.columnconfigure(0, weight=1)
        return card

    def _field(
        self,
        parent: tk.Misc,
        *,
        height_padding: int = 8,
        expand_y: bool = False,
    ) -> RoundedPanel:
        field = RoundedPanel(
            parent,
            fill=COLORS["field"],
            background=COLORS["surface"],
            radius=14,
            padding=(12, height_padding),
            expand_y=expand_y,
        )
        self._rounded_panels.append(field)
        self._field_panels.append(field)
        field.content.columnconfigure(0, weight=1)
        return field

    def _section_heading(self, parent: ttk.Frame, title: str, description: str, row: int = 0) -> int:
        ttk.Label(parent, text=title, style="Section.TLabel").grid(row=row, column=0, sticky="w")
        ttk.Label(parent, text=description, style="Muted.TLabel", wraplength=500).grid(
            row=row + 1, column=0, sticky="ew", pady=(3, 15)
        )
        return row + 2

    def _build_login_card(self, card: tk.Frame) -> None:
        row = self._section_heading(card, "Sign in to sync", "Use the same Supabase account on both devices.")
        ttk.Label(card, text="Email", style="Body.TLabel").grid(row=row, column=0, sticky="w")
        self.email_entry = ttk.Entry(card, textvariable=self.email, style="App.TEntry", takefocus=True)
        self.email_entry.grid(row=row + 1, column=0, sticky="ew", pady=(5, 13))
        ttk.Label(card, text="Password", style="Body.TLabel").grid(row=row + 2, column=0, sticky="w")
        self.password_entry = ttk.Entry(
            card, textvariable=self.password, show="•", style="App.TEntry", takefocus=True
        )
        self.password_entry.grid(row=row + 3, column=0, sticky="ew", pady=(5, 18))
        self.sign_in_button = ttk.Button(
            card, text="Sign In", style="Primary.TButton", command=self._sign_in, takefocus=True
        )
        self.sign_in_button.grid(row=row + 4, column=0, sticky="ew")

    def _build_session_content(self, parent: ttk.Frame) -> None:
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(2, weight=1)

        account_panel = self._card(parent, radius=22, padding=(18, 11))
        account_panel.grid(row=0, column=0, sticky="ew")
        account_card = account_panel.content
        account_card.columnconfigure(0, weight=1)
        ttk.Label(account_card, text="Signed in", style="Muted.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(account_card, textvariable=self.account, style="Account.TLabel").grid(
            row=1, column=0, sticky="w", pady=(1, 2)
        )
        ttk.Label(account_card, text=self.device_name, style="Muted.TLabel").grid(
            row=2, column=0, sticky="w"
        )
        ttk.Label(account_card, text="✓", style="AccountCheck.TLabel").grid(
            row=0, column=1, rowspan=3, padx=(12, 0), sticky="e"
        )

        push_panel = self._card(parent, padding=(18, 13), expand_y=True)
        push_panel.grid(row=1, column=0, sticky="nsew", pady=(14, 0))
        push_card = push_panel.content
        push_card.rowconfigure(1, weight=1, minsize=50)
        ttk.Label(push_card, text="Push", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        push_field = self._field(push_card, expand_y=True)
        push_field.grid(row=1, column=0, sticky="nsew")
        push_field.content.rowconfigure(0, weight=1)
        self.push_input = self._text_box(push_field.content, height=2)
        self.push_input.grid(row=0, column=0, sticky="nsew")
        self.push_button = ttk.Button(
            push_card,
            text="↑  Push Text",
            style="Primary.TButton",
            command=self._push,
            takefocus=True,
        )
        self.push_button.grid(row=2, column=0, sticky="ew", pady=(10, 0))

        pull_panel = self._card(parent, padding=(18, 13), expand_y=True)
        pull_panel.grid(row=2, column=0, sticky="nsew", pady=(14, 0))
        pull_card = pull_panel.content
        pull_card.rowconfigure(1, weight=1, minsize=50)
        ttk.Label(pull_card, text="Pull", style="Section.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 10)
        )
        pull_field = self._field(pull_card, expand_y=True)
        pull_field.grid(row=1, column=0, sticky="nsew")
        pull_field.content.rowconfigure(0, weight=1)
        self.pulled_display = self._text_display(pull_field.content, height=2)
        self.pulled_display.grid(row=0, column=0, sticky="nsew")
        self.pull_button = ttk.Button(
            pull_card,
            text="↓  Pull Latest",
            style="Primary.TButton",
            command=self._pull,
            takefocus=True,
        )
        self.pull_button.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        self.copy_button = ttk.Button(
            pull_card,
            text="⧉  Copy to Clipboard",
            style="Copy.TButton",
            command=self._copy_pulled_text,
            takefocus=True,
        )
        self.copy_button.grid(row=3, column=0, sticky="ew", pady=(8, 0))

        self._set_text_display(self.pulled_display, None, "Nothing pulled yet.")

    def _fit_signed_in_window(self) -> None:
        """Size the window to show the complete signed-in layout when possible."""

        if not self.winfo_ismapped():
            self._fit_when_mapped = True
            return
        if self._fit_job is not None:
            self.after_cancel(self._fit_job)
        self._fit_job = self.after_idle(self._apply_signed_in_window_size)

    def _handle_window_map(self, event: tk.Event[tk.Misc]) -> None:
        if event.widget is not self:
            return
        self._set_native_title_bar()
        if self._fit_when_mapped:
            self._fit_when_mapped = False
            self._fit_signed_in_window()

    def _apply_signed_in_window_size(self) -> None:
        self._fit_job = None
        self.update_idletasks()
        current_height = max(1, self.winfo_height())
        viewport_height = max(1, self.scroller.canvas.winfo_height())
        fixed_height = current_height - viewport_height
        desired_height = max(current_height, fixed_height + self.session_content.winfo_reqheight())
        available_height = max(560, self.winfo_screenheight() - 120)
        width = max(540, self.winfo_width())
        self.geometry(f"{width}x{min(desired_height, available_height)}")

    def _text_box(self, parent: tk.Frame, *, height: int) -> tk.Text:
        return tk.Text(
            parent,
            height=height,
            wrap="word",
            background=COLORS["field"],
            foreground=COLORS["text"],
            insertbackground=COLORS["text"],
            selectbackground=COLORS["primary"],
            selectforeground="#ffffff",
            borderwidth=0,
            highlightthickness=0,
            relief="flat",
            font=("Segoe UI", 11),
            cursor="xterm",
            takefocus=True,
            padx=0,
            pady=2,
        )

    def _text_display(self, parent: tk.Frame, *, height: int) -> tk.Text:
        widget = self._text_box(parent, height=height)
        widget.configure(cursor="arrow")
        return widget

    def _set_text_display(self, widget: tk.Text, text: str | None, placeholder: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text if text is not None else placeholder)
        widget.configure(foreground=COLORS["text"] if text is not None else COLORS["muted"])
        widget.configure(state="disabled")

    def _handle_return(self, _event: tk.Event[tk.Misc]) -> str | None:
        if not self.busy and self.login_card.winfo_ismapped():
            self._sign_in()
            return "break"
        return None

    def _sign_in(self) -> None:
        email = self.email.get().strip()
        password = self.password.get()
        if not email or not password:
            self._set_feedback("Enter your email and password.", kind="error")
            return
        self._run(
            "Signing in…",
            lambda: self.controller.login(email, password, self.device_name),
            lambda state: self._session_ready(state, "Signed in. Device ready."),
        )

    def _push(self) -> None:
        content = self.push_input.get("1.0", "end-1c")
        entered_text = content if content.strip() else None
        self._run(
            "Pushing text…",
            lambda: self.controller.push(self.device_name, entered_text),
            self._push_succeeded,
        )

    def _pull(self) -> None:
        self._run(
            "Pulling latest text…",
            self.controller.pull,
            self._pull_succeeded,
        )

    def _copy_pulled_text(self) -> None:
        if self.latest_pulled_text is None:
            self._set_feedback("Pull some text before copying it.", kind="info")
            return
        text = self.latest_pulled_text
        self._run(
            "Copying text…",
            lambda: self.controller.copy_to_clipboard(text),
            self._copy_succeeded,
        )

    def _push_succeeded(self, content: object) -> None:
        pushed_text = str(content)
        self.last_pushed_text = pushed_text
        if not self.push_input.get("1.0", "end-1c").strip():
            self.push_input.delete("1.0", "end")
            self.push_input.insert("1.0", pushed_text)
        self._set_feedback(f"Pushed {len(pushed_text)} characters.", kind="success")

    def _pull_succeeded(self, item: object) -> None:
        if item is None:
            self.latest_pulled_text = None
            self._set_text_display(self.pulled_display, None, "Nothing pulled yet.")
            self._update_buttons()
            self._set_feedback("No synced text yet.", kind="info")
            return
        pulled_text = str(item.content)
        self.latest_pulled_text = pulled_text
        self._set_text_display(self.pulled_display, pulled_text, "Nothing pulled yet.")
        self._update_buttons()
        self._set_feedback("Latest text pulled successfully.", kind="success")

    def _copy_succeeded(self, content: object) -> None:
        copied_text = str(content)
        self._set_feedback(
            f"Copied {len(copied_text)} characters to the Windows clipboard.",
            kind="success",
        )

    def _logout(self) -> None:
        self.controller.logout()
        self.password.set("")
        self._show_login()
        self._set_feedback("Logged out. This installation's device key was kept.", kind="info")

    def _run(self, message: str, work: Callable[[], object], success: Callable[[object], None]) -> None:
        if self.busy:
            return
        self._set_busy(True)
        self._set_feedback(message, kind="info")
        future = self.executor.submit(work)
        self.after(50, self._poll_future, future, success)

    def _poll_future(self, future: Future[object], success: Callable[[object], None]) -> None:
        if not future.done():
            self.after(50, self._poll_future, future, success)
            return
        self._finish(future, success)

    def _finish(self, future: Future[object], success: Callable[[object], None]) -> None:
        self._set_busy(False)
        try:
            result = future.result()
        except Exception as error:
            if isinstance(error, AuthenticationRequiredError):
                self._show_login()
            self._set_feedback(str(error) or "Something went wrong. Please try again.", kind="error")
            return
        success(result)

    def _session_ready(self, state: AppState, message: str) -> None:
        self.password.set("")
        self._show_session(state.user_email or "Signed-in user")
        self._set_feedback(message, kind="success")

    def _show_login(self) -> None:
        self.session_content.grid_remove()
        self.login_card.grid(row=0, column=0, sticky="ew")
        self.account.set("Not signed in")
        self.last_pushed_text = None
        self.latest_pulled_text = None
        self.push_input.delete("1.0", "end")
        self._set_text_display(self.pulled_display, None, "Nothing pulled yet.")
        self.scroller.canvas.yview_moveto(0)
        self.email_entry.focus_set()
        self._update_buttons()

    def _show_session(self, email: str) -> None:
        self.login_card.grid_remove()
        self.session_content.grid(row=0, column=0, sticky="nsew")
        self.account.set(email)
        self._fit_signed_in_window()
        self.scroller.canvas.yview_moveto(0)
        self.focus_set()
        self._update_buttons()

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        if busy:
            self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(9, 0))
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.grid_remove()
        self._update_buttons()

    def _update_buttons(self) -> None:
        state = "disabled" if self.busy else "normal"
        self.sign_in_button.configure(state=state)
        self.push_button.configure(state=state)
        self.pull_button.configure(state=state)
        copy_state = "disabled" if self.busy or self.latest_pulled_text is None else "normal"
        self.copy_button.configure(state=copy_state)
        self.logout_button.configure(state=state)

    def _set_feedback(self, message: str, *, kind: FeedbackKind = "info") -> None:
        self.feedback_kind = kind
        self.feedback.set(message)
        self.feedback_icon.set({"info": "i", "success": "✓", "error": "!"}[kind])
        background = COLORS[f"{kind}_background"]
        foreground = COLORS[kind]
        self.feedback_panel.set_fill(background)
        self.feedback_icon_label.configure(background=background, foreground=foreground)
        self.feedback_label.configure(background=background, foreground=foreground)

    def _close(self) -> None:
        if self._theme_job is not None:
            self.after_cancel(self._theme_job)
            self._theme_job = None
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.destroy()


def default_device_name() -> str:
    node = platform.node().strip()
    return f"{node} Windows" if node else "Windows Device"


def main() -> None:
    ClipboardSyncWindow().mainloop()


if __name__ == "__main__":
    main()
