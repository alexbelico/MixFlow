"""
MixFlow GUI — réplica fiel de los mockups MEZCLA + STEMS.
Sin consola. Negro / rojo puro / blanco. Logo AM + Bebas Neue.
"""
from __future__ import annotations

import os, threading, copy, shutil, traceback, json, math, time
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, font as tkfont

os.environ["MIXFLOW_NO_HUD"] = "1"
os.environ["MIXFLOW_GUI"] = "1"
import MixFlowAssistant as m

ROOT_DIR = Path(__file__).resolve().parent
ASSETS = ROOT_DIR / "assets"
LOGO_PNG = ASSETS / "logo_am.png"
LOGO_SM = ASSETS / "logo_am_sm.png"
BEBAS_TTF = ASSETS / "fonts" / "BebasNeue-Regular.ttf"

# ——— Paleta: rojo oscuro intenso (no naranja) ———
BG = "#000000"
CARD = "#121212"
CARD_BORDER = "#2C2C2C"
FG = "#FFFFFF"
MUTED = "#A3A3A3"
MUTED2 = "#6B6B6B"
RED = "#B71C1C"          # dark red
RED_SOFT = "#E53935"
RED_DIM = "#8B0000"
BTN_DARK = "#0A0A0A"
INPUT_BG = "#0A0A0A"
DIV = "#2A2A2A"
TITLEBAR = "#0D0D0D"     # barra superior oscura 3D
TITLEBAR_HI = "#2A2A2A"  # highlight 3D
TITLEBAR_LO = "#050505"  # sombra 3D

BEBAS = "Bebas Neue"
CREDIT_FONT = (BEBAS, 14)  # más grande, legible, espaciado
TITLE_FONT = ("Segoe UI Black", 30)


def _register_bebas():
    """Registra Bebas Neue para Tk (Windows AddFontResourceEx)."""
    global CREDIT_FONT, BEBAS
    if not BEBAS_TTF.exists():
        CREDIT_FONT = ("Impact", 14)
        BEBAS = "Impact"
        return
    try:
        import ctypes
        gdi = ctypes.windll.gdi32
        FR_PRIVATE = 0x10
        gdi.AddFontResourceExW(str(BEBAS_TTF), FR_PRIVATE, 0)
        for name in ("Bebas Neue", "BebasNeue", "Bebas Neue Regular"):
            try:
                f = tkfont.Font(family=name, size=14)
                fam = f.actual("family")
                if "bebas" in fam.lower().replace(" ", ""):
                    BEBAS = fam
                    CREDIT_FONT = (BEBAS, 14)
                    return
            except Exception:
                pass
        BEBAS = "Bebas Neue"
        CREDIT_FONT = (BEBAS, 14)
    except Exception:
        CREDIT_FONT = ("Impact", 14)
        BEBAS = "Impact"

AUDIO_TYPES = [
    ("Audio", "*.wav *.flac *.mp3 *.m4a *.aac *.ogg *.aiff *.aif *.wma"),
    ("WAV", "*.wav"), ("FLAC", "*.flac"), ("MP3", "*.mp3"), ("Todos", "*.*"),
]

STEM_DISPLAY = {
    "Beat": "BEAT",
    "Voz principal — Versos": "MAIN VOCAL",
    "Voz principal — Coros": "CHORUS",
    "Segunda voz — Versos": "MAIN VOCAL",
    "Segunda voz — Coros": "CHORUS",
    "Backs / Remarques": "BACKS",
    "Adlibs": "ADLIBS",
    "Remarques": "REMARQUES",
    "Alignment / Referencia": "REF",
}

STEM_REASSIGN = [
    "Beat", "Voz principal — Versos", "Voz principal — Coros",
    "Backs / Remarques", "Adlibs", "Remarques", "Alignment / Referencia",
]


def _hide_console():
    """Oculta y libera cualquier consola adjunta (evita ventana negra)."""
    if os.name != "nt":
        return
    try:
        import ctypes
        k32 = ctypes.windll.kernel32
        u32 = ctypes.windll.user32
        hwnd = k32.GetConsoleWindow()
        if hwnd:
            u32.ShowWindow(hwnd, 0)  # SW_HIDE
        try:
            k32.FreeConsole()
        except Exception:
            pass
    except Exception:
        pass


# Liberar consola lo antes posible al importar el módulo GUI
_hide_console()


def _fmt_time(sec):
    try:
        sec = max(0.0, float(sec))
    except (TypeError, ValueError):
        return "0:00"
    return f"{int(sec // 60)}:{int(sec % 60):02d}"


def _fmt_tc(sec):
    try:
        sec = max(0.0, float(sec))
    except (TypeError, ValueError):
        return "00:00.000"
    m, s = int(sec // 60), int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    return f"{m:02d}:{s:02d}.{ms:03d}"


def _sf(v, d=None):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _stem_label(cat):
    return STEM_DISPLAY.get(cat, (cat or "STEM").upper()[:14])


class MixFlowApp:
    def __init__(self):
        self.root = tk.Tk()
        _register_bebas()
        self.root.title("MixFlow")
        self.root.geometry("920x820+30+10")
        self.root.minsize(820, 720)
        self.root.configure(bg=BG)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(80, self._apply_dark_titlebar)

        self._busy = False
        self._mode = None
        self.src = None
        self.analysis = None
        self.preview_analysis = None
        self.target = -10.0
        self.tmp = None
        self.current = None
        self.base_filters = []
        self.history = [[]]
        self.before_snapshot = None
        self.duration_s = 0.0
        self.play_pos = 0.0
        self._play_tick = None
        self._seek_dragging = False
        self.preview_versions = []  # A/B/C paths
        self.output_sr = None
        self.presets_path = m.OUT_ROOT / "_presets.json"
        self._logo_img = None
        self._logo_img_sm = None
        self._wave_env = None  # list of float 0..1
        self._wave_canvas = None
        self._live_lufs_lbl = None
        self._wave_anim_phase = 0.0
        self._header_wave = None

        # STEMS
        self.stem_files = []
        self.classified = {}
        self.sources = {}
        self.settings = {}
        self.accepted_settings = {}
        self.stem_history = []
        self.last_target_stem = None
        self._stem_tab = "STEMS"
        self._align_reports = {}
        self._manual_offsets = {}

        self._build_shell()
        self._enable_dnd()
        self.show_home()

    def _load_logo_images(self):
        try:
            from PIL import Image, ImageTk
            path = LOGO_PNG if LOGO_PNG.exists() else LOGO_SM
            if not path.exists():
                return
            im = Image.open(path).convert("RGBA")
            # Logo AM aún más grande a la izquierda de MIXFLOW (mantiene proporción)
            target_h = 118
            ratio = target_h / max(1, im.height)
            tw = max(96, int(im.width * ratio))
            self._logo_img = ImageTk.PhotoImage(
                im.resize((tw, target_h), Image.Resampling.LANCZOS))
            sm_h = 64
            sm_w = max(56, int(im.width * (sm_h / max(1, im.height))))
            self._logo_img_sm = ImageTk.PhotoImage(
                im.resize((sm_w, sm_h), Image.Resampling.LANCZOS))
        except Exception:
            try:
                if LOGO_PNG.exists():
                    self._logo_img = tk.PhotoImage(file=str(LOGO_PNG))
                    self._logo_img_sm = self._logo_img
            except Exception:
                self._logo_img = None

    def _apply_dark_titlebar(self):
        """Barra de título de Windows más oscura (DWM)."""
        if os.name != "nt":
            return
        try:
            import ctypes
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            # 20 = DWMWA_USE_IMMERSIVE_DARK_MODE (Win10 1809+), 19 = legacy
            val = ctypes.c_int(1)
            for attr in (20, 19):
                try:
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(
                        hwnd, attr, ctypes.byref(val), ctypes.sizeof(val))
                except Exception:
                    pass
        except Exception:
            pass

    # ========== SHELL ==========
    def _build_shell(self):
        self._load_logo_images()
        # Barra superior oscura con relieve 3D
        self.titlebar = tk.Frame(self.root, bg=TITLEBAR, height=10)
        self.titlebar.pack(fill="x")
        self.titlebar.pack_propagate(False)
        tk.Frame(self.titlebar, bg=TITLEBAR_HI, height=1).pack(fill="x", side="top")
        tk.Frame(self.titlebar, bg=TITLEBAR_LO, height=2).pack(fill="x", side="bottom")

        # Márgenes superiores más compactos → contenido más arriba
        self.header = tk.Frame(self.root, bg=TITLEBAR, padx=28, pady=10)
        self.header.pack(fill="x")
        # bisel inferior del header (look 3D)
        tk.Frame(self.root, bg=TITLEBAR_HI, height=1).pack(fill="x")
        tk.Frame(self.root, bg=TITLEBAR_LO, height=2).pack(fill="x")

        self.brand_row = tk.Frame(self.header, bg=TITLEBAR)
        self.brand_row.pack(fill="x")

        self.brand_left = tk.Frame(self.brand_row, bg=TITLEBAR)
        self.brand_left.pack(side="left", anchor="center")

        self.logo_lbl = tk.Label(self.brand_left, bg=TITLEBAR, bd=0)
        if self._logo_img is not None:
            self.logo_lbl.configure(image=self._logo_img)
        self.logo_lbl.pack(side="left", padx=(0, 16))

        self.title_block = tk.Frame(self.brand_left, bg=TITLEBAR)
        self.title_block.pack(side="left")
        tk.Label(self.title_block, text="MIXFLOW", fg=FG, bg=TITLEBAR,
                 font=TITLE_FONT).pack(anchor="w")
        # Bebas Neue: más grande + tracking visual con espacios
        self.cred_lbl = tk.Label(self.title_block, text="C R E A T E D   B Y   A L E X M O E T",
                                 fg=RED, bg=TITLEBAR, font=CREDIT_FONT)
        self.cred_lbl.pack(anchor="w", pady=(4, 0))

        self.header_right = tk.Frame(self.brand_row, bg=TITLEBAR)
        self.header_right.pack(side="right", anchor="center")

        self.line_canvas = tk.Canvas(self.header, height=2, bg=TITLEBAR, highlightthickness=0)
        self.line_canvas.pack(fill="x", pady=(10, 0))
        self.line_canvas.bind("<Configure>", lambda e: self._paint_line())
        self.nav = tk.Frame(self.root, bg=BG, padx=28, pady=0)
        self.nav.pack(fill="x")
        self._inicio_btn = tk.Button(
            self.nav, text="← Inicio", command=self.show_home,
            bg=BG, fg=MUTED, activebackground=BG, activeforeground=FG,
            relief="flat", bd=0, padx=0, pady=2,
            font=("Segoe UI", 9), cursor="hand2", anchor="w")
        self._inicio_btn.pack(side="left")

        # Status más visible
        self.status_frame = tk.Frame(self.root, bg=BG, padx=28)
        self.status_frame.pack(fill="x")
        self.var_stage = tk.StringVar(value="")
        self.var_detail = tk.StringVar(value="")
        self.stage_lbl = tk.Label(self.status_frame, textvariable=self.var_stage, fg=FG, bg=BG,
                                  font=("Segoe UI Semibold", 11), anchor="w")
        self.stage_lbl.pack(fill="x")
        self.prog_canvas = tk.Canvas(self.status_frame, height=4, bg="#151515", highlightthickness=0)
        self.prog_canvas.pack(fill="x", pady=(2, 0))
        self._prog_max, self._prog_val = 1, 0
        self.detail_lbl = tk.Label(self.status_frame, textvariable=self.var_detail, fg=MUTED, bg=BG,
                                   font=("Segoe UI", 10), anchor="w", wraplength=860)
        self.detail_lbl.pack(fill="x")

        # Body con scrollbar vertical
        scroll_wrap = tk.Frame(self.root, bg=BG)
        scroll_wrap.pack(fill="both", expand=True, padx=0, pady=0)
        self._scroll_canvas = tk.Canvas(scroll_wrap, bg=BG, highlightthickness=0)
        self._vscroll = tk.Scrollbar(scroll_wrap, orient="vertical", command=self._scroll_canvas.yview,
                                    bg=BG, troughcolor="#1A1A1A", activebackground=RED)
        self._scroll_canvas.configure(yscrollcommand=self._vscroll.set)
        self._vscroll.pack(side="right", fill="y")
        self._scroll_canvas.pack(side="left", fill="both", expand=True)
        self.body = tk.Frame(self._scroll_canvas, bg=BG, padx=28, pady=2)
        self._body_win = self._scroll_canvas.create_window((0, 0), window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._on_body_configure)
        self._scroll_canvas.bind("<Configure>", self._on_scroll_configure)
        self.root.bind_all("<MouseWheel>", self._on_mousewheel)

        self.foot = tk.Frame(self.root, bg=BG)

    def _on_body_configure(self, _e=None):
        self._scroll_canvas.configure(scrollregion=self._scroll_canvas.bbox("all"))

    def _on_scroll_configure(self, e):
        self._scroll_canvas.itemconfig(self._body_win, width=e.width)

    def _on_mousewheel(self, e):
        try:
            self._scroll_canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        except Exception:
            pass

    def _scroll_top(self):
        try:
            self._scroll_canvas.yview_moveto(0)
        except Exception:
            pass

    def _paint_line(self):
        self.line_canvas.delete("all")
        w = max(self.line_canvas.winfo_width(), 40)
        self.line_canvas.create_rectangle(0, 0, w, 2, fill=RED, outline="")

    def _paint_prog(self):
        self.prog_canvas.delete("all")
        w = max(self.prog_canvas.winfo_width(), 40)
        self.prog_canvas.create_rectangle(0, 0, w, 4, fill="#151515", outline="")
        frac = 0 if self._prog_max <= 0 else min(1.0, self._prog_val / self._prog_max)
        if frac > 0:
            self.prog_canvas.create_rectangle(0, 0, int(w * frac), 4, fill=RED, outline="")

    def set_status(self, stage, step=None, total=None, detail=""):
        self.var_stage.set(stage or "")
        if step is not None and total:
            self._prog_max = max(int(total), 1)
            self._prog_val = max(0, min(int(step), int(total)))
            self.var_stage.set(f"{stage}  ·  {step}/{total}")
        self.var_detail.set((detail or "")[:300])
        self._paint_prog()
        try:
            self.root.update_idletasks()
        except tk.TclError:
            pass

    def _halt_playback(self):
        """Detiene audio + tick del playhead (cambio de pantalla / proceso / export)."""
        try:
            m.stop_playback()
        except Exception:
            pass
        self._stop_tick()

    def _clear_body(self):
        # Al salir de una vista, el audio no debe seguir sonando
        self._halt_playback()
        self._wave_canvas = None
        self._live_lufs_lbl = None
        for w in self.body.winfo_children():
            w.destroy()
        self._scroll_top()

    def _set_header_mode(self, mode):
        """mode: home | mezcla | stems — logo AM siempre visible a la izquierda."""
        for w in self.header_right.winfo_children():
            w.destroy()
        # Logo siempre presente
        if self._logo_img is not None:
            self.logo_lbl.configure(image=self._logo_img)
            if not self.logo_lbl.winfo_ismapped():
                self.logo_lbl.pack(side="left", padx=(0, 14), before=self.title_block)
        self.cred_lbl.config(fg=RED, font=CREDIT_FONT)
        # Waveform rojo siempre arriba a la derecha (rellena el vacío)
        self._header_wave = tk.Canvas(self.header_right, width=168, height=52,
                                      bg=TITLEBAR, highlightthickness=0)
        self._header_wave.pack(side="right", padx=(12, 0))
        self._draw_wf(self._header_wave, h=52, n_bars=28)
        if mode == "stems":
            badge = tk.Frame(self.header_right, bg=TITLEBAR)
            badge.pack(side="right", padx=(0, 10))
            txt = tk.Frame(badge, bg=TITLEBAR)
            txt.pack(side="left")
            tk.Label(txt, text="STEMS", fg=RED, bg=TITLEBAR,
                     font=("Segoe UI Black", 16)).pack(anchor="w")
            tk.Label(txt, text="MODE", fg=FG, bg=TITLEBAR,
                     font=("Segoe UI Semibold", 8)).pack(anchor="w")
            fad = tk.Canvas(badge, width=28, height=28, bg=TITLEBAR, highlightthickness=0)
            fad.pack(side="left", padx=(8, 0))
            for i, x in enumerate((6, 14, 22)):
                fad.create_line(x, 4, x, 24, fill=RED, width=2)
                fad.create_rectangle(x - 3, 8 + i * 3, x + 3, 14 + i * 3, fill=RED, outline="")
        elif mode == "mezcla":
            tk.Label(self.header_right, text="MEZCLA", fg=RED, bg=TITLEBAR,
                     font=("Segoe UI Black", 14)).pack(side="right", padx=(0, 8))

    def _draw_wf(self, c, h=34, n_bars=12):
        c.delete("all")
        import random
        rng = random.Random(42)
        mid = h // 2
        try:
            w = max(int(c.cget("width") or 56), 40)
        except Exception:
            w = 56
        step = max(4, w // max(1, n_bars))
        x = 2
        for i in range(n_bars):
            b = int(6 + (h * 0.38) * abs(math.sin(i * 0.55)) * (0.45 + 0.55 * rng.random()))
            c.create_rectangle(x, mid - b // 2, x + max(2, step - 2), mid + b // 2,
                               fill=RED, outline="")
            x += step

    # ========== WIDGETS ==========
    def _card(self, parent, padx=24, pady=18):
        outer = tk.Frame(parent, bg=CARD_BORDER, padx=1, pady=1)
        inner = tk.Frame(outer, bg=CARD, padx=padx, pady=pady)
        inner.pack(fill="both", expand=True)
        return outer, inner

    def _primary(self, parent, text, cmd, icon="", big=False):
        label = f"{icon}  {text}".strip() if icon else text
        return tk.Button(parent, text=label, command=cmd, bg=RED, fg=FG,
                         activebackground=RED_DIM, activeforeground=FG,
                         relief="flat", bd=0,
                         padx=(28 if big else 14), pady=(18 if big else 11),
                         font=("Segoe UI Semibold", 14 if big else 10), cursor="hand2")

    def _ghost(self, parent, text, cmd, danger=False):
        fg = RED if danger else FG
        return tk.Button(parent, text=text, command=cmd, bg=BTN_DARK, fg=fg,
                         activebackground="#1A1A1A", activeforeground=fg,
                         relief="solid", bd=1, highlightbackground="#3A3A3A",
                         highlightthickness=1, padx=12, pady=10,
                         font=("Segoe UI", 10), cursor="hand2")

    def _red_outline(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, bg=BTN_DARK, fg=RED,
                         activebackground="#1A1A1A", activeforeground=RED,
                         relief="solid", bd=1, highlightbackground=RED,
                         highlightthickness=1, padx=10, pady=10,
                         font=("Segoe UI Semibold", 9), cursor="hand2")

    def _error(self, title, problem, how_to="", actions=None):
        """Error no fatal: explica y ofrece reintentar / cancelar."""
        msg = problem
        if how_to:
            msg += f"\n\nCómo solucionarlo:\n{how_to}"
        if actions:
            # custom dialog
            win = tk.Toplevel(self.root)
            win.title(title)
            win.configure(bg=CARD)
            win.transient(self.root)
            win.grab_set()
            win.geometry("460x260")
            tk.Label(win, text=title, fg=RED, bg=CARD,
                     font=("Segoe UI Semibold", 12)).pack(anchor="w", padx=20, pady=(16, 6))
            tk.Label(win, text=msg, fg=FG, bg=CARD, justify="left", wraplength=400,
                     font=("Segoe UI", 9)).pack(anchor="w", padx=20, pady=6)
            row = tk.Frame(win, bg=CARD)
            row.pack(fill="x", padx=20, pady=16)
            result = {"v": None}

            def pick(k):
                result["v"] = k
                win.destroy()

            for label, key in actions:
                if key == "retry":
                    self._primary(row, label, lambda k=key: pick(k)).pack(side="left", padx=4)
                else:
                    self._ghost(row, label, lambda k=key: pick(k)).pack(side="left", padx=4)
            self.root.wait_window(win)
            return result["v"]
        messagebox.showerror(title, msg, parent=self.root)
        return None

    def _run_bg(self, work, on_ok=None, on_err=None, err_hint=""):
        if self._busy:
            messagebox.showinfo("MixFlow", "Espera a que termine el proceso actual.", parent=self.root)
            return
        # Nuevo proceso (render, export, afinar…) → cortar reproducción en curso
        self._halt_playback()

        def runner():
            self._busy = True
            try:
                result = work()
                self.root.after(0, lambda: self._bg_done(True, result, on_ok, on_err, err_hint))
            except Exception as e:
                tb = traceback.format_exc(limit=4)
                self.root.after(0, lambda: self._bg_done(False, f"{e}\n\n{tb}", on_ok, on_err, err_hint))

        threading.Thread(target=runner, daemon=True).start()

    def _bg_done(self, ok, payload, on_ok, on_err, err_hint):
        self._busy = False
        if ok:
            if on_ok:
                on_ok(payload)
            return
        choice = self._error(
            "Error",
            str(payload)[:900],
            how_to=err_hint or "Revisa el archivo, el espacio en disco y que FFmpeg esté instalado.",
            actions=[("Reintentar", "retry"), ("Cambiar archivo", "file"), ("Cancelar", "cancel")],
        )
        if choice == "retry" and on_err:
            on_err("retry")
        elif choice == "file":
            self.show_home()
        elif on_err:
            on_err(payload)

    def _on_close(self):
        self._halt_playback()
        try:
            if self.before_snapshot is not None:
                m.cleanup_session_outputs(self.before_snapshot)
        except Exception:
            pass
        self.root.destroy()

    def _finish_session(self):
        self._halt_playback()
        try:
            if self.before_snapshot is not None:
                m.cleanup_session_outputs(self.before_snapshot)
        except Exception:
            pass
        self.before_snapshot = None
        self.show_home()

    def _enable_dnd(self):
        # Tk drag-drop via windnd if available; else bind drop events silently
        try:
            import windnd
            windnd.hook_dropfiles(self.root, func=self._on_drop)
        except Exception:
            pass

    def _on_drop(self, files):
        try:
            paths = [Path(f.decode("utf-8") if isinstance(f, bytes) else f) for f in files]
        except Exception:
            return
        paths = [p for p in paths if p.suffix.lower() in
                 {".wav", ".flac", ".mp3", ".m4a", ".aac", ".ogg", ".aiff", ".aif", ".wma"}]
        if not paths:
            return
        if len(paths) == 1:
            self._mode = "mezcla"
            self.src = paths[0]
            self.before_snapshot = m.snapshot_output_files()
            self.set_status("Analizando…", 2, 9, self.src.name)
            self._run_bg(lambda: m.analyze_basic(self.src), on_ok=self._mezcla_after_analysis,
                         err_hint="Prueba otro archivo o convierte a WAV/FLAC.")
        else:
            self._start_stems_with(paths)

    def _versioned_path(self, folder, stem, suffix="_MASTER_FINAL.wav"):
        folder = Path(folder)
        folder.mkdir(parents=True, exist_ok=True)
        base = folder / f"{stem}{suffix}"
        if not base.exists():
            return base
        n = 2
        while True:
            p = folder / f"{stem}{suffix.replace('.wav', f'_v{n}.wav')}"
            if not p.exists():
                return p
            n += 1

    # ========== HOME ==========
    def show_home(self):
        self._halt_playback()
        self._mode = None
        self._set_header_mode("home")
        self.set_status("Listo", detail="Arrastra archivos aquí · MEZCLA (1 archivo) o STEMS (varios)")
        self._clear_body()
        outer, card = self._card(self.body, padx=24, pady=16)
        outer.pack(fill="both", expand=True)
        tk.Label(card, text="Mezcla y mastering local", fg=FG, bg=CARD,
                 font=("Segoe UI Semibold", 16)).pack(anchor="w")
        tk.Label(card, text="Analiza → procesa → preview → feedback → exporta.  "
                 "Originales intactos · 100% local.",
                 fg=MUTED, bg=CARD, font=("Segoe UI", 10), justify="left").pack(anchor="w", pady=(6, 14))

        row = tk.Frame(card, bg=CARD)
        row.pack(fill="x", anchor="w")
        col_m = tk.Frame(row, bg=CARD)
        col_m.pack(side="left", fill="both", expand=True, padx=(0, 14))
        col_s = tk.Frame(row, bg=CARD)
        col_s.pack(side="left", fill="both", expand=True)

        self._primary(col_m, "MEZCLA", self.start_mezcla, "▶", big=True).pack(fill="x")
        tk.Label(col_m,
                 text="Para un archivo estéreo ya mezclado.\n"
                      "Loudness, EQ/dinámica y master con\n"
                      "feedback en lenguaje natural.",
                 fg=MUTED, bg=CARD, font=("Segoe UI", 10), justify="left",
                 wraplength=340).pack(anchor="w", pady=(8, 0))

        tk.Button(
            col_s, text="STEMS", command=self.start_stems, bg=BTN_DARK, fg=RED,
            activebackground="#1A1A1A", activeforeground=RED,
            relief="solid", bd=1, highlightbackground=RED, highlightthickness=1,
            padx=28, pady=18, font=("Segoe UI Semibold", 14), cursor="hand2"
        ).pack(fill="x")
        tk.Label(col_s,
                 text="Para stems separados (voces, beat…).\n"
                      "Mute/Solo/Gain, afinar, alinear y\n"
                      "exportar master + voces procesadas.",
                 fg=MUTED, bg=CARD, font=("Segoe UI", 10), justify="left",
                 wraplength=340).pack(anchor="w", pady=(8, 0))

        # Waveform decorativo en el espacio libre del home
        tk.Label(card, text="Arrastra archivos aquí", fg=FG, bg=CARD,
                 font=("Segoe UI Semibold", 13)).pack(anchor="w", pady=(18, 4))
        tk.Label(card, text="1 archivo = MEZCLA  ·  varios = STEMS  ·  WAV / FLAC / MP3 / M4A / OGG / AIFF",
                 fg=MUTED, bg=CARD, font=("Segoe UI", 10)).pack(anchor="w")
        home_wave = tk.Canvas(card, height=110, bg="#0A0A0A", highlightthickness=0)
        home_wave.pack(fill="x", pady=(12, 0))
        self._draw_home_wave(home_wave)
        home_wave.bind("<Configure>", lambda e: self._draw_home_wave(home_wave))

    def _draw_home_wave(self, c):
        c.delete("all")
        w = max(c.winfo_width(), 200)
        h = max(c.winfo_height(), 80)
        mid = h // 2
        import random
        rng = random.Random(42)
        for i, x in enumerate(range(0, w, 3)):
            amp = 6 + 40 * abs(math.sin(i * 0.09)) * (0.4 + 0.6 * rng.random())
            c.create_line(x, mid - amp, x, mid + amp, fill=RED, width=2)
        c.create_text(w // 2, h - 12, text="MIXFLOW  ·  READY", fill=MUTED2,
                      font=("Segoe UI", 8))

    # ========== MEZCLA STUDIO (mockup 1 — todo dentro de la card) ==========
    def _show_mezcla_studio(self, *, title_file, meta_line, lufs, tp, target, duration,
                            on_accept, on_undo, on_loudness, on_adjust,
                            ab_path=None, ab_label="Original", pending=False, bpm_line=None):
        self._set_header_mode("mezcla")
        self._clear_body()
        outer, card = self._card(self.body, padx=22, pady=16)
        outer.pack(fill="both", expand=True)

        # —— Track header (compacto) ——
        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x")
        ico = tk.Canvas(top, width=34, height=26, bg=CARD, highlightthickness=0)
        ico.pack(side="left", padx=(0, 10))
        self._draw_wf(ico, h=26)
        info = tk.Frame(top, bg=CARD)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=str(title_file).upper(), fg=FG, bg=CARD,
                 font=("Segoe UI Semibold", 12), anchor="w").pack(fill="x")
        tk.Label(info, text=meta_line, fg=MUTED, bg=CARD,
                 font=("Segoe UI", 8), anchor="w").pack(fill="x")
        if pending:
            tk.Label(info, text="AJUSTE PENDIENTE", fg=RED, bg=CARD,
                     font=("Segoe UI Semibold", 8), anchor="w").pack(fill="x")

        tk.Frame(card, bg=DIV, height=1).pack(fill="x", pady=(12, 12))

        # —— Metrics: INTEGRATED | TRUE PEAK | gauge ——
        metrics = tk.Frame(card, bg=CARD)
        metrics.pack(fill="x")

        left = tk.Frame(metrics, bg=CARD)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="INTEGRATED", fg=MUTED, bg=CARD,
                 font=("Segoe UI", 7)).pack(anchor="w")
        tk.Label(left, text=(f"{lufs:.1f} LUFS" if lufs is not None else "— LUFS"),
                 fg=FG, bg=CARD, font=("Segoe UI Black", 30)).pack(anchor="w")
        tgt = "sin normalizar" if target is None else f"{float(target):.1f} LUFS"
        tk.Label(left, text=f"TARGET: {tgt}", fg=RED, bg=CARD,
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(4, 0))
        if bpm_line:
            tk.Label(left, text=bpm_line, fg=MUTED, bg=CARD,
                     font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))

        tk.Frame(metrics, bg=DIV, width=1).pack(side="left", fill="y", padx=18)

        right = tk.Frame(metrics, bg=CARD)
        right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text="TRUE PEAK", fg=MUTED, bg=CARD,
                 font=("Segoe UI", 7)).pack(anchor="w")
        tk.Label(right, text=(f"{tp:.1f} dBTP" if tp is not None else "— dBTP"),
                 fg=FG, bg=CARD, font=("Segoe UI Black", 30)).pack(anchor="w")
        tk.Label(right, text="MAX: -1.0 dBTP", fg=RED, bg=CARD,
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(4, 0))

        gauge = tk.Canvas(metrics, width=78, height=78, bg=CARD, highlightthickness=0)
        gauge.pack(side="right", padx=(6, 0))
        self._draw_gauge(gauge, lufs)

        # —— Buttons 2×3 ——
        grid = tk.Frame(card, bg=CARD)
        grid.pack(fill="x", pady=(18, 4))
        for c in range(3):
            grid.columnconfigure(c, weight=1, uniform="m")

        def cell(r, c, w):
            w.grid(row=r, column=c, sticky="ew", padx=5, pady=5)

        cell(0, 0, self._primary(grid, "REPRODUCIR", self._studio_play, "▶"))
        cell(0, 1, self._ghost(grid, "⇄  A/B", lambda: self._studio_ab(ab_path, ab_label)))
        cell(0, 2, self._ghost(grid, "■  DETENER", lambda: (m.stop_playback(), self._stop_tick())))
        cell(1, 0, self._ghost(grid, "▌▌  ACEPTAR MASTER", on_accept, danger=True))
        cell(1, 1, self._ghost(grid, "↩  UNDO", on_undo))
        cell(1, 2, self._ghost(grid, "≋  CAMBIAR LOUDNESS", on_loudness))

        if len(self.preview_versions) >= 2:
            abc = tk.Frame(card, bg=CARD)
            abc.pack(fill="x", pady=(2, 0))
            self._ghost(abc, "A/B/C  comparar versiones", self._abc_compare).pack(anchor="w")

        # —— Live waveform + timeline ——
        self.duration_s = float(duration or 0)
        self.play_pos = min(self.play_pos, self.duration_s) if self.duration_s else 0.0
        self._ensure_wave_env(self.current)
        wave_frame = tk.Frame(card, bg=CARD)
        wave_frame.pack(fill="x", pady=(14, 0))
        self._wave_canvas = tk.Canvas(wave_frame, height=64, bg="#0A0A0A", highlightthickness=0,
                                      cursor="sb_h_double_arrow")
        self._wave_canvas.pack(fill="x")
        self._wave_canvas.bind("<Configure>", lambda e: self._draw_live_wave())
        self._bind_seek_canvas(self._wave_canvas)
        live_row = tk.Frame(wave_frame, bg=CARD)
        live_row.pack(fill="x")
        self._live_lufs_lbl = tk.Label(live_row, text="LUFS live: —", fg=RED, bg=CARD,
                                       font=("Segoe UI Semibold", 8))
        self._live_lufs_lbl.pack(side="right")
        self._draw_live_wave()

        tl = tk.Frame(card, bg=CARD)
        tl.pack(fill="x", pady=(8, 0))
        self.tl_canvas = tk.Canvas(tl, height=18, bg=CARD, highlightthickness=0,
                                   cursor="sb_h_double_arrow")
        self.tl_canvas.pack(fill="x")
        self._bind_seek_canvas(self.tl_canvas)
        self.tl_canvas.bind("<Configure>", lambda e: self._draw_tl())
        times = tk.Frame(tl, bg=CARD)
        times.pack(fill="x", pady=(0, 0))
        self.var_t0 = tk.StringVar(value=_fmt_time(self.play_pos))
        self.var_t1 = tk.StringVar(value=_fmt_time(self.duration_s))
        tk.Label(times, textvariable=self.var_t0, fg=RED, bg=CARD,
                 font=("Segoe UI Semibold", 8)).pack(side="left")
        tk.Label(times, textvariable=self.var_t1, fg=FG, bg=CARD,
                 font=("Segoe UI", 8)).pack(side="right")
        self._draw_tl()

        # —— NL box ——
        nl = tk.Frame(card, bg=CARD)
        nl.pack(fill="x", pady=(14, 0))
        box = tk.Frame(nl, bg="#333333", padx=1, pady=1)
        box.pack(fill="x")
        inner = tk.Frame(box, bg=INPUT_BG, padx=12, pady=8)
        inner.pack(fill="x")
        tk.Label(inner, text="✦", fg=FG, bg=INPUT_BG, font=("Segoe UI", 11)).pack(side="left", padx=(0, 8))
        self.adj_entry = tk.Entry(inner, bg=INPUT_BG, fg=MUTED, insertbackground=FG,
                                  relief="flat", font=("Segoe UI", 9), highlightthickness=0)
        self.adj_entry.pack(side="left", fill="x", expand=True, ipady=3)
        self._nl_ph = 'Describe el ajuste que deseas aplicar… (ej: “más punch en los graves, menos harsh en los altos”)'
        self.adj_entry.insert(0, self._nl_ph)
        self.adj_entry.bind("<FocusIn>", self._nl_in)
        self.adj_entry.bind("<FocusOut>", self._nl_out)
        self.adj_entry.bind("<Return>", lambda e: on_adjust())
        tk.Button(inner, text="➤", command=on_adjust, bg=INPUT_BG, fg=FG, relief="flat",
                  font=("Segoe UI", 11), cursor="hand2", activebackground=INPUT_BG,
                  activeforeground=RED).pack(side="right", padx=(6, 0))
        hint = tk.Frame(nl, bg=CARD)
        hint.pack(anchor="w", pady=(8, 0))
        tk.Label(hint, text="⚡", fg=RED, bg=CARD, font=("Segoe UI", 8)).pack(side="left")
        tk.Label(hint, text="  Usa lenguaje natural. MixFlow ajustará el master en consecuencia.",
                 fg=MUTED, bg=CARD, font=("Segoe UI", 8)).pack(side="left")

        self.set_status("Preview" if not pending else "Ajuste pendiente", detail=str(title_file))

    def _draw_gauge(self, canvas, lufs):
        canvas.delete("all")
        span = max(0.08, min(1.0, (-6 - (lufs if lufs is not None else -14)) / 14.0))
        canvas.create_oval(8, 4, 70, 66, outline="#2A2A2A", width=5)
        canvas.create_arc(10, 6, 68, 64, start=90, extent=-int(270 * span),
                          style="arc", outline=RED, width=5)
        val = f"{lufs:.1f}" if lufs is not None else "—"
        canvas.create_text(39, 30, text=val, fill=FG, font=("Segoe UI Black", 13))
        canvas.create_text(39, 44, text="LUFS", fill=MUTED, font=("Segoe UI", 7))
        canvas.create_text(39, 72, text="MASTER", fill=MUTED2, font=("Segoe UI", 7))

    def _draw_tl(self):
        c = getattr(self, "tl_canvas", None)
        if not c:
            return
        c.delete("all")
        w = max(c.winfo_width(), 200)
        y = 10
        # base gris + progreso rojo
        c.create_line(2, y, w - 2, y, fill="#3A3A3A", width=2)
        frac = 0 if self.duration_s <= 0 else min(1.0, self.play_pos / self.duration_s)
        px = 2 + (w - 4) * frac
        c.create_line(2, y, px, y, fill=RED, width=2)
        for i in range(13):
            x = 2 + (w - 4) * i / 12
            c.create_line(x, y + 3, x, y + 7, fill="#555", width=1)
        c.create_polygon(px - 5, 1, px + 5, 1, px, 9, fill=RED, outline="")
        if hasattr(self, "var_t0"):
            self.var_t0.set(_fmt_time(self.play_pos))
        if hasattr(self, "var_t1"):
            self.var_t1.set(_fmt_time(self.duration_s))

    def _bind_seek_canvas(self, canvas):
        """Click + drag en waveform/timeline → seek real."""
        canvas.bind("<Button-1>", self._seek_press)
        canvas.bind("<B1-Motion>", self._seek_drag)
        canvas.bind("<ButtonRelease-1>", self._seek_release)

    def _pos_from_event(self, e):
        w = max(e.widget.winfo_width(), 40)
        pad = 4
        frac = max(0.0, min(1.0, (e.x - pad) / max(1, w - 2 * pad)))
        dur = float(self.duration_s or 0)
        return frac * dur

    def _seek_press(self, e):
        self._seek_dragging = True
        self._seek_was_playing = m.is_playing()
        self._apply_seek(self._pos_from_event(e), resume=False)

    def _seek_drag(self, e):
        if not self._seek_dragging:
            return
        self._apply_seek(self._pos_from_event(e), resume=False)

    def _seek_release(self, e):
        if not self._seek_dragging:
            return
        self._seek_dragging = False
        pos = self._pos_from_event(e)
        # Solo reinicia audio si ya estaba sonando; si no, solo mueve el playhead
        resume = bool(getattr(self, "_seek_was_playing", False)) and self.current is not None
        self._apply_seek(pos, resume=resume)

    def _apply_seek(self, pos, resume=True):
        """Actualiza playhead y, si resume, salta el audio de verdad."""
        dur = float(self.duration_s or 0)
        self.play_pos = max(0.0, min(pos, dur if dur > 0 else pos))
        self._draw_tl()
        try:
            self._draw_stems_tl()
        except Exception:
            pass
        self._draw_live_wave()
        if hasattr(self, "var_tc"):
            self.var_tc.set(_fmt_tc(self.play_pos))
        if hasattr(self, "var_t0"):
            self.var_t0.set(_fmt_time(self.play_pos))
        if not resume:
            # Solo mover playhead visualmente mientras se arrastra
            if m.is_playing():
                m.stop_playback()
                self._stop_tick()
            return
        path = self.current or getattr(m, "_PLAY_PATH", None)
        if path and Path(path).exists():
            m.play_audio(path, getattr(m, "_PLAY_LABEL", "") or "preview",
                         volume_db=float(getattr(m, "_PLAY_VOLUME_DB", 0.0) or 0.0),
                         start_s=self.play_pos)
            self._start_tick()

    def _nl_in(self, _=None):
        if self.adj_entry.get() == getattr(self, "_nl_ph", ""):
            self.adj_entry.delete(0, "end")
            self.adj_entry.config(fg=FG)

    def _nl_out(self, _=None):
        if not self.adj_entry.get().strip():
            self.adj_entry.insert(0, self._nl_ph)
            self.adj_entry.config(fg=MUTED)

    def _nl_text(self):
        t = self.adj_entry.get().strip()
        return "" if t == getattr(self, "_nl_ph", "") else t

    def _studio_play(self):
        if not self.current:
            return
        # Continúa desde el playhead actual (no siempre desde 0)
        start = float(self.play_pos or 0.0)
        if start >= float(self.duration_s or 0) - 0.05:
            start = 0.0
            self.play_pos = 0.0
        m.play_audio(self.current, "preview", start_s=start)
        self._start_tick()

    def _studio_ab(self, ab_path, ab_label):
        if not self.current:
            return
        ref = ab_path if ab_path and Path(ab_path).exists() else self.src
        if not ref:
            messagebox.showinfo("A/B", "No hay referencia.", parent=self.root)
            return
        m.ab_compare(ref, self.current, ab_label, "Preview", level_match=True)

    def _abc_compare(self):
        vers = [p for p in self.preview_versions if p and Path(p).exists()]
        if len(vers) < 2:
            messagebox.showinfo("A/B/C", "Necesitas al menos 2 previews.", parent=self.root)
            return
        labels = "ABC"
        for i, p in enumerate(vers[:3]):
            m.play_audio(p, f"Preview {labels[i]}", volume_db=0)
            if i < len(vers[:3]) - 1:
                if not messagebox.askokcancel("A/B/C", f"Escuchando {labels[i]}. OK = siguiente.", parent=self.root):
                    m.stop_playback()
                    return
                m.stop_playback()

    def _ensure_wave_env(self, path, bins=180):
        """Envelope RMS del archivo actual para animar el waveform."""
        if not path or not Path(path).exists():
            self._wave_env = [0.2] * bins
            return
        key = str(Path(path).resolve())
        if getattr(self, "_wave_env_key", None) == key and self._wave_env:
            return
        try:
            import numpy as np
            x, sr = m.audio_mono(path, max_seconds=min(600, float(self.duration_s or 90) or 90), sr=4000)
            if len(x) < bins:
                self._wave_env = [0.15] * bins
            else:
                chunk = len(x) // bins
                env = []
                for i in range(bins):
                    seg = x[i * chunk:(i + 1) * chunk]
                    env.append(float(np.sqrt(np.mean(seg * seg) + 1e-12)))
                mx = max(env) or 1.0
                self._wave_env = [min(1.0, v / mx) for v in env]
            self._wave_env_key = key
        except Exception:
            self._wave_env = [0.2 + 0.3 * abs(math.sin(i / 8)) for i in range(bins)]

    def _draw_live_wave(self):
        c = self._wave_canvas
        if c is None:
            return
        try:
            if not c.winfo_exists():
                return
        except tk.TclError:
            return
        c.delete("all")
        w = max(c.winfo_width(), 100)
        h = max(c.winfo_height(), 40)
        mid = h // 2
        env = self._wave_env or [0.2] * 120
        n = len(env)
        phase = self._wave_anim_phase
        playing = m.is_playing()
        frac = 0 if self.duration_s <= 0 else min(1.0, self.play_pos / self.duration_s)
        for i, amp in enumerate(env):
            x = int(i * w / n)
            boost = 1.0
            if playing:
                # pulso alrededor del playhead
                dist = abs(i / n - frac)
                boost = 1.0 + (0.45 * math.exp(-dist * 18)) * (0.7 + 0.3 * math.sin(phase + i * 0.2))
            ah = max(2, int(amp * (h * 0.42) * boost))
            color = RED if (playing and abs(i / n - frac) < 0.04) else RED
            c.create_line(x, mid - ah, x, mid + ah, fill=color, width=2)
        # playhead
        px = int(frac * w)
        c.create_line(px, 2, px, h - 2, fill=FG, width=1)
        if self._live_lufs_lbl is not None and playing and env:
            idx = min(n - 1, int(frac * n))
            # aproximación relativa al LUFS integrado del preview
            base = None
            a = self.preview_analysis or self.analysis
            if a:
                base = _sf(a.get("loudness", {}).get("input_i"))
            if base is not None:
                delta = 20 * math.log10(max(env[idx], 1e-4) / 0.5)
                live = base + max(-12, min(6, delta * 0.35))
                self._live_lufs_lbl.config(text=f"LUFS live ≈ {live:.1f}")
            else:
                self._live_lufs_lbl.config(text="LUFS live: …")

    def _start_tick(self):
        self._stop_tick()
        self._tick_t0 = time.monotonic()
        self._tick_pos0 = float(self.play_pos or 0.0)

        def tick():
            if self._seek_dragging:
                self._play_tick = self.root.after(100, tick)
                return
            if m.is_playing():
                # Posición = start_s del seek + tiempo real transcurrido
                elapsed = time.monotonic() - self._tick_t0
                self.play_pos = min(self.duration_s, self._tick_pos0 + elapsed)
                self._wave_anim_phase += 0.35
                self._draw_tl()
                self._draw_live_wave()
                try:
                    self._draw_stems_tl()
                except Exception:
                    pass
                if hasattr(self, "var_tc"):
                    self.var_tc.set(_fmt_tc(self.play_pos))
                if hasattr(self, "var_t0"):
                    self.var_t0.set(_fmt_time(self.play_pos))
                self._play_tick = self.root.after(100, tick)
            else:
                self._play_tick = None
                self._draw_live_wave()
        self._play_tick = self.root.after(100, tick)

    def _stop_tick(self):
        if self._play_tick is not None:
            try:
                self.root.after_cancel(self._play_tick)
            except Exception:
                pass
            self._play_tick = None

    def _metrics(self, a):
        if not a:
            return None, None, 0.0, "—"
        lufs = _sf(a.get("loudness", {}).get("input_i"))
        tp = _sf(a.get("loudness", {}).get("input_tp"))
        dur = float(a.get("duration") or 0)
        bits = a.get("bits") or a.get("bit_depth") or "24"
        ch = a.get("channels", "?")
        ch_txt = "Stereo" if ch == 2 else (f"{ch} ch" if ch else "?")
        sr = a.get("sr", 44100)
        self.output_sr = int(sr) if isinstance(sr, (int, float)) else 44100
        sr_k = f"{sr / 1000:.1f} kHz" if isinstance(sr, (int, float)) else str(sr)
        return lufs, tp, dur, f"{bits}-bit / {sr_k} / {ch_txt}"

    def _bpm_line(self, a, dur):
        if not a:
            return _fmt_time(dur)
        parts = []
        bpm = a.get("bpm") or a.get("tempo")
        key = a.get("key") or a.get("tonality")
        if bpm:
            try:
                parts.append(f"{int(float(bpm))} BPM")
            except Exception:
                parts.append(f"{bpm} BPM")
        if key:
            parts.append(str(key))
        parts.append(_fmt_time(dur))
        return " · ".join(parts)

    # ========== MEZCLA FLOW ==========
    def start_mezcla(self):
        path = filedialog.askopenfilename(parent=self.root, title="Selecciona la mezcla",
                                          filetypes=AUDIO_TYPES)
        if not path:
            return
        self._mode = "mezcla"
        self.src = Path(path)
        self.before_snapshot = m.snapshot_output_files()
        self.preview_versions = []
        self.set_status("Analizando audio…", 2, 9, self.src.name)
        self._clear_body()
        outer, card = self._card(self.body)
        outer.pack(fill="both", expand=True)
        tk.Label(card, text=f"Analizando\n{self.src.name}", fg=MUTED, bg=CARD,
                 font=("Segoe UI", 11)).pack(anchor="w")
        self._run_bg(lambda: m.analyze_basic(self.src), on_ok=self._mezcla_after_analysis,
                     err_hint="Usa WAV/FLAC/MP3 válido. Si falla, convierte con FFmpeg.")

    def _mezcla_after_analysis(self, a):
        self.analysis = a
        self._set_header_mode("mezcla")
        self.set_status("Elige loudness", 4, 9, self.src.name)
        self._clear_body()
        outer, card = self._card(self.body, padx=22, pady=16)
        outer.pack(fill="both", expand=True)
        lufs, tp, dur, meta = self._metrics(a)

        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x")
        ico = tk.Canvas(top, width=34, height=26, bg=CARD, highlightthickness=0)
        ico.pack(side="left", padx=(0, 10))
        self._draw_wf(ico, h=26)
        info = tk.Frame(top, bg=CARD)
        info.pack(side="left", fill="x", expand=True)
        tk.Label(info, text=self.src.name.upper(), fg=FG, bg=CARD,
                 font=("Segoe UI Semibold", 12), anchor="w").pack(fill="x")
        tk.Label(info, text=meta, fg=MUTED, bg=CARD, font=("Segoe UI", 8), anchor="w").pack(fill="x")

        tk.Frame(card, bg=DIV, height=1).pack(fill="x", pady=(12, 12))
        metrics = tk.Frame(card, bg=CARD)
        metrics.pack(fill="x")
        left = tk.Frame(metrics, bg=CARD)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="INTEGRATED", fg=MUTED, bg=CARD, font=("Segoe UI", 7)).pack(anchor="w")
        tk.Label(left, text=(f"{lufs:.1f} LUFS" if lufs is not None else "—"),
                 fg=FG, bg=CARD, font=("Segoe UI Black", 30)).pack(anchor="w")
        tk.Label(left, text=self._bpm_line(a, dur), fg=MUTED, bg=CARD,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(3, 0))
        tk.Frame(metrics, bg=DIV, width=1).pack(side="left", fill="y", padx=18)
        right = tk.Frame(metrics, bg=CARD)
        right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text="TRUE PEAK", fg=MUTED, bg=CARD, font=("Segoe UI", 7)).pack(anchor="w")
        tk.Label(right, text=(f"{tp:.1f} dBTP" if tp is not None else "—"),
                 fg=FG, bg=CARD, font=("Segoe UI Black", 30)).pack(anchor="w")
        tk.Label(right, text="MAX: -1.0 dBTP", fg=RED, bg=CARD,
                 font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(4, 0))
        gauge = tk.Canvas(metrics, width=78, height=78, bg=CARD, highlightthickness=0)
        gauge.pack(side="right")
        self._draw_gauge(gauge, lufs)

        rec_key, rec_target, rec_label = m.recommend_loudness(a)
        tk.Label(card, text=f"SUGERENCIA: {rec_label} ({rec_target:g} LUFS)",
                 fg=RED, bg=CARD, font=("Segoe UI Semibold", 8)).pack(anchor="w", pady=(16, 8))

        row = tk.Frame(card, bg=CARD)
        row.pack(anchor="w", fill="x")
        for label, val in [("Light -14", -14.0), ("Básico -12", -12.0),
                           ("Habitual -10", -10.0), ("Alto -8", -8.0)]:
            btn = self._primary(row, label, lambda v=val: self._mezcla_loudness(v)) if val == rec_target \
                else self._ghost(row, label, lambda v=val: self._mezcla_loudness(v))
            btn.pack(side="left", padx=(0, 8))
        row2 = tk.Frame(card, bg=CARD)
        row2.pack(anchor="w", pady=(10, 0))
        self._ghost(row2, "Personalizado…", self._mezcla_custom).pack(side="left", padx=(0, 8))
        self._ghost(row2, "Sin normalizar", lambda: self._mezcla_loudness(None)).pack(side="left", padx=(0, 8))
        self._ghost(row2, "Presets…", self._presets_menu).pack(side="left", padx=(0, 8))
        # Sample rate: preservar fuente o forzar 44.1 / 48 kHz
        sr_src = int(a.get("sr") or 44100)
        self.output_sr = sr_src
        tk.Label(card, text=f"Sample rate: {sr_src} Hz (fuente)", fg=MUTED, bg=CARD,
                 font=("Segoe UI", 8)).pack(anchor="w", pady=(12, 4))
        sr_row = tk.Frame(card, bg=CARD)
        sr_row.pack(anchor="w")
        for label, val in [("Fuente", sr_src), ("44.1 kHz", 44100), ("48 kHz", 48000)]:
            self._ghost(sr_row, label, lambda v=val: setattr(self, "output_sr", int(v))).pack(
                side="left", padx=(0, 8))

    def _mezcla_custom(self):
        v = simpledialog.askfloat("Loudness", "Objetivo LUFS (-30 a -5):",
                                  parent=self.root, minvalue=-30, maxvalue=-5)
        if v is not None:
            self._mezcla_loudness(float(v))

    def _presets_menu(self):
        data = {}
        if self.presets_path.exists():
            try:
                data = json.loads(self.presets_path.read_text(encoding="utf-8"))
            except Exception:
                data = {}
        names = list(data.keys()) or ["(ninguno)"]
        name = simpledialog.askstring(
            "Presets",
            "Nombre para guardar preset actual (loudness),\n"
            f"o escribe el nombre a cargar:\nDisponibles: {', '.join(names)}",
            parent=self.root)
        if not name:
            return
        if name in data:
            self._mezcla_loudness(data[name].get("target", -10))
            return
        # save
        data[name] = {"target": self.target}
        try:
            self.presets_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            messagebox.showinfo("Preset", f"Guardado: {name}", parent=self.root)
        except Exception as e:
            self._error("Preset", str(e), "Verifica permisos en MixFlow_Output.")

    def _mezcla_loudness(self, target):
        self.target = target
        self.set_status("Procesando…", 5, 9, "sin norm." if target is None else f"{target:g} LUFS")
        self._clear_body()
        outer, card = self._card(self.body)
        outer.pack(fill="both", expand=True)
        tk.Label(card, text="Aplicando EQ / dinámica y loudness…", fg=MUTED, bg=CARD,
                 font=("Segoe UI", 11)).pack(anchor="w")

        def work():
            self.tmp = m.OUT_ROOT / "Mezcla" / self.src.stem
            self.tmp.mkdir(parents=True, exist_ok=True)
            self.base_filters = m.adaptive_mix_filters(self.analysis)
            self.history = [[]]
            return self._mezcla_build(self.base_filters, "PREVIEW_01")

        self._run_bg(work, on_ok=lambda p: self._mezcla_show_preview(p),
                     err_hint="Prueba otro nivel de loudness o 'Sin normalizar'.")

    def _mezcla_build(self, filters, tag):
        base = self.tmp / (tag + "_base.wav")
        regular = [f for f in filters if not str(f).startswith("MIXSEL:")]
        selective = [str(f) for f in filters if str(f).startswith("MIXSEL:")]
        sr = self.output_sr or 44100
        self.root.after(0, lambda: self.set_status("EQ / dinámica…", 5, 9, tag))
        m.run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-i", str(self.src),
               "-af", ",".join(regular) if regular else "anull",
               "-ar", str(sr), "-c:a", "pcm_s24le", str(base)])
        work = base
        for idx, spec in enumerate(selective, 1):
            self.root.after(0, lambda i=idx, n=len(selective): self.set_status(
                f"Selectivo {i}/{n}", 5, 9))
            step = self.tmp / f"{tag}_SEL_{idx:02d}.wav"
            m.apply_mix_selective(work, step, spec)
            work = step
        out = self.tmp / (tag + "_PREVIEW.wav")
        self.root.after(0, lambda: self.set_status("Loudness…", 6, 9))
        report = m.apply_loudness(work, self.target, out)
        if float(report.get("estimated_dynamic_sacrifice_db") or 0) > 3.0 or report.get("status") != "verified":
            msg = (f"Sacrificio ≈ {report.get('estimated_dynamic_sacrifice_db')} dB\n"
                   f"{report.get('final_lufs')} LUFS / {report.get('final_true_peak_dbtp')} dBTP")
            self.root.after(0, lambda: messagebox.showwarning("Loudness", msg, parent=self.root))
        return Path(out)

    def _mezcla_show_preview(self, current, pending=False):
        self.current = Path(current)
        if self.current not in self.preview_versions:
            self.preview_versions.append(self.current)
        try:
            self.preview_analysis = m.analyze_basic(self.current)
        except Exception:
            self.preview_analysis = None
        a = self.preview_analysis or self.analysis
        lufs, tp, dur, meta = self._metrics(a)
        self._show_mezcla_studio(
            title_file=self.current.name, meta_line=meta,
            lufs=lufs, tp=tp, target=self.target, duration=dur,
            on_accept=self._mezcla_accept, on_undo=self._mezcla_undo,
            on_loudness=lambda: self._mezcla_after_analysis(self.analysis),
            on_adjust=self._mezcla_apply_adjust,
            ab_path=self.src, ab_label="Original", pending=pending,
            bpm_line=self._bpm_line(a, dur),
        )

    def _mezcla_apply_adjust(self):
        instruction = self._nl_text()
        if not instruction:
            return
        instruction = m.normalize_instruction(instruction)
        parsed = m.parse_mezcla_feedback_explained(instruction) if hasattr(m, "parse_mezcla_feedback_explained") \
            else {"actions": m.parse_mezcla_feedback(instruction), "summary": "", "ambiguous": False}
        new_filters = parsed.get("actions") or []
        if not new_filters:
            self._error("Ajuste", f'No pude interpretar:\n"{instruction}"',
                        "Prueba: “súbele a la voz”, “más punch en graves, menos harsh en altos”.")
            return
        summary = parsed.get("summary") or "\n".join(new_filters)
        if not messagebox.askyesno(
                "Interpretación" + (" (ambigua)" if parsed.get("ambiguous") else ""),
                f'Frase: "{instruction}"\n\nInterpreté:\n{summary}\n\n¿Aplicar?',
                parent=self.root):
            return
        pending = self.history[-1] + new_filters
        self.set_status("Aplicando ajuste…", 7, 9, instruction)

        def work():
            import re, datetime
            slug = re.sub(r"[^A-Za-z0-9]+", "_", instruction).strip("_")[:40]
            tag = f"Preview_{slug or datetime.datetime.now().strftime('%H%M%S')}"
            return self._mezcla_build(self.base_filters + pending, tag), new_filters, instruction

        def ok(payload):
            path, nf, instr = payload
            self.current = path
            self._mezcla_pending(nf, instr)

        self._run_bg(work, on_ok=ok)

    def _mezcla_pending(self, new_filters, instruction):
        try:
            self.preview_analysis = m.analyze_basic(self.current)
        except Exception:
            pass
        a = self.preview_analysis or self.analysis
        lufs, tp, dur, meta = self._metrics(a)

        def accept():
            self.history.append([*self.history[-1], *new_filters])
            self._mezcla_show_preview(self.current)

        def reject():
            self._run_bg(
                lambda: self._mezcla_build(self.base_filters + self.history[-1],
                                           f"REJECT_{len(self.history):02d}"),
                on_ok=self._mezcla_show_preview)

        self._show_mezcla_studio(
            title_file=self.current.name, meta_line=f'{meta}  ·  "{instruction}"',
            lufs=lufs, tp=tp, target=self.target, duration=dur,
            on_accept=accept, on_undo=reject,
            on_loudness=lambda: self._mezcla_after_analysis(self.analysis),
            on_adjust=self._mezcla_apply_adjust,
            ab_path=self.src, pending=True, bpm_line=self._bpm_line(a, dur),
        )

    def _mezcla_undo(self):
        if len(self.history) <= 1:
            messagebox.showinfo("Undo", "No hay ajuste anterior.", parent=self.root)
            return

        def work():
            self.history.pop()
            return self._mezcla_build(self.base_filters + self.history[-1],
                                      f"UNDO_{len(self.history):02d}")
        self._run_bg(work, on_ok=self._mezcla_show_preview)

    def _mezcla_accept(self):
        self._halt_playback()
        final = self._versioned_path(self.tmp, self.src.stem)
        shutil.copy2(self.current, final)
        self.set_status("Master listo", 9, 9, str(final))
        self._clear_body()
        outer, card = self._card(self.body)
        outer.pack(fill="both", expand=True)
        tk.Label(card, text="MASTER GUARDADO", fg=RED, bg=CARD,
                 font=("Segoe UI Semibold", 11)).pack(anchor="w")
        tk.Label(card, text=str(final), fg=FG, bg=CARD,
                 font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=(8, 16))
        self._primary(card, "REPRODUCIR", lambda: m.play_audio(final), "▶").pack(anchor="w", pady=4)
        self._ghost(card, "Abrir carpeta", lambda: os.startfile(str(self.tmp))).pack(anchor="w", pady=4)
        self._ghost(card, "Volver al inicio", self._finish_session).pack(anchor="w", pady=12)

    # ========== STEMS (mockup 2) ==========
    def start_stems(self):
        paths = filedialog.askopenfilenames(parent=self.root, title="Selecciona STEMS",
                                            filetypes=AUDIO_TYPES)
        if not paths:
            return
        self._start_stems_with([Path(p) for p in paths])

    def _start_stems_with(self, paths):
        self._mode = "stems"
        self.stem_files = list(paths)
        self.before_snapshot = m.snapshot_output_files()
        self.preview_versions = []
        self.classified = self._classify_stems(self.stem_files)
        if not self.classified:
            self.show_home()
            return
        ref = [p for p, c in self.classified.items() if c == "Alignment / Referencia"]
        if not ref:
            choice = simpledialog.askinteger(
                "Referencia",
                f"Número del archivo de alignment (1…{len(self.stem_files)}):",
                parent=self.root, minvalue=1, maxvalue=len(self.stem_files))
            if not choice:
                self.show_home()
                return
            self.classified[self.stem_files[choice - 1]] = "Alignment / Referencia"
            ref = [self.stem_files[choice - 1]]

        self._set_header_mode("stems")
        self.set_status("Alineando…", 2, 12)
        self._clear_body()
        outer, card = self._card(self.body)
        outer.pack(fill="both", expand=True)
        lines = "\n".join(f"• {_stem_label(c)}: {p.name}" for p, c in self.classified.items())
        tk.Label(card, text="Clasificación (puedes reasignar después)", fg=FG, bg=CARD,
                 font=("Segoe UI Semibold", 12)).pack(anchor="w")
        tk.Label(card, text=lines, fg=MUTED, bg=CARD, font=("Segoe UI", 9),
                 justify="left").pack(anchor="w", pady=8)

        def work():
            self.tmp = m.OUT_ROOT / "Stems" / self.stem_files[0].stem
            self.tmp.mkdir(parents=True, exist_ok=True)
            self.sources = m.align_stems(self.classified, ref[0], self.tmp,
                                         manual_offsets=self._manual_offsets)
            self._align_reports = getattr(m.align_stems, "last_reports", {}) or {}
            self.settings = {p: {"gain": 0.0, "mute": False, "solo": False}
                             for p in self.classified}
            return True

        self._run_bg(work, on_ok=lambda _: self._stems_after_align(),
                     err_hint="Revisa que haya un stem de referencia Alignment.")

    def _stems_after_align(self):
        # Pedir offset manual si score bajo
        needs = [(p, r) for p, r in self._align_reports.items()
                 if r.get("needs_manual") or float(r.get("score") or 0) < 0.20]
        for p, r in needs:
            ms = simpledialog.askfloat(
                "Alineación manual",
                f"{_stem_label(self.classified.get(p, ''))} — {p.name}\n"
                f"Score bajo ({float(r.get('score') or 0):.2f}).\n"
                "Offset en milisegundos (+ retrasa, − adelanta).\n"
                "Cancelar = dejar sin desplazar.",
                parent=self.root)
            if ms is not None:
                self._manual_offsets[p] = float(ms) / 1000.0
        if needs and self._manual_offsets:
            ref = next(p for p, c in self.classified.items() if c == "Alignment / Referencia")

            def work():
                self.sources = m.align_stems(self.classified, ref, self.tmp,
                                             manual_offsets=self._manual_offsets)
                self._align_reports = getattr(m.align_stems, "last_reports", {}) or {}
                return True
            self._run_bg(work, on_ok=lambda _: self._stems_loudness_pick())
            return
        self._stems_loudness_pick()

    def _classify_stems(self, files):
        out = {}
        for p in files:
            c = m.classify(p)
            # Remarques separado si el nombre lo indica
            n = p.stem.lower()
            if c == "Backs / Remarques" and "remarque" in n and "back" not in n:
                c = "Remarques"
            if c is None:
                c = self._ask_cat(p)
                if c is None:
                    return {}
            out[p] = c
        return out

    def _ask_cat(self, p):
        win = tk.Toplevel(self.root)
        win.title("Clasificar stem")
        win.configure(bg=BG)
        win.geometry("400x420")
        win.transient(self.root)
        win.grab_set()
        chosen = {"v": None}
        tk.Label(win, text=p.name, bg=BG, fg=FG,
                 font=("Segoe UI Semibold", 11)).pack(padx=16, pady=12, anchor="w")
        for cat in STEM_REASSIGN:
            self._ghost(win, _stem_label(cat) + f"  ({cat})",
                        lambda c=cat: (chosen.update(v=c), win.destroy())
                        ).pack(fill="x", padx=16, pady=3)
        self.root.wait_window(win)
        return chosen["v"]

    def _stems_loudness_pick(self):
        self._set_header_mode("stems")
        self.set_status("Loudness STEMS", 5, 12)
        self._clear_body()
        outer, card = self._card(self.body)
        outer.pack(fill="x")
        tk.Label(card, text="Nivel de loudness del master", fg=FG, bg=CARD,
                 font=("Segoe UI Semibold", 12)).pack(anchor="w")
        if self._align_reports:
            lines = []
            for p, rep in self._align_reports.items():
                off_ms = float(rep.get("offset_s") or 0) * 1000
                lines.append(
                    f"{_stem_label(rep.get('category', self.classified.get(p)))}  "
                    f"{off_ms:+.0f} ms  score {float(rep.get('score') or 0):.2f}")
            tk.Label(card, text="\n".join(lines), fg=MUTED, bg=CARD,
                     font=("Segoe UI", 8), justify="left").pack(anchor="w", pady=8)
        row = tk.Frame(card, bg=CARD)
        row.pack(anchor="w", pady=10)
        for label, val in [("Light -14", -14.0), ("Básico -12", -12.0),
                           ("Habitual -10", -10.0), ("Alto -8", -8.0)]:
            btn = self._primary(row, label, lambda v=val: self._stems_enter(v)) if val == -10 \
                else self._ghost(row, label, lambda v=val: self._stems_enter(v))
            btn.pack(side="left", padx=3)
        self._ghost(card, "Sin normalizar", lambda: self._stems_enter(None)).pack(anchor="w", pady=8)

    def _stems_enter(self, target):
        self.target = target
        self.accepted_settings = copy.deepcopy(self.settings)
        self.stem_history = [copy.deepcopy(self.accepted_settings)]
        self.current = None
        self._stems_desk()

    def _stems_desk(self):
        """Réplica del mockup STEMS MODE."""
        self._set_header_mode("stems")
        self.set_status("", detail="")
        self._clear_body()

        # Tabs compactos
        tabs = tk.Frame(self.body, bg=BG)
        tabs.pack(fill="x", pady=(0, 4))
        for name, icon in (("STEMS", "⬡"), ("MIXER", "▥"), ("EFFECTS", "☰")):
            active = name == self._stem_tab
            col = tk.Frame(tabs, bg=BG)
            col.pack(side="left", padx=(0, 20))
            tk.Label(col, text=f"{icon}  {name}", fg=(RED if active else MUTED), bg=BG,
                     font=("Segoe UI Semibold", 9), cursor="hand2").pack()
            tk.Frame(col, bg=(RED if active else BG), height=2).pack(fill="x", pady=(4, 0))
            if not active:
                col.bind("<Button-1>", lambda e, n=name: self._tab(n))
                for ch in col.winfo_children():
                    ch.bind("<Button-1>", lambda e, n=name: self._tab(n))

        # Stem list
        wrap = tk.Frame(self.body, bg=CARD_BORDER, padx=1, pady=1)
        wrap.pack(fill="both", expand=True)
        list_bg = tk.Frame(wrap, bg=CARD)
        list_bg.pack(fill="both", expand=True)

        canvas = tk.Canvas(list_bg, bg=CARD, highlightthickness=0)
        sb = tk.Scrollbar(list_bg, orient="vertical", command=canvas.yview)
        rows = tk.Frame(canvas, bg=CARD)
        rows.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        win_id = canvas.create_window((0, 0), window=rows, anchor="nw")

        def _sync_width(e):
            canvas.itemconfig(win_id, width=e.width)
        canvas.bind("<Configure>", _sync_width)
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        playable = [(p, c) for p, c in self.classified.items() if c != "Alignment / Referencia"]
        order = ["Beat", "Voz principal — Versos", "Backs / Remarques",
                 "Voz principal — Coros", "Adlibs", "Remarques",
                 "Segunda voz — Versos", "Segunda voz — Coros"]
        playable.sort(key=lambda x: order.index(x[1]) if x[1] in order else 99)
        for p, cat in playable:
            self._stem_row(rows, p, cat)

        # Actions — AFINAR · ALINEAR · PREVIEW · A/B · UNDO · ACEPTAR
        act = tk.Frame(self.body, bg=BG)
        act.pack(fill="x", pady=(10, 4))
        for i in range(6):
            act.columnconfigure(i, weight=1, uniform="s")
        self._red_outline(act, "♫  AFINAR", self._stems_afinar).grid(row=0, column=0, sticky="ew", padx=2)
        self._red_outline(act, "◎  ALINEAR", self._stems_realign).grid(row=0, column=1, sticky="ew", padx=2)
        self._primary(act, "PREVIEW", self._stems_preview, "▶").grid(row=0, column=2, sticky="ew", padx=2)
        self._red_outline(act, "A/B", self._stems_ab).grid(row=0, column=3, sticky="ew", padx=2)
        self._red_outline(act, "↩  UNDO", self._stems_undo).grid(row=0, column=4, sticky="ew", padx=2)
        self._red_outline(act, "✓  ACEPTAR", self._stems_accept).grid(row=0, column=5, sticky="ew", padx=2)

        # Live waveform STEMS
        if self.current:
            self._ensure_wave_env(self.current)
        wave_frame = tk.Frame(self.body, bg=BG)
        wave_frame.pack(fill="x", pady=(8, 0))
        self._wave_canvas = tk.Canvas(wave_frame, height=56, bg="#0A0A0A", highlightthickness=0,
                                      cursor="sb_h_double_arrow")
        self._wave_canvas.pack(fill="x")
        self._wave_canvas.bind("<Configure>", lambda e: self._draw_live_wave())
        self._bind_seek_canvas(self._wave_canvas)
        live_row = tk.Frame(wave_frame, bg=BG)
        live_row.pack(fill="x")
        self._live_lufs_lbl = tk.Label(live_row, text="LUFS live: —", fg=RED, bg=BG,
                                       font=("Segoe UI Semibold", 8))
        self._live_lufs_lbl.pack(side="right")
        self._draw_live_wave()

        # Transport compacto
        tr = tk.Frame(self.body, bg=BG)
        tr.pack(fill="x", pady=(8, 0))
        left = tk.Frame(tr, bg=BG)
        left.pack(side="left")
        tk.Label(left, text="TIMELINE", fg=MUTED2, bg=BG, font=("Segoe UI", 7)).pack(anchor="w")
        self.var_tc = tk.StringVar(value=_fmt_tc(self.play_pos))
        tk.Label(left, textvariable=self.var_tc, fg=FG, bg=BG,
                 font=("Segoe UI Black", 16)).pack(anchor="w")
        mid = tk.Frame(tr, bg=BG)
        mid.pack(side="left", padx=28)
        tk.Button(mid, text="⏮", command=lambda: self._seek0(), bg=BG, fg=MUTED,
                  relief="flat", font=("Segoe UI", 11), cursor="hand2").pack(side="left")
        tk.Button(mid, text="▶", command=self._studio_play, bg=BG, fg=RED,
                  relief="flat", font=("Segoe UI", 13), cursor="hand2").pack(side="left", padx=6)
        tk.Button(mid, text="■", command=lambda: (m.stop_playback(), self._stop_tick()),
                  bg=BG, fg=FG, relief="flat", font=("Segoe UI", 11), cursor="hand2").pack(side="left")

        self.duration_s = float((self.preview_analysis or {}).get("duration") or self.duration_s or 180)
        self.tl_canvas = tk.Canvas(self.body, height=32, bg=BG, highlightthickness=0,
                                   cursor="sb_h_double_arrow")
        self.tl_canvas.pack(fill="x", pady=(2, 0))
        self._bind_seek_canvas(self.tl_canvas)
        self.tl_canvas.bind("<Configure>", lambda e: self._draw_stems_tl())
        self._draw_stems_tl()

        # NL red border
        nl = tk.Frame(self.body, bg=BG)
        nl.pack(fill="x", pady=(10, 2))
        box = tk.Frame(nl, bg=RED, padx=1, pady=1)
        box.pack(fill="x")
        inner = tk.Frame(box, bg=INPUT_BG, padx=10, pady=6)
        inner.pack(fill="x")
        tk.Label(inner, text="✦", fg=RED, bg=INPUT_BG, font=("Segoe UI", 11)).pack(side="left", padx=(0, 8))
        self.adj_entry = tk.Entry(inner, bg=INPUT_BG, fg=MUTED, insertbackground=FG,
                                  relief="flat", font=("Segoe UI Italic", 9), highlightthickness=0)
        self.adj_entry.pack(side="left", fill="x", expand=True, ipady=2)
        self._nl_ph = "Describe el cambio que deseas realizar…"
        self.adj_entry.insert(0, self._nl_ph)
        self.adj_entry.bind("<FocusIn>", self._nl_in)
        self.adj_entry.bind("<FocusOut>", self._nl_out)
        self.adj_entry.bind("<Return>", lambda e: self._stems_nl())
        tk.Button(inner, text="➤", command=self._stems_nl, bg=RED, fg=FG, relief="flat",
                  font=("Segoe UI", 11), cursor="hand2", padx=10, pady=2,
                  activebackground=RED_DIM).pack(side="right")

    def _tab(self, name):
        self._halt_playback()
        self._stem_tab = name
        if name == "MIXER":
            self._stems_mixer_view()
        elif name == "EFFECTS":
            self._stems_effects_view()
        else:
            self._stems_desk()

    def _stems_mixer_view(self):
        """MIXER: faders verticales por stem + mute/solo."""
        self._set_header_mode("stems")
        self.set_status("MIXER", detail="Gain por stem · Mute / Solo")
        self._clear_body()
        tabs = tk.Frame(self.body, bg=BG)
        tabs.pack(fill="x", pady=(0, 8))
        for name in ("STEMS", "MIXER", "EFFECTS"):
            active = name == "MIXER"
            col = tk.Frame(tabs, bg=BG)
            col.pack(side="left", padx=(0, 20))
            lbl = tk.Label(col, text=name, fg=(RED if active else MUTED), bg=BG,
                           font=("Segoe UI Semibold", 10), cursor="hand2")
            lbl.pack()
            tk.Frame(col, bg=(RED if active else BG), height=2).pack(fill="x", pady=(4, 0))
            if not active:
                lbl.bind("<Button-1>", lambda e, n=name: self._tab(n))

        strip = tk.Frame(self.body, bg=CARD)
        strip.pack(fill="both", expand=True)
        playable = [(p, c) for p, c in self.classified.items() if c != "Alignment / Referencia"]
        for p, cat in playable:
            st = self.settings.setdefault(p, {"gain": 0.0, "mute": False, "solo": False})
            col = tk.Frame(strip, bg=CARD, padx=8, pady=8)
            col.pack(side="left", fill="y")
            tk.Label(col, text=_stem_label(cat), fg=FG, bg=CARD,
                     font=("Segoe UI Semibold", 8)).pack()
            gv = tk.DoubleVar(value=float(st.get("gain") or 0))
            vl = tk.Label(col, text=f"{gv.get():+.1f}", fg=RED, bg=CARD, font=("Segoe UI", 8))

            def on_g(v, path=p, lbl=vl):
                self.settings.setdefault(path, {})["gain"] = float(v)
                lbl.config(text=f"{float(v):+.1f}")

            tk.Scale(col, from_=12, to=-12, resolution=0.1, orient="vertical",
                     variable=gv, command=on_g, bg=CARD, fg=FG, troughcolor=RED,
                     highlightthickness=0, length=160, showvalue=0,
                     activebackground=FG).pack(pady=6)
            vl.pack()
            tk.Button(col, text="M", width=3, command=lambda path=p: self._tog_mute(path),
                      bg=BTN_DARK, fg=RED, relief="solid",
                      highlightbackground=RED, highlightthickness=1).pack(pady=2)
            tk.Button(col, text="S", width=3, command=lambda path=p: self._tog_solo(path),
                      bg=BTN_DARK, fg=RED, relief="solid",
                      highlightbackground=RED, highlightthickness=1).pack()
        tk.Button(self.body, text="← Volver a STEMS", command=lambda: self._tab("STEMS"),
                  bg=BTN_DARK, fg=FG, relief="flat", font=("Segoe UI", 9),
                  cursor="hand2").pack(anchor="w", pady=10)

    def _stems_effects_view(self):
        """EFFECTS: EQ bright/body y compresión explícita por stem vocal."""
        self._set_header_mode("stems")
        self.set_status("EFFECTS", detail="Bright / Body / Comp — solo si los activas")
        self._clear_body()
        tabs = tk.Frame(self.body, bg=BG)
        tabs.pack(fill="x", pady=(0, 8))
        for name in ("STEMS", "MIXER", "EFFECTS"):
            active = name == "EFFECTS"
            col = tk.Frame(tabs, bg=BG)
            col.pack(side="left", padx=(0, 20))
            lbl = tk.Label(col, text=name, fg=(RED if active else MUTED), bg=BG,
                           font=("Segoe UI Semibold", 10), cursor="hand2")
            lbl.pack()
            tk.Frame(col, bg=(RED if active else BG), height=2).pack(fill="x", pady=(4, 0))
            if not active:
                lbl.bind("<Button-1>", lambda e, n=name: self._tab(n))

        outer, card = self._card(self.body, padx=16, pady=12)
        outer.pack(fill="both", expand=True)
        vocals = [(p, c) for p, c in self.classified.items()
                  if c not in ("Alignment / Referencia", "Beat")]
        if not vocals:
            tk.Label(card, text="No hay stems vocales.", fg=MUTED, bg=CARD).pack(anchor="w")
        for p, cat in vocals:
            st = self.settings.setdefault(p, {})
            row = tk.Frame(card, bg=CARD)
            row.pack(fill="x", pady=6)
            tk.Label(row, text=_stem_label(cat), fg=FG, bg=CARD, width=12, anchor="w",
                     font=("Segoe UI Semibold", 9)).pack(side="left")
            for key, label, lo, hi in (("bright", "Bright", -3, 3), ("body", "Body", -3, 3)):
                tk.Label(row, text=label, fg=MUTED, bg=CARD, font=("Segoe UI", 8)).pack(side="left", padx=(8, 2))
                var = tk.DoubleVar(value=float(st.get(key) or 0))

                def mk(k=key, path=p, v=var):
                    def _cb(val):
                        self.settings.setdefault(path, {})[k] = float(val)
                    return _cb

                tk.Scale(row, from_=lo, to=hi, resolution=0.1, orient="horizontal",
                         variable=var, command=mk(), length=90, showvalue=1,
                         bg=CARD, fg=FG, troughcolor=RED, highlightthickness=0,
                         font=("Segoe UI", 7)).pack(side="left")
            tk.Label(row, text="Comp", fg=MUTED, bg=CARD, font=("Segoe UI", 8)).pack(side="left", padx=(8, 2))
            cv = tk.DoubleVar(value=float(st.get("comp_ratio") or 0))

            def on_comp(val, path=p):
                v = float(val)
                if v < 1.05:
                    self.settings.setdefault(path, {}).pop("comp_ratio", None)
                else:
                    self.settings.setdefault(path, {})["comp_ratio"] = v

            tk.Scale(row, from_=0, to=4, resolution=0.1, orient="horizontal",
                     variable=cv, command=on_comp, length=80, showvalue=1,
                     bg=CARD, fg=FG, troughcolor=RED, highlightthickness=0,
                     font=("Segoe UI", 7)).pack(side="left")
        tk.Button(self.body, text="← Volver a STEMS", command=lambda: self._tab("STEMS"),
                  bg=BTN_DARK, fg=FG, relief="flat", font=("Segoe UI", 9),
                  cursor="hand2").pack(anchor="w", pady=10)

    def _stem_row(self, parent, path, cat):
        st = self.settings.setdefault(path, {"gain": 0.0, "mute": False, "solo": False})
        row = tk.Frame(parent, bg=CARD, pady=4, padx=10)
        row.pack(fill="x")
        tk.Frame(parent, bg="#1A1A1A", height=1).pack(fill="x")

        # Icon box compacto
        ib = tk.Frame(row, bg=CARD, highlightbackground=RED, highlightthickness=1)
        ib.pack(side="left", padx=(0, 8))
        ico = tk.Canvas(ib, width=22, height=22, bg=CARD, highlightthickness=0)
        ico.pack()
        self._stem_icon(ico, cat)

        tk.Label(row, text=_stem_label(cat), fg=FG, bg=CARD,
                 font=("Segoe UI Semibold", 9), width=11, anchor="w").pack(side="left")

        def reassign(_e=None, p=path):
            c = self._ask_cat(p)
            if c:
                self.classified[p] = c
                self._stems_desk()
        row.bind("<Double-Button-1>", reassign)

        wf = tk.Canvas(row, width=200, height=24, bg=CARD, highlightthickness=0)
        wf.pack(side="left", padx=(4, 10), fill="x", expand=True)
        self._mini_wave(wf, w=200, h=24)

        muted = bool(st.get("mute"))
        soloed = bool(st.get("solo"))
        mb = tk.Button(row, text="M MUTE", command=lambda p=path: self._tog_mute(p),
                       bg=("#2A0000" if muted else BTN_DARK),
                       fg=(FG if muted else RED),
                       relief="solid", bd=1, highlightbackground=RED, highlightthickness=1,
                       font=("Segoe UI Semibold", 7), cursor="hand2", padx=6, pady=3)
        mb.pack(side="left", padx=(0, 3))
        sb = tk.Button(row, text="S", command=lambda p=path: self._tog_solo(p),
                       bg=(RED if soloed else BTN_DARK),
                       fg=(FG if soloed else RED),
                       relief="solid", bd=1, highlightbackground=RED, highlightthickness=1,
                       font=("Segoe UI Semibold", 8), cursor="hand2", padx=8, pady=3)
        sb.pack(side="left", padx=(0, 8))

        tk.Frame(row, bg=RED, width=1, height=18).pack(side="left", padx=(0, 8))
        tk.Label(row, text="GAIN", fg=FG, bg=CARD, font=("Segoe UI", 7)).pack(side="left")
        gv = tk.DoubleVar(value=float(st.get("gain") or 0))
        vl = tk.Label(row, text=f"{gv.get():+.1f} dB", fg=RED, bg=CARD,
                      font=("Segoe UI Semibold", 8), width=7)

        def on_g(v, p=path, g=gv, lbl=vl):
            self.settings.setdefault(p, {})["gain"] = float(v)
            lbl.config(text=f"{float(v):+.1f} dB")

        tk.Scale(row, from_=-12, to=12, resolution=0.1, orient="horizontal",
                 variable=gv, command=on_g, bg=CARD, fg=FG, troughcolor=RED,
                 highlightthickness=0, showvalue=0, length=110, borderwidth=0,
                 activebackground=FG, sliderrelief="flat").pack(side="left", padx=6)
        vl.pack(side="left")

        rep = self._align_reports.get(path, {})
        if rep:
            off_ms = float(rep.get("offset_s") or 0) * 1000
            tk.Label(row, text=f"{off_ms:+.0f} ms", fg=MUTED2, bg=CARD,
                     font=("Segoe UI", 7)).pack(side="right", padx=2)

    def _stem_icon(self, c, cat):
        c.delete("all")
        k = (cat or "").lower()
        if "beat" in k:
            c.create_oval(4, 4, 18, 18, outline=RED, width=2)
            c.create_oval(8, 8, 14, 14, fill=RED, outline="")
        elif "adlib" in k:
            c.create_polygon(11, 3, 19, 19, 3, 19, outline=RED, fill="", width=2)
        elif "back" in k or "remarque" in k:
            c.create_oval(3, 7, 10, 14, outline=RED, width=1)
            c.create_oval(8, 5, 15, 12, outline=RED, width=1)
            c.create_oval(12, 8, 19, 15, outline=RED, width=1)
        else:
            c.create_oval(6, 2, 16, 12, outline=RED, width=2)
            c.create_line(11, 12, 11, 17, fill=RED, width=2)
            c.create_line(7, 17, 15, 17, fill=RED, width=2)

    def _mini_wave(self, c, w=180, h=30):
        import random
        rng = random.Random(7)
        mid = h // 2
        for x in range(0, w, 3):
            amp = 2 + rng.random() * (h // 2 - 2)
            c.create_line(x, mid - amp, x, mid + amp, fill=RED, width=2)
        for x in (int(w * 0.28), int(w * 0.55), int(w * 0.78)):
            c.create_oval(x - 2, mid - 2, x + 2, mid + 2, fill=FG, outline="")

    def _draw_stems_tl(self):
        c = getattr(self, "tl_canvas", None)
        if not c:
            return
        c.delete("all")
        w = max(c.winfo_width(), 200)
        y = 16
        c.create_line(8, y, w - 8, y, fill="#3A3A3A", width=2)
        n = 7
        dur = self.duration_s or 180
        for i in range(n):
            x = 8 + (w - 16) * i / (n - 1)
            c.create_line(x, y - 5, x, y + 5, fill="#888", width=1)
            c.create_text(x, y + 14, text=_fmt_time(dur * i / (n - 1)), fill=MUTED,
                          font=("Segoe UI", 7))
        frac = 0 if dur <= 0 else min(1.0, self.play_pos / dur)
        px = 8 + (w - 16) * frac
        c.create_line(px, 2, px, 32, fill=RED, width=2)
        c.create_polygon(px - 5, 2, px + 5, 2, px, 10, fill=RED, outline="")

    def _tog_mute(self, path):
        st = self.settings.setdefault(path, {})
        st["mute"] = not st.get("mute", False)
        self._tab(self._stem_tab)

    def _tog_solo(self, path):
        st = self.settings.setdefault(path, {})
        st["solo"] = not st.get("solo", False)
        self._tab(self._stem_tab)

    def _seek0(self):
        was = m.is_playing()
        self._apply_seek(0.0, resume=was and self.current is not None)

    def _stems_preview(self):
        self.set_status("Preview STEMS…", 7, 12)

        def work():
            total = max(1, len([c for c in self.classified.values() if c != "Alignment / Referencia"]))
            self.root.after(0, lambda: self.set_status("Render stems…", 1, total + 2))
            preview, _ = m.render_state(self.sources, self.classified, self.settings,
                                        self.tmp, "PREVIEW_LIVE",
                                        sample_rate=self.output_sr or 44100,
                                        progress=lambda i, n, d: self.root.after(
                                            0, lambda: self.set_status(d, i, n)))
            if self.target is not None:
                self.root.after(0, lambda: self.set_status("Loudness…", total + 1, total + 2))
                loud = self.tmp / "PREVIEW_LIVE_LOUD.wav"
                m.apply_loudness(preview, self.target, loud)
                preview = loud
            return Path(preview)

        def ok(preview):
            self.current = preview
            if preview not in self.preview_versions:
                self.preview_versions.append(preview)
            try:
                self.preview_analysis = m.analyze_basic(self.current)
                self.duration_s = float(self.preview_analysis.get("duration") or 0)
                self.output_sr = int(self.preview_analysis.get("sr") or self.output_sr or 44100)
            except Exception:
                pass
            m.play_audio(self.current, "stems")
            self.play_pos = 0.0
            self._start_tick()
            self._draw_stems_tl()
            self.set_status("Preview listo", detail=self.current.name)

        self._run_bg(work, on_ok=ok, err_hint="Revisa mute/solo y que haya stems válidos.")

    def _stems_ab(self):
        if not self.current:
            messagebox.showinfo("A/B", "Genera PREVIEW primero.", parent=self.root)
            return

        def work():
            base, _ = m.render_state(self.sources, self.classified, self.accepted_settings,
                                     self.tmp, "AB_A", sample_rate=self.output_sr or 44100)
            if self.target is not None:
                loud = self.tmp / "AB_A_LOUD.wav"
                m.apply_loudness(base, self.target, loud)
                base = loud
            return Path(base)

        self._run_bg(work, on_ok=lambda a: m.ab_compare(a, self.current, "Aceptado", "Actual", True))

    def _stems_afinar(self):
        """Diálogo moderno: Low/Medium/High/Heavy + % + nota detectada."""
        self._halt_playback()
        vocals = [p for p, c in self.classified.items()
                  if c not in ("Alignment / Referencia", "Beat")]
        if not vocals:
            messagebox.showinfo("Afinar", "No hay stems de voz.", parent=self.root)
            return
        target = self.last_target_stem if self.last_target_stem in vocals else vocals[0]
        win = tk.Toplevel(self.root)
        win.title("Afinar — nota a nota")
        win.configure(bg=CARD)
        win.geometry("480x420")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="AFINAR", fg=RED, bg=CARD,
                 font=("Segoe UI Black", 14)).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(win, text="Corrección nota a nota (sin ganancia automática)",
                 fg=MUTED, bg=CARD, font=("Segoe UI", 9)).pack(anchor="w", padx=20)

        stem_var = tk.StringVar(value=str(vocals.index(target)))
        tk.Label(win, text="Stem", fg=MUTED, bg=CARD, font=("Segoe UI", 8)).pack(anchor="w", padx=20, pady=(12, 2))
        for i, p in enumerate(vocals):
            tk.Radiobutton(win, text=f"{_stem_label(self.classified[p])} — {p.name}",
                           variable=stem_var, value=str(i), bg=CARD, fg=FG,
                           selectcolor=BTN_DARK, activebackground=CARD,
                           font=("Segoe UI", 9)).pack(anchor="w", padx=24)

        levels = [("Low", 0.35), ("Medium", 0.55), ("High", 0.75), ("Heavy", 0.95)]
        level_var = tk.StringVar(value="High")
        pct_var = tk.IntVar(value=75)
        note_lbl = tk.Label(win, text="Nota detectada: analizando…", fg=FG, bg=CARD,
                            font=("Segoe UI Semibold", 10))
        note_lbl.pack(anchor="w", padx=20, pady=(10, 4))

        def set_level(name, val):
            level_var.set(name)
            pct_var.set(int(round(val * 100)))

        lv = tk.Frame(win, bg=CARD)
        lv.pack(anchor="w", padx=20, pady=6)
        for name, val in levels:
            tk.Button(lv, text=name, command=lambda n=name, v=val: set_level(n, v),
                      bg=BTN_DARK, fg=RED, relief="solid", highlightbackground=RED,
                      highlightthickness=1, padx=10, pady=6,
                      font=("Segoe UI Semibold", 9), cursor="hand2").pack(side="left", padx=3)

        tk.Label(win, text="Intensidad %", fg=MUTED, bg=CARD, font=("Segoe UI", 8)).pack(anchor="w", padx=20)
        tk.Scale(win, from_=0, to=100, orient="horizontal", variable=pct_var,
                 bg=CARD, fg=FG, troughcolor=RED, highlightthickness=0,
                 length=360).pack(anchor="w", padx=20)

        # Detectar nota dominante en background
        def detect():
            try:
                src = self.sources.get(target, target)
                notes, _ = m.segment_notes(src)
                if notes:
                    # nota más larga
                    best = max(notes, key=lambda n: n["end"] - n["start"])
                    midi = best["midi"]
                    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
                    nm = names[int(round(midi)) % 12]
                    octv = int(round(midi) // 12) - 1
                    note_lbl.config(text=f"Nota dominante ≈ {nm}{octv}  ({best['hz']:.1f} Hz)  ·  {len(notes)} notas")
                else:
                    note_lbl.config(text="Nota detectada: (sin pitch claro)")
            except Exception as e:
                note_lbl.config(text=f"Nota: no disponible ({e})")

        self.root.after(80, detect)

        result = {"ok": False}

        def go():
            result["ok"] = True
            result["idx"] = int(stem_var.get())
            result["pct"] = pct_var.get()
            win.destroy()

        tk.Button(win, text="APLICAR AFINACIÓN", command=go, bg=RED, fg=FG,
                  relief="flat", font=("Segoe UI Semibold", 10),
                  padx=16, pady=10, cursor="hand2").pack(pady=16)
        self.root.wait_window(win)
        if not result.get("ok"):
            return
        target = vocals[result["idx"]]
        intensity = max(0.0, min(1.0, result["pct"] / 100.0))
        self.set_status("Afinando nota a nota…", detail=f"{target.name} · {result['pct']}%")

        def work():
            out = self.tmp / (target.stem + "_TUNED.wav")
            src = self.sources.get(target, target)
            info = m.tune_stem_note_by_note(src, out, intensity=intensity, preserve_formants=True)
            self.settings.setdefault(target, {})["tuned_path"] = str(out)
            return info

        def ok(info):
            self.last_target_stem = target
            messagebox.showinfo(
                "Afinar",
                f"Notas: {info.get('notes', 0)}\n"
                f"Intensidad: {intensity*100:.0f}%\n"
                f"Formantes: {'sí' if info.get('formants') else 'aprox.'}\n"
                "Pulsa PREVIEW para escuchar.",
                parent=self.root)
            self._stems_desk()

        self._run_bg(work, on_ok=ok, err_hint="Prueba nivel Low o Medium.")

    def _stems_realign(self):
        """Menú moderno de alineación + mover clips manualmente (ms)."""
        self._halt_playback()
        ref = next((p for p, c in self.classified.items() if c == "Alignment / Referencia"), None)
        if not ref:
            self._error("Alinear", "No hay referencia Alignment.", "Clasifica un stem como REF.")
            return
        win = tk.Toplevel(self.root)
        win.title("Alinear stems")
        win.configure(bg=CARD)
        win.geometry("520x480")
        win.transient(self.root)
        win.grab_set()
        tk.Label(win, text="ALINEAR", fg=RED, bg=CARD,
                 font=("Segoe UI Black", 14)).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(win, text="Auto-align con score · o mueve clips manualmente (ms)",
                 fg=MUTED, bg=CARD, font=("Segoe UI", 9)).pack(anchor="w", padx=20)

        body = tk.Frame(win, bg=CARD)
        body.pack(fill="both", expand=True, padx=16, pady=10)
        vars_ms = {}
        playable = [(p, c) for p, c in self.classified.items() if c != "Alignment / Referencia"]
        for p, cat in playable:
            rep = self._align_reports.get(p, {})
            cur = float(self._manual_offsets.get(p, rep.get("offset_s") or 0)) * 1000
            row = tk.Frame(body, bg=CARD)
            row.pack(fill="x", pady=4)
            tk.Label(row, text=_stem_label(cat), fg=FG, bg=CARD, width=12, anchor="w",
                     font=("Segoe UI Semibold", 9)).pack(side="left")
            sc = float(rep.get("score") or 0)
            tk.Label(row, text=f"score {sc:.2f}", fg=MUTED, bg=CARD,
                     font=("Segoe UI", 8), width=10).pack(side="left")
            v = tk.DoubleVar(value=cur)
            vars_ms[p] = v
            tk.Scale(row, from_=-500, to=500, resolution=1, orient="horizontal",
                     variable=v, length=200, bg=CARD, fg=FG, troughcolor=RED,
                     highlightthickness=0, showvalue=1,
                     font=("Segoe UI", 7)).pack(side="left", padx=6)
            tk.Label(row, text="ms", fg=MUTED, bg=CARD, font=("Segoe UI", 8)).pack(side="left")

        choice = {"mode": None}

        def do_auto():
            choice["mode"] = "auto"
            win.destroy()

        def do_manual():
            for p, v in vars_ms.items():
                self._manual_offsets[p] = float(v.get()) / 1000.0
            choice["mode"] = "manual"
            win.destroy()

        btns = tk.Frame(win, bg=CARD)
        btns.pack(fill="x", padx=20, pady=12)
        tk.Button(btns, text="AUTO-ALIGN", command=do_auto, bg=RED, fg=FG,
                  relief="flat", padx=12, pady=8, font=("Segoe UI Semibold", 9),
                  cursor="hand2").pack(side="left", padx=4)
        tk.Button(btns, text="APLICAR OFFSETS MANUALES", command=do_manual, bg=BTN_DARK, fg=RED,
                  relief="solid", highlightbackground=RED, highlightthickness=1,
                  padx=12, pady=8, font=("Segoe UI Semibold", 9),
                  cursor="hand2").pack(side="left", padx=4)
        self.root.wait_window(win)
        if not choice["mode"]:
            return
        self.set_status("Alineando…", 3, 12)

        def work():
            if choice["mode"] == "auto":
                # limpia manuals para recalcular; conserva si score bajo pedirá ms
                self.sources = m.align_stems(self.classified, ref, self.tmp, manual_offsets=None)
            else:
                self.sources = m.align_stems(self.classified, ref, self.tmp,
                                             manual_offsets=self._manual_offsets)
            self._align_reports = getattr(m.align_stems, "last_reports", {}) or {}
            return True

        def ok(_):
            if choice["mode"] == "auto" and any(
                    r.get("needs_manual") for r in self._align_reports.values()):
                self._stems_after_align()
            else:
                self._stems_desk()
            lines = [
                f"{_stem_label(r.get('category'))}: {float(r.get('offset_s') or 0)*1000:+.0f} ms "
                f"(score {float(r.get('score') or 0):.2f})"
                for r in self._align_reports.values()]
            messagebox.showinfo("Alinear", "\n".join(lines) or "Sin cambios.", parent=self.root)

        self._run_bg(work, on_ok=ok)

    def _stems_undo(self):
        if len(self.stem_history) <= 1:
            messagebox.showinfo("Undo", "No hay un ajuste aceptado anterior.", parent=self.root)
            return
        self.stem_history.pop()
        self.accepted_settings = copy.deepcopy(self.stem_history[-1])
        self.settings = copy.deepcopy(self.accepted_settings)
        self.set_status("Undo STEMS", detail=f"Historial: {len(self.stem_history)}")

        def work():
            preview, _ = m.render_state(
                self.sources, self.classified, self.accepted_settings,
                self.tmp, f"UNDO_{len(self.stem_history):02d}",
                sample_rate=self.output_sr or 44100)
            if self.target is not None:
                loud = self.tmp / f"UNDO_{len(self.stem_history):02d}_LOUD.wav"
                m.apply_loudness(preview, self.target, loud)
                preview = loud
            return Path(preview)

        def ok(preview):
            self.current = preview
            try:
                self.preview_analysis = m.analyze_basic(self.current)
                self.duration_s = float(self.preview_analysis.get("duration") or 0)
            except Exception:
                pass
            self._stems_desk()

        self._run_bg(work, on_ok=ok)

    def _stems_nl(self):
        instruction = self._nl_text().lower()
        if not instruction:
            return
        result = m.feedback_instruction(instruction, self.classified,
                                        self.accepted_settings, self.last_target_stem)
        if not result:
            self._error("Ajuste", f'No identifiqué qué modificar:\n"{instruction}"',
                        "Ej: “bájale a los backs”, “más brillo a main vocal”.")
            return
        target_p, pending_st = result
        if not messagebox.askyesno(
                "Interpretación",
                f'Target: {_stem_label(self.classified[target_p])}\n'
                f'Cambio: {pending_st}\n\n¿Aplicar?', parent=self.root):
            return
        pending = copy.deepcopy(self.settings)
        merged = copy.deepcopy(pending.get(target_p, {}))
        merged.update(pending_st)
        pending[target_p] = merged
        self.set_status("Ajuste STEMS…", detail=instruction)

        def work():
            preview, _ = m.render_state(self.sources, self.classified, pending,
                                        self.tmp, f"PREV_{len(self.stem_history)+1:02d}",
                                        sample_rate=self.output_sr or 44100)
            if self.target is not None:
                loud = self.tmp / f"PREV_{len(self.stem_history)+1:02d}_LOUD.wav"
                m.apply_loudness(preview, self.target, loud)
                preview = loud
            return Path(preview), pending, target_p

        def ok(payload):
            preview, pending, target_p = payload
            self.current = preview
            self.settings = pending
            self.accepted_settings = copy.deepcopy(pending)
            self.stem_history.append(copy.deepcopy(pending))
            self.last_target_stem = target_p
            try:
                self.preview_analysis = m.analyze_basic(self.current)
                self.duration_s = float(self.preview_analysis.get("duration") or 0)
            except Exception:
                pass
            self._stems_desk()
            m.play_audio(self.current)
            self._start_tick()

        self._run_bg(work, on_ok=ok)

    def _stems_accept(self):
        self._halt_playback()
        self.accepted_settings = copy.deepcopy(self.settings)
        self.stem_history.append(copy.deepcopy(self.accepted_settings))
        export_vocals = messagebox.askyesno(
            "Exportar",
            "¿Exportar también los stems vocales ya procesados (WAV) "
            "en la misma carpeta que el master?",
            parent=self.root)

        def work():
            self.set_status("Render master…", 10, 12)
            preview, rendered = m.render_state(
                self.sources, self.classified, self.accepted_settings,
                self.tmp, "STEMS_FINAL", sample_rate=self.output_sr or 44100)
            final = self._versioned_path(self.tmp, "STEMS", suffix="_MASTER_FINAL.wav")
            if self.target is not None:
                m.apply_loudness(preview, self.target, final)
            else:
                shutil.copy2(preview, final)
            vocal_dir = None
            if export_vocals:
                vocal_dir = self.tmp / "STEMS_VOCALES_PROCESADOS"
                vocal_dir.mkdir(exist_ok=True)
                for processed, cat, orig in rendered:
                    if cat not in ("Beat", "Alignment / Referencia"):
                        shutil.copy2(processed, vocal_dir / (orig.stem + "_PROCESADO.wav"))
            return Path(final), vocal_dir

        def ok(payload):
            final, vocal_dir = payload
            self.current = final
            self.set_status("Listo", 12, 12, str(final))
            self._clear_body()
            outer, card = self._card(self.body)
            outer.pack(fill="both", expand=True)
            tk.Label(card, text="STEMS MASTER", fg=RED, bg=CARD,
                     font=("Segoe UI Semibold", 11)).pack(anchor="w")
            tk.Label(card, text=str(final), fg=FG, bg=CARD,
                     font=("Segoe UI Semibold", 12)).pack(anchor="w", pady=8)
            if vocal_dir:
                tk.Label(card, text=f"Voces: {vocal_dir}", fg=MUTED, bg=CARD,
                         font=("Segoe UI", 9)).pack(anchor="w")
            self._primary(card, "REPRODUCIR", lambda: m.play_audio(final), "▶").pack(anchor="w", pady=4)
            self._ghost(card, "Abrir carpeta", lambda: os.startfile(str(self.tmp))).pack(anchor="w", pady=4)
            self._ghost(card, "Volver al inicio", self._finish_session).pack(anchor="w", pady=12)

        self._run_bg(work, on_ok=ok, err_hint="Revisa espacio en disco y FFmpeg.")

    def run(self):
        self.root.mainloop()


def launch(hide_console=True):
    if hide_console:
        _hide_console()
    app = MixFlowApp()

    class _AppHud:
        disabled = False
        def update(self, stage, step=None, total=None, detail=""):
            try:
                app.set_status(stage, step, total, detail)
            except Exception:
                pass
        def close(self):
            pass
        def ensure(self):
            return True

    m._HUD = _AppHud()
    m._HUD_DISABLED = False
    app.run()


if __name__ == "__main__":
    launch(hide_console=True)
