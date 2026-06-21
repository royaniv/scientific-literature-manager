"""Entry point for Paper Organizer.

Usage:
  python main.py           # desktop GUI (default)
  python main.py --web     # Flask web server at http://127.0.0.1:5001
"""
import sys

if "--web" in sys.argv:
    from paper_organizer.web import create_app
    import webbrowser, threading
    app = create_app()
    url = "http://127.0.0.1:5001"
    threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"Paper Organizer web UI  {url}  (Ctrl+C to stop)")
    app.run(host="127.0.0.1", port=5001, debug=False, use_reloader=False)
else:
    from paper_organizer.gui import run
    run()
