from __future__ import annotations

import sys
from pathlib import Path

# Ensure local web_tools package is importable when running this script directly.
WEB_TOOLS_PATH = Path(__file__).resolve().parent / "web_tools"
if str(WEB_TOOLS_PATH) not in sys.path:
	sys.path.insert(0, str(WEB_TOOLS_PATH))

