"""Project credits and version.

The original build refused to start if this file was edited. That check has
been removed: ScrimLab is MIT-licensed and forks must be free to change it.
"""

__author__ = "IHLAMUR"
__version__ = "1.2.0"


def get_credits_banner() -> str:
    return f"""
=========================================================
 ██▓ ██░ ██  ██▓    ▄▄▄       ███▄ ▄███▓ █    ██  ██▀███
▓██▒▓██░ ██▒▓██▒   ▒████▄    ▓██▒▀█▀ ██▒ ██  ▓██▒▓██ ▒ ██▒
▒██▒▒██▀▀██░▒██░   ▒██  ▀█▄  ▓██    ▓██░▓██  ▒██░▓██ ░▄█ ▒
░██░░▓█ ░██ ▒██░   ░██▄▄▄▄██ ▒██    ▒██ ▓▓█  ░██░▒██▀▀█▄
░██░░▓█▒░██▓░██████▒▓█   ▓██▒▒██▒   ░██▒▒▒█████▓ ░██▓ ▒██▒
░▓   ▒ ░░▒░▒░ ▒░▓  ░▒▒   ▓▒█░░ ▒░   ░  ░░▒▓▒ ▒ ▒ ░ ▒▓ ░▒▓░
 ▒ ░ ▒ ░▒░ ░░ ░ ▒  ░ ▒   ▒▒ ░░  ░      ░░░▒░ ░ ░   ░▒ ░ ▒░
 ▒ ░ ░  ░░ ░  ░ ░    ░   ▒   ░      ░    ░░░ ░ ░   ░░   ░
 ░   ░  ░  ░    ░  ░     ░  ░       ░      ░        ░
    Author: {__author__}
    Version: {__version__}
    League of Legends 5v5 Bot.
=========================================================
"""
