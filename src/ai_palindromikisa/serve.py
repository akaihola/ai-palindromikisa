"""Local development server for the web interface with live reload."""

import json
import shutil
from pathlib import Path

from ai_palindromikisa.export_json import export_json
from ai_palindromikisa.paths import BENCHMARK_LOGS_DIR, WEB_DIR


def build_site(output_dir: Path) -> None:
    """Build the site into the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export JSON data
    data = export_json()
    (output_dir / "data.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False)
    )

    # Copy static files
    for file in WEB_DIR.iterdir():
        if file.is_file():
            shutil.copy(file, output_dir / file.name)


def serve_site(port: int, build_only: bool, output: str) -> None:
    """Build and serve the web interface locally with live reload.

    Args:
        port: Port to serve on.
        build_only: If True, only build without starting server.
        output: Output directory path.
    """
    from livereload import Server

    output_path = Path(output)

    print(f"Building site to {output_path}/...")
    build_site(output_path)
    print("Build complete.")

    if build_only:
        return

    # Create livereload server
    server = Server()

    # Watch benchmark_logs for changes and rebuild
    if BENCHMARK_LOGS_DIR.exists():
        server.watch(
            str(BENCHMARK_LOGS_DIR / "*.yaml"),
            lambda: build_site(output_path),
        )

    # Watch web source files for changes
    server.watch(str(WEB_DIR / "*"), lambda: build_site(output_path))

    print(f"Watching {BENCHMARK_LOGS_DIR}/*.yaml and {WEB_DIR}/* for changes...")
    print("Press Ctrl+C to stop.")

    # Serve the output directory with live reload
    server.serve(root=str(output_path), port=port, open_url_delay=None)
