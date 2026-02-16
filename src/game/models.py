from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from enum import Enum


class Team(str, Enum):
    RED = "red"
    BLUE = "blue"
    SPECTATOR = "spectator"  # Наблюдатели, если мест нет


class Player(BaseModel):
    id: str  # websocket session id
    nickname: str
    team: Team = Team.SPECTATOR
    is_connected: bool = True
    is_encoder: bool = False  # Шифровальщик в текущем раунде


class Clue(BaseModel):
    encoder_id: str
    encoder_nickname: str
    words: List[str]  # 3 подсказки
    target_code: List[int]  # Что загадали, например [1,3,2]
    round_number: int


class Guess(BaseModel):
    player_id: str
    team: Team
    guess_code: List[int]  # Что команда думает, например [1,2,3]
    is_correct: bool = False


class GamePhase(str, Enum):
    WAITING = "waiting"  # Ждем игроков
    SETUP = "setup"  # Раздача слов
    ENCODING = "encoding"  # Шифровальщик думает
    GUESSING = "guessing"  # Противники угадывают
    REVEAL = "reveal"  # Раскрытие результатов
    GAME_OVER = "game_over"


class SecretWords(BaseModel):
    team_red: List[str]
    team_blue: List[str]


class GameState(BaseModel):
    room_code: str
    phase: GamePhase = GamePhase.WAITING
    players: Dict[str, Player] = {}  # id -> Player
    red_team_ids: List[str] = []
    blue_team_ids: List[str] = []
    spectators_ids: List[str] = []

    # Секретные слова команд
    secret_words: Optional[SecretWords] = None

    # Счет
    red_intercepts: int = 0  # жетоны перехвата
    blue_intercepts: int = 0
    red_mistakes: int = 0  # штрафы (если свои не угадали)
    blue_mistakes: int = 0

    # Текущий раунд
    current_round: int = 0
    current_encoder_id: Optional[str] = None  # кто сейчас шифрует
    current_encoder_team: Optional[Team] = None
    current_code: Optional[List[int]] = None  # что нужно зашифровать
    current_clue: Optional[Clue] = None  # подсказки которые дали
    current_guesses: List[Guess] = []  # догадки команд

    # История для UI
    message_log: List[str] = []

    class Config:
        use_enum_values = True

    red_round: int = 0  # сколько раз красные шифровали
    blue_round: int = 0  # сколько раз синие шифровали
    current_turn_team: Optional[Team] = None  # кто сейчас шифрует

    # Для отображения в UI
    def get_round_display(self) -> str:
        """Возвращает строку вида 'Раунд 1 (Красные)'"""
        if self.current_encoder_team == Team.RED:
            return f"Раунд {self.red_round} (🔴 Красные)"
        elif self.current_encoder_team == Team.BLUE:
            return f"Раунд {self.blue_round} (🔵 Синие)"
        return "Раунд 0"