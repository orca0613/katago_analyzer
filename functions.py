import json
import re
import sys
from typing import List
import platform
import os
import subprocess

KATAGO_JSON_PATH = "katago.json"

def extract_komi(sgf):
  km_match = re.search(r'KM\[(.*?)\]', sgf)
  return float(km_match.group(1)) if km_match else 6.5


def convert_sequence_for_katago(sequence: List[int]):
  converted = []
  for i, move in enumerate(sequence):
    x, y = move // 19, move % 19
    color = "W" if i % 2 else "B"
    Y = chr(y + 65) if y < 8 else chr(y + 66)
    X = str(x + 1)
    converted.append([color, Y + X])
  
  return converted


def convert_pv(pv: List[str]):
  converted = []
  for move in pv:
    if len(move) > 3:
      converted.append(-1)
      break

    alpha, digit = move[0], move[1:]
    x = ord(alpha) - 65
    y = int(digit) - 1

    loc = y * 19 + x
    if x > 8:
      loc -= 1
    converted.append(loc)

  return converted


def get_file_path_for_windows(title: str):

  import tkinter as tk
  from tkinter import filedialog

  root = tk.Tk()
  root.withdraw()
  root.attributes('-topmost', True)

  file_path = filedialog.askopenfilename(title=title)
  root.destroy()
  return os.path.normpath(file_path) if file_path else None


def get_file_path_for_mac(title: str):
  script = f"""
    set theFile to choose file with prompt "{title}"
    POSIX path of theFile
  """
  try:
      proc = subprocess.run(['osascript', '-e', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
      if proc.returncode == 0:
          return proc.stdout.strip()
  except Exception:
      pass
  return None


def refine_response(response: str):
  try:
    data = json.loads(response)
    if not "rootInfo" in data:
      return {}
    root = data["rootInfo"]
    best_move = data["moveInfos"][0] if data.get("moveInfos") else {}
    if not best_move:
      return {}
    pv = best_move.get("pv")
    refined = {
      "id": data.get("id"),               # 쿼리 식별자
      "turn": data.get("turnNumber"),     # 수순 (몇 번째 수인지)
      "pv": convert_pv(pv),
      "winrate": round(root.get("winrate", 0) * 100, 1),
      "score": round(root.get("scoreLead", 0), 1),
      "complexity": round(root.get("scoreStdev", 0), 2)
    }
    return refined
  
  except Exception as e:
    print(e)
    return {}

  
def get_katago_cmd():
  katago_json = load_json(KATAGO_JSON_PATH)
  katago = katago_json["katago"]
  model = katago_json["model"]
  config = katago_json["config"]

  if katago and model and config:
    cmd = [katago, "analysis", "-config", config, "-model", model]
    return cmd
  updated_katago_json = initialize_katago_json()
  cmd = [
    updated_katago_json["katago"], "analysis", 
    "-config", updated_katago_json["config"], 
    "-model", updated_katago_json["model"]
  ]
  return cmd


def get_real_path(relative_path: str) -> str:
  """실제 .exe 파일 또는 스크립트가 있는 위치를 기준으로 절대 경로를 반환합니다."""
  if getattr(sys, 'frozen', False):
    # .exe 파일로 실행된 경우, .exe 파일이 있는 폴더 경로
    base_path = os.path.dirname(sys.executable)
  else:
    # 일반 파이썬 스크립트로 실행된 경우, 현재 파일(helper.py)의 부모 폴더 경로
    base_path = os.path.dirname(os.path.abspath(__file__))
    # 만약 helper.py가 최상위에 있다면 위 코드로 충분하고, 
    # 혹시 하위 폴더에 있다면 아래처럼 프로젝트 루트를 잡아야 합니다.
    # base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

  return os.path.join(base_path, relative_path)


def load_json(path: str) -> dict:
  real_path = get_real_path(path)
  if os.path.exists(real_path):
    with open(real_path, "r", encoding="utf-8") as f:
      return json.load(f)
  return {}


def update_json(path, json_data):
  real_path = get_real_path(path)
  try:
    with open(real_path, "w", encoding="utf-8") as f:
      json.dump(json_data, f, indent=4)
    return True
  
  except Exception as e:
    print(e)
    return False


def initialize_katago_json():
  os_name = platform.system()

  katago_path = ""
  model_path = ""
  config_path = ""

  if os_name == "Windows":
    katago_path = get_file_path_for_windows("Katago Path")
    model_path = get_file_path_for_windows("Model Path")
    config_path = get_file_path_for_windows("Config Path")
  
  elif os_name == "Darwin":
    katago_path = get_file_path_for_mac("Katago Path")
    model_path = get_file_path_for_mac("Model Path")
    config_path = get_file_path_for_mac("Config Path")
  
  katago_json = {
    "katago": katago_path,
    "model": model_path,
    "config": config_path
  }

  update_json(KATAGO_JSON_PATH, katago_json)
  return katago_json