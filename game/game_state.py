import random
from typing import List, Dict, Optional
from .models import (
    GameState, Player, Team, Clue,
    GamePhase, SecretWords
)
from itertools import permutations


class DecryptoGame:
    def __init__(self, room_code: str, word_bank: List[str]):
        self.room_code = room_code
        self.word_bank = word_bank
        self.state = GameState(room_code=room_code)
        self.all_possible_codes = [list(p) for p in permutations([1, 2, 3, 4], 3)]
        self.intercept_given_in_current_round = False

        # НОВОЕ: хранилище истории раундов для отображения подсказок
        self.rounds_history = []  # список завершенных раундов

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

    def start_game(self, unique_codes: bool = True) -> bool:
        if len(self.state.red_team_ids) < 2 or len(self.state.blue_team_ids) < 2:
            self._add_message("❌ Нужно минимум по 2 игрока в каждой команде")
            return False

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

        self.rounds_history = []  # очищаем историю при старте новой игры

        self.state.phase = GamePhase.ENCODING
        self._next_round()
        self._add_message("🎮 Игра началась! Слова розданы")
        return True

    def _next_round(self):
        self.state.current_round += 1
        self.intercept_given_in_current_round = False

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

        idx = (team_round - 1) % len(team_ids)
        self.state.current_encoder_id = team_ids[idx]

        for pid in self.state.players:
            self.state.players[pid].is_encoder = False
        self.state.players[self.state.current_encoder_id].is_encoder = True

        self.state.current_code = random.choice(self.all_possible_codes)

        encoder = self.state.players[self.state.current_encoder_id]
        self._add_message(f"▶️ Раунд {team_round} ({team_name}). Шифрует {encoder.nickname}")

    def submit_clue(self, player_id: str, clue_words: List[str]) -> bool:
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

        self.state.phase = GamePhase.GUESSING

        team_name = "Красные" if self.state.current_encoder_team == Team.RED else "Синие"
        round_num = self.state.red_round if self.state.current_encoder_team == Team.RED else self.state.blue_round
        self._add_message(f"💭 {team_name} дали подсказки (Раунд {round_num})")

        return True

    def handle_round_result(self, encoder_id: str, result: str) -> bool:
        """
        Обработка результата раунда от шифровальщика
        result может быть:
        - 'own_team_guessed' - своя команда угадала (завершает раунд)
        - 'own_team_not_guessed' - своя команда не угадала (завершает раунд + штраф)
        - 'enemy_team_guessed' - противники угадали (ТОЛЬКО перехват, раунд не завершается)
        """
        print(f"handle_round_result: encoder_id={encoder_id}, result={result}")

        if encoder_id != self.state.current_encoder_id:
            print("Ошибка: не тот шифровальщик")
            return False

        if self.state.phase != GamePhase.GUESSING:
            print(f"Ошибка: не та фаза {self.state.phase}")
            return False

        team_name = "Красные" if self.state.current_encoder_team == Team.RED else "Синие"
        enemy_team = "Синие" if self.state.current_encoder_team == Team.RED else "Красные"

        # Проверка на первый раунд (нельзя перехватить в первом раунде команды)
        is_first_round = False
        if self.state.current_encoder_team == Team.RED and self.state.red_round == 1:
            is_first_round = True
        if self.state.current_encoder_team == Team.BLUE and self.state.blue_round == 1:
            is_first_round = True

        if result == 'enemy_team_guessed':
            # Противники угадали - даем перехват, но раунд НЕ завершаем
            if is_first_round:
                self._add_message(f"⚠️ В первом раунде {team_name.lower()} перехват невозможен!")
                return True

            if not self.intercept_given_in_current_round:
                self.intercept_given_in_current_round = True

                if self.state.current_encoder_team == Team.RED:
                    self.state.blue_intercepts += 1
                    self._add_message(f"🎯 СИНИЕ перехватили код у красных!")
                else:
                    self.state.red_intercepts += 1
                    self._add_message(f"🎯 КРАСНЫЕ перехватили код у синих!")

                winner = self._check_winner()
                if winner:
                    self.state.phase = GamePhase.GAME_OVER
                    self._add_message(f"🏆 {winner} ПОБЕДИЛИ!")
            else:
                self._add_message(f"⚠️ В этом раунде уже был перехват!")

            return True

        elif result == 'own_team_not_guessed':
            # НОВОЕ: сохраняем раунд в историю перед завершением
            if self.state.current_clue:
                round_data = {
                    'team': self.state.current_encoder_team.value,
                    'round_num': self.state.red_round if self.state.current_encoder_team == Team.RED else self.state.blue_round,
                    'code': self.state.current_code,
                    'clues': self.state.current_clue.words,
                    'completed': True,
                    'intercept_given': self.intercept_given_in_current_round,
                    'mistake': True
                }
                self.rounds_history.append(round_data)

            if self.state.current_encoder_team == Team.RED:
                self.state.red_mistakes += 1
                self._add_message(f"❌ Красные не угадали свой код! Штраф. Раунд завершен.")
            else:
                self.state.blue_mistakes += 1
                self._add_message(f"❌ Синие не угадали свой код! Штраф. Раунд завершен.")

            self._end_current_round()

        elif result == 'own_team_guessed':
            # НОВОЕ: сохраняем раунд в историю перед завершением
            if self.state.current_clue:
                round_data = {
                    'team': self.state.current_encoder_team.value,
                    'round_num': self.state.red_round if self.state.current_encoder_team == Team.RED else self.state.blue_round,
                    'code': self.state.current_code,
                    'clues': self.state.current_clue.words,
                    'completed': True,
                    'intercept_given': self.intercept_given_in_current_round,
                    'mistake': False
                }
                self.rounds_history.append(round_data)

            self._add_message(f"✅ {team_name} угадали свой код! Раунд завершен.")
            self._end_current_round()

        winner = self._check_winner()
        if winner:
            self.state.phase = GamePhase.GAME_OVER
            self._add_message(f"🏆 {winner} ПОБЕДИЛИ!")

        return True

    def _end_current_round(self):
        print("Завершение раунда и переход к следующему")

        self.state.current_clue = None
        self.state.phase = GamePhase.ENCODING
        self.state.current_encoder_id = None
        self.state.current_code = None

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

    def get_state_for_player(self, player_id: str) -> dict:
        """Возвращает состояние для конкретного игрока"""
        state_dict = self.state.model_dump()

        # НОВОЕ: добавляем историю раундов в состояние
        state_dict['rounds_history'] = self.rounds_history

        if player_id in self.state.players:
            player = self.state.players[player_id]
            state_dict['my_team'] = player.team.value if player.team else None
            state_dict['my_nickname'] = player.nickname
            state_dict['is_encoder'] = player.is_encoder

        return state_dict