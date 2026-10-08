"""Tk widget smoke test; no network or real measurement is started."""

import os
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "win32", "Windows GUI")
class GuiTests(unittest.TestCase):
    def test_initial_widgets(self):
        with tempfile.TemporaryDirectory(prefix="lagcheck-gui-") as tmp:
            env = {**os.environ, "LAGCHECK_DATA_DIR": tmp}
            code = """import tkinter as tk
from lagcheck.gui import App
r=tk.Tk(); r.withdraw(); a=App(r); r.update_idletasks()
assert str(a.start_button['state']) == 'normal'
assert str(a.stop_button['state']) == 'disabled'
assert len(a.cards) == 6
assert len(a.marker_buttons) == 3
assert a.network.get() and a.alt_tab.get()
r.destroy()
"""
            subprocess.run(
                [sys.executable, "-c", code], env=env, check=True, timeout=30
            )


if __name__ == "__main__":
    unittest.main()
