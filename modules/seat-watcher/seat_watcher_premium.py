"""Responsive UI for Seat Watcher; search behavior stays in V44 unchanged."""
import customtkinter as ctk
import tkinter as tk
import sys

from seat_watcher_v44 import APP_NAME, SeatWatcherGUI
from ui_theme import THEME as T


class Card(ctk.CTkFrame):
    def __init__(self, master, step, title, subtitle, accent):
        tint = {T.purple: "#1B1028", T.cyan: "#0B1D28",
                "#7488FF": "#11182B", T.green: "#0D201A"}.get(accent, T.surface)
        super().__init__(master, fg_color=tint, corner_radius=18,
                         border_width=2, border_color=accent)
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(self, height=5, fg_color=accent, corner_radius=3).grid(
            row=0, column=0, sticky="ew", padx=42)
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=1, column=0, sticky="ew", padx=20, pady=(18, 13))
        head.grid_columnconfigure(1, weight=1)
        icon = ctk.CTkFrame(head, width=42, height=42, fg_color=accent, corner_radius=12)
        icon.grid(row=0, column=0, rowspan=3, sticky="nw", padx=(0, 12)); icon.grid_propagate(False)
        ctk.CTkLabel(icon, text=step.split()[0], text_color="#06070B",
                     font=ctk.CTkFont(size=15, weight="bold")).place(relx=.5, rely=.5, anchor="center")
        ctk.CTkLabel(head, text=" ".join(step.split()[1:]).upper(), text_color=accent,
                     font=ctk.CTkFont(size=9, weight="bold")).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(head, text=title, text_color=T.text,
                     font=ctk.CTkFont(size=19, weight="bold")).grid(row=1, column=1, sticky="w", pady=(1, 0))
        ctk.CTkLabel(head, text=subtitle, text_color=T.dim,
                     font=ctk.CTkFont(size=11)).grid(row=2, column=1, sticky="w", pady=(3, 0))


class SeatWatcherPremiumGUI(SeatWatcherGUI):
    """Presentation-only subclass retaining the proven V44 behavior contract."""

    def build_ui(self):
        ctk.set_appearance_mode("dark")
        self.root.title(f"{APP_NAME} — Premium")
        self.root.geometry("1160x860")
        self.root.minsize(720, 640)

        # Aliases expected by inherited event and rendering methods.
        self.bg, self.shell, self.field_bg = T.canvas, T.shell, T.field
        self.text, self.text_soft, self.text_dim = T.text, T.soft, T.dim
        self.accent, self.accent_hover = T.purple, T.purple_hover
        self.blue, self.blue_hover, self.green = T.cyan, T.cyan_hover, T.green
        self.advanced_visible = self.theaters_visible = False
        self._layout_mode = None

        self.root.configure(fg_color=T.canvas)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.ambient_canvas = tk.Canvas(self.root, bg=T.canvas, highlightthickness=0, bd=0)
        self.ambient_canvas.grid(row=0, column=0, sticky="nsew")
        self.outer_frame = ctk.CTkScrollableFrame(self.root, fg_color="transparent", corner_radius=0)
        self.outer_frame.grid(row=0, column=0, sticky="nsew")
        self.outer_frame.grid_columnconfigure(0, weight=1)
        self.shell_shadow = ctk.CTkFrame(self.outer_frame, fg_color="#000106", corner_radius=30,
                                         border_width=1, border_color="#151B2B")
        self.shell_shadow.grid(row=0, column=0, sticky="ew", padx=14, pady=(31, 17))
        self.app_shell = ctk.CTkFrame(self.outer_frame, fg_color=T.shell, corner_radius=26,
                                      border_width=2, border_color="#36425D")
        self.app_shell.grid(row=0, column=0, sticky="ew", padx=20, pady=(22, 34))
        self.app_shell.grid_columnconfigure(0, weight=1)
        self.content = ctk.CTkFrame(self.app_shell, fg_color="transparent")
        self.content.grid(row=0, column=0, sticky="nsew", padx=24, pady=22)

        self._header()
        self._movie()
        self._where()
        self._when()
        self._advanced()
        self._action()
        self._status()
        self.on_date_mode_change(self.date_mode.get())

        self.root.bind("<Configure>", self._on_window_resize, add="+")
        self.root.bind("<Configure>", self._ambient_resize, add="+")
        self.root.after(40, self._apply_responsive_width)
        self.root.after(60, self._draw_ambient_background)
        self._bind_mac_scrolling()

    def _header(self):
        self.header = ctk.CTkFrame(self.content, fg_color="#19102B", corner_radius=20,
                                   border_width=2, border_color="#7742A0")
        ctk.CTkFrame(self.header, height=5, fg_color=T.purple, corner_radius=3).place(
            relx=.16, rely=0, relwidth=.32, anchor="n")
        ctk.CTkFrame(self.header, height=5, fg_color=T.cyan, corner_radius=3).place(
            relx=.70, rely=0, relwidth=.20, anchor="n")
        inner = ctk.CTkFrame(self.header, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=22)
        brand = ctk.CTkFrame(inner, fg_color="transparent")
        brand.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(brand, text="SEAT WATCHER  /  LIVE CINEMA INTELLIGENCE", text_color=T.cyan,
                     font=ctk.CTkFont(size=10, weight="bold")).pack(anchor="w")
        ctk.CTkLabel(brand, text="The right seats.\nBefore someone else finds them.",
                     justify="left", text_color=T.text,
                     font=ctk.CTkFont(size=29, weight="bold")).pack(anchor="w", pady=(5, 0))
        ctk.CTkLabel(brand, text="Build your perfect show once — the watcher handles the chase.",
                     text_color="#C8B6DB", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(7, 0))
        badge = ctk.CTkFrame(inner, fg_color="#0C1C21", corner_radius=14,
                             border_width=2, border_color="#278C87")
        badge.pack(side="right", padx=(14, 0))
        ctk.CTkLabel(badge, text="WATCH MODE", text_color=T.green,
                     font=ctk.CTkFont(size=8, weight="bold")).pack(padx=18, pady=(11, 1))
        ctk.CTkLabel(badge, textvariable=self.status_text, text_color=T.soft,
                     font=ctk.CTkFont(size=13, weight="bold")).pack(padx=18, pady=(0, 11))

    def _entry(self, master, variable, placeholder=""):
        return ctk.CTkEntry(master, textvariable=variable, placeholder_text=placeholder,
                            height=46, corner_radius=11, fg_color=T.field,
                            border_width=2, border_color=T.border_hi, text_color=T.text,
                            font=ctk.CTkFont(size=13, weight="bold"))

    def _field(self, master, label, variable, col, placeholder=""):
        master.grid_columnconfigure(col, weight=1)
        box = ctk.CTkFrame(master, fg_color="transparent")
        box.grid(row=0, column=col, sticky="ew", padx=(0, 10) if col == 0 else 0)
        ctk.CTkLabel(box, text=label.upper(), text_color=T.soft,
                     font=ctk.CTkFont(size=9, weight="bold")).pack(anchor="w", pady=(0, 5))
        entry = self._entry(box, variable, placeholder)
        entry.pack(fill="x")
        return entry

    def _movie(self):
        self.movie_card = Card(self.content, "◆  NOW PLAYING", "Choose the film",
                               "Search nearby listings or type any title.", T.purple)
        row = ctk.CTkFrame(self.movie_card, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12)); row.grid_columnconfigure(0, weight=1)
        self.movie_combo = ctk.CTkComboBox(row, variable=self.movie,
            values=self.movie_options or [self.movie.get()], height=48, corner_radius=11,
            fg_color=T.field, border_width=2, border_color="#8D43B4", text_color=T.text,
            button_color="#5A2479", button_hover_color="#75319B",
            dropdown_fg_color=T.raised, dropdown_text_color=T.text)
        self.movie_combo.grid(row=0, column=0, sticky="ew")
        self.find_movies_button = ctk.CTkButton(row, text="Find movies", command=self.find_movies,
            width=116, height=48, corner_radius=11, fg_color="#47205E", hover_color="#632C82",
            border_width=2, border_color="#9B4AC4", text_color="#F5DCFF")
        self.find_movies_button.grid(row=0, column=1, padx=(10, 0))
        prefs = ctk.CTkFrame(self.movie_card, fg_color="transparent")
        prefs.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        self._field(prefs, "Seats together", self.seats_required, 0)
        self._field(prefs, "Minimum row", self.minimum_row, 1)

    def _where(self):
        self.where_card = Card(self.content, "◎  NEARBY", "Choose the neighborhood",
                               "Set the search zone, then curate the theater lineup.", T.cyan)
        row = ctk.CTkFrame(self.where_card, fg_color="transparent")
        row.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 10)); row.grid_columnconfigure(0, weight=1)
        self.location_entry = self._entry(row, self.location_query, "City, ZIP code, or address")
        self.location_entry.grid(row=0, column=0, sticky="ew")
        self.use_location_button = ctk.CTkButton(row, text="Use location", command=self.use_my_location,
            width=108, height=46, corner_radius=11, fg_color="#104156", hover_color="#175C78",
            border_width=1, border_color="#2787A6", text_color="#D3F8FF")
        self.use_location_button.grid(row=0, column=1, padx=(8, 0))
        self.find_theaters_button = ctk.CTkButton(row, text="Find theaters", command=self.find_theaters,
            width=108, height=46, corner_radius=11, fg_color=T.cyan, hover_color=T.cyan_hover,
            text_color="#061117", font=ctk.CTkFont(size=11, weight="bold"))
        self.find_theaters_button.grid(row=0, column=2, padx=(8, 0))
        prefs = ctk.CTkFrame(self.where_card, fg_color="transparent")
        prefs.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 10))
        self._field(prefs, "Radius (miles)", self.search_radius, 0)
        fmt = ctk.CTkFrame(prefs, fg_color="transparent"); fmt.grid(row=0, column=1, sticky="ew"); prefs.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(fmt, text="FORMAT", text_color=T.dim, font=ctk.CTkFont(size=9, weight="bold")).pack(anchor="w", pady=(0, 5))
        self.format_combo = ctk.CTkComboBox(fmt, variable=self.format,
            values=["ANY", "IMAX 70MM", "IMAX", "70MM", "DOLBY", "PRIME", "LASER"],
            height=42, corner_radius=10, fg_color=T.field, border_color=T.border_hi,
            button_color="#183D4A", button_hover_color="#225565", text_color=T.text)
        self.format_combo.pack(fill="x")
        self.theater_summary_button = ctk.CTkButton(self.where_card, text="Theaters selected  ›",
            command=self.toggle_theaters, height=40, corner_radius=10, anchor="w",
            fg_color=T.raised, hover_color="#202838", text_color=T.cyan)
        self.theater_summary_button.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 16))
        self.theater_panel = ctk.CTkFrame(self.where_card, fg_color=T.field, corner_radius=12,
                                          border_width=1, border_color=T.border)
        self.theater_panel.grid(row=5, column=0, sticky="ew", padx=20, pady=(0, 18)); self.theater_panel.grid_columnconfigure(0, weight=1)
        self.theater_grid = ctk.CTkFrame(self.theater_panel, fg_color="transparent")
        self.theater_grid.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.theater_grid.grid_columnconfigure((0, 1), weight=1)
        self.render_theaters(); self.theater_panel.grid_remove()

    def _when(self):
        self.when_card = Card(self.content, "◷  SHOW WINDOW", "Set the moment",
                              "Choose a date strategy and the hours worth watching.", "#7488FF")
        self.date_mode_control = ctk.CTkSegmentedButton(self.when_card, variable=self.date_mode,
            values=["NEXT BEST", "SPECIFIC DATE", "DATE RANGE"], command=self.on_date_mode_change,
            height=44, corner_radius=11, fg_color=T.field, selected_color="#697CFF",
            selected_hover_color=T.purple_hover, unselected_color=T.raised,
            unselected_hover_color="#252E40", text_color=T.text)
        self.date_mode_control.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 12))
        self.date_fields = ctk.CTkFrame(self.when_card, fg_color="transparent")
        self.date_fields.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 12)); self.date_fields.grid_columnconfigure((0, 1), weight=1)
        self.date_start_entry = self._entry(self.date_fields, self.date_start, "MM/DD/YYYY")
        self.date_start_entry.grid(row=0, column=0, sticky="ew", padx=(0, 5))
        self.date_end_entry = self._entry(self.date_fields, self.date_end, "MM/DD/YYYY")
        self.date_end_entry.grid(row=0, column=1, sticky="ew", padx=(5, 0))
        times = ctk.CTkFrame(self.when_card, fg_color="transparent")
        times.grid(row=4, column=0, sticky="ew", padx=20, pady=(0, 20))
        self._field(times, "After", self.earliest_time, 0, "1:00pm")
        self._field(times, "Before", self.latest_time, 1, "7:15pm")

    def _advanced(self):
        self.advanced_wrap = ctk.CTkFrame(self.content, fg_color="transparent"); self.advanced_wrap.grid_columnconfigure(0, weight=1)
        self.advanced_button = ctk.CTkButton(self.advanced_wrap, text="More options  +",
            command=self.toggle_advanced, height=34, anchor="w", fg_color="transparent",
            hover_color=T.surface, text_color=T.dim)
        self.advanced_button.grid(row=0, column=0, sticky="ew")
        self.advanced_card = ctk.CTkFrame(self.advanced_wrap, fg_color=T.surface, corner_radius=12,
                                          border_width=1, border_color=T.border)
        self.advanced_card.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        inner = ctk.CTkFrame(self.advanced_card, fg_color="transparent"); inner.pack(fill="x", padx=14, pady=14)
        self._field(inner, "Check interval", self.check_interval, 0)
        ctk.CTkSwitch(inner, text="Sound alert", variable=self.sound_alert, progress_color=T.purple, text_color=T.soft).grid(row=0, column=1, padx=12)
        ctk.CTkSwitch(inner, text="Open browser", variable=self.open_browser, progress_color=T.cyan, text_color=T.soft).grid(row=0, column=2)
        self.advanced_card.grid_remove()

    def _action(self):
        self.action_card = ctk.CTkFrame(self.content, fg_color="#26113A", corner_radius=18,
                                        border_width=2, border_color=T.purple)
        self.action_card.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.action_card, text="AUTOMATION ARMED", text_color=T.cyan,
                     font=ctk.CTkFont(size=9, weight="bold")).grid(row=0, column=0, sticky="w", padx=18, pady=(15, 0))
        ctk.CTkLabel(self.action_card, text="Let Movies watch", text_color=T.text,
                     font=ctk.CTkFont(size=20, weight="bold")).grid(row=1, column=0, sticky="w", padx=18, pady=(4, 2))
        ctk.CTkLabel(self.action_card, text="Continuous checks. Ranked seats. Instant handoff.",
                     text_color="#CDB4DD", font=ctk.CTkFont(size=10)).grid(row=2, column=0, sticky="w", padx=18, pady=(0, 12))
        buttons = ctk.CTkFrame(self.action_card, fg_color="transparent")
        buttons.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14)); buttons.grid_columnconfigure(0, weight=1)
        self.start_button = ctk.CTkButton(buttons, text="START WATCHING", command=self.start,
            height=54, corner_radius=13, fg_color=T.purple, hover_color=T.purple_hover,
            border_width=2, border_color="#F0B8FF",
            font=ctk.CTkFont(size=12, weight="bold"))
        self.start_button.grid(row=0, column=0, sticky="ew")
        self.stop_button = ctk.CTkButton(buttons, text="Stop", command=self.stop, state="disabled",
            width=62, height=48, corner_radius=11, fg_color="#321C25", hover_color="#462632", text_color="#F2B5C2")
        self.stop_button.grid(row=0, column=1, padx=(8, 0))
        self.open_button = ctk.CTkButton(buttons, text="Open seats", command=self.open_best_match,
            state="disabled", width=84, height=48, corner_radius=11, fg_color="#15392C",
            hover_color="#1D503D", text_color="#8AF0BE")
        self.open_button.grid(row=0, column=2, padx=(8, 0))

    def _status(self):
        self.result_card = Card(self.content, "●  LIVE SIGNAL", "Watch activity",
                                "Every cycle, candidate, and winning seat at a glance.", T.green)
        self.result_main = ctk.CTkLabel(self.result_card, text="Not currently watching",
            justify="left", anchor="w", text_color=T.text, font=ctk.CTkFont(size=18, weight="bold"))
        self.result_main.grid(row=2, column=0, sticky="ew", padx=20)
        self.result_sub = ctk.CTkLabel(self.result_card,
            text="Choose a movie, location, and time window to begin.", justify="left",
            anchor="w", wraplength=360, text_color=T.dim, font=ctk.CTkFont(size=11))
        self.result_sub.grid(row=3, column=0, sticky="ew", padx=20, pady=(5, 14))
        stats = ctk.CTkFrame(self.result_card, fg_color=T.field, corner_radius=12)
        stats.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 10))
        for i in range(4): stats.grid_columnconfigure(i, weight=1)
        for i, (label, variable) in enumerate((("CYCLE", self.cycle_text), ("SHOWTIMES", self.showtime_text),
                                               ("GROUPS", self.groups_text), ("LAST", self.last_cycle_text))):
            box = ctk.CTkFrame(stats, fg_color="transparent"); box.grid(row=0, column=i, sticky="ew", pady=9)
            ctk.CTkLabel(box, textvariable=variable, text_color=T.cyan if i in (1, 2) else T.purple,
                         font=ctk.CTkFont(size=14, weight="bold")).pack()
            ctk.CTkLabel(box, text=label, text_color=T.dim, font=ctk.CTkFont(size=8, weight="bold")).pack()
        self.details_button = ctk.CTkButton(self.result_card, text="Activity  ›", command=self.toggle_details,
            height=32, fg_color="transparent", hover_color=T.raised, text_color=T.cyan)
        self.details_button.grid(row=5, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.details_card = ctk.CTkFrame(self.content, fg_color=T.surface, corner_radius=14,
                                         border_width=1, border_color=T.border)
        self.log = ctk.CTkTextbox(self.details_card, height=210, wrap="word", fg_color=T.field,
                                  text_color=T.soft, font=("Consolas", 10), corner_radius=10)
        self.log.pack(fill="both", expand=True, padx=12, pady=12); self.log.configure(state="disabled")
        self.details_card.grid_remove()

    def _bind_mac_scrolling(self):
        """Add the Tk 9 precision-trackpad path without double-binding MouseWheel.

        CustomTkinter already owns <MouseWheel>. On macOS with Tk 9, Apple
        precision trackpads emit <TouchpadScroll> instead. Binding MouseWheel
        here as well can make ordinary wheel input fire twice.
        """
        if sys.platform != "darwin":
            return
        try:
            self.root.bind_all("<TouchpadScroll>", self._on_mac_touchpad_scroll, add="+")
        except tk.TclError:
            # Tk 8.6 does not know TouchpadScroll; CustomTkinter's MouseWheel
            # handler remains the fallback.
            pass

    @staticmethod
    def _signed_16(value):
        value &= 0xFFFF
        return value - 0x10000 if value & 0x8000 else value

    @classmethod
    def _decode_touchpad_delta(cls, raw_delta):
        """Decode Tk 9's packed TouchpadScroll %D value as (dx, dy)."""
        raw = int(raw_delta or 0) & 0xFFFFFFFF
        dx = cls._signed_16(raw >> 16)
        dy = cls._signed_16(raw)
        return dx, dy

    def _event_targets_log(self, widget):
        log_widgets = {
            self.log,
            getattr(self.log, "_textbox", None),
        }
        current = widget
        while current is not None:
            if current in log_widgets:
                return True
            current = getattr(current, "master", None)
        return False

    def _on_mac_touchpad_scroll(self, event):
        try:
            _, delta_y = self._decode_touchpad_delta(getattr(event, "delta", 0))
        except Exception:
            return None

        if not delta_y:
            return None

        try:
            if self._event_targets_log(getattr(event, "widget", None)):
                target = getattr(self.log, "_textbox", self.log)
                target.yview_scroll(delta_y, "units")
            else:
                canvas = getattr(self.outer_frame, "_parent_canvas", None)
                if canvas is None:
                    return None
                canvas.yview_scroll(delta_y, "units")
            return "break"
        except Exception:
            return None

    def start(self):
        # During live validation, make activity visible automatically so a
        # completed no-match search cannot look like a silent failure.
        try:
            self.details_visible = True
            self.details_card.grid()
            self.details_button.configure(text="Hide activity")
        except Exception:
            pass
        return super().start()

    def _draw_ambient_background(self):
        """Cinematic light field behind the product shell."""
        if not hasattr(self, "ambient_canvas"):
            return
        c = self.ambient_canvas
        c.delete("ambient")
        w, h = max(1, c.winfo_width()), max(1, c.winfo_height())

        # Hard-edged concentric fields read like colored bloom in Tk, which
        # has no alpha channel or blur support.
        for scale, color in ((.72, "#130822"), (.55, "#210B37"),
                             (.39, "#32104E"), (.24, "#481569")):
            rx, ry = int(w * scale), int(h * scale * .55)
            c.create_oval(-rx, -ry, rx * 2, ry * 2, fill=color, outline="", tags="ambient")
        for scale, color in ((.68, "#031924"), (.50, "#05293A"),
                             (.34, "#073C55"), (.20, "#095673")):
            rx, ry = int(w * scale), int(h * scale * .55)
            c.create_oval(w - rx * 2, h - ry * 2, w + rx, h + ry,
                          fill=color, outline="", tags="ambient")

        # Center stage and perspective rails give the shell a physical plane.
        c.create_rectangle(0, int(h * .26), w, int(h * .78),
                           fill="#050914", outline="", tags="ambient")
        cx = w // 2
        for offset, color, width in ((650, "#263351", 2), (690, "#123C50", 1),
                                     (730, "#37154E", 1)):
            c.create_line(cx-offset, 0, cx-offset, h, fill=color, width=width, tags="ambient")
            c.create_line(cx+offset, 0, cx+offset, h, fill=color, width=width, tags="ambient")
        c.create_line(0, int(h*.26), w, int(h*.26), fill="#3B2058", width=1, tags="ambient")
        c.create_line(0, int(h*.78), w, int(h*.78), fill="#0E485E", width=1, tags="ambient")
        c.tag_lower("ambient")

    def _apply_responsive_width(self):
        if not hasattr(self, "content"): return
        width = max(1, self.root.winfo_width())
        mode = "wide" if width >= 1040 else "compact"
        margin = max(12, (width - min(1180, width - 24)) // 2)
        self.app_shell.grid_configure(padx=margin)
        self.shell_shadow.grid_configure(padx=max(8, margin - 6))
        if mode == self._layout_mode: return
        self._layout_mode = mode
        widgets = (self.header, self.movie_card, self.where_card, self.when_card,
                   self.advanced_wrap, self.action_card, self.result_card, self.details_card)
        for widget in widgets: widget.grid_forget()
        if mode == "wide":
            self.content.grid_columnconfigure(0, weight=3); self.content.grid_columnconfigure(1, weight=2, minsize=350)
            self.header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
            self.movie_card.grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
            self.where_card.grid(row=2, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
            self.when_card.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(0, 12))
            self.advanced_wrap.grid(row=4, column=0, sticky="ew", padx=(0, 8))
            self.action_card.grid(row=1, column=1, sticky="new", padx=(8, 0))
            self.result_card.grid(row=2, column=1, sticky="new", padx=(8, 0))
            self.details_card.grid(row=3, column=1, rowspan=2, sticky="nsew", padx=(8, 0))
        else:
            self.content.grid_columnconfigure(0, weight=1); self.content.grid_columnconfigure(1, weight=0, minsize=0)
            for row, widget in enumerate(widgets): widget.grid(row=row, column=0, sticky="ew", pady=(0, 12))
        if not self.details_visible: self.details_card.grid_remove()


if __name__ == "__main__":
    root = ctk.CTk()
    SeatWatcherPremiumGUI(root)
    root.mainloop()
