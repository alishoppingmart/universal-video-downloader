"""
Android entry point for AI Video Studio (Kivy).

Buildozer looks for a `main.py` at the project root. This just launches the
mobile control-panel UI in mobile/ui.py. (Desktop users run studio_app.py.)
"""

from mobile.ui import run

if __name__ == "__main__":
    run()
