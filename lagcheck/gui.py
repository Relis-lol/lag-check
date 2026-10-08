"""Tk desktop interface. All sampling runs in a separate, cooperative worker."""

import csv
import datetime as dt
import json
import os
import pathlib
import subprocess
import sys
import time
import tkinter as tk
from collections import deque
from tkinter import filedialog, messagebox, ttk

from . import __version__
from .analysis import KINDS, format_result, local_time, safe_export
from .config import DATA

BG, PANEL, FIELD = "#101923", "#192735", "#223443"
FG, MUTED, ACCENT, AMBER = "#eff4f8", "#b2c1cf", "#7de2b4", "#ffcd82"

HELP = """SO GEHT'S

1. „Messung starten“ anklicken und wie gewohnt spielen.
2. Bei einem Ruckler kurz zur App wechseln und den passenden Marker drücken.
   „Bild hängt“: Das Bild friert ein. „Zurückgesetzt“: Bewegung wird korrigiert,
   die Welt steht oder Figuren springen. „Anderer Ruckler“: wenn du unsicher bist.
3. „Stoppen & auswerten“ anklicken. Nach einem Marker sammelt die App noch
   bis zu 10 Sekunden weiter. Danach die Ergebnisse öffnen.

Die App darf minimiert werden. Sie hat kein Overlay und keine globale
Tastenerfassung. F6 / F7 / F8 markieren nur, wenn dieses Fenster aktiv ist.
Alt-Tab ist erlaubt: Lass „Ich tabbe häufig raus“ eingeschaltet.

ERGEBNISSE VERSTEHEN

Router auffällig: Eine lokale Verbindung oder der Router könnte beteiligt sein.
Internet auffällig: Externe Pings sind auffällig, während der Router antwortet.
PC auffällig: Zeitgleich erhöhte Systemlast, aber noch kein Beweis einer Ursache.
Spielroute / Server: Nur eine offene Möglichkeit bei einem Rubberband-Marker
und sauberen Messwerten. Der Spielserver wird nicht untersucht.
Ursache offen: Die Messwerte liefern keinen eindeutigen Hinweis.

Ein Ping misst die Antwortzeit einer ICMP-Probe. ICMP kann gefiltert oder
nachrangig behandelt werden; ein Timeout ist kein Beweis für Spiel-Paketverlust.
Ein Sample pro Sekunde kann sehr kurze Störungen übersehen. GPU-Abfälle beim
Raustabben und hohe GPU-Last beim Spielen sind nicht automatisch Fehler.

DATENSCHUTZ

Kein Konto, keine Telemetrie, keine Uploads, keine automatische Update-Prüfung.
Bei aktivierten Netzwerkproben gehen etwa drei kleine ICMP-Pakete pro Sekunde
an den Router sowie Cloudflare und Google. Diese Ziele sehen technisch die
Absenderadresse. Mit ausgeschalteten Netzwerkproben gibt es diese Proben nicht.

Rohdaten bleiben lokal: %LOCALAPPDATA%\\LagCheck\\sessions.
Sie können lokale IPs, Adapterbezeichnungen, Zeitpunkte und Windows-
Ereignismeldungen enthalten. Poste niemals den kompletten Sitzungsordner.
„Datensparsam exportieren“ erstellt eine neue Datei mit ausgewählten Zahlen
und Kategorien, ohne IPs, Pfade, Gerätenamen oder absolute Zeitstempel.
Auch diese Datei vor einer Weitergabe prüfen. Die App lädt nichts selbst hoch.

ANFORDERUNGEN UND RISIKEN

Windows 10/11, 64 Bit; eine normale Benutzersitzung. Für die EXE wird kein Python
benötigt. Kein Administrator nötig. Einige Counter können trotzdem fehlen.
GPU-Daten hängen von Windows und Treiber ab. Temperatur, GPU-Takt, genaue
VRAM-Kapazität sowie FPS/Frametimes werden nicht erfasst. Nur IPv4-Ping.

Die App liest Systemzähler und optional das Windows-Systemprotokoll. Keine
Spielprozesse, Spielspeicher, Spieldateien, Logs, Injection, Hooks oder Anti-Cheat-
Schnittstellen. Keine Optimierungen oder Systemänderungen. Eine Freigabe durch
Spielehersteller oder Anti-Cheat-Anbieter wird nicht zugesichert.

Benutzung auf eigene Verantwortung, ohne Garantie, soweit rechtlich zulässig.
Der Monitor verbraucht selbst etwas CPU, RAM, Speicherplatz und Netzwerk.
Richtwert für Rohdaten: einige Dutzend MB je Stunde, abhängig vom System.
Dateien werden nicht automatisch gelöscht. Alte Sitzungen kannst du bei
gestoppter Messung über „Datenordner“ im Explorer entfernen.
Keine Treiber oder Schutzfunktionen aufgrund einzelner Messwerte verändern.

OFFEN UND ÜBERPRÜFBAR

Lag Check ist ein unabhängiges Community-Projekt unter der MIT-Lizenz.
Keine Verbindung zu einem Spielehersteller; kein offizielles Diagnosezertifikat.
Projekt: https://github.com/Relis-lol/lag-check
Die portable EXE ist nicht digital signiert. Prüfsumme und Herkunft kontrollieren;
bei Unsicherheit nicht starten und Schutzsoftware nicht deaktivieren.
"""


def load(path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        return default


def monitor_running():
    import msvcrt

    DATA.mkdir(parents=True, exist_ok=True)
    with (DATA / "monitor.lock").open("a+b") as handle:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            return True
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    return False


class App:
    def __init__(self, root):
        self.root = root
        root.title("Lag Check")
        root.geometry("1120x800")
        root.minsize(960, 720)
        root.configure(bg=BG)
        root.protocol("WM_DELETE_WINDOW", self.close)
        self.process = None
        self.worker_log = None
        self.folder = None
        self.result = None
        self.running = False
        self.stopping = False
        self.stop_at = None
        self.close_after_stop = False
        self.last_marker = 0
        self.last_sample = None
        self.chart_data = deque(maxlen=120)
        self.last_refresh = 0
        self.style()
        self.build()
        for key, kind in [("F6", "FREEZE"), ("F7", "RUBBERBAND"), ("F8", "LAG")]:
            root.bind("<" + key + ">", lambda event, k=kind: self.mark(k))
        self.refresh_history()
        active = load(DATA / "active.json")
        if active and monitor_running():
            self.folder = pathlib.Path(active["session"])
            self.running = True
            self.network.set(active.get("options", {}).get("network", True))
            self.events.set(active.get("options", {}).get("events", True))
            self.alt_tab.set(active.get("options", {}).get("alt_tab", True))
            self.set_controls(True)
        self.tick()

    def style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure(
            "TButton", background=FIELD, foreground=FG, padding=(14, 10), borderwidth=0
        )
        style.map(
            "TButton",
            background=[("active", "#314b5d"), ("disabled", PANEL)],
            foreground=[("disabled", "#6e8293")],
        )
        style.configure(
            "Accent.TButton",
            background=ACCENT,
            foreground=BG,
            font=("Segoe UI Semibold", 11),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#a0edcb"), ("disabled", PANEL)],
            foreground=[("disabled", MUTED)],
        )
        style.configure("TCheckbutton", background=PANEL, foreground=FG, padding=4)
        style.map("TCheckbutton", background=[("active", PANEL)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab", background=PANEL, foreground=MUTED, padding=(20, 10)
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", FIELD)],
            foreground=[("selected", ACCENT)],
        )
        style.configure(
            "Treeview",
            background=PANEL,
            fieldbackground=PANEL,
            foreground=FG,
            rowheight=34,
            borderwidth=0,
        )
        style.configure(
            "Treeview.Heading", background=FIELD, foreground=MUTED, padding=8
        )
        style.map(
            "Treeview",
            background=[("selected", "#315445")],
            foreground=[("selected", FG)],
        )

    def label(self, parent, text, size=10, color=FG, bg=BG, **kwargs):
        return tk.Label(
            parent,
            text=text,
            bg=bg,
            fg=color,
            font=("Segoe UI", size),
            anchor="w",
            **kwargs,
        )

    def build(self):
        head = tk.Frame(self.root, bg=BG)
        head.pack(fill="x", padx=28, pady=(12, 10))
        self.label(head, "LAG CHECK", 22, color=ACCENT).pack(side="left")
        self.label(head, "  /  Ruckler verstehen.", 13, color=MUTED).pack(
            side="left", padx=12
        )
        self.label(head, "WINDOWS  ·  v" + __version__, 10, color=MUTED).pack(
            side="right"
        )
        self.book = ttk.Notebook(self.root)
        self.book.pack(fill="both", expand=True, padx=28, pady=(0, 8))
        self.live = tk.Frame(self.book, bg=BG)
        self.history = tk.Frame(self.book, bg=BG)
        self.help = tk.Frame(self.book, bg=BG)
        self.book.add(self.live, text="Messung")
        self.book.add(self.history, text="Ergebnisse")
        self.book.add(self.help, text="Anleitung & Sicherheit")

        hero = tk.Frame(self.live, bg=PANEL, padx=22, pady=12)
        hero.pack(fill="x", pady=(12, 10))
        self.state_label = self.label(
            hero, "Bereit, wenn der nächste Ruckler kommt.", 18, bg=PANEL
        )
        self.state_label.pack(anchor="w")
        self.status = self.label(
            hero,
            "1  Starten     →     2  Bei einem Lag markieren     →     3  Auswerten",
            10,
            color=MUTED,
            bg=PANEL,
        )
        self.status.pack(anchor="w", pady=(6, 12))
        actions = tk.Frame(hero, bg=PANEL)
        actions.pack(fill="x")
        self.start_button = ttk.Button(
            actions, text="Messung starten", style="Accent.TButton", command=self.start
        )
        self.start_button.pack(side="left")
        self.stop_button = ttk.Button(
            actions, text="Stoppen & auswerten", command=self.stop, state="disabled"
        )
        self.stop_button.pack(side="left", padx=10)
        self.elapsed = self.label(
            actions, "00:00   ·   0 Marker", 12, color=MUTED, bg=PANEL
        )
        self.elapsed.pack(side="right")
        self.network = tk.BooleanVar(value=True)
        self.events = tk.BooleanVar(value=True)
        self.alt_tab = tk.BooleanVar(value=True)
        checks = tk.Frame(hero, bg=PANEL)
        checks.pack(fill="x", pady=(10, 0))
        self.checks = []
        for text, var in [
            ("Netzwerkproben", self.network),
            ("Windows-Ereignisse", self.events),
            ("Ich tabbe häufig raus", self.alt_tab),
        ]:
            cb = ttk.Checkbutton(checks, text=text, variable=var)
            cb.pack(side="left", padx=(0, 16))
            self.checks.append(cb)
        self.label(
            hero,
            "Netzwerkproben senden kleine Pings an Router, Cloudflare und Google. Keine Uploads.",
            9,
            color=MUTED,
            bg=PANEL,
        ).pack(anchor="w", pady=(7, 0))

        cards = tk.Frame(self.live, bg=BG)
        cards.pack(fill="x", pady=(0, 12))
        self.cards = {}
        for index, (key, title) in enumerate(
            [
                ("cpu_pct", "CPU"),
                ("gpu_pct", "GPU"),
                ("ram_pct", "ARBEITSSPEICHER"),
                ("gateway", "ROUTER"),
                ("cloudflare", "INTERNET A"),
                ("google", "INTERNET B"),
            ]
        ):
            cards.columnconfigure(index, weight=1, uniform="card")
            frame = tk.Frame(cards, bg=PANEL, padx=14, pady=9)
            frame.grid(
                row=0, column=index, sticky="nsew", padx=(0, 8 if index < 5 else 0)
            )
            self.label(frame, title, 9, color=MUTED, bg=PANEL).pack(anchor="w")
            value = self.label(frame, "—", 22, bg=PANEL)
            value.pack(anchor="w", pady=(3, 0))
            self.cards[key] = value
        chart_head = tk.Frame(self.live, bg=BG)
        chart_head.pack(fill="x")
        self.label(chart_head, "SYSTEMLAST · LETZTE 2 MINUTEN", 9, color=MUTED).pack(
            side="left"
        )
        self.label(
            chart_head, "CPU  grün     GPU  blau     RAM  sand", 9, color=MUTED
        ).pack(side="right")
        self.chart = tk.Canvas(self.live, bg=PANEL, height=88, highlightthickness=0)
        self.chart.pack(fill="x", pady=(6, 12))
        self.chart.bind("<Configure>", lambda e: self.draw_chart())

        self.label(self.live, "Gerade geruckelt? Setze einen Marker.", 14).pack(
            anchor="w"
        )
        marker_actions = tk.Frame(self.live, bg=BG)
        marker_actions.pack(fill="x", pady=(8, 6))
        self.marker_buttons = []
        for text, kind in [
            ("Bild hängt  ·  F6", "FREEZE"),
            ("Zurückgesetzt / Welt steht  ·  F7", "RUBBERBAND"),
            ("Anderer Ruckler  ·  F8", "LAG"),
        ]:
            button = ttk.Button(
                marker_actions,
                text=text,
                command=lambda k=kind: self.mark(k),
                state="disabled",
            )
            button.pack(side="left", fill="x", expand=True, padx=(0, 8))
            self.marker_buttons.append(button)
        self.marker_feedback = self.label(
            self.live,
            "F6–F8 funktionieren nur in diesem Fenster. Kein Overlay, keine globalen Hotkeys.",
            9,
            color=MUTED,
        )
        self.marker_feedback.pack(anchor="w", pady=(0, 8))
        self.marker_tree = ttk.Treeview(
            self.live, columns=("time", "kind"), show="headings", height=3
        )
        self.marker_tree.heading("time", text="Markerzeit (lokal)")
        self.marker_tree.heading("kind", text="Was du bemerkt hast")
        self.marker_tree.column("time", width=200, stretch=False)
        self.marker_tree.pack(fill="both", expand=True)

        top = tk.Frame(self.history, bg=BG)
        top.pack(fill="x", pady=14)
        self.label(top, "Deine Messungen", 18).pack(side="left")
        ttk.Button(top, text="Aktualisieren", command=self.refresh_history).pack(
            side="right"
        )
        self.history_tree = ttk.Treeview(
            self.history,
            columns=("date", "duration", "markers", "state"),
            show="headings",
            height=4,
        )
        for k, t, w in [
            ("date", "Beginn (lokal)", 220),
            ("duration", "Dauer", 100),
            ("markers", "Marker", 90),
            ("state", "Status", 240),
        ]:
            self.history_tree.heading(k, text=t)
            self.history_tree.column(k, width=w)
        self.history_tree.pack(fill="x")
        self.history_tree.bind("<<TreeviewSelect>>", self.select_session)
        row = tk.Frame(self.history, bg=BG)
        row.pack(fill="x", pady=12)
        self.report_button = ttk.Button(
            row,
            text="Lesbaren Bericht öffnen",
            command=self.open_report,
            state="disabled",
        )
        self.report_button.pack(side="left")
        self.export_button = ttk.Button(
            row, text="Datensparsam exportieren", command=self.export, state="disabled"
        )
        self.export_button.pack(side="left", padx=8)
        ttk.Button(
            row,
            text="Datenordner",
            command=lambda: os.startfile(str(DATA / "sessions")),
        ).pack(side="right")
        self.result_text = self.text_box(self.history)
        self.set_text(
            self.result_text,
            "Noch keine Auswertung ausgewählt.\n\nStarte eine Messung, markiere Ruckler und stoppe danach.\nDie Ergebnisse werden hier verständlich zusammengefasst.",
        )
        self.help_text = self.text_box(self.help)
        self.set_text(self.help_text, HELP)
        self.label(
            self.root,
            "LOKAL GESPEICHERT   ·   Kein Zugriff auf dein Spiel   ·   Hinweise statt Schuldzuweisungen",
            9,
            color=MUTED,
        ).pack(anchor="w", padx=28, pady=(0, 14))

    def text_box(self, parent):
        frame = tk.Frame(parent, bg=PANEL)
        frame.pack(fill="both", expand=True, pady=(0, 8))
        text = tk.Text(
            frame,
            bg=PANEL,
            fg=FG,
            insertbackground=FG,
            wrap="word",
            font=("Segoe UI", 11),
            padx=18,
            pady=16,
            relief="flat",
            spacing3=6,
        )
        scrollbar = ttk.Scrollbar(frame, command=text.yview)
        scrollbar.pack(side="right", fill="y")
        text.configure(yscrollcommand=scrollbar.set)
        text.pack(fill="both", expand=True)
        return text

    def set_text(self, widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def set_controls(self, running):
        self.start_button.configure(state="disabled" if running else "normal")
        self.stop_button.configure(
            state="normal" if running and not self.stopping else "disabled"
        )
        for cb in self.checks:
            cb.configure(state="disabled" if running else "normal")
        for button in self.marker_buttons:
            button.configure(
                state="normal" if running and not self.stopping else "disabled"
            )

    def start(self):
        if self.running:
            return
        if monitor_running():
            messagebox.showinfo(
                "Messung läuft",
                "Eine Messung läuft bereits. App neu öffnen, um sie anzuzeigen.",
            )
            return
        args = [sys.executable]
        if not getattr(sys, "frozen", False):
            args.append(str(pathlib.Path(__file__).resolve().parent.parent / "run.py"))
        args += ["--monitor", "--data-dir", str(DATA)]
        if not self.network.get():
            args.append("--no-network")
        if not self.events.get():
            args.append("--no-events")
        if not self.alt_tab.get():
            args.append("--no-alt-tab")
        try:
            self.worker_log = (DATA / "worker.log").open("w", encoding="utf-8")
            self.process = subprocess.Popen(
                args,
                stdout=self.worker_log,
                stderr=self.worker_log,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except OSError as exc:
            if self.worker_log:
                self.worker_log.close()
                self.worker_log = None
            messagebox.showerror("Start nicht möglich", str(exc))
            return
        self.folder = None
        self.running = True
        self.stopping = False
        self.last_marker = 0
        self.last_sample = None
        self.chart_data.clear()
        self.marker_tree.delete(*self.marker_tree.get_children())
        self.set_controls(True)
        self.state_label.configure(text="Messung wird vorbereitet …")

    def mark(self, kind):
        if not self.running or self.stopping or not self.folder:
            return
        try:
            from .engine import mark

            mark(kind)
            self.last_marker = time.monotonic()
            self.marker_feedback.configure(
                text="Marker gespeichert: "
                + KINDS[kind]
                + " · "
                + dt.datetime.now().strftime("%H:%M:%S"),
                fg=ACCENT,
            )
            self.update_markers()
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Marker nicht gespeichert", str(exc))

    def stop(self):
        if not self.running or self.stopping:
            return
        self.stopping = True
        self.stop_at = max(time.monotonic(), self.last_marker + 10.5)
        self.set_controls(True)

    def update_markers(self):
        if not self.folder:
            return
        try:
            with (self.folder / "lag_markers.csv").open(
                encoding="utf-8-sig", newline=""
            ) as f:
                markers = list(csv.DictReader(f))
            self.marker_tree.delete(*self.marker_tree.get_children())
            for m in markers[-30:]:
                self.marker_tree.insert(
                    "",
                    0,
                    values=(
                        local_time(m["timestamp"]),
                        KINDS.get(m["kind"], "Ruckler"),
                    ),
                )
            return len(markers)
        except (OSError, KeyError, ValueError):
            return 0

    def tick(self):
        try:
            if self.running:
                active = load(DATA / "active.json")
                if active and (
                    self.process is None or active.get("pid") == self.process.pid
                ):
                    self.folder = pathlib.Path(active["session"])
                if self.folder:
                    meta = load(self.folder / "session_info.json", {})
                    live = load(self.folder / "live.json", {})
                    if live:
                        age = (
                            time.time()
                            - dt.datetime.fromisoformat(live["timestamp"]).timestamp()
                        )
                        for k in ("cpu_pct", "gpu_pct", "ram_pct"):
                            v = live.get(k)
                            self.cards[k].configure(
                                text=f"{v:.0f} %"
                                if isinstance(v, (float, int)) and age < 5
                                else "—"
                            )
                        if self.last_sample != live["timestamp"]:
                            self.chart_data.append(live)
                            self.last_sample = live["timestamp"]
                            self.draw_chart()
                        self.state_label.configure(
                            text="Messung läuft. Spiel einfach weiter."
                            if age < 5
                            else "Messwerte verzögert – bitte warten …"
                        )
                    for label in ("gateway", "cloudflare", "google"):
                        ping = load(self.folder / f"ping_{label}.json", {})
                        fresh = bool(
                            ping
                            and time.time()
                            - dt.datetime.fromisoformat(ping["timestamp"]).timestamp()
                            < 5
                        )
                        text = (
                            f"{ping['rtt_ms']} ms"
                            if fresh and ping.get("status") == "SUCCESS"
                            else "Timeout"
                            if fresh and ping.get("status") == "TIMEOUT"
                            else "—"
                        )
                        self.cards[label].configure(text=text)
                    duration = (
                        max(
                            0,
                            int(
                                time.time()
                                - dt.datetime.fromisoformat(meta["start"]).timestamp()
                            ),
                        )
                        if meta.get("start")
                        else 0
                    )
                    count = self.update_markers() or 0
                    self.elapsed.configure(
                        text=f"{duration // 60:02}:{duration % 60:02}   ·   {count} Marker"
                    )
                    self.status.configure(
                        text="Ein Messpunkt pro Sekunde · Daten bleiben auf diesem PC"
                    )
                    if self.stopping:
                        remaining = max(0, math_ceil(self.stop_at - time.monotonic()))
                        self.state_label.configure(
                            text=f"Noch {remaining} Sekunden nach dem Marker …"
                            if remaining
                            else "Auswertung wird erstellt …"
                        )
                        if not remaining:
                            (self.folder / "stop.request").touch(exist_ok=True)
                finished = (
                    self.process.poll() is not None
                    if self.process
                    else not monitor_running()
                )
                if finished:
                    self.finished()
        except (OSError, KeyError, ValueError):
            self.status.configure(
                text="Daten momentan nicht lesbar. Die App versucht es erneut."
            )
        if not (self.close_after_stop and not self.running):
            self.root.after(1000, self.tick)

    def finished(self):
        self.running = False
        self.stopping = False
        self.set_controls(False)
        if self.worker_log:
            self.worker_log.close()
            self.worker_log = None
        if self.folder and (self.folder / "analysis.json").exists():
            self.state_label.configure(text="Fertig. Deine Auswertung ist da.")
            self.refresh_history(select=self.folder)
            self.book.select(self.history)
        else:
            self.state_label.configure(
                text="Die Messung konnte nicht abgeschlossen werden."
            )
            messagebox.showerror(
                "Messung unterbrochen",
                "Die bisherigen lokalen Daten bleiben erhalten. Details stehen in worker.log im Datenordner. Es wurden keine Prozesse beendet oder Systemeinstellungen geändert.",
            )
        if self.close_after_stop:
            self.root.destroy()

    def draw_chart(self):
        self.chart.delete("all")
        width = max(100, self.chart.winfo_width())
        height = 88
        for p in (0, 50, 100):
            y = height - 12 - (height - 24) * p / 100
            self.chart.create_line(30, y, width - 8, y, fill="#304253")
            self.chart.create_text(17, y, text=str(p), fill=MUTED, font=("Segoe UI", 8))
        for key, color in [
            ("cpu_pct", ACCENT),
            ("gpu_pct", "#81bfff"),
            ("ram_pct", AMBER),
        ]:
            segment = []
            for i, row in enumerate(self.chart_data):
                v = row.get(key)
                if isinstance(v, (int, float)):
                    segment += [
                        32 + i * (width - 44) / 119,
                        height - 12 - (height - 24) * max(0, min(100, v)) / 100,
                    ]
                else:
                    if len(segment) >= 4:
                        self.chart.create_line(*segment, fill=color, width=2)
                    segment = []
            if len(segment) >= 4:
                self.chart.create_line(*segment, fill=color, width=2)

    def refresh_history(self, select=None):
        self.history_tree.delete(*self.history_tree.get_children())
        sessions = DATA / "sessions"
        sessions.mkdir(parents=True, exist_ok=True)
        self.session_paths = {}
        for p in sorted(sessions.iterdir(), reverse=True):
            if not p.is_dir():
                continue
            meta = load(p / "session_info.json", {})
            if not meta.get("start"):
                continue
            result = load(p / "analysis.json")
            duration = (
                f"{(result.get('duration_s') or 0) / 60:.1f} min" if result else "—"
            )
            state = (
                "Ausgewertet"
                if result
                else "Läuft"
                if self.running and p == self.folder
                else "Unvollständig"
            )
            iid = self.history_tree.insert(
                "",
                "end",
                values=(
                    local_time(meta["start"]),
                    duration,
                    len(result["markers"]) if result else "—",
                    state,
                ),
            )
            self.session_paths[iid] = p
            if select == p:
                self.history_tree.selection_set(iid)
                self.history_tree.see(iid)

    def select_session(self, event=None):
        chosen = self.history_tree.selection()
        if not chosen:
            return
        self.selected_folder = self.session_paths[chosen[0]]
        self.result = load(self.selected_folder / "analysis.json")
        self.report_button.configure(state="normal" if self.result else "disabled")
        self.export_button.configure(state="normal" if self.result else "disabled")
        self.set_text(
            self.result_text,
            format_result(self.result)
            if self.result
            else "Diese Messung ist noch nicht ausgewertet. Laufende Messungen zuerst stoppen. Bei einem unerwarteten Abbruch bleiben die Rohdaten im Datenordner erhalten.",
        )

    def open_report(self):
        if self.result:
            os.startfile(str(self.selected_folder / "report.html"))

    def export(self):
        if not self.result:
            return
        dest = filedialog.asksaveasfilename(
            title="Datensparsame Zusammenfassung speichern",
            defaultextension=".json",
            initialfile="lag-check-zusammenfassung.json",
            filetypes=[("JSON-Zusammenfassung", "*.json")],
        )
        if not dest:
            return
        try:
            pathlib.Path(dest).write_text(
                json.dumps(safe_export(self.result), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            messagebox.showinfo(
                "Export gespeichert",
                "Nur ausgewählte Zahlen und Kategorien exportiert. Keine IPs, Pfade, Gerätenamen, Windows-Meldungen oder absoluten Zeitstempel. Bitte vor einer Weitergabe prüfen. Es wurde nichts hochgeladen.",
            )
        except OSError as exc:
            messagebox.showerror("Export fehlgeschlagen", str(exc))

    def close(self):
        if self.running:
            if messagebox.askyesno(
                "Messung noch aktiv",
                "Messung beenden, auswerten und danach schließen?\n\nMit „Nein“ bleibt die App geöffnet. Du kannst sie stattdessen minimieren.",
            ):
                self.close_after_stop = True
                self.stop()
        else:
            self.root.destroy()


def math_ceil(value):
    import math

    return math.ceil(value)


def main():
    import msvcrt

    DATA.mkdir(parents=True, exist_ok=True)
    handle = (DATA / "gui.lock").open("a+b")
    handle.seek(0)
    try:
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo(
            "Lag Check", "Lag Check ist bereits geöffnet. Schau in die Taskleiste."
        )
        root.destroy()
        return
    root = tk.Tk()
    try:
        App(root)
        root.mainloop()
    finally:
        handle.close()
