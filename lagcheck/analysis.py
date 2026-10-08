"""Conservative evidence-based analysis; never claim to identify a game process."""

import csv
import datetime as dt
import html
import json
import math
import statistics
from collections import Counter
from pathlib import Path

TITLES = {
    "NETWORK_LOCAL": "Hinweis auf das lokale Netzwerk",
    "NETWORK_INTERNET": "Hinweis auf den Internetweg",
    "CLIENT_OR_HARDWARE_STUTTER": "Zeitgleiche Auffälligkeit am PC",
    "NETWORK_GAME_ROUTE_OR_SERVER": "Spielroute / Server als offene Möglichkeit",
    "UNKNOWN": "Ursache bleibt offen",
}
KINDS = {
    "FREEZE": "Bild hängt",
    "RUBBERBAND": "Zurückgesetzt / Welt steht",
    "LAG": "Anderer Ruckler",
}
METRICS = {
    "cpu_pct": "CPU (%)",
    "core_max_pct": "Stärkster CPU-Kern (%)",
    "gpu_pct": "GPU (%)",
    "ram_pct": "RAM (%)",
    "commit_pct": "Zugesagter Speicher (%)",
    "disk_busy_pct": "Datenträger aktiv (%)",
    "disk_queue_max": "Datenträger-Warteschlange",
    "disk_response_ms": "Datenträger-Antwortzeit (ms)",
    "pages_in_s": "Eingelesene Speicherseiten/s",
    "tcp_retrans_s": "TCP-Neusendungen/s",
}


def read(folder, name):
    path = Path(folder) / name
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def number(row, key):
    try:
        value = float(row[key])
        return value if math.isfinite(value) else None
    except (KeyError, ValueError, TypeError):
        return None


def epoch(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def local_time(value):
    return (
        dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        .astimezone()
        .strftime("%d.%m.%Y %H:%M:%S")
    )


def values(rows, key):
    return [v for row in rows if (v := number(row, key)) is not None]


def stats(vals):
    return (
        {
            "count": len(vals),
            "mean": statistics.mean(vals),
            "median": statistics.median(vals),
            "p95": sorted(vals)[math.ceil(len(vals) * 0.95) - 1],
            "max": max(vals),
        }
        if vals
        else {"count": 0}
    )


def window(rows, at, before=10, after=10):
    return [r for r in rows if at - before <= epoch(r["timestamp"]) <= at + after]


def coverage(rows, at):
    times = sorted(epoch(r["timestamp"]) for r in rows)
    return bool(
        len(times) >= 16
        and times[0] <= at - 8
        and times[-1] >= at + 8
        and all(0 < b - a <= 2.5 for a, b in zip(times, times[1:]))
    )


def network_state(rows, at, baseline):
    nearby = window(rows, at)
    # No successful baseline means ICMP could simply be filtered for this target.
    failures = [
        r for r in nearby if r["status"] == "TIMEOUT" or r["status"].startswith("ICMP_")
    ]
    spikes = [
        r
        for r in nearby
        if r["status"] == "SUCCESS"
        and baseline is not None
        and number(r, "rtt_ms") is not None
        and float(r["rtt_ms"]) > baseline + 100
    ]
    good = [r for r in nearby if r["status"] == "SUCCESS"]
    changed_target = len({r.get("target", "") for r in nearby}) > 1
    clean = (
        baseline is not None
        and coverage(good, at)
        and len(good) == len(nearby)
        and not spikes
        and not changed_target
    )
    return {
        "clean": clean,
        "bad": bool(
            baseline is not None and (failures or spikes) and not changed_target
        ),
        "timeouts": len(failures),
        "spikes": len(spikes),
        "max_ms": max(values(good, "rtt_ms"), default=None),
        "samples": len(nearby),
    }


def analyze(folder):
    folder = Path(folder)
    info = json.loads((folder / "session_info.json").read_text(encoding="utf-8"))
    rows = read(folder, "system_metrics.csv")
    markers = read(folder, "lag_markers.csv")
    events = read(folder, "windows_events.csv")
    options = info.get("options", {"network": True, "events": True, "alt_tab": True})
    times = [epoch(m["timestamp"]) for m in markers]
    base_rows = [
        r for r in rows if all(abs(epoch(r["timestamp"]) - t) > 10 for t in times)
    ]
    hardware = {k: stats(values(base_rows, k)) for k in METRICS}
    networks, baselines, net_summary = {}, {}, {}
    for label in ("gateway", "cloudflare", "google"):
        data = read(folder, f"network_{label}.csv")
        networks[label] = data
        good = [r for r in data if r["status"] == "SUCCESS"]
        # Baseline per actual destination, so route changes don't mix medians.
        targets = {r.get("target", "") for r in good}
        baselines[label] = {}
        for target in targets:
            base = values(
                [
                    r
                    for r in good
                    if r.get("target", "") == target
                    and all(abs(epoch(r["timestamp"]) - t) > 10 for t in times)
                ],
                "rtt_ms",
            )
            baselines[label][target] = (
                statistics.median(base) if len(base) >= 10 else None
            )
        net_summary[label] = stats(values(good, "rtt_ms"))
        net_summary[label].update(
            timeouts=sum(
                r["status"] == "TIMEOUT" or r["status"].startswith("ICMP_")
                for r in data
            ),
            unavailable=sum(
                r["status"] != "SUCCESS"
                and r["status"] != "TIMEOUT"
                and not r["status"].startswith("ICMP_")
                for r in data
            ),
        )
    results = []
    for marker in markers:
        at = epoch(marker["timestamp"])
        nearby = window(rows, at)
        ns = {}
        for label, data in networks.items():
            target_rows = window(data, at)
            target = target_rows[0].get("target", "") if target_rows else ""
            ns[label] = network_state(data, at, baselines[label].get(target))
        findings, notes = [], []

        def flag(key, threshold, text):
            hits = [
                r
                for r in nearby
                if number(r, key) is not None and float(r[key]) >= threshold
            ]
            if hits:
                findings.append(
                    {
                        "code": key,
                        "text": text,
                        "max": max(values(hits, key)),
                        "offset_s": round(epoch(hits[0]["timestamp"]) - at, 1),
                        "samples": len(hits),
                    }
                )

        for key, threshold, text in [
            ("cpu_pct", 95, "CPU fast vollständig ausgelastet"),
            ("core_max_pct", 99, "Ein CPU-Kern fast vollständig ausgelastet"),
            ("ram_pct", 95, "Arbeitsspeicher fast voll"),
            ("commit_pct", 95, "Zugesagter Speicher nahe am Limit"),
            ("disk_busy_pct", 95, "Datenträger fast durchgehend beschäftigt"),
        ]:
            flag(key, threshold, text)
        for key, minimum, text in [
            ("disk_queue_max", 2, "Erhöhte Datenträger-Warteschlange"),
            ("disk_response_ms", 50, "Längere Datenträger-Antwortzeit"),
            ("pages_in_s", 1000, "Vermehrtes Einlesen von Speicherseiten"),
            ("tcp_retrans_s", 10, "Mehr TCP-Neusendungen"),
        ]:
            if hardware[key]["count"] >= 10:
                flag(key, max(minimum, 3 * hardware[key]["p95"]), text)
        gpu_max = max(values(nearby, "gpu_pct"), default=0)
        if gpu_max >= 95:
            notes.append(
                "GPU zeitweise über 95 %. Das kann normale Spielelast sein und ist allein kein Fehlerhinweis."
            )
        extended = window(rows, at, 12, 10)
        drops = [
            (a, b)
            for a, b in zip(extended, extended[1:])
            if epoch(b["timestamp"]) >= at - 10
            and 0 < epoch(b["timestamp"]) - epoch(a["timestamp"]) <= 2.5
            and number(a, "gpu_pct") is not None
            and number(b, "gpu_pct") is not None
            and float(a["gpu_pct"]) - float(b["gpu_pct"]) >= 50
        ]
        if drops:
            notes.append(
                "GPU-Auslastung fällt kurz ab. "
                + (
                    "Alt-Tab ist angegeben: kein eigenständiger Fehlerhinweis."
                    if options.get("alt_tab", True)
                    else "Auch Szenenwechsel oder eine Pause können das verursachen."
                )
            )
        if any("pages_in_s" == f["code"] for f in findings):
            notes.append(
                "Eingelesene Speicherseiten können normales Nachladen von Dateien sein; das beweist weder RAM-Mangel noch einen Defekt."
            )
        for a, b in zip(nearby, nearby[1:]):
            aa, bb = (
                json.loads(a.get("adapters_json") or "{}"),
                json.loads(b.get("adapters_json") or "{}"),
            )
            if any(
                v.get(k, 0) > aa.get(adapter, {}).get(k, v.get(k, 0))
                for adapter, v in bb.items()
                for k in (
                    "net_rx_errors",
                    "net_tx_errors",
                    "net_rx_discards",
                    "net_tx_discards",
                )
            ):
                notes.append(
                    "Adapter meldet zusätzliche Fehler oder verworfene Pakete."
                )
                break
        relevant = window(events, at)
        critical = [
            e
            for e in relevant
            if e.get("provider", "").lower()
            in (
                "microsoft-windows-whea-logger",
                "display",
                "disk",
                "stornvme",
                "storahci",
                "microsoft-windows-kernel-power",
            )
            and e.get("id")
            in ("1", "7", "11", "17", "18", "19", "41", "51", "129", "153", "4101")
        ]
        if critical:
            findings.append(
                {
                    "code": "windows_event",
                    "text": "Zeitnahes Hardware-/Treiberereignis im Systemprotokoll",
                    "max": len(critical),
                    "offset_s": round(epoch(critical[0]["timestamp"]) - at, 1),
                    "samples": len(critical),
                }
            )
        system_complete = coverage(nearby, at)
        if not system_complete:
            notes.append(
                "System-Messfenster unvollständig. Keine sichere Entwarnung möglich."
            )
        ext_clean = ns["cloudflare"]["clean"] and ns["google"]["clean"]
        if ns["gateway"]["bad"]:
            category = "NETWORK_LOCAL"
        elif ns["gateway"]["clean"] and (
            ns["cloudflare"]["bad"] or ns["google"]["bad"]
        ):
            category = "NETWORK_INTERNET"
        elif ext_clean and findings:
            category = "CLIENT_OR_HARDWARE_STUTTER"
        elif (
            system_complete
            and ns["gateway"]["clean"]
            and ext_clean
            and marker["kind"] == "RUBBERBAND"
        ):
            category = "NETWORK_GAME_ROUTE_OR_SERVER"
        else:
            category = "UNKNOWN"
        if category == "NETWORK_GAME_ROUTE_OR_SERVER":
            notes.append(
                "Nur eine offene Möglichkeit: Die Route zum Spiel und der Spielserver werden nicht gemessen. Auch ein Clientproblem bleibt möglich."
            )
        if not all(n["clean"] or n["bad"] for n in ns.values()):
            notes.append(
                "Für mindestens ein Ping-Ziel fehlen belastbare Vergleichsdaten oder vollständige Proben."
            )
        results.append(
            {
                "timestamp": marker["timestamp"],
                "kind": marker["kind"],
                "category": category,
                "network": ns,
                "findings": findings,
                "notes": notes,
                "system_complete": system_complete,
                "ranges": {
                    k: {"min": min(v), "max": max(v)}
                    for k in METRICS
                    if (v := values(nearby, k))
                },
            }
        )
    quality = []
    if not rows:
        quality.append("Keine System-Samples verfügbar.")
    if not markers:
        quality.append(
            "Keine Ruckler markiert. Eine Ursache lässt sich ohne Zeitpunkt nicht zuordnen."
        )
    if not info.get("end"):
        quality.append(
            "Messung wurde nicht regulär abgeschlossen; Systemereignisse können fehlen."
        )
    if info.get("failure"):
        quality.append(
            "Der Monitor hat einen Fehler gemeldet; lokale errors.csv prüfen."
        )
    missing = Counter(
        k for r in rows for k in json.loads(r.get("counter_errors_json") or "{}")
    )
    if missing:
        quality.append("Einzelne Leistungszähler fehlen: " + ", ".join(sorted(missing)))
    available_path = folder / "counter_availability.json"
    if available_path.exists():
        available = json.loads(available_path.read_text(encoding="utf-8"))
        unavailable = [
            k for k, v in available.items() if v.get("add_status") != "00000000"
        ]
        if unavailable:
            quality.append(
                "Nicht verfügbare Leistungszähler: " + ", ".join(unavailable)
            )
    status_path = folder / "events_status.json"
    event_status = (
        json.loads(status_path.read_text(encoding="utf-8-sig")).get(
            "status", "unavailable"
        )
        if status_path.exists()
        else "unavailable"
    )
    if event_status != "ok":
        quality.append(
            "Windows-Ereignisse nicht vollständig gelesen (deaktiviert oder nicht verfügbar)."
        )
    if read(folder, "errors.csv"):
        quality.append("Messfehler wurden protokolliert; lokale errors.csv prüfen.")
    result = {
        "schema": 1,
        "version": "0.1.0",
        "start": info["start"],
        "end": info.get("end"),
        "duration_s": max(0, epoch(info["end"]) - epoch(info["start"]))
        if info.get("end")
        else None,
        "samples": len(rows),
        "network": net_summary,
        "hardware": hardware,
        "markers": results,
        "quality": quality,
        "events_count": len(events),
        "event_status": event_status,
        "options": options,
    }
    (folder / "analysis.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    render_report(folder, result)
    return result


def format_result(result):
    out = [
        f"Messdauer: {(result.get('duration_s') or 0) / 60:.1f} Minuten · {result['samples']} Messpunkte · {len(result['markers'])} Marker",
        "",
        "Die Kategorien sind Hinweise, keine bewiesenen Ursachen.",
    ]
    for label, title in [
        ("gateway", "Router"),
        ("cloudflare", "Internet A"),
        ("google", "Internet B"),
    ]:
        n = result["network"][label]
        out.append(
            f"{title}: Median {n.get('median', '—')} ms · Maximum {n.get('max', '—')} ms · {n['timeouts']} ICMP-Ausfälle · {n['unavailable']} fehlende/fehlerhafte Proben"
        )
    out.extend(["", *result["quality"]])
    for m in result["markers"]:
        out += [
            "",
            f"{local_time(m['timestamp'])} · {KINDS.get(m['kind'], 'Ruckler')}",
            TITLES[m["category"]],
        ]
        for label, title in [
            ("gateway", "Router"),
            ("cloudflare", "Internet A"),
            ("google", "Internet B"),
        ]:
            n = m["network"][label]
            out.append(
                f"  {title}: "
                + (
                    "unauffällig"
                    if n["clean"]
                    else "auffällig"
                    if n["bad"]
                    else "nicht sicher beurteilbar"
                )
            )
        for f in m["findings"]:
            out.append(
                f"  • {f['text']}: max. {f['max']:.1f}; zuerst {f['offset_s']:+.1f} s zum Marker"
            )
        out += ["  " + note for note in m["notes"]]
    out += [
        "",
        "Wichtig: Alt-Tab, Nachladen und normale hohe Spielelast können Werte verändern. Keine FPS-/Frametime-Messung, keine Temperatur oder zuverlässige VRAM-Kapazität. Saubere Pings schließen Spielroute-, UDP- oder Serverprobleme nicht aus. Einsekunden-Sampling kann kürzere Störungen übersehen.",
    ]
    return "\n".join(out)


def render_report(folder, result):
    text = format_result(result)
    (folder / "diagnostic_summary.md").write_text(
        "# Lag Check – Diagnosebericht\n\n" + text + "\n", encoding="utf-8"
    )
    safe = html.escape(text)
    markup = (
        '<!doctype html><html lang="de"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lag Check – Auswertung</title><style>body{background:#101923;color:#e6edf3;font:17px/1.7 system-ui;margin:0}main{max-width:960px;margin:50px auto;padding:32px}h1{font-size:42px;color:#7de2b4}pre{white-space:pre-wrap;font:inherit;background:#192735;border:1px solid #304253;border-radius:16px;padding:28px}.badge{color:#aabccb}a{color:#7de2b4}</style><main><div class="badge">LAG CHECK / LOKALE AUSWERTUNG</div><h1>Was ist passiert?</h1><p>Die Messwerte helfen beim Eingrenzen. Sie beweisen keine Ursache.</p><pre>'
        + safe
        + "</pre><p>Dieser Bericht enthält Zeitangaben. Zum Teilen den datensparsamen Export in der App verwenden.</p></main></html>"
    )
    (folder / "report.html").write_text(markup, encoding="utf-8")


def safe_export(result):
    """Build a NEW allowlisted object. Never copy raw text, paths, IPs or timestamps."""

    def numeric(source, keys):
        return {
            k: float(v)
            for k in keys
            if isinstance((v := source.get(k)), (int, float))
            and not isinstance(v, bool)
            and math.isfinite(v)
        }

    out = {
        "format": "lag-check-share-v1",
        "duration_minutes": round((result.get("duration_s") or 0) / 60, 1),
        "samples": int(result.get("samples", 0)),
        "network": {},
        "markers": [],
    }
    for label in ("gateway", "cloudflare", "google"):
        out["network"][label] = numeric(
            result.get("network", {}).get(label, {}),
            ("count", "mean", "median", "p95", "max", "timeouts", "unavailable"),
        )
    for marker in result.get("markers", []):
        category = marker.get("category")
        kind = marker.get("kind")
        out["markers"].append(
            {
                "number": len(out["markers"]) + 1,
                "kind": kind if kind in KINDS else "LAG",
                "category": category if category in TITLES else "UNKNOWN",
                "findings": [
                    {"code": f["code"], **numeric(f, ("max", "offset_s", "samples"))}
                    for f in marker.get("findings", [])
                    if f.get("code") in METRICS or f.get("code") == "windows_event"
                ],
            }
        )
    return out
