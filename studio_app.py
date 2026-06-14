#!/usr/bin/env python3
"""
Entry point for AI Video Studio (the desktop app).

Run from source:   python studio_app.py
Packaged build:    this is what PyInstaller turns into AIVideoStudio.exe
"""

from ai_video_studio.app import main

if __name__ == "__main__":
    main()
