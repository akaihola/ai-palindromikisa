"""Local development server for the web interface with live reload."""

import json
import shutil
from pathlib import Path

from ai_palindromikisa.export_json import export_json


def build_site(output_dir: Path) -> None:
    """Build the site into the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export JSON data
    data = export_json()
    (output_dir / "data.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False)
    )

    # Copy static files
    web_dir = Path(__file__).parent / "web"
    for file in web_dir.iterdir():
        if file.is_file():
            shutil.copy(file, output_dir / file.name)
