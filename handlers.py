"""
WebSocket handlers and bot AI logic for poker games.
"""

import random
import threading
import time
import sys
import os
from collections import Counter
from flask_socketio import emit, join_room
from flask import request

from game_classes import StudFollowQueenGame, HoldemGame

# =============================================================================
# BOT CONFIGURATION
# =============================================================================
BOT_CAN_FOLD = False  # Set to True to allow bots to fold, False to prevent folding

# Available player names
PLAYER_NAMES = ['Alan K', 'Andy L', 'Michael H', 'Mark A', 'Ron R', 'Peter R', 'Chunk G', 'Andrew G', 'Bot 1', 'Bot 2', 'Bot 3', 'Bot 4', 'Bot 5']

# Global state (will be set by init_handlers)
game = None
taken_names = {}
socketio = None


def init_handlers(socketio_instance, initial_game=None):
    """Initialize handlers with socketio instance and game reference."""
    global socketio, game, taken_names
    socketio = socketio_instance
    if initial_game is not None:
        game = initial_game
    taken_names = {}


def get_game():
    """Get current game instance."""
    return game


def set_game(new_game):
    """Set game instance."""
    global game
    game = new_game


def get_taken_names():
    """Get taken names dictionary."""
    return taken_names


# =============================================================================
# BOT PLAYER LOGIC
# =============================================================================

def evaluate_bot_hand(player, wild_rank='Q'):
    """Evaluate a bot's hand strength (0.0 to 1.0 scale).

    Returns a tuple: (hand_strength, hand_name)
    Hand strength scale:
    - 0.0-0.15: Nothing/High card
    - 0.15-0.30: One pair
    - 0.30-0.45: Two pair
    - 0.45-0.55: Three of a kind
    - 0.55-0.65: Straight
    - 0.65-0.75: Flush
    - 0.75-0.85: Full house
    - 0.85-0.92: Four of a kind
    - 0.92-1.0: Straight flush / Five of a kind
    """
    down_cards = player.get('down_cards', [])
    up_cards = player.get('up_cards', [])
    all_cards = down_cards + up_cards

    if not all_cards:
        return 0.0, "Nothing"

    # Count ranks and suits
    ranks = []
    suits = []
    wild_count = 0

    rank_values = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
                   '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}

    for card in all_cards:
        rank = card.get('rank', '')
        suit = card.get('suit', '')

        # Check if wild (Queens always wild, plus Follow the Queen rank)
        if rank == 'Q' or rank == wild_rank:
            wild_count += 1
        else:
            if rank in rank_values:
                ranks.append(rank)
                suits.append(suit)

    if not ranks and wild_count == 0:
        return 0.0, "Nothing"

    rank_counts = Counter(ranks)
    suit_counts = Counter(suits)

    # Get the most common rank count
    if rank_counts:
        most_common = rank_counts.most_common()
        highest_count = most_common[0][1] + wild_count
        second_count = most_common[1][1] if len(most_common) > 1 else 0
    else:
        highest_count = wild_count
        second_count = 0

    # Check for flush potential (5+ cards of same suit)
    max_suit_count = max(suit_counts.values()) if suit_counts else 0
    has_flush = (max_suit_count + wild_count) >= 5

    # Check for straight potential
    if ranks:
        rank_nums = sorted(set(rank_values.get(r, 0) for r in ranks))
        # Simple straight check: look for 5 consecutive or close to it
        has_straight = False
        for i in range(len(rank_nums) - 3):
            span = rank_nums[min(i+4, len(rank_nums)-1)] - rank_nums[i]
            gaps = span - 4
            if gaps <= wild_count:
                has_straight = True
                break
        # Check for wheel (A-2-3-4-5)
        if 14 in rank_nums and 2 in rank_nums:
            low_cards = [r for r in rank_nums if r <= 5 or r == 14]
            if len(low_cards) + wild_count >= 5:
                has_straight = True
    else:
        has_straight = False

    # Determine hand strength
    if highest_count >= 5:
        return 0.95, "Five of a Kind"
    elif has_straight and has_flush and len(all_cards) >= 5:
        return 0.93, "Straight Flush"
    elif highest_count >= 4:
        return 0.88, "Four of a Kind"
    elif highest_count >= 3 and second_count >= 2:
        return 0.78, "Full House"
    elif has_flush and len(all_cards) >= 5:
        return 0.70, "Flush"
    elif has_straight and len(all_cards) >= 5:
        return 0.60, "Straight"
    elif highest_count >= 3:
        return 0.50, "Three of a Kind"
    elif highest_count >= 2 and second_count >= 2:
        return 0.38, "Two Pair"
    elif highest_count >= 2:
        return 0.22, "One Pair"
    elif wild_count >= 1:
        return 0.22, "Pair (wild)"
    else:
        # High card - value based on highest card
        if ranks:
            high_value = max(rank_values.get(r, 0) for r in ranks)
            return 0.05 + (high_value / 14) * 0.10, "High Card"
        return 0.05, "High Card"

def evaluate_bot_low_hand(player, wild_rank='Q'):
    """Evaluate a bot's low hand potential for Hi-Lo games (0.0 to 1.0 scale).

    Returns a tuple: (low_strength, low_name)
    Low strength scale:
    - 0.0: No qualifying low possible
    - 0.3-0.5: Eight low
    - 0.5-0.7: Seven low
    - 0.7-0.85: Six low
    - 0.85-0.95: Wheel draw or six-four
    - 0.95-1.0: The Wheel (A-2-3-4-5)
    """
    down_cards = player.get('down_cards', [])
    up_cards = player.get('up_cards', [])
    all_cards = down_cards + up_cards

    if len(all_cards) < 3:
        # Too early to evaluate low potential
        return 0.0, "Too early"

    # Count low cards (A-8) excluding wilds
    low_ranks = set()
    wild_count = 0

    for card in all_cards:
        rank = card.get('rank', '')
        if rank == 'Q' or rank == wild_rank:
            wild_count += 1
        elif rank in ['A', '2', '3', '4', '5', '6', '7', '8']:
            low_ranks.add(rank)

    # Calculate low potential
    unique_low_cards = len(low_ranks)
    total_low_potential = unique_low_cards + wild_count

    if total_low_potential < 5:
        # Can't make a qualifying low
        if total_low_potential >= 3:
            return 0.15, "Low draw"
        return 0.0, "No low"

    # Has qualifying low - evaluate strength
    # Convert ranks to values for comparison
    low_values = {'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8}
    card_values = sorted([low_values[r] for r in low_ranks])

    # Add wild cards as best available
    available = [v for v in [1, 2, 3, 4, 5, 6, 7, 8] if v not in card_values]
    for _ in range(wild_count):
        if available:
            card_values.append(available.pop(0))
    card_values = sorted(card_values)[:5]

    if card_values == [1, 2, 3, 4, 5]:
        return 0.98, "The Wheel"
    elif max(card_values) == 6:
        return 0.80, "Six Low"
    elif max(card_values) == 7:
        return 0.60, "Seven Low"
    else:
        return 0.40, "Eight Low"


def get_bot_action(player, game_state, wild_rank='Q'):
    """Determine what action a bot should take based on hand strength.

    Smart bot strategy:
    - Evaluate actual hand strength
    - Strong hands (>0.5): Bet/raise aggressively
    - Medium hands (0.25-0.5): Call reasonable bets, sometimes bet
    - Weak hands (<0.25): Check when free, fold to big bets
    - Consider pot odds vs hand strength
    - In Hi-Lo mode: also consider low hand potential
    """
    current_bet = game_state.get('current_bet', 0)
    player_bet = player.get('current_bet', 0)
    to_call = current_bet - player_bet
    pot = game_state.get('pot', 0)
    chips = player.get('chips', 0)
    phase = game_state.get('phase', '')
    hi_lo = game_state.get('hi_lo', False)

    # Evaluate HIGH hand strength
    hand_strength, hand_name = evaluate_bot_hand(player, wild_rank)

    # In Hi-Lo mode, also evaluate LOW hand potential
    low_strength = 0.0
    low_name = ""
    if hi_lo:
        low_strength, low_name = evaluate_bot_low_hand(player, wild_rank)

        # Combine high and low for overall hand value
        # A hand that can scoop (win both high and low) is very valuable
        if hand_strength > 0.5 and low_strength > 0.3:
            # Potential scoop - boost effective strength
            combined_strength = (hand_strength * 0.6) + (low_strength * 0.5)
            hand_name = f"{hand_name} + {low_name}"
        elif low_strength > 0.3:
            # Has low potential - this adds value even if high is weak
            combined_strength = max(hand_strength, low_strength * 0.8)
            if low_strength > hand_strength:
                hand_name = f"{low_name} (low draw)"
        else:
            combined_strength = hand_strength

        hand_strength = min(combined_strength, 1.0)

    # Add some randomness (personality)
    effective_strength = hand_strength + random.uniform(-0.1, 0.1)
    effective_strength = max(0, min(1, effective_strength))

    # Calculate pot odds
    pot_odds = to_call / (pot + to_call) if (pot + to_call) > 0 else 0

    # Determine action
    if to_call == 0:
        # Can check for free
        if effective_strength > 0.6:
            # Strong hand - bet for value
            bet_size = pot * (0.5 + effective_strength * 0.5)
            bet_amount = int(min(chips, max(10, bet_size)))
            if random.random() < 0.7:
                print(f"    [{player['name']} has {hand_name}, betting {int(bet_amount)} tokens]")
                return 'bet', bet_amount
            else:
                # Slow play sometimes
                print(f"    [{player['name']} has {hand_name}, slow-playing]")
                return 'check', 0
        elif effective_strength > 0.35:
            # Medium hand - sometimes bet, usually check
            if random.random() < 0.3:
                bet_amount = int(min(chips, max(10, pot / 3)))
                print(f"    [{player['name']} has {hand_name}, probing with {int(bet_amount)} tokens]")
                return 'bet', bet_amount
            print(f"    [{player['name']} has {hand_name}, checking]")
            return 'check', 0
        else:
            # Weak hand - check and hope to improve
            print(f"    [{player['name']} has {hand_name}, checking]")
            return 'check', 0

    else:
        # Must call, raise, or fold
        # Compare hand strength to pot odds
        call_profitable = effective_strength > pot_odds

        if effective_strength > 0.65:
            # Very strong hand - raise!
            if random.random() < 0.6:
                raise_amount = int(min(chips, to_call + pot * 0.75))
                print(f"    [{player['name']} has {hand_name}, raising to {raise_amount} tokens]")
                return 'raise', raise_amount
            print(f"    [{player['name']} has {hand_name}, calling]")
            return 'call', 0

        elif effective_strength > 0.4:
            # Good hand - usually call, sometimes raise
            if call_profitable or pot_odds < 0.3:
                if random.random() < 0.2 and effective_strength > 0.5:
                    raise_amount = int(min(chips, to_call + pot * 0.5))
                    print(f"    [{player['name']} has {hand_name}, raising to {raise_amount} tokens]")
                    return 'raise', raise_amount
                print(f"    [{player['name']} has {hand_name}, calling {int(to_call)} tokens]")
                return 'call', 0
            else:
                # Pot odds not good enough
                if random.random() < 0.4:
                    print(f"    [{player['name']} has {hand_name}, calling despite odds]")
                    return 'call', 0
                print(f"    [{player['name']} has {hand_name}, folding (bad odds)]")
                return 'fold', 0

        elif effective_strength > 0.2:
            # Mediocre hand - call small bets, fold to big ones
            if pot_odds < 0.25:
                print(f"    [{player['name']} has {hand_name}, calling small bet]")
                return 'call', 0
            elif call_profitable and random.random() < 0.5:
                print(f"    [{player['name']} has {hand_name}, calling]")
                return 'call', 0
            else:
                print(f"    [{player['name']} has {hand_name}, folding]")
                return 'fold', 0
        else:
            # Weak hand - usually fold
            if pot_odds < 0.15 and random.random() < 0.3:
                # Cheap call, might get lucky
                print(f"    [{player['name']} has {hand_name}, calling cheap]")
                return 'call', 0
            print(f"    [{player['name']} has {hand_name}, folding]")
            return 'fold', 0

def process_bot_turn():
    """Check if current player is a bot and process their turn."""
    global game

    if not game or not game.game_started:
        return

    if game.phase == 'showdown' or game.round_complete:
        return

    if game.current_player >= len(game.players):
        return

    current_player = game.players[game.current_player]

    if not current_player.get('is_bot', False):
        return

    if current_player.get('folded', False) or current_player.get('is_all_in', False):
        return

    # Get game state for decision making
    game_state = {
        'current_bet': game.current_bet,
        'pot': game.pot,
        'phase': game.phase,
        'hi_lo': getattr(game, 'hi_lo', False)
    }

    # Get wild rank for hand evaluation
    wild_rank = getattr(game, 'current_wild_rank', 'Q')

    # Determine bot action
    action, amount = get_bot_action(current_player, game_state, wild_rank)

    # If BOT_CAN_FOLD is False, convert fold to call
    if not BOT_CAN_FOLD and action == 'fold':
        action = 'call'
        amount = 0
        print(f"[BOT] {current_player['name']} would fold but BOT_CAN_FOLD=False, calling instead")
    else:
        print(f"[BOT] {current_player['name']} decides to {action}" + (f" {int(amount)} tokens" if amount else ""))

    # Execute the action after a short delay (makes it feel more natural)
    def execute_bot_action():
        success, message = game.player_action(action, amount)
        if success:
            broadcast_game_state()

            # Check if hand is over
            active_players = game.get_active_players()
            if len(active_players) == 1 or game.phase == 'showdown':
                handle_determine_winner()
            elif game.round_complete and game.phase != 'showdown':
                handle_advance_phase()
            else:
                # Check if next player is also a bot
                process_bot_turn()
        else:
            print(f"[BOT] {current_player['name']} action failed: {message}")

    # Delay bot action by 1-2 seconds for realism
    delay = random.uniform(1.0, 2.0)
    timer = threading.Timer(delay, execute_bot_action)
    timer.start()


# =============================================================================
# BROADCAST FUNCTIONS
# =============================================================================

def broadcast_name_availability():
    """Broadcast which names are available to all clients."""
    available = [name for name in PLAYER_NAMES if name not in taken_names.values()]
    taken = list(taken_names.values())
    socketio.emit('name_availability', {
        'available': available,
        'taken': taken,
        'all_names': PLAYER_NAMES
    }, room='poker_game')

def broadcast_two_sevens_win(results):
    """Broadcast special two natural 7s win to all clients."""
    socketio.emit('two_sevens_win', {
        'winners': [{
            'player': {
                'name': w['player']['name'],
                'chips': w['player']['chips']
            },
            'amount': w['amount'],
            'hand': w['hand'],
            'win_type': w['win_type'],
            'player_id': w.get('player_id')
        } for w in results]
    }, room='poker_game')
    broadcast_game_state()
    # Re-enable the New Game button for all players
    socketio.emit('new_game_button_enabled', {}, room='poker_game')

def broadcast_game_state():
    """Broadcast game state to all connected clients."""
    if not game:
        return
    print(f"BROADCASTING GAME STATE - Players: {len(game.players)}, Phase: {game.phase if hasattr(game, 'phase') else 'N/A'}")  # DEBUG

    # Send personalized state to each player in the game
    for session_id, player_id in game.player_sessions.items():
        state = game.get_state(for_session=session_id)
        print(f"  Sending to session {session_id}: players={len(state.get('players', []))}, game_mode={state.get('game_mode')}")  # DEBUG
        socketio.emit('game_state', state, room=session_id)

    # Also broadcast a generic state to spectators (those not in player_sessions)
    # They see the game without any hole cards revealed
    spectator_state = game.get_state(for_session=None)
    socketio.emit('game_state', spectator_state, room='poker_game', skip_sid=list(game.player_sessions.keys()))


# =============================================================================
# WEBSOCKET EVENT HANDLERS
# =============================================================================

def handle_determine_winner():
    """Determine the winner and distribute pot."""
    if not game:
        return
    winners = game.determine_winners()

    # Check if this is a two natural 7s win
    if winners and winners[0].get('win_type') == 'two_natural_sevens':
        broadcast_two_sevens_win(winners)
        return

    socketio.emit('winners', {
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
        'hi_lo': getattr(game, 'hi_lo', False)
    }, room='poker_game')
    broadcast_game_state()

    # Re-enable the New Game button for all players
    socketio.emit('new_game_button_enabled', {}, room='poker_game')

    # Game stays at showdown - no auto-deal
    # Players can review cards and click "New Hand" when ready

def handle_advance_phase():
    """Advance to the next phase."""
    if not game:
        return
    game.advance_phase()

    # Check for two natural 7s instant win after dealing new cards
    sevens_winner = game._check_two_natural_sevens()
    if sevens_winner:
        results, both_sevens_face_up = game._handle_two_natural_sevens_win(sevens_winner)
        broadcast_game_state()
        # Only show winner dialog if both 7s are face up
        if both_sevens_face_up:
            broadcast_two_sevens_win(results)
        return

    broadcast_game_state()

    if game.phase == 'showdown':
        handle_determine_winner()
    else:
        # Check if first player in new phase is a bot
        process_bot_turn()


def register_socket_handlers(socketio_instance):
    """Register all socket handlers with the socketio instance."""
    global socketio
    socketio = socketio_instance

    @socketio.on('connect')
    def handle_connect():
        """Handle client connection."""
        join_room('poker_game')
        join_room(request.sid)  # Join player's personal room
        emit('connected', {'session_id': request.sid})
        # Send current name availability to the new client
        broadcast_name_availability()

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        # Free up the player's name
        if request.sid in taken_names:
            del taken_names[request.sid]
            # Broadcast updated name availability
            broadcast_name_availability()

    @socketio.on('join_game')
    def handle_join_game(data):
        """Handle player joining the game."""
        print(f"JOIN_GAME event received: {data}")  # DEBUG
        player_name = data.get('name', f'Player {len(game.players) + 1}')
        print(f"Player name: {player_name}")  # DEBUG

        # Check if name is already taken
        if player_name in taken_names.values():
            print(f"Name {player_name} already taken")  # DEBUG
            emit('join_failed', {'message': f'{player_name} is already taken. Please select another name.'})
            return

        player_id, message = game.add_player(request.sid, player_name)
        print(f"Add player result: player_id={player_id}, message={message}")  # DEBUG

        if player_id is None:
            emit('join_failed', {'message': message})
        else:
            # Mark name as taken
            taken_names[request.sid] = player_name
            emit('join_success', {'player_id': player_id, 'name': player_name})
            print(f"Player {player_name} joined successfully. Total players: {len(game.players)}")  # DEBUG

            # NOTE: Auto-start removed. Use "Start Game" button when ready.
            # Players can now join until game is manually started.

            # Broadcast updated state to all players
            broadcast_game_state()
            # Broadcast updated name availability
            broadcast_name_availability()

    @socketio.on('new_game')
    def handle_new_game(data):
        """Handle new game creation."""
        global game, taken_names
        game_mode = data.get('game_mode', 'stud_follow_queen')
        num_players = data.get('num_players', 6)
        hi_lo = data.get('hi_lo', False)
        two_natural_sevens_wins = data.get('two_natural_sevens_wins', False)
        deal_sevens_to_michael = data.get('deal_sevens_to_michael', False)

        # Save existing players and their session mappings if any
        existing_players = []
        if game and len(game.players) > 0:
            existing_players = list(game.players)  # Make a copy

        if game_mode == 'stud_follow_queen':
            game = StudFollowQueenGame(
                num_players=num_players,
                starting_chips=1000,
                ante_amount=5,
                bring_in_amount=10,
                hi_lo=hi_lo,
                two_natural_sevens_wins=two_natural_sevens_wins,
                deal_sevens_to_michael=deal_sevens_to_michael
            )
        else:  # Default to Hold'em
            game = HoldemGame(
                num_players=num_players,
                starting_chips=1000,
                ante_amount=5
            )

        # Re-add existing players to the new game, preserving their chips
        for old_player in existing_players:
            player_id, _ = game.add_player(old_player['session_id'], old_player['name'])
            if player_id is not None:
                # Restore the player's chips from before the new game
                game.players[player_id]['chips'] = old_player['chips']
            # Update taken_names to track this player
            taken_names[old_player['session_id']] = old_player['name']

        # NOTE: Auto-start removed. Use "Start Game" button when ready.
        # Players can now join until game is manually started.

        # Disable the New Game button for all players
        socketio.emit('new_game_button_disabled', {}, room='poker_game')

        broadcast_game_state()
        broadcast_name_availability()

    @socketio.on('start_game')
    def handle_start_game():
        """Lock the game, prevent new players from joining, and auto-deal the first hand. Only dealer can start."""
        if len(game.players) < 2:
            emit('error', {'message': 'Need at least 2 players to start the game'})
            return

        # Check if only dealer can start game
        player_id = game.get_player_by_session(request.sid)
        if player_id is None or player_id != game.dealer_position:
            emit('error', {'message': 'Only the dealer can start the game'})
            return

        game.game_started = True

        # Set dealer so that after new_hand() increments it, the starting player becomes dealer
        if player_id is not None:
            game.dealer_position = (player_id - 1) % len(game.players)

        # Auto-deal the first hand
        game.new_hand()

        # Check for two natural 7s instant win after initial deal
        sevens_winner = game._check_two_natural_sevens()
        if sevens_winner:
            results, both_sevens_face_up = game._handle_two_natural_sevens_win(sevens_winner)
            broadcast_game_state()
            socketio.emit('game_locked', {'message': 'Game has started! No more players can join.'}, room='poker_game')
            # Only show winner dialog if both 7s are face up
            if both_sevens_face_up:
                broadcast_two_sevens_win(results)
            return

        broadcast_game_state()
        socketio.emit('game_locked', {'message': 'Game has started! No more players can join.'}, room='poker_game')

        # Check if first player is a bot
        process_bot_turn()

    @socketio.on('new_hand')
    def handle_new_hand():
        """Handle dealing a new hand - only dealer can do this."""
        player_id = game.get_player_by_session(request.sid)

        # Check if this player is the dealer
        # if player_id is None or player_id != game.dealer_position:
        #     emit('error', {'message': 'Only the dealer can deal a new hand'})
        #     return

        if len(game.players) < 2:
            emit('error', {'message': 'Need at least 2 players to start'})
            return

        game.new_hand()

        # Check for two natural 7s instant win after initial deal
        sevens_winner = game._check_two_natural_sevens()
        if sevens_winner:
            results, both_sevens_face_up = game._handle_two_natural_sevens_win(sevens_winner)
            broadcast_game_state()
            # Only show winner dialog if both 7s are face up
            if both_sevens_face_up:
                broadcast_two_sevens_win(results)
            return

        broadcast_game_state()

        # Check if first player is a bot
        process_bot_turn()

    @socketio.on('reset_game')
    def handle_reset_game():
        """Reset the entire game - dealer or non-joined players can do this. Hard server restart."""
        global game, taken_names

        player_id = game.get_player_by_session(request.sid) if game else None

        # Check if only dealer can reset game (but allow if player hasn't joined yet)
        if game and len(game.players) > 0 and player_id is not None:
            # Player is in the game - must be dealer to reset
            if player_id != game.dealer_position:
                emit('error', {'message': 'Only the dealer can reset the server'})
                return
        # If player_id is None, they haven't joined yet - allow reset

        # Get player name if available, otherwise use "A USER"
        if game and player_id is not None:
            player = game.players[player_id]
            playerName = player['name'].upper()
        else:
            playerName = "A USER"

        # Notify all clients that server is restarting
        socketio.emit('server_restart', {'message': f"Game reset by {playerName}. Server restarting..."}, room='poker_game')

        print("\n" + "=" * 50)
        print(f"HARD RESET TRIGGERED BY {playerName}")
        print("Clearing all game state and restarting server...")
        print("=" * 50 + "\n")

        # Clear all game state
        game = None
        taken_names = {}

        # Give clients a moment to receive the message
        time.sleep(1)

        # Hard restart the server by re-executing the script
        # Use __file__ instead of sys.argv to handle paths with spaces correctly
        script_path = os.path.abspath(sys.modules['__main__'].__file__)
        os.execv(sys.executable, [sys.executable, script_path])

    @socketio.on('reveal_cards')
    def handle_reveal_cards():
        """Allow a player to reveal their down cards to all other players at showdown."""
        global game

        player_id = game.get_player_by_session(request.sid)

        if player_id is None:
            emit('error', {'message': 'You are not in this game'})
            return

        # Only allow during showdown
        if game.phase != 'showdown':
            emit('error', {'message': 'You can only reveal cards at showdown'})
            return

        player = game.players[player_id]

        # Mark player as having revealed their cards
        player['cards_revealed'] = True

        # Get the player's actual down cards (not hidden)
        down_cards = []
        for card in player.get('down_cards', []):
            down_cards.append({
                'rank': card['rank'],
                'suit': card['suit'],
                'hidden': False
            })

        # Broadcast to all players that this player revealed their cards
        socketio.emit('cards_revealed', {
            'player_id': player_id,
            'player_name': player['name'],
            'cards': down_cards
        }, room='poker_game')

        # Broadcast updated game state so all clients show the revealed cards
        broadcast_game_state()

        print(f"{player['name']} revealed their down cards")

    @socketio.on('reveal_two_sevens_winner')
    def handle_reveal_two_sevens_winner():
        """Auto-reveal the two natural 7s winner's cards at showdown, but only if both 7s are face up."""
        global game

        if not game:
            return

        # Check if there's a pending two sevens winner to reveal
        winner_id = getattr(game, 'two_sevens_winner_id', None)
        if winner_id is None:
            return

        # Clear the pending winner regardless
        game.two_sevens_winner_id = None

        # Only allow during showdown
        if game.phase != 'showdown':
            return

        player = game.players[winner_id]

        # Count 7s in down cards (hole cards)
        sevens_in_hole = sum(1 for card in player.get('down_cards', []) if card['rank'] == '7')

        # Only auto-reveal if NO 7s are in the hole (both 7s are face up)
        # If any 7 is in the hole, player must manually reveal
        if sevens_in_hole > 0:
            print(f"{player['name']} has {sevens_in_hole} seven(s) in the hole - not auto-revealing")
            return

        # Both 7s are face up, so auto-reveal the down cards
        player['cards_revealed'] = True

        # Get the player's actual down cards
        down_cards = []
        for card in player.get('down_cards', []):
            down_cards.append({
                'rank': card['rank'],
                'suit': card['suit'],
                'hidden': False
            })

        # Broadcast to all players that this player revealed their cards
        socketio.emit('cards_revealed', {
            'player_id': winner_id,
            'player_name': player['name'],
            'cards': down_cards
        }, room='poker_game')

        # Broadcast updated game state
        broadcast_game_state()

        print(f"{player['name']}'s cards auto-revealed at showdown (both 7s were face up)")

    @socketio.on('player_action')
    def handle_player_action(data):
        """Handle player action."""
        player_id = game.get_player_by_session(request.sid)

        if player_id is None:
            emit('error', {'message': 'You are not in this game'})
            return

        # Compare the current player's ID (not index) with this player's ID
        current_player_obj = game.players[game.current_player] if game.current_player < len(game.players) else None
        if current_player_obj is None or current_player_obj['id'] != player_id:
            emit('error', {'message': 'It is not your turn'})
            return

        action = data.get('action')
        amount = data.get('amount', 0)

        success, message = game.player_action(action, amount)

        if not success:
            emit('error', {'message': message})
        else:
            broadcast_game_state()

            # Check if hand is over
            active_players = game.get_active_players()
            if len(active_players) == 1 or game.phase == 'showdown':
                handle_determine_winner()
            elif game.round_complete and game.phase != 'showdown':
                handle_advance_phase()
            else:
                # Check if next player is a bot
                process_bot_turn()

    @socketio.on('advance_phase')
    def socket_advance_phase():
        """Advance to the next phase (socket event wrapper)."""
        handle_advance_phase()

    @socketio.on('determine_winner')
    def socket_determine_winner():
        """Determine the winner (socket event wrapper)."""
        handle_determine_winner()
