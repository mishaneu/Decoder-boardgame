import random
import string
from typing import Dict, Optional
from .models import GameState, Player, Team, SecretWords, GamePhase
from .game_state import DecryptoGame


class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, DecryptoGame] = {}
        # Большой словарь слов (можно заменить своим)
        self.word_bank = [
            "пират", "космос", "музей", "кролик", "компьютер", "море", "огонь",
            "книга", "солнце", "луна", "поезд", "самолет", "дерево", "цветок",
            "кофе", "чай", "пицца", "суши", "хлеб", "сыр", "вино", "пиво",
            "футбол", "баскетбол", "теннис", "шахматы", "музыка", "кино",
            "фото", "телефон", "часы", "очки", "зонт", "ветер", "дождь",
            "снег", "гора", "река", "озеро", "лес", "поле", "город",
            "метро", "такси", "велосипед", "мотоцикл", "лодка"
        ]

    def create_room(self) -> str:
        """Создает новую комнату с уникальным кодом"""
        while True:
            # Генерируем 6-значный код
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if code not in self.rooms:
                self.rooms[code] = DecryptoGame(code, self.word_bank.copy())
                return code

    def get_room(self, room_code: str) -> Optional[DecryptoGame]:
        """Получает комнату по коду"""
        return self.rooms.get(room_code.upper())

    def room_exists(self, room_code: str) -> bool:
        return room_code.upper() in self.rooms

    def cleanup_empty_rooms(self):
        """Удаляет пустые комнаты (можно вызывать периодически)"""
        empty_rooms = []
        for code, game in self.rooms.items():
            if not game.state.players:  # нет игроков
                empty_rooms.append(code)

        for code in empty_rooms:
            del self.rooms[code]