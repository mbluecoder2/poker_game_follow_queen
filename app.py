"""
Texas Hold'em Poker Game
A Flask web application with dealing, hand evaluation, and betting mechanics
Supports deployment on Render.com with WebSocket support via simple-websocket
"""

import os
import logging
import secrets

from flask import Flask, render_template, jsonify, request
from flask_socketio import SocketIO  # type: ignore[import-untyped]

# Import from modules
from evaluators import create_deck, shuffle_deck
from game_classes import HoldemGame, StudFollowQueenGame
# frontend.py no longer needed - using templates/index.html
from handlers import (
    init_handlers,
    register_socket_handlers,
    get_game,
    set_game,
    broadcast_game_state
)

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Check simple-websocket availability
try:
    import simple_websocket
    logger.info("simple-websocket is installed")
except ImportError as e:
    logger.warning(f"simple-websocket not available: {e}")

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)

# Log the actual async mode being used
logger.info(f"SocketIO async_mode: {socketio.async_mode}")

# Initialize game
initial_game = StudFollowQueenGame(num_players=7, starting_chips=1000, ante_amount=5, bring_in_amount=10)

# Initialize handlers with socketio and game
init_handlers(socketio, initial_game)
register_socket_handlers(socketio)


# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/new-game', methods=['POST'])
def api_new_game():
    data = request.get_json() or {}
    num_players = data.get('num_players', 6)
    new_game = HoldemGame(num_players=num_players, starting_chips=1000, ante_amount=5)
    set_game(new_game)
    return jsonify(new_game.get_state())

@app.route('/api/new-hand', methods=['POST'])
def api_new_hand():
    game = get_game()
    game.new_hand()
    return jsonify(game.get_state())

@app.route('/api/action', methods=['POST'])
def api_action():
    game = get_game()
    data = request.get_json()
    action = data.get('action')
    amount = data.get('amount', 0)

    success, message = game.player_action(action, amount)

    return jsonify({
        'success': success,
        'message': message,
        'state': game.get_state()
    })

@app.route('/api/ai-action', methods=['POST'])
def api_ai_action():
    game = get_game()
    result = game.ai_action()

    if result:
        action, amount = result
        player_name = game.players[game.current_player]['name']
        game.player_action(action, amount)
        return jsonify({
            'action': action,
            'player': player_name,
            'state': game.get_state()
        })

    return jsonify({'state': game.get_state()})

@app.route('/api/advance', methods=['POST'])
def api_advance():
    game = get_game()
    game.advance_phase()
    return jsonify(game.get_state())

@app.route('/api/winner', methods=['POST'])
def api_winner():
    game = get_game()
    winners = game.determine_winners()
    return jsonify({
        'winners': [{
            'player': {
                'name': w['player']['name'],
                'chips': w['player']['chips']
            },
            'amount': w['amount'],
            'hand': w['hand'],
            'win_type': w.get('win_type', 'high'),
            'low_hand': w.get('low_hand')
        } for w in winners],
        'state': game.get_state(),
        'hi_lo': getattr(game, 'hi_lo', False)
    })

@app.route('/api/shuffle')
def api_shuffle():
    """Original shuffle endpoint for standalone shuffle view."""
    deck = create_deck()
    shuffled = shuffle_deck(deck)
    return jsonify(shuffled)

if __name__ == '__main__':
    debug_mode = os.environ.get('FLASK_ENV') != 'production'
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=debug_mode, host='0.0.0.0', port=port)
