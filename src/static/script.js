// Состояние клиента
let socket = null;
let playerId = null;
let roomCode = null;
let myNickname = null;
let gameState = null;
let myTeam = null;

// DOM элементы (будем инициализировать после загрузки)
let elements = {};

// Инициализация после загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    initElements();
    initEventListeners();
    checkUrlForRoom();
});

function initElements() {
    // Экраны
    elements.loginScreen = document.getElementById('login-screen');
    elements.lobbyScreen = document.getElementById('lobby-screen');
    elements.gameScreen = document.getElementById('game-screen');

    // Вкладки логина
    elements.tabBtns = document.querySelectorAll('.tab-btn');
    elements.createTab = document.getElementById('create-tab');
    elements.joinTab = document.getElementById('join-tab');

    // Поля ввода
    elements.createNickname = document.getElementById('create-nickname');
    elements.joinRoomCode = document.getElementById('join-room-code');
    elements.joinNickname = document.getElementById('join-nickname');
    elements.loginError = document.getElementById('login-error');

    // Кнопки
    elements.createRoomBtn = document.getElementById('create-room-btn');
    elements.joinRoomBtn = document.getElementById('join-room-btn');
    elements.startGameBtn = document.getElementById('start-game-btn');
    elements.leaveRoomBtn = document.getElementById('leave-room-btn');
    elements.copyRoomCode = document.getElementById('copy-room-code');

    // Лобби
    elements.roomCodeDisplay = document.getElementById('room-code-display');
    elements.redTeamList = document.getElementById('red-team-list');
    elements.blueTeamList = document.getElementById('blue-team-list');
    elements.spectatorsList = document.getElementById('spectators-list');

    // Кнопки команд
    document.querySelectorAll('.join-team-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const team = e.target.dataset.team;
            joinTeam(team);
        });
    });

    // Игровой экран
    elements.gameRoomCode = document.getElementById('game-room-code');
    elements.redIntercepts = document.getElementById('red-intercepts');
    elements.blueIntercepts = document.getElementById('blue-intercepts');
    elements.redMistakes = document.getElementById('red-mistakes');
    elements.blueMistakes = document.getElementById('blue-mistakes');
    elements.currentRound = document.getElementById('current-round');

    elements.redWords = document.getElementById('red-words');
    elements.blueWords = document.getElementById('blue-words');
    elements.spectatorNote = document.getElementById('spectator-note');

    elements.phaseIndicator = document.getElementById('phase-indicator');
    elements.cluesDisplay = document.getElementById('clues-display');
    elements.cluesBox = document.getElementById('clues-box');

    elements.encoderPanel = document.getElementById('encoder-panel');
    elements.encoderCode = document.getElementById('encoder-code');
    elements.clue1 = document.getElementById('clue1');
    elements.clue2 = document.getElementById('clue2');
    elements.clue3 = document.getElementById('clue3');
    elements.submitClueBtn = document.getElementById('submit-clue-btn');

    elements.guessingPanel = document.getElementById('guessing-panel');
    elements.guessingClues = document.getElementById('guessing-clues');
    elements.guess1 = document.getElementById('guess1');
    elements.guess2 = document.getElementById('guess2');
    elements.guess3 = document.getElementById('guess3');
    elements.submitGuessBtn = document.getElementById('submit-guess-btn');

    elements.resolvePanel = document.getElementById('resolve-panel');
    elements.resolveYes = document.getElementById('resolve-yes');
    elements.resolveNo = document.getElementById('resolve-no');

    elements.messageLog = document.getElementById('message-log');
}

function initEventListeners() {
    // Переключение вкладок логина
    elements.tabBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            elements.tabBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            if (btn.dataset.tab === 'create') {
                elements.createTab.classList.add('active');
                elements.joinTab.classList.remove('active');
            } else {
                elements.createTab.classList.remove('active');
                elements.joinTab.classList.add('active');
            }
        });
    });

    // Создание комнаты
    elements.createRoomBtn.addEventListener('click', () => {
        const nickname = elements.createNickname.value.trim();
        if (!nickname) {
            showError('Введите никнейм');
            return;
        }
        myNickname = nickname;
        connectAndCreate();
    });

    // Присоединение к комнате
    elements.joinRoomBtn.addEventListener('click', () => {
        const nickname = elements.joinNickname.value.trim();
        const code = elements.joinRoomCode.value.trim().toUpperCase();

        if (!nickname) {
            showError('Введите никнейм');
            return;
        }
        if (!code) {
            showError('Введите код комнаты');
            return;
        }

        myNickname = nickname;
        roomCode = code;
        connectAndJoin();
    });

    // Копирование кода комнаты
    elements.copyRoomCode.addEventListener('click', () => {
        navigator.clipboard.writeText(roomCode);
        alert('Код скопирован!');
    });

    // Выход из комнаты
    elements.leaveRoomBtn.addEventListener('click', () => {
        if (socket) {
            socket.close();
        }
        showLoginScreen();
    });

    // Старт игры
    elements.startGameBtn.addEventListener('click', () => {
        sendMessage({
            type: 'start_game',
            room_code: roomCode
        });
    });

    // Отправка подсказок
    elements.submitClueBtn.addEventListener('click', () => {
        const clue1 = elements.clue1.value.trim();
        const clue2 = elements.clue2.value.trim();
        const clue3 = elements.clue3.value.trim();

        if (!clue1 || !clue2 || !clue3) {
            alert('Введите все три подсказки');
            return;
        }

        sendMessage({
            type: 'submit_clue',
            room_code: roomCode,
            player_id: playerId,
            clue_words: [clue1, clue2, clue3]
        });

        // Очищаем поля
        elements.clue1.value = '';
        elements.clue2.value = '';
        elements.clue3.value = '';
    });

    // Отправка догадки
    elements.submitGuessBtn.addEventListener('click', () => {
        const guess = [
            parseInt(elements.guess1.value),
            parseInt(elements.guess2.value),
            parseInt(elements.guess3.value)
        ];

        sendMessage({
            type: 'make_guess',
            room_code: roomCode,
            player_id: playerId,
            team: myTeam,
            guess_code: guess
        });
    });

    // Завершение раунда
    elements.resolveYes.addEventListener('click', () => {
        console.log('Нажали ДА - своя команда угадала');
        sendMessage({
            type: 'confirm_own_guess',  // БЫЛО: 'resolve_round'
            room_code: roomCode,
            player_id: playerId,
            guessed_correctly: true
        });
    });

    elements.resolveNo.addEventListener('click', () => {
        console.log('Нажали НЕТ - своя команда НЕ угадала');
        sendMessage({
            type: 'confirm_own_guess',  // БЫЛО: 'resolve_round'
            room_code: roomCode,
            player_id: playerId,
            guessed_correctly: false
        });
    });
}

function checkUrlForRoom() {
    // Можно добавить логику для URL параметров
}

// WebSocket соединение
function connectAndCreate() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        sendMessage({
            type: 'create_room'
        });
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    socket.onclose = () => {
        console.log('Соединение закрыто');
    };
}

function connectAndJoin() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        sendMessage({
            type: 'join_room',
            room_code: roomCode,
            nickname: myNickname
        });
    };

    socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    socket.onclose = () => {
        console.log('Соединение закрыто');
    };
}

function sendMessage(message) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(JSON.stringify(message));
    }
}

// Обработка сообщений от сервера
function handleMessage(data) {
    console.log('Received:', data);

    switch (data.type) {
        case 'room_created':
            roomCode = data.room_code;
            connectAndJoin(); // Переподключаемся для входа
            break;

        case 'joined':
            playerId = data.player_id;
            roomCode = data.room_code;
            showLobbyScreen();
            break;

        case 'state_update':
            gameState = data.state;
            if (data.your_player_id === playerId) {
                // Определяем свою команду
                if (gameState.red_team_ids.includes(playerId)) {
                    myTeam = 'red';
                } else if (gameState.blue_team_ids.includes(playerId)) {
                    myTeam = 'blue';
                } else {
                    myTeam = 'spectator';
                }
            }
            updateUI();
            break;

        case 'error':
            showError(data.message);
            break;
    }
}

// Обновление интерфейса
function updateUI() {
    if (!gameState) return;

    // Проверяем, на каком мы экране
    if (gameState.phase === 'waiting' || gameState.phase === 'setup') {
        updateLobbyUI();
    } else {
        updateGameUI();
    }
    if (gameState.rounds_history) {
        displayRoundHistory();
    }
}

function updateLobbyUI() {
    // Очищаем списки
    elements.redTeamList.innerHTML = '';
    elements.blueTeamList.innerHTML = '';
    elements.spectatorsList.innerHTML = '';

    // Отображаем код комнаты
    elements.roomCodeDisplay.textContent = roomCode;

    // Заполняем игроков
    Object.values(gameState.players).forEach(player => {
        const playerEl = document.createElement('div');
        playerEl.className = 'player-item';

        let teamList;
        if (player.team === 'red') {
            teamList = elements.redTeamList;
        } else if (player.team === 'blue') {
            teamList = elements.blueTeamList;
        } else {
            teamList = elements.spectatorsList;
        }

        playerEl.innerHTML = `
            <span>${player.nickname}</span>
            ${player.is_encoder ? '<span class="encoder-badge">🎤</span>' : ''}
        `;

        teamList.appendChild(playerEl);
    });

    // Активируем кнопку старта если достаточно игроков
    const redCount = gameState.red_team_ids.length;
    const blueCount = gameState.blue_team_ids.length;
    elements.startGameBtn.disabled = !(redCount >= 2 && blueCount >= 2);
}

function updateGameUI() {
    // Показываем игровой экран
    showGameScreen();

    // Обновляем код комнаты
    elements.gameRoomCode.textContent = roomCode;

    // Обновляем счет
    elements.redIntercepts.textContent = gameState.red_intercepts || 0;
    elements.blueIntercepts.textContent = gameState.blue_intercepts || 0;
    elements.redMistakes.textContent = gameState.red_mistakes || 0;
    elements.blueMistakes.textContent = gameState.blue_mistakes || 0;


    if (gameState.current_encoder_team === 'red') {
        elements.currentRound.textContent = `${gameState.red_round || 0} (🔴 Красные)`;
    } else if (gameState.current_encoder_team === 'blue') {
        elements.currentRound.textContent = `${gameState.blue_round || 0} (🔵 Синие)`;
    } else {
        elements.currentRound.textContent = `${gameState.current_round || 0}`;
    }

    // Показываем секретные слова (только своей команды)
    updateSecretWords();

    // Обновляем фазу игры
    updateGamePhase();

    // Обновляем лог
    updateMessageLog();

    if (gameState.rounds_history) {
        displayRoundHistory();
    }
}

function updateSecretWords() {
    // Скрываем все карточки слов по умолчанию
    elements.redWords.style.display = 'none';
    elements.blueWords.style.display = 'none';
    elements.spectatorNote.style.display = 'none';

    if (myTeam === 'red' && gameState.secret_words) {
        elements.redWords.style.display = 'grid';
        elements.redWords.innerHTML = gameState.secret_words.team_red
            .map(word => `<div class="word-item">${word}</div>`)
            .join('');
    } else if (myTeam === 'blue' && gameState.secret_words) {
        elements.blueWords.style.display = 'grid';
        elements.blueWords.innerHTML = gameState.secret_words.team_blue
            .map(word => `<div class="word-item">${word}</div>`)
            .join('');
    } else {
        elements.spectatorNote.style.display = 'block';
    }
}

function updateGamePhase() {
    // Обновляем индикатор фазы
    const phaseText = {
        'encoding': '🔐 Шифрование',
        'guessing': '🤔 Угадывание',
        'reveal': '📢 Раскрытие',
        'game_over': '🏆 Игра окончена'
    };

    elements.phaseIndicator.textContent = phaseText[gameState.phase] || gameState.phase;

    // Показываем подсказки если есть
    if (gameState.current_clue) {
        elements.cluesDisplay.innerHTML = gameState.current_clue.words
            .map(word => `<span class="clue-word">${word}</span>`)
            .join('');
        elements.cluesBox.style.display = 'block';
    } else {
        elements.cluesDisplay.innerHTML = `
            <span class="clue-word">---</span>
            <span class="clue-word">---</span>
            <span class="clue-word">---</span>
        `;
    }

    // Скрываем все панели
    elements.encoderPanel.style.display = 'none';
    elements.guessingPanel.style.display = 'none';
    elements.resolvePanel.style.display = 'none';

    // Показываем нужную панель в зависимости от фазы и роли
    if (gameState.phase === 'encoding') {
        // Проверяем, шифровальщик ли я
        if (gameState.current_encoder_id === playerId) {
            elements.encoderPanel.style.display = 'block';
            elements.encoderCode.textContent = gameState.current_code.join('-');
        }
    } else if (gameState.phase === 'guessing') {
        // Проверяю, могу ли я угадывать (я в команде противника)
        const encoderTeam = gameState.current_encoder_team;
        if (myTeam && myTeam !== encoderTeam && myTeam !== 'spectator') {
            elements.guessingPanel.style.display = 'block';
            if (gameState.current_clue) {
                elements.guessingClues.textContent = gameState.current_clue.words.join(' | ');
            }
        }

        // ПОКАЗЫВАЕМ ПАНЕЛЬ ЗАВЕРШЕНИЯ РАУНДА ТОЛЬКО ДЛЯ ШИФРОВАЛЬЩИКА
        if (gameState.current_encoder_id === playerId) {
            console.log('Показываем панель завершения раунда для шифровальщика');
            elements.resolvePanel.style.display = 'block';
        }
    }
}

function updateMessageLog() {
    if (!gameState.message_log) return;

    elements.messageLog.innerHTML = gameState.message_log
        .map(msg => `<div class="log-message">${msg}</div>`)
        .join('');

    // Скроллим вниз
    elements.messageLog.scrollTop = elements.messageLog.scrollHeight;
}

function joinTeam(team) {
    sendMessage({
        type: 'join_team',
        room_code: roomCode,
        player_id: playerId,
        team: team
    });
}

function showLoginScreen() {
    elements.loginScreen.classList.add('active');
    elements.lobbyScreen.classList.remove('active');
    elements.gameScreen.classList.remove('active');
}

function showLobbyScreen() {
    elements.loginScreen.classList.remove('active');
    elements.lobbyScreen.classList.add('active');
    elements.gameScreen.classList.remove('active');
}

function showGameScreen() {
    elements.loginScreen.classList.remove('active');
    elements.lobbyScreen.classList.remove('active');
    elements.gameScreen.classList.add('active');
}

function showError(message) {
    elements.loginError.textContent = message;
    setTimeout(() => {
        elements.loginError.textContent = '';
    }, 3000);
}

function displayRoundHistory() {
    if (!gameState || !gameState.rounds_history) {
        return;
    }

    const historyContainer = document.getElementById('rounds-history');
    if (!historyContainer) return;

    historyContainer.innerHTML = '';

    // Показываем историю в обратном порядке
    const sortedHistory = [...gameState.rounds_history].reverse();

    sortedHistory.forEach(round => {
        // Показываем только завершённые раунды
        if (!round.round_completed) return;

        const roundEl = document.createElement('div');
        roundEl.className = 'round-history-item';

        const isMyTeamRound = (myTeam === round.team);
        const teamEmoji = round.team === 'red' ? '🔴' : '🔵';
        const teamName = round.team === 'red' ? 'Красные' : 'Синие';

        let html = `<div class="round-header ${round.team}">
            ${teamEmoji} Раунд ${round.round_num} (${teamName}) - ${round.encoder}
        </div>`;

        // Подсказки (видны всем для завершённых раундов)
        if (round.clues && Array.isArray(round.clues) && round.clues.length === 3) {
            html += `<div class="clues-section">`;
            html += `<div class="clue-label">Подсказки:</div>`;
            html += `<div class="clues">${round.clues[0]} | ${round.clues[1]} | ${round.clues[2]}</div>`;
            html += `</div>`;
        }

        // Код (виден только своей команде для завершённых раундов)
        if (isMyTeamRound && round.code) {
            html += `<div class="code-section">`;
            html += `<div class="code-label">Код:</div>`;
            html += `<div class="code">${round.code.join('-')}</div>`;
            html += `</div>`;
        }

        // Результаты (только для завершённых раундов)
        if (round.intercepted) {
            const interceptor = round.intercepted_by === 'red' ? '🔴 Красные' : '🔵 Синие';
            html += `<div class="intercept-badge">🎯 Перехват команды ${interceptor}!</div>`;
        }

        if (round.own_team_guessed !== null && round.own_team_guessed !== undefined) {
            if (round.own_team_guessed) {
                html += `<div class="success-badge">✅ Своя команда угадала</div>`;
            } else {
                html += `<div class="mistake-badge">❌ Своя команда НЕ угадала</div>`;
            }
        }

        roundEl.innerHTML = html;
        historyContainer.appendChild(roundEl);
    });
}