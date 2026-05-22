"""LEGACY: pre-Rich ANSI colorizer. Use Hermes display.final_response_markdown=render instead."""
import sys
import re
import os

if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8', errors='ignore')
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

if os.name == 'nt':
    from ctypes import windll, c_ulong
    try:
        stdout_handle = windll.kernel32.GetStdHandle(-11)
        mode = c_ulong()
        windll.kernel32.GetConsoleMode(stdout_handle, sys.byref(mode))
        windll.kernel32.SetConsoleMode(stdout_handle, mode.value | 0x0004)
    except Exception:
        pass


def convert_markdown_to_institutional(text):
    text = text.replace('\ufeff', '').replace('ï»¿', '')
    text = text.replace('Cli?nt', 'Cliënt').replace('cli?nt', 'cliënt')
    text = text.replace('be?indiging', 'beëindiging').replace('Be?indiging', 'Beëindiging')
    text = text.replace('financi?le', 'financiële').replace('Financi?le', 'Financiële')
    text = re.sub(r'\[COLOR_BLUE\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[COLOR_TEAL\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[COLOR_GREEN\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'\[RESET\]', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^#\s+(.*)$', r'\033[1;97m\1\033[0m', text, flags=re.MULTILINE)
    text = re.sub(r'^##\s+(.*)$', r'\033[1;97m\1\033[0m', text, flags=re.MULTILINE)
    text = re.sub(r'^###\s+(.*)$', r'\033[1;34m\1\033[0m', text, flags=re.MULTILINE)
    text = re.sub(r'\*\*(.*?)\*\*', r'\033[32m\1\033[0m', text)
    return text


def main():
    if not sys.stdin.isatty():
        input_text = sys.stdin.read()
        sys.stdout.write(convert_markdown_to_institutional(input_text))


if __name__ == "__main__":
    main()
