import random
from typing import List, Dict, Optional, Any
from .models import (
    GameState, Player, Team, Clue, Guess,
    GamePhase, SecretWords
)
from datetime import datetime


class RoundHistory:
    """Класс для хранения истории одного раунда"""

    def __init__(self, team: Team, round_num: int, encoder: str, encoder_id: str):
        self.team = team
        self.round_num = round_num
        self.encoder = encoder
        self.encoder_id = encoder_id
        self.code = None
        self.clues = None
        self.guesses = []
        self.intercepted = False
        self.intercepted_by = None
        self.own_team_guessed = None  # None = ещё не известно, True/False после подтверждения
        self.round_completed = False  # флаг, что раунд завершён
        self.timestamp = datetime.now().isoformat()

    def to_dict(self, for_team: Optional[str] = None) -> dict:
        data = {
            'team': self.team.value,
            'round_num': self.round_num,
            'encoder': self.encoder,
            'clues': self.clues,
            'intercepted': self.intercepted,
            'intercepted_by': self.intercepted_by,
            'own_team_guessed': self.own_team_guessed,
            'round_completed': self.round_completed,
            'timestamp': self.timestamp
        }

        # Код показываем только если раунд завершён ИЛИ это своя команда
        if self.round_completed:
            # Если раунд завершён, своя команда видит код
            if for_team and for_team == self.team.value:
                data['code'] = self.code
            else:
                data['code'] = None  # чужая команда не видит код даже после завершения
        else:
            # Если раунд НЕ завершён, код не видит никто
            data['code'] = None

            # Результаты показываем только если раунд завершён
        if not self.round_completed:
            # Скрываем результаты незавершённых раундов
            data['own_team_guessed'] = None
            data['intercepted'] = False
            data['intercepted_by'] = None

        return data


class DecryptoGame:
    def __init__(self, room_code: str, word_bank: List[str]):
        self.room_code = room_code
        self.word_bank = word_bank
        self.state = GameState(room_code=room_code)
        self.message_log = []

        self.used_codes_history = []
        self.unique_codes_enabled = True

        self.rounds_history: List[RoundHistory] = []
        self.current_round_history: Optional[RoundHistory] = None

        from itertools import permutations
        self.all_possible_codes = [list(code) for code in permutations([1, 2, 3, 4], 3)]

    def add_player(self, player_id: str, nickname: str) -> Player:
        player = Player(id=player_id, nickname=nickname)
        self.state.players[player_id] = player
        self.state.spectators_ids.append(player_id)
        self._add_message(f"✨ {nickname} присоединился к игре")
        return player

    def remove_player(self, player_id: str):
        if player_id in self.state.players:
            player = self.state.players[player_id]
            self._add_message(f"👋 {player.nickname} покинул игру")

            if player_id in self.state.red_team_ids:
                self.state.red_team_ids.remove(player_id)
            if player_id in self.state.blue_team_ids:
                self.state.blue_team_ids.remove(player_id)
            if player_id in self.state.spectators_ids:
                self.state.spectators_ids.remove(player_id)

            del self.state.players[player_id]

    def join_team(self, player_id: str, team: Team) -> bool:
        if player_id not in self.state.players:
            return False

        player = self.state.players[player_id]

        if player_id in self.state.red_team_ids:
            self.state.red_team_ids.remove(player_id)
        if player_id in self.state.blue_team_ids:
            self.state.blue_team_ids.remove(player_id)
        if player_id in self.state.spectators_ids:
            self.state.spectators_ids.remove(player_id)

        if team == Team.RED:
            self.state.red_team_ids.append(player_id)
        elif team == Team.BLUE:
            self.state.blue_team_ids.append(player_id)
        else:
            self.state.spectators_ids.append(player_id)

        player.team = team
        self._add_message(f"🔄 {player.nickname} перешел в команду {team.value}")
        return True

    def start_game(self, unique_codes: bool = True):
        if len(self.state.red_team_ids) < 2 or len(self.state.blue_team_ids) < 2:
            self._add_message("❌ Нужно минимум по 2 игрока в каждой команде")
            return False

        self.unique_codes_enabled = unique_codes
        self.used_codes_history = []
        self.rounds_history = []
        self.message_log = []

        random.shuffle(self.word_bank)
        red_words = self.word_bank[:4]
        blue_words = self.word_bank[4:8]

        self.state.secret_words = SecretWords(
            team_red=red_words,
            team_blue=blue_words
        )

        self.state.red_round = 0
        self.state.blue_round = 0
        self.state.current_round = 0
        self.state.red_intercepts = 0
        self.state.blue_intercepts = 0
        self.state.red_mistakes = 0
        self.state.blue_mistakes = 0

        self.state.phase = GamePhase.ENCODING
        self._next_round()
        self._add_message("🎮 Игра началась! Слова розданы")
        return True

    def _generate_code(self) -> List[int]:
        if not self.unique_codes_enabled:
            return random.sample([1, 2, 3, 4], 3)

        if not self.used_codes_history:
            new_code = random.sample([1, 2, 3, 4], 3)
            self.used_codes_history.append(new_code)
            return new_code

        available_codes = [
            code for code in self.all_possible_codes
            if code not in self.used_codes_history
        ]

        if not available_codes:
            self._add_message("🔄 Все комбинации использованы! Начинаем новый цикл.")
            self.used_codes_history = []
            available_codes = self.all_possible_codes.copy()

        new_code = random.choice(available_codes)
        self.used_codes_history.append(new_code)
        return new_code

    def _next_round(self):
        """Переход к следующему раунду"""
        self.state.current_round += 1

        # Определяем команду
        if self.state.current_round % 2 == 1:
            self.state.current_encoder_team = Team.RED
            self.state.red_round += 1
            team_ids = self.state.red_team_ids
            team_round = self.state.red_round
            team_name = "Красные"
        else:
            self.state.current_encoder_team = Team.BLUE
            self.state.blue_round += 1
            team_ids = self.state.blue_team_ids
            team_round = self.state.blue_round
            team_name = "Синие"

        if not team_ids:
            return

        # Выбираем шифровальщика
        idx = (team_round - 1) % len(team_ids)
        self.state.current_encoder_id = team_ids[idx]

        # Снимаем флаг со всех и ставим текущему
        for pid in self.state.players:
            self.state.players[pid].is_encoder = False
        self.state.players[self.state.current_encoder_id].is_encoder = True

        # Генерируем код
        self.state.current_code = self._generate_code()

        # Создаем запись в истории
        encoder = self.state.players[self.state.current_encoder_id]
        self.current_round_history = RoundHistory(
            team=self.state.current_encoder_team,
            round_num=team_round,
            encoder=encoder.nickname,
            encoder_id=encoder.id
        )
        self.current_round_history.code = self.state.current_code
        self.rounds_history.append(self.current_round_history)

        # Сообщение в лог
        self._add_message(f"▶️ Раунд {team_round} ({team_name}). Шифрует {encoder.nickname}")

    def submit_clue(self, player_id: str, clue_words: List[str]) -> bool:
        """Шифровальщик отправляет подсказки"""
        if (player_id != self.state.current_encoder_id or
                len(clue_words) != 3 or
                self.state.phase != GamePhase.ENCODING):
            return False

        encoder = self.state.players[player_id]

        self.state.current_clue = Clue(
            encoder_id=player_id,
            encoder_nickname=encoder.nickname,
            words=clue_words,
            target_code=self.state.current_code,
            round_number=self.state.current_round
        )

        # Сохраняем подсказки в историю
        if self.current_round_history:
            self.current_round_history.clues = clue_words

        self.state.phase = GamePhase.GUESSING

        team_name = "Красные" if self.state.current_encoder_team == Team.RED else "Синие"
        round_num = self.state.red_round if self.state.current_encoder_team == Team.RED else self.state.blue_round
        self._add_message(f"💭 {team_name} дали подсказки (Раунд {round_num})")

        return True

    def make_guess(self, player_id: str, guess_code: List[int], team: Team) -> bool:
        """Команда противника делает предположение"""
        if (self.state.phase != GamePhase.GUESSING or
                len(guess_code) != 3 or
                len(set(guess_code)) != 3 or
                team == self.state.current_encoder_team):
            return False

        player = self.state.players[player_id]

        guess = Guess(
            player_id=player_id,
            team=team,
            guess_code=guess_code,
            is_correct=(guess_code == self.state.current_code)
        )

        self.state.current_guesses.append(guess)

        # Сохраняем в историю
        if self.current_round_history:
            self.current_round_history.guesses.append({
                'player': player.nickname,
                'player_id': player_id,
                'team': team.value,
                'code': guess_code,
                'correct': guess.is_correct
            })

        return True

    def confirm_intercept(self, encoder_id: str, intercepting_team: Team) -> bool:
        """Шифровальщик подтверждает перехват"""
        if encoder_id != self.state.current_encoder_id:
            print(f"confirm_intercept: не тот шифровальщик {encoder_id} != {self.state.current_encoder_id}")
            return False

        if self.state.phase != GamePhase.GUESSING:
            print(f"confirm_intercept: не та фаза {self.state.phase}")
            return False

        # Проверка на первый раунд
        if self.state.current_encoder_team == Team.RED and self.state.red_round == 1:
            self._add_message("⚠️ В первом раунде красных перехват невозможен")
            return False
        if self.state.current_encoder_team == Team.BLUE and self.state.blue_round == 1:
            self._add_message("⚠️ В первом раунде синих перехват невозможен")
            return False

        # Проверяем, был ли правильный код среди догадок
        correct_guesses = [
            g for g in self.state.current_guesses
            if g.is_correct and g.team == intercepting_team
        ]

        if correct_guesses:
            if intercepting_team == Team.RED:
                self.state.red_intercepts += 1
                self._add_message(f"🎯 КРАСНЫЕ перехватили код! {self.state.current_code}")
            elif intercepting_team == Team.BLUE:
                self.state.blue_intercepts += 1
                self._add_message(f"🎯 СИНИЕ перехватили код! {self.state.current_code}")

            if self.current_round_history:
                self.current_round_history.intercepted = True
                self.current_round_history.intercepted_by = intercepting_team.value
                self.current_round_history.round_completed = True

            # Проверяем победу
            winner = self._check_winner()
            if winner:
                self.state.phase = GamePhase.GAME_OVER
                self._add_message(f"🏆 {winner} ПОБЕДИЛИ!")
                return True

            # Переходим к следующему раунду
            self._end_current_round()
            return True

        return False

    def confirm_own_guess(self, encoder_id: str, guessed_correctly: bool) -> bool:
        """
        Шифровальщик подтверждает, угадала ли своя команда код.
        """
        print(f"confirm_own_guess: encoder_id={encoder_id}, guessed_correctly={guessed_correctly}")
        print(f"current_encoder_id={self.state.current_encoder_id}, phase={self.state.phase}")

        if encoder_id != self.state.current_encoder_id:
            print("Ошибка: не тот шифровальщик")
            return False

        if self.state.phase != GamePhase.GUESSING:
            print(f"Ошибка: не та фаза {self.state.phase}")
            return False

        # Сохраняем результат
        if self.current_round_history:
            self.current_round_history.own_team_guessed = guessed_correctly
            self.current_round_history.round_completed = True

        if not guessed_correctly:
            # Штраф, если не угадали
            if self.state.current_encoder_team == Team.RED:
                self.state.red_mistakes += 1
                self._add_message("❌ Красные не угадали свой код! Штраф")
            else:
                self.state.blue_mistakes += 1
                self._add_message("❌ Синие не угадали свой код! Штраф")
        else:
            # Своя команда угадала - просто сообщение
            team_name = "Красные" if self.state.current_encoder_team == Team.RED else "Синие"
            self._add_message(f"✅ {team_name} угадали свой код!")

        # Проверяем победу после штрафа
        winner = self._check_winner()
        if winner:
            self.state.phase = GamePhase.GAME_OVER
            self._add_message(f"🏆 {winner} ПОБЕДИЛИ!")
            return True

        # Переходим к следующему раунду
        self._end_current_round()
        return True

    def _end_current_round(self):
        """Завершает текущий раунд и начинает новый"""
        print("Завершение раунда и переход к следующему")

        # Отмечаем раунд как завершенный в истории
        if self.current_round_history:
            self.current_round_history.round_completed = True

        # Очищаем текущее состояние
        self.state.current_clue = None
        self.state.current_guesses = []
        self.state.phase = GamePhase.ENCODING
        self.state.current_encoder_id = None
        self.state.current_code = None

        # Начинаем новый раунд
        self._next_round()

    def _check_winner(self) -> Optional[str]:
        if self.state.red_intercepts >= 2:
            return "КРАСНЫЕ"
        if self.state.blue_intercepts >= 2:
            return "СИНИЕ"
        if self.state.red_mistakes >= 2:
            return "СИНИЕ"
        if self.state.blue_mistakes >= 2:
            return "КРАСНЫЕ"
        return None

    def _add_message(self, message: str):
        self.state.message_log.append(message)
        if len(self.state.message_log) > 50:
            self.state.message_log.pop(0)

    def get_rounds_history(self, for_player_id: Optional[str] = None) -> List[dict]:
        if not for_player_id or for_player_id not in self.state.players:
            return [r.to_dict() for r in self.rounds_history]

        player = self.state.players[for_player_id]
        player_team = player.team.value if player.team else None

        history = []
        for round_data in self.rounds_history:
            data = round_data.to_dict(player_team)
            history.append(data)

        return history

    def get_state_for_player(self, player_id: str) -> dict:
        """Возвращает состояние для конкретного игрока"""
        state_dict = self.state.model_dump()

        # Добавляем историю раундов
        state_dict['rounds_history'] = self.get_rounds_history(player_id)

        # Добавляем информацию об игроке
        if player_id in self.state.players:
            player = self.state.players[player_id]
            state_dict['my_team'] = player.team.value if player.team else None
            state_dict['my_nickname'] = player.nickname
            state_dict['is_encoder'] = player.is_encoder

        return state_dict