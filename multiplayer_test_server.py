#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import random
import argparse
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import words


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "8000"))
ROOMS = {}


def html_response(handler, status, html):
    body = html.encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def json_response(handler, status, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def read_json(handler):
    length = int(handler.headers.get("Content-Length", "0"))
    if not length:
        return {}
    return json.loads(handler.rfile.read(length).decode("utf-8"))


def new_room_id():
    while True:
        room_id = str(random.randint(1000, 9999))
        if room_id not in ROOMS:
            return room_id


def public_state(room, message=""):
    hints = room.get("hints", [])
    revealed_count = room.get("revealed_count", 0)
    return {
        "room_id": room["room_id"],
        "category": room["category"],
        "difficulty": room["difficulty"],
        "round_number": room["round_number"],
        "revealed_hints": hints[:revealed_count],
        "scoreboard": room["scoreboard"],
        "guesses": room["guesses"][-20:],
        "attempts_used": len(room["guesses"]),
        "round_active": room["round_active"],
        "game_over": room["game_over"],
        "message": message,
    }


def choose_round(room):
    entries = list(words.get_words_by_category(room["category"]).items())
    random.shuffle(entries)
    available = [(word, hints) for word, hints in entries if word not in room["used_words"]]
    if room["max_rounds"] is not None and room["round_number"] >= room["max_rounds"]:
        room["game_over"] = True
        room["round_active"] = False
        return "המשחק הסתיים."
    if not available:
        room["game_over"] = True
        room["round_active"] = False
        return "נגמרו המילים בקטגוריה."

    word, hints = available[0]
    room["used_words"].add(word)
    room["secret_word"] = word
    room["hints"] = words.order_hints_by_difficulty(hints)
    room["revealed_count"] = 1
    room["guesses"] = []
    room["round_number"] += 1
    room["round_active"] = True
    return "מילה חדשה התחילה."


def create_room(payload):
    room_id = new_room_id()
    player = payload.get("player") or "שחקן"
    room = {
        "room_id": room_id,
        "players": {player},
        "scoreboard": {player: 0},
        "category": payload.get("category") or words.get_categories()[0],
        "difficulty": payload.get("difficulty") or "רגיל",
        "max_rounds": payload.get("max_rounds"),
        "used_words": set(),
        "secret_word": "",
        "hints": [],
        "revealed_count": 0,
        "guesses": [],
        "round_number": 0,
        "round_active": False,
        "game_over": False,
    }
    ROOMS[room_id] = room
    message = choose_round(room)
    return room, message


def server_home_page():
    return """<!doctype html>
<html lang="he" dir="rtl">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alias AI Multiplayer Server</title>
  <style>
    body {
      margin: 0;
      font-family: Arial, sans-serif;
      background: #fbf7f8;
      color: #1a1a1a;
    }
    main {
      max-width: 760px;
      margin: 48px auto;
      padding: 28px;
      background: #ffffff;
      border: 2px solid #ffe2e7;
    }
    h1 {
      margin: 0 0 12px;
      color: #b80f2a;
      font-size: 30px;
    }
    .status {
      display: inline-block;
      margin: 10px 0 20px;
      padding: 8px 12px;
      background: #e8f8ef;
      color: #1a7a4a;
      font-weight: bold;
    }
    code {
      direction: ltr;
      display: inline-block;
      background: #fff3f5;
      padding: 3px 6px;
    }
    a {
      color: #8f1230;
      font-weight: bold;
    }
  </style>
</head>
<body>
  <main>
    <h1>Alias AI Multiplayer Server</h1>
    <div class="status">השרת עובד</div>
    <p>זה עמוד בדיקה של שרת ה-Multiplayer. אם אתה רואה את העמוד הזה בכרום, אפשר לגשת לשרת.</p>
    <p>במשחק הכנס את כתובת השרת, למשל: <code>http://127.0.0.1:8000</code></p>
    <p>בדיקת API: <a href="/health">/health</a></p>
  </main>
</body>
</html>
"""


class MultiplayerHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        return

    def do_GET(self):
        path = urlparse(self.path).path
        parts = [part for part in path.split("/") if part]
        if path == "/":
            html_response(self, 200, server_home_page())
            return
        if path == "/favicon.ico":
            self.send_response(204)
            self.end_headers()
            return
        if path == "/health":
            json_response(self, 200, {"status": "ok", "rooms": len(ROOMS)})
            return
        if len(parts) == 3 and parts[0] == "rooms" and parts[2] == "state":
            room = ROOMS.get(parts[1])
            if not room:
                json_response(self, 404, {"error": "room not found"})
                return
            json_response(self, 200, public_state(room))
            return
        json_response(self, 404, {"error": "not found"})

    def do_POST(self):
        path = urlparse(self.path).path
        parts = [part for part in path.split("/") if part]
        try:
            payload = read_json(self)
        except json.JSONDecodeError:
            json_response(self, 400, {"error": "invalid json"})
            return

        if path == "/rooms":
            room, message = create_room(payload)
            json_response(self, 200, {"room_id": room["room_id"], "state": public_state(room, message)})
            return

        if len(parts) != 3 or parts[0] != "rooms":
            json_response(self, 404, {"error": "not found"})
            return

        room = ROOMS.get(parts[1])
        action = parts[2]
        if not room:
            json_response(self, 404, {"error": "room not found"})
            return

        player = payload.get("player") or "שחקן"
        room["players"].add(player)
        room["scoreboard"].setdefault(player, 0)

        if action == "join":
            json_response(self, 200, {"state": public_state(room, f"{player} הצטרף לחדר.")})
            return

        if action == "start":
            room["category"] = payload.get("category") or room["category"]
            room["difficulty"] = payload.get("difficulty") or room["difficulty"]
            room["max_rounds"] = payload.get("max_rounds")
            room["used_words"] = set()
            room["round_number"] = 0
            room["game_over"] = False
            message = choose_round(room)
            json_response(self, 200, {"state": public_state(room, message)})
            return

        if action == "next-round":
            message = choose_round(room)
            json_response(self, 200, {"state": public_state(room, message)})
            return

        if action == "hint":
            if room["round_active"] and room["revealed_count"] < len(room["hints"]):
                room["revealed_count"] += 1
                message = "נפתח רמז נוסף."
            else:
                message = "אין עוד רמזים לפתוח."
            json_response(self, 200, {"state": public_state(room, message)})
            return

        if action == "skip":
            room["round_active"] = False
            json_response(self, 200, {"state": public_state(room, f"{player} דילג על המילה.")})
            return

        if action == "guess":
            guess = payload.get("guess", "")
            room["guesses"].append(f"{player}: {guess}")
            correct = words.normalize_guess(guess) == words.normalize_guess(room.get("secret_word", ""))
            if correct and room["round_active"]:
                points = words.get_points_for_hint_number(room["revealed_count"])
                room["scoreboard"][player] += points
                room["round_active"] = False
                message = f"{player} צדק וקיבל {points} נקודות."
            else:
                if room["round_active"] and room["revealed_count"] < len(room["hints"]):
                    room["revealed_count"] += 1
                message = f"{player} ניחש לא נכון."
            json_response(self, 200, {"state": public_state(room, message)})
            return

        json_response(self, 404, {"error": "not found"})


def main():
    parser = argparse.ArgumentParser(description="Run a local Alias multiplayer test server.")
    parser.add_argument("--host", default=HOST)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MultiplayerHandler)
    display_host = "127.0.0.1" if args.host == "0.0.0.0" else args.host
    print(f"Multiplayer server: http://{display_host}:{args.port}")
    print("במחשב מקומי הכניסו את הכתובת הזאת. באינטרנט הכניסו את כתובת ה-HTTPS שהשירות נותן.")
    server.serve_forever()


if __name__ == "__main__":
    main()
