"""Entry point — launches the desktop GUI by default.

Usage:
  python main.py              # desktop GUI
  python main.py --web        # web server
  python main.py preview ...  # CLI preview
  python main.py apply ...    # CLI apply
"""
import sys


def main() -> None:
    if "--web" in sys.argv:
        sys.argv.remove("--web")
        from web.server import create_app
        app = create_app()
        app.run(debug=False, port=5050)
    elif len(sys.argv) > 1 and sys.argv[1] in ("preview", "apply"):
        from slm.cli import run
        sys.exit(run())
    else:
        from slm.app import run
        run()


if __name__ == "__main__":
    main()
