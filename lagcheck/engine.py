import csv
import datetime as dt
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import time
import traceback
from .native import PDH, Ping, memory, adapter_status
from .config import DATA as ROOT, RESOURCES

ROOT.mkdir(parents=True, exist_ok=True)
ACTIVE = ROOT / "active.json"
UTC = dt.timezone.utc


def stamp():
    return dt.datetime.now(UTC).isoformat(timespec="milliseconds")


def save(path, data):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def ps(script, *args):
    r = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(RESOURCES / script),
            *map(str, args),
        ],
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    if r.returncode:
        raise RuntimeError(r.stderr)
    return r.stdout.lstrip("\ufeff")


class Log:
    def __init__(self, path, fields):
        self.file = path.open("w", encoding="utf-8-sig", newline="")
        self.writer = csv.DictWriter(self.file, fieldnames=fields)
        self.writer.writeheader()
        self.file.flush()

    def row(self, data):
        self.writer.writerow(data)
        self.file.flush()

    def close(self):
        self.file.close()


def active():
    if not ACTIVE.exists():
        raise RuntimeError("Keine aktive Session.")
    return json.loads(ACTIVE.read_text(encoding="utf-8"))


def mark(kind):
    at = stamp()
    a = active()
    folder = pathlib.Path(a["session"])
    if (folder / "stop.request").exists():
        raise RuntimeError("Session wird bereits beendet.")
    # Append only, with a short exclusive file lock for simultaneous marker scripts.
    import msvcrt

    with (folder / "lag_markers.csv").open("r+b", buffering=0) as f:
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
        try:
            f.seek(0, 2)
            f.write(f"{at},{kind}\r\n".encode("utf-8"))
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    print(f"{kind}: {at}")


def run(seconds=0, options=None):
    options = options or {"network": True, "events": True, "alt_tab": True}
    # Exclusive lock prevents concurrent sessions; OS releases it on crashes.
    import msvcrt

    lock = (ROOT / "monitor.lock").open("a+b")
    lock.seek(0)
    try:
        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        raise RuntimeError("Eine Messung laeuft bereits.")
    folder = ROOT / "sessions" / dt.datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
    folder.mkdir(parents=True)
    info = {
        "start": stamp(),
        "end": None,
        "pid": os.getpid(),
        "session": str(folder),
        "interval_s": 1,
        "python": sys.version,
        "timezone": "UTC; ISO-8601 mit Millisekunden",
        "limitations": [
            "ICMP ist kein Spielverkehr; fehlende Antworten beweisen keinen Spiel-Paketverlust.",
            "Keine GPU-Temperatur/Takt oder verlaessliche VRAM-Kapazitaet.",
            "CPU MHz ist ein grober Windows-Wert.",
            "Pages Input/Output enthalten auch dateibasierte Seiten, nicht nur Pagefile.",
            "Adapterstatus pro Sekunde; IPv4-Gatewaywahl alle 30 Sekunden. Kein IPv6-Ping.",
            "Keine Prozess-/Spiel-/Dateizugriffe; GPU-Windowszaehler werden nur aggregiert gespeichert.",
        ],
    }
    info["options"] = options
    info["app_version"] = "0.1.0"
    save(folder / "session_info.json", info)
    (folder / "lag_markers.csv").write_text("timestamp,kind\n", encoding="utf-8")
    save(ACTIVE, info)
    save(ROOT / "latest.json", info)
    events = Log(
        folder / "windows_events.csv",
        ["timestamp", "id", "level", "provider", "message"],
    )
    events.close()
    errors = Log(folder / "errors.csv", ["timestamp", "component", "error"])
    error_lock = threading.Lock()

    def error(component, e):
        with error_lock:
            errors.row({"timestamp": stamp(), "component": component, "error": str(e)})

    stop = threading.Event()
    state = {"gateway": None}
    threads = []

    def route_worker():
        route_log = Log(
            folder / "routes.csv",
            ["timestamp", "gateway", "interface_index", "details"],
        )
        try:
            while not stop.is_set():
                try:
                    data = json.loads(ps("inventory.ps1"))
                    g = data.get("gateway") or {}
                    state["gateway"] = g.get("gateway")
                    route_log.row(
                        {
                            "timestamp": stamp(),
                            "gateway": state["gateway"],
                            "interface_index": g.get("index"),
                            "details": json.dumps(data, ensure_ascii=False),
                        }
                    )
                except Exception as e:
                    state["gateway"] = None
                    error("gateway", e)
                stop.wait(30)
        finally:
            route_log.close()

    def ping_worker(label, target):
        log = Log(
            folder / f"network_{label}.csv",
            [
                "timestamp",
                "completed_at",
                "monotonic_s",
                "target",
                "status",
                "rtt_ms",
                "probe_duration_ms",
            ],
        )
        p = None
        try:
            p = Ping()
            deadline = time.perf_counter()
            while not stop.is_set():
                ip = state["gateway"] if label == "gateway" else target
                t = time.perf_counter()
                at = stamp()
                try:
                    status, rtt = p.send(ip) if ip else ("UNAVAILABLE", "")
                except Exception as e:
                    status, rtt = "ERROR", ""
                    error(label, e)
                ping_row = {
                    "timestamp": at,
                    "completed_at": stamp(),
                    "monotonic_s": round(t, 6),
                    "target": ip or "",
                    "status": status,
                    "rtt_ms": rtt,
                    "probe_duration_ms": round((time.perf_counter() - t) * 1000, 3),
                }
                log.row(ping_row)
                save(folder / f"ping_{label}.json", ping_row)
                deadline += 1
                stop.wait(max(0, deadline - time.perf_counter()))
                if time.perf_counter() - deadline > 1:
                    deadline = time.perf_counter()
        except Exception as e:
            error(label, e)
        finally:
            if p:
                p.close()
            log.close()

    fields = [
        "timestamp",
        "monotonic_s",
        "interval_s",
        "collection_ms",
        "cpu_pct",
        "core_max_pct",
        "cpu_cores_json",
        "cpu_mhz",
        "ram_pct",
        "ram_total_bytes",
        "ram_available_bytes",
        "commit_pct",
        "commit_bytes",
        "commit_limit",
        "pages_in_s",
        "pages_out_s",
        "pagefile_pct",
        "disk_busy_pct",
        "disk_queue_max",
        "disk_response_ms",
        "disk_read_bps",
        "disk_write_bps",
        "disks_json",
        "net_rx_bps",
        "net_tx_bps",
        "adapters_json",
        "adapter_status_json",
        "tcp_retrans_s",
        "tcp6_retrans_s",
        "gpu_pct",
        "gpu_3d_pct",
        "gpu_copy_pct",
        "gpu_vram_bytes",
        "gpu_adapters_json",
        "counter_errors_json",
        "monitor_cpu_pct",
        "monitor_rss_bytes",
    ]
    log = Log(folder / "system_metrics.csv", fields)
    pdh = None
    started = time.perf_counter()
    previous = started
    cpu_previous = time.process_time()
    try:
        pdh = PDH()
        save(folder / "counter_availability.json", pdh.availability)
        workers = (
            [
                (route_worker, ()),
                (ping_worker, ("gateway", None)),
                (ping_worker, ("cloudflare", "1.1.1.1")),
                (ping_worker, ("google", "8.8.8.8")),
            ]
            if options["network"]
            else []
        )
        for fn, args in workers:
            thread = threading.Thread(target=fn, args=args)
            thread.start()
            threads.append(thread)
        pass  # GUI reads live.json; no console required.
        deadline = started + 1
        while not (folder / "stop.request").exists() and not (
            seconds and time.perf_counter() - started >= seconds
        ):
            time.sleep(max(0, deadline - time.perf_counter()))
            t = time.perf_counter()
            at = stamp()
            raw, failed = pdh.sample()
            row = memory()
            row.update(
                timestamp=at, monotonic_s=round(t, 6), interval_s=round(t - previous, 4)
            )
            cpu = raw.get("cpu", {})
            cores = {k: v for k, v in cpu.items() if k != "_Total"}
            row.update(
                cpu_pct=cpu.get("_Total"),
                core_max_pct=max(cores.values(), default=None),
                cpu_cores_json=json.dumps(cores, separators=(",", ":")),
            )
            for key in [
                "cpu_mhz",
                "commit_pct",
                "commit_bytes",
                "commit_limit",
                "pages_in_s",
                "pages_out_s",
                "pagefile_pct",
                "tcp_retrans_s",
                "tcp6_retrans_s",
            ]:
                row[key] = raw.get(key)
            disks = {}
            for key in [
                "disk_idle",
                "disk_queue",
                "disk_response_s",
                "disk_read_bps",
                "disk_write_bps",
            ]:
                for name, value in raw.get(key, {}).items():
                    if name != "_Total":
                        disks.setdefault(name, {})[key] = value

            def vals(key):
                return [v[key] for v in disks.values() if key in v]

            row.update(
                disk_busy_pct=max(
                    [min(100, max(0, 100 - x)) for x in vals("disk_idle")], default=None
                ),
                disk_queue_max=max(vals("disk_queue"), default=None),
                disk_response_ms=max(
                    [1000 * x for x in vals("disk_response_s")], default=None
                ),
                disks_json=json.dumps(disks, separators=(",", ":")),
            )
            for key in ["disk_read_bps", "disk_write_bps"]:
                row[key] = sum(vals(key)) if vals(key) else None
            adapters = {}
            for key in [k for k in raw if k.startswith("net_")]:
                for name, value in raw[key].items():
                    adapters.setdefault(name, {})[key] = value
            for key in ["net_rx_bps", "net_tx_bps"]:
                row[key] = sum(raw[key].values()) if raw.get(key) else None
            row["adapters_json"] = json.dumps(adapters, separators=(",", ":"))
            row["adapter_status_json"] = json.dumps(
                adapter_status(), separators=(",", ":")
            )
            engines = {}
            for name, value in raw.get("gpu_engines", {}).items():
                name = re.sub(r"^pid_\d+_", "", name)
                engines[name] = engines.get(name, 0) + value
            row["gpu_pct"] = min(100, max(engines.values())) if engines else None
            for label, engine in [("gpu_3d_pct", "3D"), ("gpu_copy_pct", "Copy")]:
                values = [
                    v for k, v in engines.items() if k.endswith("engtype_" + engine)
                ]
                row[label] = min(100, max(values)) if values else None
            vram = raw.get("gpu_vram_bytes", {})
            row["gpu_vram_bytes"] = sum(vram.values()) if vram else None
            row["gpu_adapters_json"] = json.dumps(
                {"engines": engines, "vram_bytes": vram}, separators=(",", ":")
            )
            row["counter_errors_json"] = json.dumps(failed)
            cp = time.process_time()
            row["monitor_cpu_pct"] = round(
                (cp - cpu_previous) / (t - previous) / os.cpu_count() * 100, 3
            )
            cpu_previous = cp
            # Working set of this monitor only, never another process.
            import ctypes as C

            class PMC(C.Structure):
                _fields_ = [("cb", C.c_ulong), ("faults", C.c_ulong)] + [
                    (k, C.c_size_t)
                    for k in (
                        "peak",
                        "working",
                        "pool_peak",
                        "pool",
                        "nonpool_peak",
                        "nonpool",
                        "pagefile",
                        "pagefile_peak",
                    )
                ]

            pm = PMC()
            pm.cb = C.sizeof(pm)
            C.windll.psapi.GetProcessMemoryInfo.argtypes = [
                C.c_void_p,
                C.c_void_p,
                C.c_ulong,
            ]
            if C.windll.psapi.GetProcessMemoryInfo(C.c_void_p(-1), C.byref(pm), pm.cb):
                row["monitor_rss_bytes"] = pm.working
            row["collection_ms"] = round((time.perf_counter() - t) * 1000, 3)
            log.row(row)
            save(folder / "live.json", row)
            previous = t
            deadline += 1
            if time.perf_counter() > deadline:
                deadline = time.perf_counter() + 1
    except KeyboardInterrupt:
        pass
    except Exception as e:
        error("monitor", traceback.format_exc())
        info["failure"] = str(e)
    finally:
        stop.set()
        for thread in threads:
            thread.join()
        if pdh:
            pdh.close()
        log.close()
        info["end"] = stamp()
        save(folder / "session_info.json", info)
        try:
            if options["events"]:
                ps("events.ps1", folder)
            else:
                save(folder / "events_status.json", {"status": "disabled"})
        except Exception as e:
            error("events", e)
            save(
                folder / "events_status.json",
                {"status": "unavailable", "detail": str(e)},
            )
        errors.close()
        if ACTIVE.exists() and active().get("session") == str(folder):
            ACTIVE.unlink()
        save(ROOT / "latest.json", info)
        from .analysis import analyze

        analyze(folder)
        pass
        lock.close()
