"""Tkinter toast window — screen bottom-right, dark theme, three action buttons.

Design decisions:
  - Dynamic height: window resizes based on command length (capped at 500 px).
  - Draggable: drag by the title bar (overrideredirect windows have no chrome).
  - Buttons always visible: scrollable command card if content exceeds cap.
"""

from __future__ import annotations

import tkinter as tk
from typing import Literal

ToastResult = Literal["deny", "allow_once", "allow_session", "timeout"]

WINDOW_WIDTH = 420
MAX_HEIGHT = 500
MARGIN = 20


def show_toast(
    tool: str,
    command: str,
    cwd: str,
    timeout_seconds: int = 30,
) -> ToastResult:
    """Display a permission toast at screen bottom-right. Block until user acts."""
    result: ToastResult = "deny"

    win = tk.Tk()
    win.title("")
    win.overrideredirect(True)
    win.attributes("-topmost", True)
    win.resizable(False, False)

    # ── Dark theme colours ──
    BG = "#252526"
    FG = "#e0e0e0"
    ACCENT = "#0e639c"
    SUCCESS = "#16825d"
    DANGER = "#555555"
    CARD_BG = "#1a1a1a"
    BORDER = "#3c3c3c"
    CODE_COLOR = "#ce9178"
    LABEL_COLOR = "#888888"

    win.configure(bg=BG)

    # ── Drag support ──
    _drag_data = {"x": 0, "y": 0}

    def _drag_start(e: tk.Event) -> None:
        _drag_data["x"] = e.x_root
        _drag_data["y"] = e.y_root

    def _drag_move(e: tk.Event) -> None:
        dx = e.x_root - _drag_data["x"]
        dy = e.y_root - _drag_data["y"]
        _drag_data["x"] = e.x_root
        _drag_data["y"] = e.y_root
        wx = win.winfo_x() + dx
        wy = win.winfo_y() + dy
        win.geometry(f"+{wx}+{wy}")

    def _make_draggable(w: tk.Widget) -> None:
        w.bind("<ButtonPress-1>", _drag_start)
        w.bind("<B1-Motion>", _drag_move)

    # ── Title bar ──
    title_frame = tk.Frame(win, bg=BG, height=36)
    title_frame.pack(fill="x", padx=14, pady=(10, 0))
    _make_draggable(title_frame)

    # Indicator dot
    dot = tk.Canvas(title_frame, width=10, height=10, bg=BG, highlightthickness=0)
    dot.create_oval(2, 2, 10, 10, fill="#ff6b6b", outline="")
    dot.pack(side="left", padx=(0, 8))

    title_label = tk.Label(
        title_frame,
        text="Permission Request",
        fg=FG,
        bg=BG,
        font=("Segoe UI", 11, "bold"),
    )
    title_label.pack(side="left")

    close_btn = tk.Label(
        title_frame,
        text="×",
        fg="#555555",
        bg=BG,
        font=("Segoe UI", 16),
        cursor="hand2",
    )
    close_btn.pack(side="right")
    close_btn.bind("<Button-1>", lambda e: _close(win, "deny"))

    # ── Info row ──
    info_frame = tk.Frame(win, bg=BG)
    info_frame.pack(fill="x", padx=14, pady=(6, 0))

    tool_tag = tk.Label(
        info_frame,
        text="Tool",
        fg="#569cd6",
        bg=BG,
        font=("Segoe UI", 9, "bold"),
    )
    tool_tag.pack(side="left", padx=(0, 4))

    tool_val = tk.Label(
        info_frame,
        text=tool,
        fg=LABEL_COLOR,
        bg=BG,
        font=("Segoe UI", 9),
    )
    tool_val.pack(side="left", padx=(0, 12))

    sep = tk.Label(info_frame, text="|", fg="#444444", bg=BG)
    sep.pack(side="left", padx=(0, 12))

    dir_val = tk.Label(
        info_frame,
        text=("…" + cwd[-60:] if len(cwd) > 60 else cwd),
        fg=LABEL_COLOR,
        bg=BG,
        font=("Segoe UI", 9),
    )
    dir_val.pack(side="left")

    # ── Command preview — scrollable when tall ──
    card = tk.Frame(win, bg=CARD_BG, highlightbackground=BORDER, highlightthickness=1)
    card.pack(fill="x", padx=14, pady=(8, 0))

    # Use Text widget so it scrolls if needed
    cmd_text = tk.Text(
        card,
        fg=CODE_COLOR,
        bg=CARD_BG,
        font=("Consolas", 11),
        wrap="word",
        relief="flat",
        bd=0,
        highlightthickness=0,
        height=1,
        padx=10,
        pady=10,
        spacing3=2,
    )
    cmd_text.insert("1.0", command)
    cmd_text.config(state="disabled")

    # Compute required height for the text content
    line_count = int(cmd_text.index("end-1c").split(".")[0])
    char_width = 11  # approximate monospace char width at 11pt
    chars_per_line = max(1, (WINDOW_WIDTH - 60) // char_width)
    wrapped_lines = sum(
        max(1, (len(line) + chars_per_line - 1) // chars_per_line)
        for line in command.split("\n")
    )

    visible_lines = min(wrapped_lines, 14)  # cap for scrolling
    if wrapped_lines <= 14:
        cmd_text.config(height=visible_lines)
        cmd_text.pack(fill="x", side="top")
    else:
        cmd_text.config(height=14)
        cmd_text.pack(fill="both", side="left", expand=True)
        scrollbar = tk.Scrollbar(
            card,
            orient="vertical",
            command=cmd_text.yview,
            bg=CARD_BG,
            troughcolor=BG,
        )
        scrollbar.pack(side="right", fill="y")
        cmd_text.config(yscrollcommand=scrollbar.set)

    # ── Button row ──
    btn_frame = tk.Frame(win, bg=BG)
    btn_frame.pack(fill="x", padx=14, pady=(10, 10))

    # Reject
    reject_btn = tk.Button(
        btn_frame,
        text="Reject",
        bg=DANGER,
        fg="#cccccc",
        activebackground="#666666",
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        font=("Segoe UI", 10),
        cursor="hand2",
        command=lambda: _close(win, "deny"),
    )
    reject_btn.pack(side="right", padx=(6, 0))

    # Allow Session
    sess_btn = tk.Button(
        btn_frame,
        text="Allow Session",
        bg=SUCCESS,
        fg="#ffffff",
        activebackground="#1a9b6d",
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        font=("Segoe UI", 10),
        cursor="hand2",
        command=lambda: _close(win, "allow_session"),
    )
    sess_btn.pack(side="right", padx=(6, 0))

    # Allow Once (default focused)
    allow_btn = tk.Button(
        btn_frame,
        text="Allow Once",
        bg=ACCENT,
        fg="#ffffff",
        activebackground="#1a85d6",
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        padx=16,
        pady=4,
        font=("Segoe UI", 10),
        cursor="hand2",
        command=lambda: _close(win, "allow_once"),
    )
    allow_btn.pack(side="right", padx=(6, 0))
    allow_btn.focus_set()

    # ── Keyboard bindings ──
    win.bind("<Escape>", lambda e: _close(win, "deny"))
    win.bind("<Return>", lambda e: _close(win, "allow_once"))
    win.bind("<Alt-s>", lambda e: _close(win, "allow_session"))
    win.bind("<Alt-r>", lambda e: _close(win, "deny"))
    win.bind("<Alt-o>", lambda e: _close(win, "allow_once"))

    # ── Timeout ──
    def on_timeout() -> None:
        _close(win, "timeout")

    win._timeout_id = win.after(timeout_seconds * 1000, on_timeout)

    # ── Close helper ──
    def _close(w: tk.Tk, value: ToastResult) -> None:
        nonlocal result
        result = value
        tid = getattr(w, "_timeout_id", None)
        if tid:
            w.after_cancel(tid)
        w.destroy()

    # ── Dynamic window height ──
    win.update_idletasks()
    req_height = win.winfo_reqheight()
    final_h = min(req_height, MAX_HEIGHT)
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = sw - WINDOW_WIDTH - MARGIN
    y = sh - final_h - MARGIN
    win.geometry(f"{WINDOW_WIDTH}x{final_h}+{x}+{y}")
    # If content exceeds max height, let the card expand to fill
    if req_height > MAX_HEIGHT:
        card.pack_configure(fill="both", expand=True)

    # ── Trap interaction: grab all input ──
    win.grab_set()
    win.wait_window()

    return result
