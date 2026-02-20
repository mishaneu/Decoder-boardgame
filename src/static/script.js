// Состояние клиента
let socket = null;
let playerId = null;
let roomCode = null;
let myNickname = null;
let gameState = null;
let myTeam = null;

// DOM элементы
let elements = {};

// Инициализация после загрузки страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM загружен');
    initElements();
    initEventListeners();
});

function initElements() {
    console.log('Инициализация элементов');

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

    // Панель результатов для шифровальщика
    elements.resolvePanel = document.getElementById('resolve-panel');
    elements.ownTeamGuessedBtn = document.getElementById('own-team-guessed');
    elements.ownTeamNotGuessedBtn = document.getElementById('own-team-not-guessed');
    elements.enemyTeamGuessedBtn = document.getElementById('enemy-team-guessed');

    // Лог
    elements.messageLog = document.getElementById('message-log');

    console.log('Элементы инициализированы');
}

function initEventListeners() {
    console.log('Инициализация обработчиков событий');

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

        elements.clue1.value = '';
        elements.clue2.value = '';
        elements.clue3.value = '';
    });

    // КНОПКИ РЕЗУЛЬТАТОВ
    if (elements.ownTeamGuessedBtn) {
        elements.ownTeamGuessedBtn.addEventListener('click', () => {
            console.log('Кнопка "Своя команда угадала" нажата');
            sendRoundResult('own_team_guessed');
        });
    }

    if (elements.ownTeamNotGuessedBtn) {
        elements.ownTeamNotGuessedBtn.addEventListener('click', () => {
            console.log('Кнопка "Своя команда не угадала" нажата');
            sendRoundResult('own_team_not_guessed');
        });
    }

    if (elements.enemyTeamGuessedBtn) {
        elements.enemyTeamGuessedBtn.addEventListener('click', () => {
            console.log('Кнопка "Противники угадали" нажата');
            sendRoundResult('enemy_team_guessed');
        });
    }

    console.log('Обработчики событий инициализированы');
}

// Функция для отправки результата раунда
function sendRoundResult(result) {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
        console.error('WebSocket не подключен');
        return;
    }

    if (!roomCode || !playerId) {
        console.error('Нет roomCode или playerId');
        return;
    }

    const message = {
        type: 'round_result',
        room_code: roomCode,
        player_id: playerId,
        result: result
    };

    console.log('Отправка результата:', message);
    socket.send(JSON.stringify(message));
}

// WebSocket соединение
function connectAndCreate() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

    console.log('Подключение к:', wsUrl);

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('WebSocket открыт, отправка create_room');
        sendMessage({
            type: 'create_room'
        });
    };

    socket.onmessage = (event) => {
        console.log('Получено сообщение:', event.data);
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    socket.onclose = () => {
        console.log('Соединение закрыто');
    };

    socket.onerror = (error) => {
        console.error('WebSocket ошибка:', error);
    };
}

function connectAndJoin() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws`;

    console.log('Подключение к:', wsUrl);

    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
        console.log('WebSocket открыт, отправка join_room');
        sendMessage({
            type: 'join_room',
            room_code: roomCode,
            nickname: myNickname
        });
    };

    socket.onmessage = (event) => {
        console.log('Получено сообщение:', event.data);
        const data = JSON.parse(event.data);
        handleMessage(data);
    };

    socket.onclose = () => {
        console.log('Соединение закрыто');
    };

    socket.onerror = (error) => {
        console.error('WebSocket ошибка:', error);
    };
}

function sendMessage(message) {
    if (socket && socket.readyState === WebSocket.OPEN) {
        const jsonMessage = JSON.stringify(message);
        console.log('Отправка:', jsonMessage);
        socket.send(jsonMessage);
    } else {
        console.error('WebSocket не готов, состояние:', socket?.readyState);
    }
}

// Обработка сообщений от сервера
function handleMessage(data) {
    console.log('Обработка сообщения:', data);

    switch (data.type) {
        case 'room_created':
            console.log('Комната создана, код:', data.room_code);
            roomCode = data.room_code;
            connectAndJoin();
            break;

        case 'joined':
            console.log('Присоединился к комнате, playerId:', data.player_id);
            playerId = data.player_id;
            roomCode = data.room_code;
            showLobbyScreen();
            break;

        case 'state_update':
            console.log('Обновление состояния');
            gameState = data.state;
            if (data.your_player_id === playerId) {
                if (gameState.red_team_ids && gameState.red_team_ids.includes(playerId)) {
                    myTeam = 'red';
                } else if (gameState.blue_team_ids && gameState.blue_team_ids.includes(playerId)) {
                    myTeam = 'blue';
                } else {
                    myTeam = 'spectator';
                }
                console.log('Моя команда:', myTeam);
            }
            updateUI();
            break;

        case 'error':
            console.error('Ошибка от сервера:', data.message);
            showError(data.message);
            break;
    }
}

// Обновление интерфейса
function updateUI() {
    if (!gameState) return;

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
    elements.redTeamList.innerHTML = '';
    elements.blueTeamList.innerHTML = '';
    elements.spectatorsList.innerHTML = '';

    elements.roomCodeDisplay.textContent = roomCode;

    if (gameState.players) {
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
    }

    const redCount = gameState.red_team_ids ? gameState.red_team_ids.length : 0;
    const blueCount = gameState.blue_team_ids ? gameState.blue_team_ids.length : 0;
    elements.startGameBtn.disabled = !(redCount >= 2 && blueCount >= 2);
}

function updateGameUI() {
    showGameScreen();

    elements.gameRoomCode.textContent = roomCode;

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

    updateSecretWords();
    updateGamePhase();
    updateMessageLog();
}

function updateSecretWords() {
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
    const phaseText = {
        'encoding': '🔐 Шифрование',
        'guessing': '🤔 Ожидание результатов',
        'game_over': '🏆 Игра окончена'
    };

    elements.phaseIndicator.textContent = phaseText[gameState.phase] || gameState.phase;

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

    elements.encoderPanel.style.display = 'none';
    elements.resolvePanel.style.display = 'none';

    if (gameState.phase === 'encoding') {
        if (gameState.current_encoder_id === playerId) {
            elements.encoderPanel.style.display = 'block';
            elements.encoderCode.textContent = gameState.current_code ? gameState.current_code.join('-') : '???';
        }
    } else if (gameState.phase === 'guessing') {
        // Показываем панель результатов ТОЛЬКО шифровальщику
        if (gameState.current_encoder_id === playerId) {
            console.log('Показываем панель результатов для шифровальщика');
            elements.resolvePanel.style.display = 'block';
        }
    }
}

function updateMessageLog() {
    if (!gameState.message_log) return;

    elements.messageLog.innerHTML = gameState.message_log
        .map(msg => `<div class="log-message">${msg}</div>`)
        .join('');

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

    const sortedHistory = [...gameState.rounds_history].reverse();

    sortedHistory.forEach(round => {
        if (!round.round_completed) return;

        const roundEl = document.createElement('div');
        roundEl.className = 'round-history-item';

        const isMyTeamRound = (myTeam === round.team);
        const teamEmoji = round.team === 'red' ? '🔴' : '🔵';
        const teamName = round.team === 'red' ? 'Красные' : 'Синие';

        let html = `<div class="round-header ${round.team}">
            ${teamEmoji} Раунд ${round.round_num} (${teamName}) - ${round.encoder}
        </div>`;

        if (round.clues && Array.isArray(round.clues) && round.clues.length === 3) {
            html += `<div class="clues-section">`;
            html += `<div class="clue-label">Подсказки:</div>`;
            html += `<div class="clues">${round.clues[0]} | ${round.clues[1]} | ${round.clues[2]}</div>`;
            html += `</div>`;
        }

        if (isMyTeamRound && round.code) {
            html += `<div class="code-section">`;
            html += `<div class="code-label">Код:</div>`;
            html += `<div class="code">${round.code.join('-')}</div>`;
            html += `</div>`;
        }

        if (round.intercepted) {
            const interceptor = round.intercepted_by === 'red' ? '🔴 Красные' : '🔵 Синие';
            html += `<div class="intercept-badge">🎯 Перехват команды ${interceptor}!</div>`;
        }

        if (round.mistake) {
            const team = round.team === 'red' ? '🔴 Красные' : '🔵 Синие';
            html += `<div class="mistake-badge">❌ ${team} получили штраф (не угадали свой код)</div>`;
        }

        if (round.own_team_guessed && !round.mistake && !round.intercepted) {
            html += `<div class="success-badge">✅ Своя команда угадала код</div>`;
        }

        roundEl.innerHTML = html;
        historyContainer.appendChild(roundEl);
    });
}