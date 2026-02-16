from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import Request
import json
import asyncio
from typing import Dict
import uuid

from game.room_manager import RoomManager
from game.models import Team, GamePhase

app = FastAPI(title="Decrypto Game")

# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Менеджер комнат (общий для всех)
room_manager = RoomManager()

# Хранилище connection_id -> (websocket, room_code, player_id)
connections: Dict[str, tuple] = {}


@app.get("/", response_class=HTMLResponse)
async def get_index(request: Request):
    """Отдаем главную страницу"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connection_id = str(uuid.uuid4())

    try:
        while True:
            # Ждем сообщение от клиента
            data = await websocket.receive_text()
            message = json.loads(data)

            # Обрабатываем тип сообщения
            await handle_message(connection_id, websocket, message)

    except WebSocketDisconnect:
        # Клиент отключился
        if connection_id in connections:
            _, room_code, player_id = connections[connection_id]

            # Удаляем игрока из комнаты
            room = room_manager.get_room(room_code)
            if room:
                room.remove_player(player_id)

                # Рассылаем обновленное состояние
                await broadcast_room_state(room_code)

            del connections[connection_id]

    except Exception as e:
        print(f"Error: {e}")
        if connection_id in connections:
            del connections[connection_id]


async def handle_message(conn_id: str, websocket: WebSocket, message: dict):
    """Обработчик всех типов сообщений"""
    msg_type = message.get("type")

    if msg_type == "create_room":
        # Создаем новую комнату
        room_code = room_manager.create_room()
        await websocket.send_json({
            "type": "room_created",
            "room_code": room_code
        })

    elif msg_type == "join_room":
        # Присоединяемся к комнате
        room_code = message.get("room_code", "").upper()
        nickname = message.get("nickname", "Anonymous")

        if not room_manager.room_exists(room_code):
            await websocket.send_json({
                "type": "error",
                "message": "Комната не найдена"
            })
            return

        room = room_manager.get_room(room_code)

        # Создаем игрока
        player_id = str(uuid.uuid4())
        player = room.add_player(player_id, nickname)

        # Сохраняем связь
        connections[conn_id] = (websocket, room_code, player_id)

        # Отправляем подтверждение
        await websocket.send_json({
            "type": "joined",
            "player_id": player_id,
            "room_code": room_code,
            "nickname": nickname
        })

        # Рассылаем всем новое состояние
        await broadcast_room_state(room_code)

    elif msg_type == "join_team":
        # Выбор команды
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        team = Team(message.get("team"))

        room = room_manager.get_room(room_code)
        if room:
            room.join_team(player_id, team)
            await broadcast_room_state(room_code)

    elif msg_type == "start_game":
        # Старт игры
        room_code = message.get("room_code")
        unique_codes = message.get("unique_codes", True)

        room = room_manager.get_room(room_code)
        if room:
            if room.start_game(unique_codes):
                await broadcast_room_state(room_code)

    elif msg_type == "submit_clue":
        # Шифровальщик отправил подсказки
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        clue_words = message.get("clue_words", [])

        room = room_manager.get_room(room_code)
        if room and room.submit_clue(player_id, clue_words):
            await broadcast_room_state(room_code)

    elif msg_type == "make_guess":
        # Команда делает предположение
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        guess_code = message.get("guess_code", [])
        team = Team(message.get("team"))

        room = room_manager.get_room(room_code)
        if room:
            room.make_guess(player_id, guess_code, team)
            await broadcast_room_state(room_code)

    elif msg_type == "confirm_intercept":
        # Шифровальщик подтверждает перехват
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        intercepting_team = Team(message.get("intercepting_team"))

        room = room_manager.get_room(room_code)
        if room:
            room.confirm_intercept(player_id, intercepting_team)
            await broadcast_room_state(room_code)

    elif msg_type == "confirm_own_guess":
        # Шифровальщик подтверждает, угадала ли своя команда
        print(f"confirm_own_guess: {message}")  # ОТЛАДКА
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        guessed_correctly = message.get("guessed_correctly", False)

        room = room_manager.get_room(room_code)
        if room:
            room.confirm_own_guess(player_id, guessed_correctly)
            await broadcast_room_state(room_code)

    elif msg_type == "resolve_round":  # Для обратной совместимости
        print(f"Получен устаревший тип resolve_round от {conn_id}")
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        guessed_correctly = message.get("own_team_correct", False)

        room = room_manager.get_room(room_code)
        if room:
            room.confirm_own_guess(player_id, guessed_correctly)
            await broadcast_room_state(room_code)

    elif msg_type == "get_state":
        # Запрос текущего состояния
        room_code = message.get("room_code")
        player_id = message.get("player_id")
        await send_room_state(websocket, room_code, player_id)


async def send_room_state(websocket: WebSocket, room_code: str, player_id: str = None):
    """Отправляет состояние комнаты конкретному клиенту"""
    room = room_manager.get_room(room_code)
    if room:
        if player_id:
            # Используем персонализированное состояние
            player_state = room.get_state_for_player(player_id)
            await websocket.send_json({
                "type": "state_update",
                "state": player_state,
                "your_player_id": player_id
            })
        else:
            # Общее состояние (для обратной совместимости)
            state_dict = room.state.model_dump()
            await websocket.send_json({
                "type": "state_update",
                "state": state_dict
            })


async def broadcast_room_state(room_code: str):
    """Расслылает состояние всем в комнате"""
    room = room_manager.get_room(room_code)
    if not room:
        return

    # Ищем все соединения в этой комнате
    for conn_id, (ws, conn_room, player_id) in list(connections.items()):
        if conn_room == room_code:
            try:
                # Отправляем персонализированное состояние каждому игроку
                player_state = room.get_state_for_player(player_id)

                await ws.send_json({
                    "type": "state_update",
                    "state": player_state,
                    "your_player_id": player_id
                })
            except Exception as e:
                print(f"Error sending to {conn_id}: {e}")
                if conn_id in connections:
                    del connections[conn_id]


if __name__ == "__main__":
    import uvicorn

    # Запускаем сервер
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)