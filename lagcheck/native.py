"""Read-only Windows PDH, memory and ICMP interfaces; standard library only."""

import ctypes as C
from ctypes import wintypes as W
import socket

COUNTERS = {
    "cpu": r"\Processor(*)\% Processor Time",
    "cpu_mhz": r"\Processor Information(_Total)\Processor Frequency",
    "commit_pct": r"\Memory\% Committed Bytes In Use",
    "commit_bytes": r"\Memory\Committed Bytes",
    "commit_limit": r"\Memory\Commit Limit",
    "pages_in_s": r"\Memory\Pages Input/sec",
    "pages_out_s": r"\Memory\Pages Output/sec",
    "pagefile_pct": r"\Paging File(_Total)\% Usage",
    "disk_idle": r"\PhysicalDisk(*)\% Idle Time",
    "disk_read_bps": r"\PhysicalDisk(*)\Disk Read Bytes/sec",
    "disk_write_bps": r"\PhysicalDisk(*)\Disk Write Bytes/sec",
    "disk_queue": r"\PhysicalDisk(*)\Current Disk Queue Length",
    "disk_response_s": r"\PhysicalDisk(*)\Avg. Disk sec/Transfer",
    "net_rx_bps": r"\Network Interface(*)\Bytes Received/sec",
    "net_tx_bps": r"\Network Interface(*)\Bytes Sent/sec",
    "net_rx_errors": r"\Network Interface(*)\Packets Received Errors",
    "net_tx_errors": r"\Network Interface(*)\Packets Outbound Errors",
    "net_rx_discards": r"\Network Interface(*)\Packets Received Discarded",
    "net_tx_discards": r"\Network Interface(*)\Packets Outbound Discarded",
    "tcp_retrans_s": r"\TCPv4\Segments Retransmitted/sec",
    "tcp6_retrans_s": r"\TCPv6\Segments Retransmitted/sec",
    "gpu_engines": r"\GPU Engine(*)\Utilization Percentage",
    "gpu_vram_bytes": r"\GPU Adapter Memory(*)\Dedicated Usage",
}


class Value(C.Structure):
    _fields_ = [("status", W.DWORD), ("value", C.c_double)]


class Item(C.Structure):
    _fields_ = [("name", W.LPWSTR), ("value", Value)]


class PDH:
    def __init__(self):
        self.dll = C.WinDLL("pdh")
        self.dll.PdhOpenQueryW.argtypes = [W.LPCWSTR, C.c_size_t, C.POINTER(W.HANDLE)]
        self.dll.PdhAddEnglishCounterW.argtypes = [
            W.HANDLE,
            W.LPCWSTR,
            C.c_size_t,
            C.POINTER(W.HANDLE),
        ]
        self.dll.PdhCollectQueryData.argtypes = [W.HANDLE]
        self.dll.PdhGetFormattedCounterValue.argtypes = [
            W.HANDLE,
            W.DWORD,
            C.c_void_p,
            C.POINTER(Value),
        ]
        self.dll.PdhGetFormattedCounterArrayW.argtypes = [
            W.HANDLE,
            W.DWORD,
            C.POINTER(W.DWORD),
            C.POINTER(W.DWORD),
            C.c_void_p,
        ]
        self.dll.PdhCloseQuery.argtypes = [W.HANDLE]
        self.query = W.HANDLE()
        rc = self.dll.PdhOpenQueryW(None, 0, C.byref(self.query))
        if rc:
            raise OSError(f"PdhOpenQuery: {rc & 0xFFFFFFFF:08x}")
        self.handles, self.availability = {}, {}
        for key, path in COUNTERS.items():
            handle = W.HANDLE()
            rc = self.dll.PdhAddEnglishCounterW(self.query, path, 0, C.byref(handle))
            self.availability[key] = {
                "path": path,
                "add_status": f"{rc & 0xFFFFFFFF:08x}",
            }
            if not rc:
                self.handles[key] = handle
        self.dll.PdhCollectQueryData(self.query)

    def sample(self):
        rc = self.dll.PdhCollectQueryData(self.query)
        result, errors = {}, {}
        for key, handle in self.handles.items():
            if "*" in COUNTERS[key]:
                size, count = W.DWORD(), W.DWORD()
                self.dll.PdhGetFormattedCounterArrayW(
                    handle, 0x200 | 0x8000, C.byref(size), C.byref(count), None
                )
                if not size.value:
                    errors[key] = "no_instances"
                    continue
                buf = C.create_string_buffer(size.value)
                status = self.dll.PdhGetFormattedCounterArrayW(
                    handle, 0x200 | 0x8000, C.byref(size), C.byref(count), buf
                )
                if not status:
                    items = C.cast(buf, C.POINTER(Item))
                    result[key] = {
                        items[i].name: round(items[i].value.value, 4)
                        for i in range(count.value)
                        if items[i].value.status in (0, 1)
                    }
                    if not result[key]:
                        errors[key] = "no_valid_values"
                else:
                    errors[key] = f"{status & 0xFFFFFFFF:08x}"
            else:
                v = Value()
                status = self.dll.PdhGetFormattedCounterValue(
                    handle, 0x200 | 0x8000, None, C.byref(v)
                )
                if not status and v.status in (0, 1):
                    result[key] = round(v.value, 4)
                else:
                    errors[key] = f"{(status or v.status) & 0xFFFFFFFF:08x}"
        if rc:
            errors["collect"] = f"{rc & 0xFFFFFFFF:08x}"
        return result, errors

    def close(self):
        self.dll.PdhCloseQuery(self.query)


class Memory(C.Structure):
    _fields_ = [("length", W.DWORD), ("load", W.DWORD)] + [
        (k, C.c_ulonglong)
        for k in (
            "total",
            "available",
            "page_total",
            "page_available",
            "virtual_total",
            "virtual_available",
            "extended",
        )
    ]


def memory():
    m = Memory()
    m.length = C.sizeof(m)
    if not C.windll.kernel32.GlobalMemoryStatusEx(C.byref(m)):
        return {}
    return {
        "ram_pct": round(100 * (1 - m.available / m.total), 3),
        "ram_total_bytes": m.total,
        "ram_available_bytes": m.available,
    }


class IfRow(C.Structure):
    _fields_ = (
        [
            ("name", W.WCHAR * 256),
            ("index", W.DWORD),
            ("type", W.DWORD),
            ("mtu", W.DWORD),
            ("speed", W.DWORD),
            ("phys_len", W.DWORD),
            ("phys", C.c_ubyte * 8),
        ]
        + [
            (k, W.DWORD)
            for k in (
                "admin",
                "oper",
                "change",
                "in_bytes",
                "in_ucast",
                "in_nucast",
                "in_discards",
                "in_errors",
                "in_unknown",
                "out_bytes",
                "out_ucast",
                "out_nucast",
                "out_discards",
                "out_errors",
                "out_queue",
                "descr_len",
            )
        ]
        + [("descr", C.c_char * 256)]
    )


def adapter_status():
    dll = C.WinDLL("iphlpapi")
    size = W.ULONG()
    dll.GetIfTable(None, C.byref(size), False)
    buf = C.create_string_buffer(size.value)
    if dll.GetIfTable(buf, C.byref(size), False):
        return {}
    count = C.cast(buf, C.POINTER(W.DWORD)).contents.value
    rows = C.cast(C.addressof(buf) + 4, C.POINTER(IfRow))
    return {
        str(rows[i].index): {
            "name": bytes(rows[i].descr).decode("utf-8", "replace"),
            "admin": rows[i].admin,
            "oper": rows[i].oper,
        }
        for i in range(count)
        if rows[i].type != 24
    }


class Options(C.Structure):
    _fields_ = [
        ("ttl", C.c_ubyte),
        ("tos", C.c_ubyte),
        ("flags", C.c_ubyte),
        ("size", C.c_ubyte),
        ("data", C.c_void_p),
    ]


class Reply(C.Structure):
    _fields_ = [
        ("address", W.ULONG),
        ("status", W.ULONG),
        ("rtt", W.ULONG),
        ("size", W.WORD),
        ("reserved", W.WORD),
        ("data", C.c_void_p),
        ("options", Options),
    ]


class Ping:
    def __init__(self):
        self.dll = C.WinDLL("iphlpapi", use_last_error=True)
        self.dll.IcmpCreateFile.restype = W.HANDLE
        self.dll.IcmpSendEcho.argtypes = [
            W.HANDLE,
            W.ULONG,
            C.c_void_p,
            W.WORD,
            C.c_void_p,
            C.c_void_p,
            W.DWORD,
            W.DWORD,
        ]
        self.dll.IcmpCloseHandle.argtypes = [W.HANDLE]
        self.handle = self.dll.IcmpCreateFile()
        if self.handle == C.c_void_p(-1).value:
            raise C.WinError(C.get_last_error())

    def send(self, ip):
        address = int.from_bytes(socket.inet_aton(ip), "little")
        buf = C.create_string_buffer(256)
        n = self.dll.IcmpSendEcho(
            self.handle, address, b"passive-diagnostic", 18, None, buf, len(buf), 800
        )
        if n:
            r = C.cast(buf, C.POINTER(Reply)).contents
            return (
                "SUCCESS"
                if r.status == 0
                else "TIMEOUT"
                if r.status == 11010
                else f"ICMP_{r.status}",
                r.rtt if r.status == 0 else "",
            )
        e = C.get_last_error()
        return ("TIMEOUT" if e == 11010 else f"ERROR_{e}", "")

    def close(self):
        self.dll.IcmpCloseHandle(self.handle)
