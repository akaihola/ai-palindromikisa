"""Local development server for the web interface."""

import http.server
import shutil
import socketserver
from pathlib import Path

from ai_palindromikisa.export_json import export_json


def build_site(output_dir: Path) -> None:
    """Build the site into the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Export JSON data
    import json

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
    """Build site and start local development server."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="ai-palindromikisa serve",
        description="Build and serve the web interface locally",
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

    # Change to output directory and serve
    import os

    os.chdir(args.output)

    handler = http.server.SimpleHTTPRequestHandler

    # Allow socket reuse to avoid "Address already in use" after Ctrl+C
    class ReuseAddrTCPServer(socketserver.TCPServer):
        allow_reuse_address = True

    with ReuseAddrTCPServer(("", args.port), handler) as httpd:
        print(f"Serving at http://localhost:{args.port}")
        print("Press Ctrl+C to stop.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


if __name__ == "__main__":
    main()
