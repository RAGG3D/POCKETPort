"""Cross-platform bootstrap. No admin rights, no global AI config modification."""
import json
import os
from pathlib import Path
import subprocess
import sys
import venv

root = Path(__file__).resolve().parent.parent
if not (3, 12) <= sys.version_info[:2] < (3, 14):
    raise SystemExit("POCKETPort requires Python 3.12 or 3.13. Install it from python.org and retry.")
venv.create(root / ".venv", with_pip=True)
python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
subprocess.run([str(python), "-m", "pip", "install", "-e", str(root)], check=True)
config = {"mcpServers": {"pocketport": {"command": str(python), "args": ["-m", "pocketport", "mcp"]}}}
destination = root / "mcp.local.json"
destination.write_text(json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"\nPOCKETPort installed. MCP settings: {destination}")
print(f'Claude Code: claude mcp add --transport stdio pocketport -- "{python}" -m pocketport mcp')
print(f'Codex: codex mcp add pocketport -- "{python}" -m pocketport mcp')
print("Or use Start-POCKETPort to open the desktop dashboard.")
