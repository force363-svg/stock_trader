"""
GUI → AI 명령 파일 읽기 (command.json)
"""
import json
import os
import sys


def get_command_path():
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(os.path.dirname(sys.executable))
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "command.json")


def read_command() -> dict:
    """
    command.json 읽기. 없으면 {} 반환.
    읽은 후 파일 삭제 (일회성 명령).
    예: {"command": "set_mode", "params": {"mode": "paper"}}
    """
    path = get_command_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            cmd = json.load(f)
        os.remove(path)
        return cmd
    except Exception as e:
        print(f"[명령] 읽기 실패: {e}")
        return {}


def write_command(command: str, params: dict = None):
    """GUI에서 AI로 명령 전송"""
    path = get_command_path()
    payload = {"command": command, "params": params or {}}
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[명령] 쓰기 실패: {e}")
