"""Local development server for the web interface with live reload."""

import json
import shutil
from pathlib import Path

from livereload import Server

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


def main() -> None:
    """Build site and start local development server with live reload."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="ai-palindromikisa serve",
        description="Build and serve the web interface locally with live reload",
    )
    parser.add_argument(
        "-p", "--port", type=int, default=8000, help="Port to serve on (default: 8000)"
    )
    parser.add_argument(
        "--build-only", action="store_true", help="Only build, don't start server"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("gh-pages"),
        help="Output directory (default: gh-pages)",
    )
    args = parser.parse_args()

    print(f"Building site to {args.output}/...")
    build_site(args.output)
    print("Build complete.")

    if args.build_only:
        return

    # Create livereload server
    server = Server()

    # Watch benchmark_logs for changes and rebuild
    benchmark_logs = Path("benchmark_logs")
    if benchmark_logs.exists():
        server.watch(
            str(benchmark_logs / "*.yaml"),
            lambda: build_site(args.output),
        )

    # Watch web source files for changes
    web_dir = Path(__file__).parent / "web"
    server.watch(str(web_dir / "*"), lambda: build_site(args.output))

    print(f"Watching {benchmark_logs}/*.yaml and {web_dir}/* for changes...")
    print("Press Ctrl+C to stop.")

    # Serve the output directory with live reload
    server.serve(root=str(args.output), port=args.port, open_url_delay=None)


if __name__ == "__main__":
    main()
