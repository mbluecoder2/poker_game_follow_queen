let socket = io({
    transports: ['websocket', 'polling'],
    reconnection: true,
    reconnectionAttempts: 10,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    timeout: 20000
});
let gameState = null;
let sessionId = null;
let myPlayerName = null;

// Display mode and theme preferences
let currentDisplayMode = 'standard';
let currentTheme = 'green';

function setDisplayMode(mode) {
    currentDisplayMode = mode;
    document.body.setAttribute('data-display-mode', mode);
    savePreferences();
    if (gameState) updateDisplay();
}

function setTheme(theme) {
    currentTheme = theme;
    document.body.setAttribute('data-theme', theme);
    savePreferences();
}

function savePreferences() {
    if (!myPlayerName) return;
    localStorage.setItem(`poker_prefs_${myPlayerName}`,
        JSON.stringify({ theme: currentTheme, displayMode: currentDisplayMode }));
}

function loadPreferences() {
    if (!myPlayerName) return;
    const saved = localStorage.getItem(`poker_prefs_${myPlayerName}`);
    if (saved) {
        try {
            const prefs = JSON.parse(saved);
            if (prefs.theme) {
                currentTheme = prefs.theme;
                document.body.setAttribute('data-theme', prefs.theme);
                document.getElementById('themeSelect').value = prefs.theme;
            }
            if (prefs.displayMode) {
                currentDisplayMode = prefs.displayMode;
                document.body.setAttribute('data-display-mode', prefs.displayMode);
                document.getElementById('displayMode').value = prefs.displayMode;
            }
        } catch (e) {
            console.log('Error loading preferences:', e);
        }
    }
}

function toggleFoldedStrip() {
    const strip = document.getElementById('lfFoldedStrip');
    if (strip) strip.classList.toggle('expanded');
}

// Show loading state in dropdown initially
function setDropdownLoading(loading) {
    const dropdown = document.getElementById('playerName');
    const joinStatus = document.getElementById('joinStatus');
    if (loading) {
        dropdown.innerHTML = '<option value="">Loading...</option>';
        dropdown.disabled = true;
        if (joinStatus) joinStatus.textContent = 'Waiting for server connection...';
    } else {
        dropdown.disabled = false;
        if (joinStatus) joinStatus.textContent = '';
    }
}

// Set loading state on page load
setDropdownLoading(true);

// Socket.IO connection event handlers
socket.on('connect', () => {
    console.log('Socket connected');
    setDropdownLoading(false);
});

socket.on('connect_error', (error) => {
    console.log('Connection error:', error);
    const dropdown = document.getElementById('playerName');
    dropdown.innerHTML = '<option value="">Connection failed - retrying...</option>';
    const joinStatus = document.getElementById('joinStatus');
    if (joinStatus) joinStatus.textContent = 'Server may be starting up, please wait...';
});

socket.on('disconnect', (reason) => {
    console.log('Disconnected:', reason);
    const joinStatus = document.getElementById('joinStatus');
    if (joinStatus && !myPlayerName) {
        joinStatus.textContent = 'Disconnected - reconnecting...';
    }
});

socket.on('reconnect', (attemptNumber) => {
    console.log('Reconnected after', attemptNumber, 'attempts');
    const joinStatus = document.getElementById('joinStatus');
    if (joinStatus) joinStatus.textContent = '';
});

// Socket.IO event listeners
socket.on('connected', (data) => {
    sessionId = data.session_id;
    console.log('Connected with session:', sessionId);
});

socket.on('name_availability', (data) => {
    setDropdownLoading(false);
    updatePlayerNameDropdown(data.all_names, data.taken);
});

socket.on('join_success', (data) => {
    myPlayerName = data.name;
    document.getElementById('joinSection').style.display = 'none';
    document.getElementById('gameControls').style.display = 'flex';
    document.getElementById('gameTitle').innerHTML = `<span class="royal-flush-icon"></span> Poker - Multiplayer - ${data.name}`;
    updateResetButtonVisibility();
    updateStatusMessage();
    loadPreferences();
});

socket.on('join_failed', (data) => {
    document.getElementById('joinStatus').textContent = data.message;
});

socket.on('game_state', (state) => {
    gameState = state;

    // Safe logging with null checks
    const playerInfo = state.players ? state.players.map(p => {
        const cardCount = p.hole_cards ? p.hole_cards.length :
                         (p.down_cards && p.up_cards ? p.down_cards.length + p.up_cards.length : 0);
        return { id: p.id, name: p.name, cards: cardCount };
    }) : [];

    console.log('Game state received:', {
        myPlayerId: state.my_player_id,
        currentPlayer: state.current_player,
        isMyTurn: state.is_my_turn,
        gameStarted: state.game_started,
        gameMode: state.game_mode,
        hiLo: state.hi_lo,
        players: playerInfo
    });

    // Sync Hi-Lo checkbox with current game state
    const hiLoCheckbox = document.getElementById('hiLoMode');
    if (hiLoCheckbox && state.hi_lo !== undefined) {
        hiLoCheckbox.checked = state.hi_lo;
    }

    // Sync Two Sevens checkbox with current game state
    const twoSevensCheckbox = document.getElementById('twoSevensMode');
    if (twoSevensCheckbox && state.two_natural_sevens_wins !== undefined) {
        twoSevensCheckbox.checked = state.two_natural_sevens_wins;
    }

    // Sync Deal Sevens to Michael checkbox with current game state
    const dealSevensCheckbox = document.getElementById('dealSevensToMichael');
    if (dealSevensCheckbox && state.deal_sevens_to_michael !== undefined) {
        dealSevensCheckbox.checked = state.deal_sevens_to_michael;
    }

    updateDisplay();
    updateButtons();
    updateStatusMessage();
});

socket.on('game_locked', (data) => {
    console.log(data.message);
});

socket.on('new_game_button_disabled', () => {
    const newGameBtn = document.getElementById('newGameBtn');
    if (newGameBtn) {
        newGameBtn.disabled = true;
    }
});

socket.on('new_game_button_enabled', () => {
    const newGameBtn = document.getElementById('newGameBtn');
    if (newGameBtn) {
        newGameBtn.disabled = false;
    }
});

socket.on('game_reset', (data) => {
    // Game has been reset - reload the page to start fresh
    alert(data.message);
    location.reload();
});

socket.on('server_restart', (data) => {
    // Server is restarting - show message and auto-reload after delay
    document.body.innerHTML = `
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: linear-gradient(135deg, #1a3555 0%, #2c5a8f 100%); color: white; font-family: Arial, sans-serif;">
            <h1 style="font-size: 3rem; margin-bottom: 20px;">Server Restarting</h1>
            <p style="font-size: 1.5rem; color: #ffd700;">${data.message}</p>
            <p style="font-size: 1.2rem; margin-top: 30px;">Page will refresh automatically in <span id="countdown">5</span> seconds...</p>
        </div>
    `;
    let seconds = 5;
    const countdown = setInterval(() => {
        seconds--;
        const el = document.getElementById('countdown');
        if (el) el.textContent = seconds;
        if (seconds <= 0) {
            clearInterval(countdown);
            location.reload();
        }
    }, 1000);
});

socket.on('winners', (data) => {
    // Build winner display HTML with Hi-Lo support
    let winnerHTML = '';
    const isHiLo = data.hi_lo || false;

    data.winners.forEach(w => {
        // Determine win type badge styling
        let winTypeBadge = '';
        let winTypeColor = '#ffd700';

        if (w.win_type === 'low') {
            winTypeBadge = 'LOW';
            winTypeColor = '#2ecc71';
        } else if (w.win_type === 'SCOOP (high + low)') {
            winTypeBadge = 'SCOOP!';
            winTypeColor = '#e74c3c';
        } else if (w.win_type === 'high (scoops - no qualifying low)') {
            winTypeBadge = 'HIGH (No Low)';
            winTypeColor = '#ffd700';
        } else if (w.win_type === 'high' && isHiLo) {
            winTypeBadge = 'HIGH';
            winTypeColor = '#ffd700';
        }

        // Build hand description
        let handDesc = w.hand || '';
        if (w.win_type === 'SCOOP (high + low)' && w.low_hand) {
            handDesc = `${w.hand} + ${w.low_hand}`;
        }

        winnerHTML += `<div class="winner-entry">
            <div class="winner-name">${w.player.name}</div>
            ${winTypeBadge ? `<div style="color: ${winTypeColor}; font-weight: bold; font-size: 0.9rem;">${winTypeBadge}</div>` : ''}
            <div class="winner-amount">Wins ${formatMoney(w.amount)} tokens ($${tokensToDollars(w.amount)})</div>
            ${handDesc ? `<div class="winner-hand">${handDesc}</div>` : ''}
        </div>`;
    });

    // Show the winner modal
    const winnerDetails = document.getElementById('winnerDetails');
    const winnerModal = document.getElementById('winnerModal');
    if (winnerDetails && winnerModal) {
        winnerDetails.innerHTML = winnerHTML;
        winnerModal.style.display = 'flex';

        // Start countdown timer
        let countdown = 35;
        const countdownEl = document.getElementById('winnerCountdown');
        if (countdownEl) countdownEl.textContent = countdown;

        // Clear any existing countdown
        if (winnerCountdownInterval) {
            clearInterval(winnerCountdownInterval);
        }

        winnerCountdownInterval = setInterval(() => {
            countdown--;
            if (countdownEl) countdownEl.textContent = countdown;
            if (countdown <= 0) {
                closeWinnerModal(true);  // true = auto-closed, will start new hand
            }
        }, 1000);
    }

    // Also update status message
    let winnerText = data.winners.map(w => {
        let typeLabel = '';
        if (isHiLo && w.win_type !== 'fold') {
            if (w.win_type === 'low') typeLabel = ' (Low)';
            else if (w.win_type === 'SCOOP (high + low)') typeLabel = ' (SCOOP!)';
            else if (w.win_type.includes('high')) typeLabel = ' (High)';
        }
        return `${w.player.name} wins ${formatMoney(w.amount)} tokens${typeLabel}${w.hand ? ` with ${w.hand}` : ''}`;
    }).join('. ');
    const statusEl = document.getElementById('gameStatus');
    if (statusEl) {
        statusEl.innerHTML = `<strong style="color: #ffd700; font-size: 1.2rem;">${winnerText}</strong><br><em>Click your down cards to reveal them to other players.</em>`;
    }

    // Game stays in showdown phase - no auto-reset
    console.log('Hand complete:', winnerText);
});

// Handle two natural 7s instant win
socket.on('two_sevens_win', (data) => {
    let winnerHTML = '';

    data.winners.forEach(w => {
        winnerHTML += `<div class="winner-entry">
            <div class="winner-name" style="color: #ff6b6b;">${w.player.name}</div>
            <div style="color: #ff6b6b; font-weight: bold; font-size: 1.2rem;">TWO NATURAL 7s!</div>
            <div class="winner-amount">Wins ${formatMoney(w.amount)} tokens ($${tokensToDollars(w.amount)})</div>
            <div class="winner-hand" style="color: #ff6b6b;">Instant Win - Two Natural 7s</div>
        </div>`;
    });

    // Show the winner modal with special styling
    const winnerDetails = document.getElementById('winnerDetails');
    const winnerModal = document.getElementById('winnerModal');
    if (winnerDetails && winnerModal) {
        winnerDetails.innerHTML = winnerHTML;
        winnerModal.style.display = 'flex';

        // Start countdown timer
        let countdown = 35;
        const countdownEl = document.getElementById('winnerCountdown');
        if (countdownEl) countdownEl.textContent = countdown;

        if (winnerCountdownInterval) {
            clearInterval(winnerCountdownInterval);
        }

        winnerCountdownInterval = setInterval(() => {
            countdown--;
            if (countdownEl) countdownEl.textContent = countdown;
            if (countdown <= 0) {
                closeWinnerModal(true);
            }
        }, 1000);
    }

    // Update status message
    const w = data.winners[0];
    const statusEl = document.getElementById('gameStatus');
    if (statusEl) {
        statusEl.innerHTML = `<strong style="color: #ff6b6b; font-size: 1.3rem;">${w.player.name} WINS WITH TWO NATURAL 7s!</strong><br>Wins ${formatMoney(w.amount)} tokens instantly!`;
    }

    // Auto-reveal the winner's cards after a delay (3 seconds)
    setTimeout(() => {
        socket.emit('reveal_two_sevens_winner');
    }, 3000);

    console.log('Two Natural 7s Win:', w.player.name);
});

// Handle card reveal from other players
socket.on('cards_revealed', (data) => {
    console.log('Cards revealed by player:', data.player_name, data.cards);
    // Refresh game state to show revealed cards
    if (gameState) {
        // Update the player's down cards to be visible
        const playerIdx = data.player_id;
        if (gameState.players && gameState.players[playerIdx]) {
            gameState.players[playerIdx].down_cards = data.cards;
            gameState.players[playerIdx].cards_revealed = true;
            updateDisplay();
        }
    }
});

socket.on('error', (data) => {
    alert(data.message);
});

// Handle fold announcement
let foldPopupTimer = null;
let foldCountdownInterval = null;

socket.on('player_folded', (data) => {
    showFoldPopup(data.player_name);
});

function showFoldPopup(playerName) {
    const popup = document.getElementById('foldPopup');
    const nameEl = document.getElementById('foldPlayerName');
    const countdownEl = document.getElementById('foldCountdown');

    // Clear any existing timers
    if (foldPopupTimer) clearTimeout(foldPopupTimer);
    if (foldCountdownInterval) clearInterval(foldCountdownInterval);

    // Set the player name
    nameEl.textContent = playerName;

    // Reset and show popup
    popup.classList.remove('hiding');
    popup.classList.add('show');

    // Start countdown
    let countdown = 5;
    countdownEl.textContent = countdown;

    foldCountdownInterval = setInterval(() => {
        countdown--;
        countdownEl.textContent = countdown;
        if (countdown <= 0) {
            clearInterval(foldCountdownInterval);
        }
    }, 1000);

    // Auto-close after 5 seconds
    foldPopupTimer = setTimeout(() => {
        closeFoldPopup();
    }, 5000);
}

function closeFoldPopup() {
    const popup = document.getElementById('foldPopup');

    // Clear timers
    if (foldPopupTimer) clearTimeout(foldPopupTimer);
    if (foldCountdownInterval) clearInterval(foldCountdownInterval);
    foldPopupTimer = null;
    foldCountdownInterval = null;

    // Animate out
    popup.classList.add('hiding');

    setTimeout(() => {
        popup.classList.remove('show', 'hiding');
    }, 300);
}

// Game functions
function updatePlayerNameDropdown(allNames, takenNames) {
    const dropdown = document.getElementById('playerName');
    const currentSelection = dropdown.value;

    // Clear existing options except the first placeholder
    dropdown.innerHTML = '<option value="">-- Select Your Name --</option>';

    // Add all names
    allNames.forEach(name => {
        const option = document.createElement('option');
        option.value = name;
        option.textContent = name;

        // Disable and style taken names
        if (takenNames.includes(name)) {
            option.disabled = true;
            option.style.color = '#999';
            option.style.fontStyle = 'italic';
            option.textContent = `${name} (taken)`;
        }

        dropdown.appendChild(option);
    });

    // Restore selection if it's still available
    if (currentSelection && !takenNames.includes(currentSelection)) {
        dropdown.value = currentSelection;
    }
}

function joinGame() {
    console.log('joinGame() called');  // DEBUG
    const playerName = document.getElementById('playerName').value.trim();
    console.log('Player name:', playerName);  // DEBUG

    if (!playerName || playerName === '') {
        console.log('No player name selected');  // DEBUG
        document.getElementById('joinStatus').textContent = 'Please select a name';
        return;
    }

    document.getElementById('joinStatus').textContent = '';
    console.log('Emitting join_game event with name:', playerName);  // DEBUG
    socket.emit('join_game', { name: playerName });
    console.log('join_game event emitted');  // DEBUG
}

function newGame() {
    const hiLo = document.getElementById('hiLoMode').checked;
    const twoSevens = document.getElementById('twoSevensMode').checked;
    const dealSevensToMichael = document.getElementById('dealSevensToMichael').checked;
    socket.emit('new_game', {
        game_mode: 'stud_follow_queen',
        num_players: 7,
        hi_lo: hiLo,
        two_natural_sevens_wins: twoSevens,
        deal_sevens_to_michael: dealSevensToMichael
    });
}

function startGame() {
    socket.emit('start_game');
}

function newHand() {
    socket.emit('new_hand');
}

function resetGame() {
    if (confirm('Are you sure you want to reset the entire game? This will clear all players and start fresh.')) {
        socket.emit('reset_game');
    }
}

function playerAction(action) {
    let amount = 0;
    if (action === 'raise') {
        amount = parseInt(document.getElementById('raiseAmount').value) || 0;
        if (amount < 0) amount = 0;
    }

    hideRaiseControls();
    socket.emit('player_action', { action, amount });
}

function updateButtons() {
    const startGameBtn = document.getElementById('startGameBtn');
    const newHandBtn = document.getElementById('newHandBtn');

    if (!gameState || gameState.my_player_id === null || gameState.my_player_id === undefined) {
        startGameBtn.style.display = 'none';
        newHandBtn.style.display = 'none';
        return;
    }

    const isDealer = gameState.my_player_id === gameState.dealer_position;

    // Show Start Game button if game hasn't started yet
    if (!gameState.game_started) {
        startGameBtn.style.display = 'inline-block';
        newHandBtn.style.display = 'none';
        // Only dealer can start game, and need at least 2 players
        if (isDealer && gameState.players.length >= 2) {
            startGameBtn.disabled = false;
            startGameBtn.style.opacity = '1';
        } else {
            startGameBtn.disabled = true;
            startGameBtn.style.opacity = '0.5';
        }
    } else {
        // Game has started - show New Hand button only for dealer
        startGameBtn.style.display = 'none';
        newHandBtn.style.display = 'inline-block';

        // Only enable if this player is the dealer
        if (isDealer) {
            newHandBtn.disabled = false;
            newHandBtn.style.opacity = '1';
        } else {
            newHandBtn.disabled = true;
            newHandBtn.style.opacity = '0.5';
        }
    }

    // Reset Server button - dealer can use it (or anyone if not yet joined)
    const resetBtn = document.getElementById('resetGameBtn');
    if (resetBtn) {
        if (isDealer) {
            resetBtn.disabled = false;
            resetBtn.style.opacity = '1';
        } else {
            resetBtn.disabled = true;
            resetBtn.style.opacity = '0.5';
        }
    }
}

function updateResetButtonForJoinScreen() {
    // On join screen (before joining), anyone can reset
    const resetBtn = document.getElementById('resetGameBtn');
    if (resetBtn) {
        resetBtn.disabled = false;
        resetBtn.style.opacity = '1';
    }
}

function updateResetButtonVisibility() {
    const resetBtn = document.getElementById('resetGameBtn');
    resetBtn.style.display = 'inline-block';
    // On join screen (not yet in game), enable for everyone
    // Once in game, updateButtons() will restrict to dealer only
    if (!gameState || gameState.my_player_id === null || gameState.my_player_id === undefined) {
        resetBtn.disabled = false;
        resetBtn.style.opacity = '1';
    }
}

function updateStatusMessage() {
    if (!gameState) return;

    const statusEl = document.getElementById('gameStatus');

    if (!gameState.game_started) {
        const playerCount = gameState.players ? gameState.players.length : 0;
        const maxPlayers = gameState.num_players || 6;
        statusEl.innerHTML = `Waiting for additional players (${playerCount}/${maxPlayers}). Click "Start Game" when ready (minimum 2 players).`;
    } else if (gameState.phase === 'showdown') {
        statusEl.innerHTML = 'Hand complete! Dealer can deal next hand.';
    } else if (gameState.is_my_turn) {
        statusEl.innerHTML = `<span class="turn-indicator my-turn">YOUR TURN TO ACT!</span>`;
    } else if (gameState.players && gameState.current_player >= 0) {
        const currentPlayer = gameState.players[gameState.current_player];
        const playerName = currentPlayer ? currentPlayer.name : 'player';
        statusEl.innerHTML = `<span class="turn-indicator waiting">Waiting for <span class="player-name-highlight">${playerName}</span>...</span>`;
    }
}

function createCardHTML(card, extraClass = '') {
    if (!card || card.suit === 'back') {
        return `<div class="card back ${extraClass}"></div>`;
    }
    // Check if card is wild (Queens always wild, plus current wild rank)
    const wildRank = gameState ? gameState.current_wild_rank : 'Q';
    const isWild = card.rank === 'Q' || card.rank === wildRank;
    const wildClass = isWild ? 'wild' : '';
    return `
        <div class="card ${card.suit} ${extraClass} ${wildClass}">
            <div class="card-corner top">
                <span class="card-rank">${card.rank}</span>
                <span class="card-suit">${card.symbol}</span>
            </div>
            <div class="card-center">${card.symbol}</div>
            <div class="card-corner bottom">
                <span class="card-rank">${card.rank}</span>
                <span class="card-suit">${card.symbol}</span>
            </div>
        </div>
    `;
}

function updateWildCardDisplay(gameState) {
    try {
        const wildPanel = document.getElementById('wildCardPanel');
        const currentWildEl = document.getElementById('currentWild');
        const wildHistoryEl = document.getElementById('wildHistory');

        if (!wildPanel || !currentWildEl || !wildHistoryEl) return;

        if (gameState.game_mode !== 'stud_follow_queen') {
            wildPanel.style.display = 'none';
            return;
        }

        wildPanel.style.display = 'block';

    // Current wild rank
    const wildRank = gameState.current_wild_rank;
    const wildText = wildRank === 'Q' ? 'Queens Only' : `Queens and ${wildRank}s`;
    currentWildEl.innerHTML = `<span class="royal-flush-icon large"></span> Wild Cards: <span style="font-size: 4rem;">${wildText}</span>`;

    // Wild card history
    if (gameState.wild_card_history && gameState.wild_card_history.length > 0) {
        let historyHTML = '';
        gameState.wild_card_history.forEach((change, i) => {
            historyHTML += `
                <div class="wild-change-badge">
                    ${change.phase.replace('_', ' ')}: ${change.player_name} -> ${change.new_wild_rank}s wild
                </div>
            `;
        });
        wildHistoryEl.innerHTML = historyHTML;
    } else {
        wildHistoryEl.innerHTML = '<div class="wild-change-badge">No wild card changes yet</div>';
    }
    } catch (error) {
        console.error('Error in updateWildCardDisplay:', error);
    }
}

// Evaluate current poker hand from visible cards
function evaluateCurrentHand(downCards, upCards, wildRank) {
    // Combine all visible cards (not hidden)
    const allCards = [];

    (downCards || []).forEach(card => {
        if (!card.hidden && card.rank && card.suit) {
            allCards.push(card);
        }
    });

    (upCards || []).forEach(card => {
        if (card.rank && card.suit) {
            allCards.push(card);
        }
    });

    if (allCards.length < 2) return null;

    // Count ranks and suits, track cards by rank
    const rankOrder = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];
    const rankCounts = {};
    const cardsByRank = {};
    const suitCounts = {};
    const cardsBySuit = {};
    const wildCards = [];

    allCards.forEach(card => {
        // Check if this card is wild (Queen or the current wild rank)
        const isWild = card.rank === 'Q' || (wildRank && card.rank === wildRank);
        if (isWild) {
            wildCards.push(card);
        } else {
            rankCounts[card.rank] = (rankCounts[card.rank] || 0) + 1;
            if (!cardsByRank[card.rank]) cardsByRank[card.rank] = [];
            cardsByRank[card.rank].push(card);
        }
        suitCounts[card.suit] = (suitCounts[card.suit] || 0) + 1;
        if (!cardsBySuit[card.suit]) cardsBySuit[card.suit] = [];
        cardsBySuit[card.suit].push(card);
    });

    const wildCount = wildCards.length;

    // Find the rank with most cards
    const sortedRanks = Object.keys(rankCounts).sort((a, b) => {
        if (rankCounts[b] !== rankCounts[a]) return rankCounts[b] - rankCounts[a];
        return rankOrder.indexOf(b) - rankOrder.indexOf(a);
    });

    const bestRank = sortedRanks[0];
    const secondRank = sortedRanks[1];
    const maxOfKind = (rankCounts[bestRank] || 0) + wildCount;
    const secondOfKind = rankCounts[secondRank] || 0;

    // Check for flush (5+ of same suit)
    const flushSuit = Object.keys(suitCounts).find(s => suitCounts[s] >= 5);
    const hasFlush = !!flushSuit;

    // Helper to format result with cards
    function result(name, cards) {
        const cardsStr = cardsToShortNotation(cards);
        return cardsStr ? `${name} (${cardsStr})` : name;
    }

    // Get hand cards for of-a-kind hands
    function getOfAKindCards(rank, count) {
        const cards = [...(cardsByRank[rank] || [])];
        // Add wild cards to complete the hand
        for (let i = 0; i < wildCards.length && cards.length < count; i++) {
            cards.push(wildCards[i]);
        }
        return cards;
    }

    // Check for straight (including with wild cards)
    function checkStraight(cards, wilds) {
        // Get unique rank indices of non-wild cards
        const nonWildRankIndices = [];
        cards.forEach(card => {
            const isWild = card.rank === 'Q' || (wildRank && card.rank === wildRank);
            if (!isWild) {
                const idx = rankOrder.indexOf(card.rank);
                if (idx !== -1 && !nonWildRankIndices.includes(idx)) {
                    nonWildRankIndices.push(idx);
                }
            }
        });
        nonWildRankIndices.sort((a, b) => a - b);

        const numWilds = wilds.length;
        const numNonWilds = nonWildRankIndices.length;

        // Need at least 5 total cards to make a straight
        if (numNonWilds + numWilds < 5) return null;

        // Try to find a 5-card straight window
        // Check each possible starting position (0=2 through 9=10 for regular, or wheel A-5)
        for (let start = 9; start >= 0; start--) {
            // Check if we can make a straight from 'start' to 'start+4'
            let gaps = 0;
            let straightCards = [];
            for (let i = start; i <= start + 4; i++) {
                if (nonWildRankIndices.includes(i)) {
                    // Find a card with this rank
                    const rank = rankOrder[i];
                    const card = cards.find(c => c.rank === rank && !straightCards.includes(c));
                    if (card) straightCards.push(card);
                } else {
                    gaps++;
                }
            }
            if (gaps <= numWilds) {
                // We can make this straight with wilds
                for (let i = 0; i < gaps && i < wilds.length; i++) {
                    straightCards.push(wilds[i]);
                }
                return { highCard: start + 4, cards: straightCards };
            }
        }

        // Check for wheel (A-2-3-4-5) - Ace is index 12
        let wheelGaps = 0;
        let wheelCards = [];
        const wheelIndices = [12, 0, 1, 2, 3]; // A, 2, 3, 4, 5
        for (const i of wheelIndices) {
            if (nonWildRankIndices.includes(i)) {
                const rank = rankOrder[i];
                const card = cards.find(c => c.rank === rank && !wheelCards.includes(c));
                if (card) wheelCards.push(card);
            } else {
                wheelGaps++;
            }
        }
        if (wheelGaps <= numWilds) {
            for (let i = 0; i < wheelGaps && i < wilds.length; i++) {
                wheelCards.push(wilds[i]);
            }
            return { highCard: 3, cards: wheelCards }; // 5-high straight
        }

        return null;
    }

    // Check for straight flush
    function checkStraightFlush() {
        for (const suit of Object.keys(cardsBySuit)) {
            const suitCards = cardsBySuit[suit];
            // Include wild cards of this suit
            const wildsInSuit = wildCards.filter(c => c.suit === suit);
            if (suitCards.length + wildsInSuit.length >= 5) {
                const straightResult = checkStraight(suitCards, wildsInSuit);
                if (straightResult) {
                    return { ...straightResult, suit: suit };
                }
            }
        }
        return null;
    }

    // Evaluate hand (check in order of hand strength)
    if (maxOfKind >= 5) {
        return result("Five of a Kind!", getOfAKindCards(bestRank, 5));
    }

    // Check for straight flush (before regular flush or straight)
    const straightFlush = checkStraightFlush();
    if (straightFlush) {
        if (straightFlush.highCard === 12) {
            return result("Royal Flush!", straightFlush.cards);
        }
        return result("Straight Flush", straightFlush.cards);
    }

    if (maxOfKind >= 4) {
        return result("Four of a Kind", getOfAKindCards(bestRank, 4));
    }
    if (maxOfKind >= 3 && secondOfKind >= 2) {
        const tripCards = getOfAKindCards(bestRank, 3);
        const pairCards = (cardsByRank[secondRank] || []).slice(0, 2);
        return result("Full House", [...tripCards, ...pairCards]);
    }
    if (hasFlush) {
        return result("Flush", cardsBySuit[flushSuit].slice(0, 5));
    }

    // Check for regular straight
    const straight = checkStraight(allCards, wildCards);
    if (straight) {
        return result("Straight", straight.cards);
    }

    if (maxOfKind >= 3) {
        return result("Three of a Kind", getOfAKindCards(bestRank, 3));
    }
    if (maxOfKind >= 2 && secondOfKind >= 2) {
        const pair1 = getOfAKindCards(bestRank, 2);
        const pair2 = (cardsByRank[secondRank] || []).slice(0, 2);
        return result("Two Pair", [...pair1, ...pair2]);
    }
    if (maxOfKind >= 2) {
        return result("Pair", getOfAKindCards(bestRank, 2));
    }
    if (wildCount > 0) {
        return result("Wild Card", wildCards);
    }

    // High card
    if (sortedRanks.length > 0) {
        const highCard = sortedRanks[0];
        const displayRank = highCard === 'A' ? 'Ace' :
                           highCard === 'K' ? 'King' :
                           highCard === 'Q' ? 'Queen' :
                           highCard === 'J' ? 'Jack' : highCard;
        return result(`${displayRank} High`, [cardsByRank[highCard][0]]);
    }

    return "No Hand";
}

// Format a card to 2-character notation (e.g., "Ah" for Ace of hearts)
function cardToShortNotation(card) {
    if (!card || !card.rank || !card.suit) return '??';
    const rankChar = card.rank === '10' ? 'T' : card.rank;
    const suitSymbols = { hearts: '\u2665', diamonds: '\u2666', clubs: '\u2663', spades: '\u2660' };
    const suitChar = suitSymbols[card.suit] || card.suit.charAt(0);
    return rankChar + suitChar;
}

// Format an array of cards to 2-character notation string
function cardsToShortNotation(cards) {
    if (!cards || !Array.isArray(cards) || cards.length === 0) return '';
    return cards.map(cardToShortNotation).join(' ');
}

// Format tokens as integer
function formatMoney(amount) {
    return Math.floor(amount);
}

// Convert tokens to dollars (100 tokens = $1)
function tokensToDollars(tokens) {
    return (tokens / 100).toFixed(2);
}

function renderStudTable(gameState) {
    try {
        // Safety check for players array
        if (!gameState || !gameState.players || !Array.isArray(gameState.players)) {
            console.warn('Invalid gameState in renderStudTable', {
                hasGameState: !!gameState,
                hasPlayers: !!gameState?.players,
                isArray: Array.isArray(gameState?.players),
                playersLength: gameState?.players?.length,
                gameState: gameState
            });
            return;
        }

        // New Stud-specific rendering
        console.log('renderStudTable called with', gameState.players.length, 'players');  // DEBUG
        const studPlayersGrid = document.getElementById('studPlayersGrid');
        console.log('studPlayersGrid element found:', !!studPlayersGrid);  // DEBUG
        if (!studPlayersGrid) {
            console.error('studPlayersGrid element not found!');  // DEBUG
            return;
        }

    let playersHTML = '';
    gameState.players.forEach((player, idx) => {
        const isActive = idx === gameState.current_player && !gameState.round_complete;

        // Build down cards HTML (vertical)
        let downCardsHTML = '';
        (player.down_cards || []).forEach((card, i) => {
            downCardsHTML += createCardHTML(card);
            downCardsHTML += `<div class="street-indicator">Down ${i + 1}</div>`;
        });

        // Build up cards HTML (vertical with street labels)
        let upCardsHTML = '';
        (player.up_cards || []).forEach((card, i) => {
            upCardsHTML += createCardHTML(card);
            const street = i === 0 ? '3rd' : i === 1 ? '4th' : i === 2 ? '5th' : '6th';
            upCardsHTML += `<div class="street-indicator">${street} Street</div>`;
        });

        // Player status
        let statusHTML = '';
        if (player.folded) {
            statusHTML = '<span class="player-status status-folded">FOLDED</span>';
        } else if (player.is_all_in) {
            statusHTML = '<span class="player-status status-all-in">ALL IN</span>';
        }

        // Hand result (high and low in Hi-Lo mode)
        let handResultHTML = '';
        if (player.hand_result && gameState.phase === 'showdown') {
            const cardsStr = player.hand_result.best_cards ? cardsToShortNotation(player.hand_result.best_cards) : '';
            const highLabel = gameState.hi_lo ? '<span style="color: #ffd700;">HIGH:</span> ' : '';
            handResultHTML = `<div class="hand-result">${highLabel}${player.hand_result.name}${cardsStr ? ' (' + cardsStr + ')' : ''}</div>`;

            // Show low hand if Hi-Lo mode
            if (gameState.hi_lo && player.low_result) {
                if (player.low_result.qualifies) {
                    const lowCardsStr = player.low_result.best_cards ? cardsToShortNotation(player.low_result.best_cards) : '';
                    handResultHTML += `<div class="hand-result" style="color: #2ecc71;"><span>LOW:</span> ${player.low_result.name}${lowCardsStr ? ' (' + lowCardsStr + ')' : ''}</div>`;
                } else {
                    handResultHTML += `<div class="hand-result" style="color: #e74c3c; opacity: 0.7;"><span>LOW:</span> No Qualifier</div>`;
                }
            }
        }

        // Check if this player's down cards are visible (not hidden)
        // Only show hand evaluation for the current viewer's own cards
        // Hidden cards have rank='?' or hidden=true
        const canSeeDownCards = (player.down_cards || []).some(card => !card.hidden && card.rank !== '?');
        let currentHandHTML = '';
        if (canSeeDownCards && !player.folded) {
            const handName = evaluateCurrentHand(
                player.down_cards,
                player.up_cards,
                gameState.current_wild_rank
            );
            if (handName) {
                currentHandHTML = `<div class="current-hand-display">${handName}</div>`;
            }
        }

        // Check if this is the current player's own cards and it's showdown
        const isMyCards = idx === gameState.my_player_id;
        const isShowdown = gameState.phase === 'showdown';
        const canReveal = isMyCards && isShowdown && !player.cards_revealed;
        const revealClass = canReveal ? 'clickable-reveal' : '';
        const revealClick = canReveal ? 'onclick="revealMyCards()"' : '';
        const revealHint = canReveal ? '<div class="reveal-hint">Click to reveal</div>' : '';

        playersHTML += `
            <div class="stud-player-card ${isActive ? 'active' : ''} ${player.folded ? 'folded' : ''}">
                <div class="player-info">
                    <div class="player-name">
                        <span class="player-number">${idx + 1}</span>
                        ${player.name}
                        ${player.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
                    </div>
                    <div class="player-chips">${formatMoney(player.chips)} tokens <span class="dollar-equiv">($${tokensToDollars(player.chips)})</span></div>
                    ${player.last_win > 0 ? `<div class="player-last-win" style="color: #2ecc71; font-size: 0.85rem;">Last win: +${formatMoney(player.last_win)}</div>` : ''}
                    ${player.current_bet > 0 ? `<div class="player-bet">Bet: ${formatMoney(player.current_bet)}</div>` : ''}
                    ${statusHTML}
                    ${handResultHTML}
                </div>
                <div class="card-progression">
                    <div class="down-cards-group ${revealClass}" ${revealClick}>
                        <label>Down Cards</label>
                        <div class="cards-vertical">
                            ${downCardsHTML || '<div style="color: #666;">No cards yet</div>'}
                        </div>
                        ${revealHint}
                    </div>
                    <div class="up-cards-group">
                        <label>Up Cards</label>
                        <div class="cards-vertical">
                            ${upCardsHTML || '<div style="color: #666;">No cards yet</div>'}
                        </div>
                    </div>
                </div>
                ${currentHandHTML}
            </div>
        `;
    });

    studPlayersGrid.innerHTML = playersHTML;

    // Update Stud pot and phase
    const studPotEl = document.getElementById('studPotAmount');
    const studPhaseEl = document.getElementById('studPhaseDisplay');

    if (studPotEl) studPotEl.textContent = formatMoney(gameState.pot);
    const studPotDollarsEl = document.getElementById('studPotDollars');
    if (studPotDollarsEl) studPotDollarsEl.textContent = tokensToDollars(gameState.pot);

    if (studPhaseEl) {
        const PHASE_NAMES = {
            'third_street': 'Third Street',
            'fourth_street': 'Fourth Street',
            'fifth_street': 'Fifth Street',
            'sixth_street': 'Sixth Street',
            'seventh_street': 'Seventh Street',
            'showdown': 'Showdown'
        };
        studPhaseEl.textContent = PHASE_NAMES[gameState.phase] || gameState.phase;
    }

    // Show/hide Hi-Lo badge
    const hiLoBadge = document.getElementById('hiLoBadge');
    if (hiLoBadge) {
        hiLoBadge.style.display = gameState.hi_lo ? 'inline-block' : 'none';
    }

    // Show/hide Two Sevens badge
    const twoSevensBadge = document.getElementById('twoSevensBadge');
    if (twoSevensBadge) {
        twoSevensBadge.style.display = gameState.two_natural_sevens_wins ? 'inline-block' : 'none';
    }
    } catch (error) {
        console.error('Error in renderStudTable:', error);
    }
}

function renderHoldemTable(gameState) {
    try {
    // Safety check for players array
    if (!gameState || !gameState.players || !Array.isArray(gameState.players)) {
        console.warn('Invalid gameState in renderHoldemTable');
        return;
    }

    // Update pot and phase
    const potEl = document.getElementById('potAmount');
    const phaseEl = document.getElementById('phaseDisplay');

    if (potEl) potEl.textContent = formatMoney(gameState.pot);
    const potDollarsEl = document.getElementById('potDollars');
    if (potDollarsEl) potDollarsEl.textContent = tokensToDollars(gameState.pot);

    if (phaseEl) {
        const PHASE_NAMES = {
            'pre-flop': 'Pre-Flop',
            'flop': 'Flop',
            'turn': 'Turn',
            'river': 'River',
            'showdown': 'Showdown'
        };
        phaseEl.textContent = PHASE_NAMES[gameState.phase] || gameState.phase;
    }

    // Update community cards
    const communityDiv = document.getElementById('communityCards');
    if (communityDiv) {
        let communityHTML = '';

        if (gameState.community_cards) {
            const totalCommunity = 5;
            const revealed = gameState.community_cards.length;

            for (let i = 0; i < totalCommunity; i++) {
                if (i < revealed) {
                    communityHTML += createCardHTML(gameState.community_cards[i], 'community card-deal');
                } else {
                    communityHTML += '<div class="card community placeholder"></div>';
                }
            }
        }
        communityDiv.innerHTML = communityHTML;
    }

    // Update players
    const playersDiv = document.getElementById('playersArea');
    if (!playersDiv) return;
    let playersHTML = '';

    gameState.players.forEach((player, idx) => {
        const isActive = idx === gameState.current_player && !gameState.round_complete;
        const classes = [
            'player-spot',
            isActive ? 'active' : '',
            player.folded ? 'folded' : '',
            player.is_human ? 'human' : ''
        ].filter(Boolean).join(' ');

        let statusHTML = '';
        if (player.folded) {
            statusHTML = '<span class="player-status status-folded">FOLDED</span>';
        } else if (player.is_all_in) {
            statusHTML = '<span class="player-status status-all-in">ALL IN</span>';
        }

        let handResultHTML = '';
        if (player.hand_result && gameState.phase === 'showdown') {
            const cardsStr = player.hand_result.best_cards ? cardsToShortNotation(player.hand_result.best_cards) : '';
            handResultHTML = `<div class="hand-result">${player.hand_result.name}${cardsStr ? ' (' + cardsStr + ')' : ''}</div>`;
        }

        const cardsHTML = player.hole_cards ? player.hole_cards.map(c => createCardHTML(c)).join('') : '';

        playersHTML += `
            <div class="${classes}">
                <div class="player-name">
                    <span class="player-number">${idx + 1}</span>
                    ${player.name}
                    ${player.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
                </div>
                <div class="player-chips">${formatMoney(player.chips)} tokens <span class="dollar-equiv">($${tokensToDollars(player.chips)})</span></div>
                ${player.last_win > 0 ? `<div class="player-last-win" style="color: #2ecc71; font-size: 0.85rem;">Last win: +${formatMoney(player.last_win)}</div>` : ''}
                ${player.current_bet > 0 ? `<div class="player-bet">Bet: ${formatMoney(player.current_bet)}</div>` : ''}
                <div class="player-cards">
                    ${cardsHTML}
                </div>
                ${statusHTML}
                ${handResultHTML}
            </div>
        `;
    });
    playersDiv.innerHTML = playersHTML;
    } catch (error) {
        console.error('Error in renderHoldemTable:', error);
    }
}

// Large Format Mode Rendering
function renderLargeFormatTable() {
    if (!gameState) return;

    try {
        const gameMode = gameState.game_mode || 'holdem';
        const myPlayer = gameState.players.find(p => p.id === gameState.my_player_id);

        // Separate active and folded players
        const activePlayers = gameState.players.filter(p => !p.folded && p.id !== gameState.my_player_id);
        const foldedPlayers = gameState.players.filter(p => p.folded);

        // Sort active opponents by chip stack (highest first)
        activePlayers.sort((a, b) => b.chips - a.chips);

        // Take top 3-4 opponents
        const displayOpponents = activePlayers.slice(0, 4);

        // Render opponents zone
        const opponentsZone = document.getElementById('lfOpponentsZone');
        if (opponentsZone) {
            let opponentsHTML = '';
            displayOpponents.forEach((player, idx) => {
                const isActive = gameState.players.indexOf(player) === gameState.current_player && !gameState.round_complete;
                opponentsHTML += renderLargeFormatPlayer(player, isActive, gameMode);
            });
            opponentsZone.innerHTML = opponentsHTML;
        }

        // Render center zone (pot + community cards)
        const potDisplay = document.getElementById('lfPotDisplay');
        if (potDisplay) {
            potDisplay.innerHTML = `Pot: ${formatMoney(gameState.pot)} tokens ($${tokensToDollars(gameState.pot)})`;
        }

        const phaseDisplay = document.getElementById('lfPhaseDisplay');
        if (phaseDisplay) {
            const phaseNames = {
                'pre_deal': 'Waiting',
                'pre_flop': 'Pre-Flop',
                'flop': 'Flop',
                'turn': 'Turn',
                'river': 'River',
                'showdown': 'Showdown',
                'ante': 'Ante',
                'third_street': '3rd Street',
                'fourth_street': '4th Street',
                'fifth_street': '5th Street',
                'sixth_street': '6th Street',
                'seventh_street': '7th Street'
            };
            phaseDisplay.innerHTML = `Phase: ${phaseNames[gameState.phase] || gameState.phase}`;
        }

        // Render community cards (for Hold'em) or wild card info (for Stud)
        const communityCards = document.getElementById('lfCommunityCards');
        if (communityCards) {
            if (gameMode === 'holdem' && gameState.community_cards) {
                let cardsHTML = '';
                for (let i = 0; i < 5; i++) {
                    if (gameState.community_cards[i]) {
                        cardsHTML += createCardHTML(gameState.community_cards[i], true);
                    } else {
                        cardsHTML += '<div class="card community placeholder"></div>';
                    }
                }
                communityCards.innerHTML = cardsHTML;
            } else if (gameMode === 'stud_follow_queen') {
                // Show wild card info for stud
                const wildRank = gameState.current_wild_rank;
                const wildText = wildRank === 'Q' ? 'Queens Only' : `Queens + ${wildRank}s`;
                const wildCardInfo = `<div class="lf-info-box lf-wild-info">Wild: ${wildText}</div>`;
                communityCards.innerHTML = wildCardInfo;
            }
        }

        // Render player zone (my cards)
        const playerZone = document.getElementById('lfPlayerZone');
        if (playerZone && myPlayer) {
            const isMyTurn = gameState.is_my_turn && !gameState.round_complete;
            playerZone.innerHTML = renderLargeFormatPlayer(myPlayer, isMyTurn, gameMode, true);
        }

        // Update folded strip
        const foldedCount = document.getElementById('foldedCount');
        if (foldedCount) {
            foldedCount.textContent = foldedPlayers.length;
        }

        const foldedPlayersDiv = document.getElementById('lfFoldedPlayers');
        if (foldedPlayersDiv) {
            let foldedHTML = '';
            foldedPlayers.forEach(player => {
                foldedHTML += `<div class="lf-folded-player">${player.name} (${formatMoney(player.chips)})</div>`;
            });
            foldedPlayersDiv.innerHTML = foldedHTML || '<div class="lf-folded-player">No folded players</div>';
        }
    } catch (error) {
        console.error('Error in renderLargeFormatTable:', error);
    }
}

function renderLargeFormatPlayer(player, isActive, gameMode, isCurrentPlayer = false) {
    const classes = [
        'lf-player-spot',
        isActive ? 'active' : '',
        isCurrentPlayer ? 'current-player' : '',
        player.folded ? 'folded' : ''
    ].filter(Boolean).join(' ');

    let statusHTML = '';
    if (player.folded) {
        statusHTML = '<span class="player-status status-folded">FOLDED</span>';
    } else if (player.is_all_in) {
        statusHTML = '<span class="player-status status-all-in">ALL IN</span>';
    }

    let handResultHTML = '';
    if (player.hand_result && gameState.phase === 'showdown') {
        handResultHTML = `<div class="hand-result" style="font-size: calc(var(--font-critical) * 0.7);">${player.hand_result.name}</div>`;
    }

    // Render cards based on game mode
    let cardsHTML = '';
    if (gameMode === 'holdem') {
        cardsHTML = player.hole_cards ? player.hole_cards.map(c => createCardHTML(c)).join('') : '';
    } else if (gameMode === 'stud_follow_queen') {
        // Stud mode: show down cards and up cards
        if (player.down_cards) {
            cardsHTML += '<div class="down-cards-group" style="display: flex; gap: 5px;">';
            cardsHTML += player.down_cards.map(c => createCardHTML(c)).join('');
            cardsHTML += '</div>';
        }
        if (player.up_cards) {
            cardsHTML += '<div class="up-cards-group" style="display: flex; gap: 5px; margin-top: 5px;">';
            cardsHTML += player.up_cards.map(c => createCardHTML(c)).join('');
            cardsHTML += '</div>';
        }
    }

    return `
        <div class="${classes}">
            <div class="player-name">
                <span class="player-number">${player.id + 1}</span>
                ${player.name}
                ${player.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
            </div>
            <div class="player-chips">${formatMoney(player.chips)} tokens</div>
            ${player.current_bet > 0 ? `<div class="player-bet" style="font-size: calc(var(--font-body) * 0.9);">Bet: ${formatMoney(player.current_bet)}</div>` : ''}
            <div class="player-cards">
                ${cardsHTML}
            </div>
            ${statusHTML}
            ${handResultHTML}
        </div>
    `;
}

function updateDisplay() {
    if (!gameState) return;

    try {
        const gameMode = gameState.game_mode || 'holdem';
        console.log('updateDisplay called with gameMode:', gameMode);  // DEBUG

        // Set game mode attribute on container for CSS switching
        const container = document.querySelector('.game-container');
        console.log('Container found:', !!container);  // DEBUG
        if (container) {
            container.setAttribute('data-game-mode', gameMode);
            console.log('Set data-game-mode to:', gameMode);  // DEBUG
        }

        // Update title based on game mode
        const gameTitle = gameMode === 'holdem' ? "Texas Hold'em Poker" : "Follow the Queen Poker";
        const titleElement = document.getElementById('gameTitle');
        if (titleElement && myPlayerName) {
            titleElement.innerHTML = `<span class="royal-flush-icon"></span> ${gameTitle} - Multiplayer - ${myPlayerName}`;
        } else if (titleElement) {
            titleElement.innerHTML = `<span class="royal-flush-icon"></span> ${gameTitle} - Multiplayer`;
        }

        // Route to appropriate renderer based on display mode and game mode
        if (currentDisplayMode === 'large') {
            // Large format mode - use simplified layout for both game types
            if (gameMode === 'stud_follow_queen') {
                updateWildCardDisplay(gameState);
            }
            renderLargeFormatTable();
        } else {
            // Standard mode - use original renderers
            if (gameMode === 'holdem') {
                renderHoldemTable(gameState);
            } else if (gameMode === 'stud_follow_queen') {
                updateWildCardDisplay(gameState);
                renderStudTable(gameState);
            }
        }

        // Update action panel (common to both)
        updateActionPanel();
    } catch (error) {
        console.error('Error in updateDisplay:', error);
    }
}

function updateActionPanel() {
    const panel = document.getElementById('actionPanel');
    const checkCallBtn = document.getElementById('checkCallBtn');

    if (!gameState || gameState.phase === 'showdown' || !gameState.is_my_turn ||
        gameState.my_player_id === null || gameState.my_player_id === undefined) {
        panel.style.display = 'none';
        return;
    }

    panel.style.display = 'block';

    const myPlayer = gameState.players.find(p => p.id === gameState.my_player_id);
    if (!myPlayer) {
        panel.style.display = 'none';
        return;
    }

    const toCall = gameState.current_bet - myPlayer.current_bet;

    if (toCall > 0) {
        checkCallBtn.textContent = `Call ${toCall}`;
        checkCallBtn.onclick = () => playerAction('call');
        checkCallBtn.className = 'btn btn-call';
    } else {
        checkCallBtn.textContent = 'Check';
        checkCallBtn.onclick = () => playerAction('check');
        checkCallBtn.className = 'btn btn-check';
    }

    // Set default raise amount
    document.getElementById('raiseAmount').value = gameState.current_bet * 2 || gameState.ante_amount * 2 || 10;
}

function showRaiseControls() {
    document.getElementById('raiseControls').style.display = 'flex';
}

function hideRaiseControls() {
    document.getElementById('raiseControls').style.display = 'none';
}

function addToBet(amount) {
    const input = document.getElementById('raiseAmount');
    const currentValue = parseInt(input.value) || 0;
    const newValue = currentValue + amount;
    input.value = Math.max(0, newValue);
}

function clearBet() {
    document.getElementById('raiseAmount').value = 0;
}

let winnerCountdownInterval = null;
let newHandTimeout = null;

function closeWinnerModal(autoClose = false) {
    if (winnerCountdownInterval) {
        clearInterval(winnerCountdownInterval);
        winnerCountdownInterval = null;
    }
    // If manually closed, cancel any pending new hand timer
    if (!autoClose && newHandTimeout) {
        clearTimeout(newHandTimeout);
        newHandTimeout = null;
    }
    document.getElementById('winnerModal').style.display = 'none';

    // Auto-start new hand disabled for now
    // if (autoClose) {
    //     // Auto-closed: start new hand in 8 seconds
    //     document.getElementById('gameStatus').textContent = 'New hand starting in 8 seconds...';
    //     newHandTimeout = setTimeout(() => {
    //         newHandTimeout = null;
    //         newHand();
    //     }, 8000);
    // } else {
    //     document.getElementById('gameStatus').textContent = 'Click "New Game" to continue!';
    // }
    document.getElementById('gameStatus').textContent = 'Click "New Game" to continue!';
}

function revealMyCards() {
    // Send request to reveal down cards to all players
    socket.emit('reveal_cards');
    console.log('Revealing my cards to all players');
}

function toggleAlgorithmInfo() {
    const info = document.getElementById('algorithmInfo');
    const handRankings = document.getElementById('handRankingsInfo');
    // Hide hand rankings when showing algorithm info
    if (handRankings) handRankings.style.display = 'none';
    info.style.display = info.style.display === 'none' ? 'block' : 'none';
}

function toggleHandRankings() {
    const info = document.getElementById('handRankingsInfo');
    const algorithmInfo = document.getElementById('algorithmInfo');
    // Hide algorithm info when showing hand rankings
    if (algorithmInfo) algorithmInfo.style.display = 'none';
    info.style.display = info.style.display === 'none' ? 'block' : 'none';
}

// Proximity-based opacity for action panel
(function() {
    const MIN_OPACITY = 0.12;  // Minimum opacity when far away
    const MAX_OPACITY = 1.0;   // Full opacity when close
    const MAX_DISTANCE = 400;  // Distance (px) at which minimum opacity is reached

    document.addEventListener('mousemove', function(e) {
        const panel = document.getElementById('actionPanel');
        if (!panel || panel.style.display === 'none') return;

        // Get panel bounding rect
        const rect = panel.getBoundingClientRect();

        // Check if mouse is directly over the panel - if so, full opacity
        if (e.clientX >= rect.left && e.clientX <= rect.right &&
            e.clientY >= rect.top && e.clientY <= rect.bottom) {
            panel.style.opacity = MAX_OPACITY;
            return;
        }

        // Get panel center position
        const panelCenterX = rect.left + rect.width / 2;
        const panelCenterY = rect.top + rect.height / 2;

        // Calculate distance from mouse to panel center
        const dx = e.clientX - panelCenterX;
        const dy = e.clientY - panelCenterY;
        const distance = Math.sqrt(dx * dx + dy * dy);

        // Calculate opacity based on distance
        // Closer = more opaque, farther = more transparent
        const normalizedDistance = Math.min(distance / MAX_DISTANCE, 1);
        const opacity = MAX_OPACITY - (normalizedDistance * (MAX_OPACITY - MIN_OPACITY));

        panel.style.opacity = opacity;
    });

    // Ensure full opacity when hovering directly over the panel
    document.addEventListener('DOMContentLoaded', function() {
        const panel = document.getElementById('actionPanel');
        if (panel) {
            panel.addEventListener('mouseenter', function() {
                this.style.opacity = MAX_OPACITY;
            });
        }
    });
})();
