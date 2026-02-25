import base64
import sys

# Encoded author ID
_v1 = b'SUhMQU1VUg=='
__author__ = base64.b64decode(_v1).decode('utf-8')
__version__ = "1.0.0"

def _verify_integrity():
    """Core verification metric. Do not modify or the bot will fail to start."""
    try:
        a = base64.b64encode(__author__.encode('utf-8'))
        if a != _v1 or sum(ord(c) for c in __author__) != 530:
            return False
        return True
    except:
        return False

def get_credits_banner():
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
