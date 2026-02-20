from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import json
import uuid
from typing import Dict

from game.room_manager import RoomManager
from game.models import Team

app = FastAPI(title="Decrypto Game")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

room_manager = RoomManager()
connections: Dict[str, tuple] = {}


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid.uuid4())
    print(f"Новое подключение: {connection_id}")

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Получено от {connection_id}: {data}")
            message = json.loads(data)
            await handle_message(connection_id, websocket, message)

    except WebSocketDisconnect:
        print(f"Отключение: {connection_id}")
        if connection_id in connections:
            _, room_code, player_id = connections[connection_id]
            room = room_manager.get_room(room_code)
            if room:
                room.remove_player(player_id)
                await broadcast_room_state(room_code)
            del connections[connection_id]

    except Exception as e:
        print(f"Ошибка {connection_id}: {e}")
        if connection_id in connections:
            del connections[connection_id]


async def handle_message(conn_id: str, websocket: WebSocket, message: dict):
    msg_type = message.get("type")
    print(f"Обработка типа: {msg_type}")

    if msg_type == "create_room":
        room_code = room_manager.create_room()
        await websocket.send_json({
            "type": "room_created",
            "room_code": room_code
        })

    elif msg_type == "join_room":
        room_code = message.get("room_code", "").upper()
        nickname = message.get("nickname", "Anonymous")

        if not room_manager.room_exists(room_code):
            await websocket.send_json({
                "type": "error",
                "message": "Комната не найдена"
            })
            return

        room = room_manager.get_room(room_code)
        player_id = str(uuid.uuid4())
        player = room.add_player(player_id, nickname)

        connections[conn_id] = (websocket, room_code, player_id)

        await websocket.send_json({
            "type": "joined",
            "player_id": player_id,
            "room_code": room_code,
            "nickname": nickname
        })

        await broadcast_room_state(room_code)

    elif msg_type == "join_team":
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        team = Team(message.get("team"))

        room = room_manager.get_room(room_code)
        if room:
            room.join_team(player_id, team)
            await broadcast_room_state(room_code)

    elif msg_type == "start_game":
        room_code = message.get("room_code")
        room = room_manager.get_room(room_code)
        if room and room.start_game():
            await broadcast_room_state(room_code)

    elif msg_type == "submit_clue":
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        clue_words = message.get("clue_words", [])

        room = room_manager.get_room(room_code)
        if room and room.submit_clue(player_id, clue_words):
            await broadcast_room_state(room_code)

    elif msg_type == "round_result":
        print(f"!!! ПОЛУЧЕН РЕЗУЛЬТАТ РАУНДА: {message}")
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        result = message.get("result")

        room = room_manager.get_room(room_code)
        if room:
            room.handle_round_result(player_id, result)
            await broadcast_room_state(room_code)


async def broadcast_room_state(room_code: str):
    room = room_manager.get_room(room_code)
    if not room:
        return

    print(f"Расслылка состояния для комнаты {room_code}")

    for conn_id, (ws, conn_room, player_id) in list(connections.items()):
        if conn_room == room_code:
            try:
                player_state = room.get_state_for_player(player_id)
                await ws.send_json({
                    "type": "state_update",
                    "state": player_state,
                    "your_player_id": player_id
                })
                print(f"Состояние отправлено игроку {player_id}")
            except Exception as e:
                print(f"Ошибка отправки {conn_id}: {e}")
                if conn_id in connections:
                    del connections[conn_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)