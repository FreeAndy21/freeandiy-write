#!/usr/bin/env python3
# Modified-by: FreeANDIY (Free Andy Agency), 2026. New file, not part of upstream.
"""Print the text runs (UTF-8, at least 6 characters) in a file, one per line: `strings`, but the
same on macOS and Linux and whole for accented and non-Latin text.  Usage: strings.py FILE"""
import re
import sys

data = open(sys.argv[1], "rb").read()
text = data.decode("utf-8", errors="replace")
for run in re.findall(r"[^\x00-\x08\x0a-\x1f\x7f�]{6,}", text):
    print(run)
