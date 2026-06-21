"""Launch the Scientific Literature Manager desktop app.

Most users should double-click START_HERE_RUN_APP.bat.
This file is the small Python entry point used by that launcher.
"""

from literature_manager.gui import run_gui


if __name__ == "__main__":
    run_gui()
