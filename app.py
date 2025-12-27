"""
Texas Hold'em Poker Game
A Flask web application with dealing, hand evaluation, and betting mechanics
For PythonAnywhere hosting
"""

from flask import Flask, render_template_string, jsonify, request, session
from flask_socketio import SocketIO, emit, join_room
from itertools import combinations
from collections import Counter
import random
import secrets
import os

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
socketio = SocketIO(app, cors_allowed_origins="*")

# =============================================================================
# CARD AND DECK MANAGEMENT
# =============================================================================

SUITS = ['hearts', 'diamonds', 'clubs', 'spades']
RANKS = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
RANK_VALUES = {rank: idx for idx, rank in enumerate(RANKS)}

SUIT_SYMBOLS = {
    'hearts': '♥',
    'diamonds': '♦',
    'clubs': '♣',
    'spades': '♠'
}

def create_deck():
    """Create a standard 52-card deck."""
    return [{'rank': rank, 'suit': suit, 'symbol': SUIT_SYMBOLS[suit]} 
            for suit in SUITS for rank in RANKS]

def shuffle_deck(deck, iterations=7):
    """Fisher-Yates shuffle with multiple iterations."""
    shuffled = deck.copy()
    for _ in range(iterations):
        for i in range(len(shuffled) - 1, 0, -1):
            j = random.randint(0, i)
            shuffled[i], shuffled[j] = shuffled[j], shuffled[i]
    return shuffled

# =============================================================================
# HAND EVALUATION ENGINE
# =============================================================================

class HandEvaluator:
    """Evaluates poker hands and determines winners."""

    HAND_RANKS = {
        'Five of a Kind': 11,  # Only possible with wild cards
        'Royal Flush': 10,
        'Straight Flush': 9,
        'Four of a Kind': 8,
        'Full House': 7,
        'Flush': 6,
        'Straight': 5,
        'Three of a Kind': 4,
        'Two Pair': 3,
        'One Pair': 2,
        'High Card': 1
    }
    
    @staticmethod
    def card_value(card):
        """Get numeric value of a card for comparison."""
        return RANK_VALUES[card['rank']]
    
    @staticmethod
    def is_flush(cards):
        """Check if all cards are the same suit."""
        return len(set(c['suit'] for c in cards)) == 1
    
    @staticmethod
    def is_straight(cards):
        """Check if cards form a straight."""
        values = sorted(set(HandEvaluator.card_value(c) for c in cards))
        if len(values) != 5:
            return False, None
        
        # Check regular straight
        if values[-1] - values[0] == 4:
            return True, values[-1]
        
        # Check wheel (A-2-3-4-5)
        if values == [0, 1, 2, 3, 12]:  # 2,3,4,5,A
            return True, 3  # 5-high straight
        
        return False, None
    
    @staticmethod
    def get_rank_counts(cards):
        """Get count of each rank in hand."""
        ranks = [c['rank'] for c in cards]
        return Counter(ranks)
    
    @staticmethod
    def evaluate_five(cards):
        """
        Evaluate a 5-card hand.
        Returns (hand_rank, tiebreakers, hand_name)
        """
        is_flush = HandEvaluator.is_flush(cards)
        is_straight, high = HandEvaluator.is_straight(cards)
        rank_counts = HandEvaluator.get_rank_counts(cards)
        counts = sorted(rank_counts.values(), reverse=True)
        
        # Sort ranks by count then by value for tiebreakers
        sorted_ranks = sorted(
            rank_counts.keys(),
            key=lambda r: (rank_counts[r], RANK_VALUES[r]),
            reverse=True
        )
        tiebreakers = [RANK_VALUES[r] for r in sorted_ranks]

        # Five of a Kind (only possible with wild cards)
        if counts == [5]:
            return (11, tiebreakers, 'Five of a Kind')

        # Royal Flush
        if is_flush and is_straight and high == 12:
            return (10, [12], 'Royal Flush')
        
        # Straight Flush
        if is_flush and is_straight:
            return (9, [high], 'Straight Flush')
        
        # Four of a Kind
        if counts == [4, 1]:
            return (8, tiebreakers, 'Four of a Kind')
        
        # Full House
        if counts == [3, 2]:
            return (7, tiebreakers, 'Full House')
        
        # Flush
        if is_flush:
            values = sorted([HandEvaluator.card_value(c) for c in cards], reverse=True)
            return (6, values, 'Flush')
        
        # Straight
        if is_straight:
            return (5, [high], 'Straight')
        
        # Three of a Kind
        if counts == [3, 1, 1]:
            return (4, tiebreakers, 'Three of a Kind')
        
        # Two Pair
        if counts == [2, 2, 1]:
            return (3, tiebreakers, 'Two Pair')
        
        # One Pair
        if counts == [2, 1, 1, 1]:
            return (2, tiebreakers, 'One Pair')
        
        # High Card
        values = sorted([HandEvaluator.card_value(c) for c in cards], reverse=True)
        return (1, values, 'High Card')
    
    @staticmethod
    def best_hand(hole_cards, community_cards):
        """
        Find the best 5-card hand from hole cards + community cards.
        Returns (hand_rank, tiebreakers, hand_name, best_5_cards)
        """
        all_cards = hole_cards + community_cards
        best = None
        best_cards = None
        
        for combo in combinations(all_cards, 5):
            result = HandEvaluator.evaluate_five(list(combo))
            if best is None or (result[0], result[1]) > (best[0], best[1]):
                best = result
                best_cards = list(combo)
        
        return (*best, best_cards)
    
    @staticmethod
    def compare_hands(hand1, hand2):
        """Compare two hands. Returns 1 if hand1 wins, -1 if hand2 wins, 0 for tie."""
        if hand1[0] != hand2[0]:
            return 1 if hand1[0] > hand2[0] else -1

        for t1, t2 in zip(hand1[1], hand2[1]):
            if t1 != t2:
                return 1 if t1 > t2 else -1

        return 0


class WildCardEvaluator(HandEvaluator):
    """Evaluates poker hands with wild cards."""

    @staticmethod
    def expand_wild_cards(cards, wild_ranks):
        """
        Generate all possible hands by substituting wild cards.

        Args:
            cards: List of 5 cards
            wild_ranks: List of ranks that are wild (e.g., ['Q', '7'])

        Returns:
            List of all possible hands (each hand is a list of 5 cards)
        """
        if not wild_ranks:
            return [cards]

        # Find wild cards in this hand
        wild_indices = []
        non_wild_cards = []
        for i, card in enumerate(cards):
            if card['rank'] in wild_ranks:
                wild_indices.append(i)
            else:
                non_wild_cards.append(card)

        if not wild_indices:
            return [cards]  # No wilds in this hand

        # Get all possible card values to substitute (all 52 cards minus those already in hand)
        used_cards = set()
        for card in non_wild_cards:
            used_cards.add((card['rank'], card['suit']))

        # Generate all possible substitutions
        possible_hands = []

        def generate_substitutions(wild_idx, current_hand, used_in_hand):
            if wild_idx >= len(wild_indices):
                # All wilds substituted, add this hand
                possible_hands.append(current_hand[:])
                return

            # Try all possible ranks for this wild card
            for rank in RANKS:
                # For each rank, we can use any suit that's not already used for this rank in current_hand
                for suit in SUITS:
                    if (rank, suit) not in used_in_hand:
                        # Create substitution
                        sub_card = {'rank': rank, 'suit': suit, 'symbol': SUIT_SYMBOLS[suit]}
                        new_hand = current_hand[:]
                        new_hand[wild_indices[wild_idx]] = sub_card
                        new_used = used_in_hand.copy()
                        new_used.add((rank, suit))

                        # Recursively substitute remaining wilds
                        generate_substitutions(wild_idx + 1, new_hand, new_used)

        # Start substitution process
        initial_hand = cards[:]
        initial_used = used_cards.copy()
        generate_substitutions(0, initial_hand, initial_used)

        # Optimization: limit to reasonable number of hands (if too many wilds)
        if len(possible_hands) > 10000:
            possible_hands = possible_hands[:10000]

        return possible_hands

    @staticmethod
    def best_hand_with_wilds(all_cards, wild_ranks):
        """
        Find the best 5-card hand from 7 cards with wild cards.

        Args:
            all_cards: List of 7 cards
            wild_ranks: List of ranks that are wild (e.g., ['Q'] or ['Q', '7'])

        Returns:
            (hand_rank, tiebreakers, hand_name, best_5_cards)
        """
        from itertools import combinations
        from collections import Counter

        if not wild_ranks:
            # No wild cards, use standard evaluation
            return HandEvaluator.best_hand([], all_cards)

        best_hand = None
        best_combo = None

        # Try all 5-card combinations from 7 cards
        for combo in combinations(all_cards, 5):
            combo_list = list(combo)

            # Special check for Five of a Kind before expanding
            # (because expansion can't create impossible cards like 5th Ace)
            wild_count = sum(1 for c in combo_list if c['rank'] in wild_ranks)
            if wild_count > 0:
                # Count non-wild ranks
                rank_counts = Counter(c['rank'] for c in combo_list if c['rank'] not in wild_ranks)
                if rank_counts:
                    # Most common non-wild rank
                    most_common_rank, most_common_count = rank_counts.most_common(1)[0]
                    # Can we make Five of a Kind?
                    if most_common_count + wild_count >= 5:
                        # Five of a Kind!
                        rank_value = RANK_VALUES[most_common_rank]
                        result = (11, [rank_value], 'Five of a Kind')
                        if best_hand is None or result[0] > best_hand[0] or \
                           (result[0] == best_hand[0] and result[1] > best_hand[1]):
                            best_hand = result
                            best_combo = combo_list
                        continue  # Skip expansion for this combo

            # Expand wild cards in this combo
            possible_hands = WildCardEvaluator.expand_wild_cards(combo_list, wild_ranks)

            # Evaluate each possible hand
            for possible_hand in possible_hands:
                result = HandEvaluator.evaluate_five(possible_hand)

                if best_hand is None:
                    best_hand = result
                    best_combo = combo_list
                else:
                    # Compare hands
                    comparison = HandEvaluator.compare_hands(
                        (result[0], result[1]),
                        (best_hand[0], best_hand[1])
                    )
                    if comparison > 0:
                        best_hand = result
                        best_combo = combo_list

                # Optimization: if we found Five of a Kind, can't do better
                if best_hand[0] == 11:  # Five of a Kind
                    return (*best_hand, best_combo)

        return (*best_hand, best_combo)


# =============================================================================
# GAME STATE MANAGEMENT
# =============================================================================

class BasePokerGame:
    """Base class for poker game variants."""

    PHASES = []  # Subclasses define their phases

    def __init__(self, num_players=5, starting_chips=1000):
        self.num_players = num_players
        self.starting_chips = starting_chips
        self.reset_game()
    
    def reset_game(self):
        """Reset for a new game."""
        self.deck = []
        self.pot = 0
        self.current_bet = 0
        self.phase = self.PHASES[0] if self.PHASES else 'start'
        self.dealer_position = 0
        self.current_player = 0
        self.last_raiser = None
        self.round_complete = False
        self.player_sessions = {}  # Maps session_id to player_id
        self.game_started = False  # Lock game after start
        self.players = []
        # Players will be added dynamically as they join

    def add_player(self, session_id, player_name):
        """Add a new player to the game."""
        if self.game_started:
            return None, "Game has already started. Please wait for the next game."

        if len(self.players) >= self.num_players:
            return None, "Game is full"

        if session_id in self.player_sessions:
            return None, "You are already in the game"

        player_id = len(self.players)
        self.players.append({
            'id': player_id,
            'name': player_name or f'Player {player_id + 1}',
            'chips': self.starting_chips,
            'hole_cards': [],
            'current_bet': 0,
            'folded': False,
            'is_all_in': False,
            'is_human': True,
            'session_id': session_id,
            'hand_result': None
        })
        self.player_sessions[session_id] = player_id
        return player_id, "OK"

    def get_player_by_session(self, session_id):
        """Get player ID by session ID."""
        return self.player_sessions.get(session_id)

    def new_hand(self):
        """Start a new hand."""
        self.deck = shuffle_deck(create_deck())
        self.pot = 0
        self.current_bet = 0
        self.phase = self.PHASES[0] if self.PHASES else 'start'
        self.last_raiser = None
        self.round_complete = False

        # Reset player states for new hand - subclasses may add more fields
        for player in self.players:
            player['current_bet'] = 0
            player['folded'] = False
            player['is_all_in'] = False
            player['hand_result'] = None
            player['cards_revealed'] = False  # Reset reveal status for new hand
            # Subclass-specific card fields will be reset in _reset_player_cards

        self._reset_player_cards()

        # Remove busted players
        self.players = [p for p in self.players if p['chips'] > 0]

        if len(self.players) < 2:
            return  # Game over

        # Move dealer button
        self.dealer_position = (self.dealer_position + 1) % len(self.players)

        # Initialize hand (post blinds/antes, deal cards, set first player)
        self._initialize_hand()

    def _reset_player_cards(self):
        """Reset player cards - override in subclasses for variant-specific card structures."""
        pass

    def _initialize_hand(self):
        """Initialize a new hand - must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement _initialize_hand")
    
    def _skip_folded_players(self):
        """Move to next active player."""
        attempts = 0
        while self.players[self.current_player]['folded'] or self.players[self.current_player]['is_all_in']:
            self.current_player = (self.current_player + 1) % len(self.players)
            attempts += 1
            if attempts >= len(self.players):
                break
    
    def get_active_players(self):
        """Get players still in the hand."""
        return [p for p in self.players if not p['folded']]
    
    def get_players_to_act(self):
        """Get players who can still act (not folded, not all-in)."""
        return [p for p in self.players if not p['folded'] and not p['is_all_in']]
    
    def player_action(self, action, amount=0):
        """Process a player's action."""
        player = self.players[self.current_player]
        
        if action == 'fold':
            player['folded'] = True
        
        elif action == 'check':
            if self.current_bet > player['current_bet']:
                return False, "Cannot check, must call or raise"
        
        elif action == 'call':
            call_amount = min(self.current_bet - player['current_bet'], player['chips'])
            player['chips'] -= call_amount
            player['current_bet'] += call_amount
            self.pot += call_amount
            if player['chips'] == 0:
                player['is_all_in'] = True
        
        elif action == 'raise':
            if amount < self.current_bet * 2 and amount < player['chips'] + player['current_bet']:
                return False, f"Minimum raise is {self.current_bet * 2}"
            
            raise_amount = min(amount - player['current_bet'], player['chips'])
            player['chips'] -= raise_amount
            player['current_bet'] += raise_amount
            self.pot += raise_amount
            self.current_bet = player['current_bet']
            self.last_raiser = self.current_player
            
            if player['chips'] == 0:
                player['is_all_in'] = True
        
        elif action == 'all-in':
            all_in_amount = player['chips']
            player['current_bet'] += all_in_amount
            self.pot += all_in_amount
            player['chips'] = 0
            player['is_all_in'] = True
            
            if player['current_bet'] > self.current_bet:
                self.current_bet = player['current_bet']
                self.last_raiser = self.current_player
        
        # Move to next player
        self.current_player = (self.current_player + 1) % len(self.players)
        self._skip_folded_players()
        
        # Check if betting round is complete
        self._check_round_complete()
        
        return True, "OK"
    
    def _check_round_complete(self):
        """Check if the current betting round is complete."""
        active = self.get_active_players()
        to_act = self.get_players_to_act()
        
        # Only one player left
        if len(active) == 1:
            self.round_complete = True
            self.phase = 'showdown'
            return
        
        # No one left to act
        if len(to_act) == 0:
            self.round_complete = True
            return
        
        # Everyone has matched the bet or folded
        all_matched = all(
            p['current_bet'] == self.current_bet or p['folded'] or p['is_all_in']
            for p in self.players
        )
        
        # Back to the last raiser
        back_to_raiser = self.current_player == self.last_raiser
        
        if all_matched and back_to_raiser:
            self.round_complete = True
    
    def advance_phase(self):
        """Move to the next phase - must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement advance_phase")

    def _evaluate_hands(self):
        """Evaluate hands - must be overridden by subclasses."""
        raise NotImplementedError("Subclasses must implement _evaluate_hands")
    
    def determine_winners(self):
        """Determine the winner(s) and distribute pot."""
        active = self.get_active_players()
        
        if len(active) == 1:
            # Everyone else folded
            winner = active[0]
            winner['chips'] += self.pot
            return [{'player': winner, 'amount': self.pot, 'hand': None}]
        
        # Compare hands
        self._evaluate_hands()
        
        # Find best hand(s)
        best_players = []
        best_hand = None
        
        for player in active:
            hr = player['hand_result']
            player_hand = (hr['rank'], hr['tiebreakers'])
            
            if best_hand is None:
                best_hand = player_hand
                best_players = [player]
            else:
                comparison = HandEvaluator.compare_hands(player_hand, best_hand)
                if comparison > 0:
                    best_hand = player_hand
                    best_players = [player]
                elif comparison == 0:
                    best_players.append(player)
        
        # Split pot among winners
        share = self.pot // len(best_players)
        remainder = self.pot % len(best_players)
        
        results = []
        for i, player in enumerate(best_players):
            amount = share + (1 if i < remainder else 0)
            player['chips'] += amount
            results.append({
                'player': player,
                'amount': amount,
                'hand': player['hand_result']['name']
            })
        
        return results
    
    def ai_action(self):
        """Simple AI for computer players."""
        player = self.players[self.current_player]
        
        if player['is_human']:
            return None
        
        # Simple AI logic
        to_call = self.current_bet - player['current_bet']
        pot_odds = to_call / (self.pot + to_call) if (self.pot + to_call) > 0 else 0
        
        # Random factor for unpredictability
        r = random.random()
        
        if to_call == 0:
            # Can check
            if r < 0.7:
                return 'check', 0
            else:
                # Raise sometimes
                raise_amount = self.big_blind * random.randint(2, 4)
                if raise_amount <= player['chips']:
                    return 'raise', self.current_bet + raise_amount
                return 'check', 0
        else:
            # Must call, raise, or fold
            if to_call > player['chips'] * 0.5:
                # Large bet relative to stack
                if r < 0.6:
                    return 'fold', 0
                elif r < 0.9:
                    return 'call', 0
                else:
                    return 'all-in', 0
            elif to_call > player['chips'] * 0.2:
                # Medium bet
                if r < 0.3:
                    return 'fold', 0
                elif r < 0.85:
                    return 'call', 0
                else:
                    return 'raise', self.current_bet * 2
            else:
                # Small bet
                if r < 0.1:
                    return 'fold', 0
                elif r < 0.7:
                    return 'call', 0
                else:
                    return 'raise', self.current_bet * 2
    
    def get_state(self, for_session=None):
        """Get current game state for client."""
        player_id = self.player_sessions.get(for_session) if for_session else None

        players_state = []
        for p in self.players:
            player_data = {
                'id': p['id'],
                'name': p['name'],
                'chips': p['chips'],
                'current_bet': p['current_bet'],
                'folded': p['folded'],
                'is_all_in': p['is_all_in'],
                'is_human': p['is_human'],
                'is_dealer': self.players.index(p) == self.dealer_position
            }

            # Only show hole cards for this player or at showdown
            if p['id'] == player_id or self.phase == 'showdown':
                player_data['hole_cards'] = p['hole_cards']
                if p['hand_result']:
                    player_data['hand_result'] = p['hand_result']
            else:
                # Show back cards only if this player has cards
                if len(p['hole_cards']) > 0:
                    player_data['hole_cards'] = [{'rank': '?', 'suit': 'back', 'symbol': ''}] * len(p['hole_cards'])
                else:
                    player_data['hole_cards'] = []

            players_state.append(player_data)

        is_my_turn = False
        if self.players and player_id is not None:
            # Compare the current player's ID with this player's ID
            current_player_obj = self.players[self.current_player] if self.current_player < len(self.players) else None
            is_my_turn = current_player_obj is not None and current_player_obj['id'] == player_id

        state = {
            'phase': self.phase,
            'pot': self.pot,
            'current_bet': self.current_bet,
            'players': players_state,
            'current_player': self.current_player,
            'is_my_turn': is_my_turn,
            'my_player_id': player_id,
            'dealer_position': self.dealer_position,
            'round_complete': self.round_complete,
            'game_started': self.game_started,
            'num_players': self.num_players,
            'game_mode': 'base'  # Subclasses override this
        }
        # Subclasses can add variant-specific fields
        return state


# =============================================================================
# TEXAS HOLD'EM GAME
# =============================================================================

class HoldemGame(BasePokerGame):
    """Texas Hold'em poker game."""

    PHASES = ['pre-flop', 'flop', 'turn', 'river', 'showdown']

    def __init__(self, num_players=5, starting_chips=1000, small_blind=10, big_blind=20):
        self.small_blind = small_blind
        self.big_blind = big_blind
        super().__init__(num_players, starting_chips)

    def reset_game(self):
        """Reset for a new game."""
        super().reset_game()
        self.community_cards = []

    def _reset_player_cards(self):
        """Reset hole cards for all players."""
        for player in self.players:
            player['hole_cards'] = []

    def _initialize_hand(self):
        """Initialize a Hold'em hand: post blinds, deal hole cards."""
        # Post blinds
        self._post_blinds()

        # Deal hole cards
        self._deal_hole_cards()

        # Set first player to act (UTG = dealer + 3)
        self.current_player = (self.dealer_position + 3) % len(self.players)
        self._skip_folded_players()

    def _post_blinds(self):
        """Post small and big blinds."""
        sb_pos = (self.dealer_position + 1) % len(self.players)
        bb_pos = (self.dealer_position + 2) % len(self.players)

        # Small blind
        sb_amount = min(self.small_blind, self.players[sb_pos]['chips'])
        self.players[sb_pos]['chips'] -= sb_amount
        self.players[sb_pos]['current_bet'] = sb_amount
        self.pot += sb_amount

        # Big blind
        bb_amount = min(self.big_blind, self.players[bb_pos]['chips'])
        self.players[bb_pos]['chips'] -= bb_amount
        self.players[bb_pos]['current_bet'] = bb_amount
        self.pot += bb_amount

        self.current_bet = self.big_blind
        self.last_raiser = bb_pos

    def _deal_hole_cards(self):
        """Deal 2 hole cards to each player."""
        for _ in range(2):
            for player in self.players:
                if not player['folded']:
                    player['hole_cards'].append(self.deck.pop())

    def advance_phase(self):
        """Move to the next phase of the hand."""
        if not self.round_complete:
            return False

        # Reset for new betting round
        for player in self.players:
            player['current_bet'] = 0
        self.current_bet = 0
        self.round_complete = False

        if self.phase == 'pre-flop':
            # Deal flop (3 cards)
            self.deck.pop()  # Burn card
            for _ in range(3):
                self.community_cards.append(self.deck.pop())
            self.phase = 'flop'

        elif self.phase == 'flop':
            # Deal turn (1 card)
            self.deck.pop()  # Burn card
            self.community_cards.append(self.deck.pop())
            self.phase = 'turn'

        elif self.phase == 'turn':
            # Deal river (1 card)
            self.deck.pop()  # Burn card
            self.community_cards.append(self.deck.pop())
            self.phase = 'river'

        elif self.phase == 'river':
            self.phase = 'showdown'
            self._evaluate_hands()
            return True

        # Set first to act (after dealer)
        self.current_player = (self.dealer_position + 1) % len(self.players)
        self._skip_folded_players()
        self.last_raiser = self.current_player

        # Check if only all-in players remain
        if len(self.get_players_to_act()) <= 1:
            self.round_complete = True

        return True

    def _evaluate_hands(self):
        """Evaluate all remaining players' hands."""
        for player in self.get_active_players():
            result = HandEvaluator.best_hand(player['hole_cards'], self.community_cards)
            player['hand_result'] = {
                'rank': result[0],
                'tiebreakers': result[1],
                'name': result[2],
                'best_cards': result[3]
            }

    def get_state(self, for_session=None):
        """Get current game state for client."""
        state = super().get_state(for_session)
        state['game_mode'] = 'holdem'
        state['community_cards'] = self.community_cards
        state['small_blind'] = self.small_blind
        state['big_blind'] = self.big_blind
        return state


# =============================================================================
# SEVEN-CARD STUD FOLLOW THE QUEEN
# =============================================================================

class StudFollowQueenGame(BasePokerGame):
    """Seven-Card Stud Follow the Queen poker game."""

    PHASES = ['third_street', 'fourth_street', 'fifth_street',
              'sixth_street', 'seventh_street', 'showdown']

    def __init__(self, num_players=5, starting_chips=1000, ante_amount=5, bring_in_amount=10):
        self.ante_amount = ante_amount
        self.bring_in_amount = bring_in_amount
        self.current_wild_rank = 'Q'  # Always starts with Queens only
        self.wild_card_history = []
        super().__init__(num_players, starting_chips)

    def reset_game(self):
        """Reset for a new game."""
        super().reset_game()
        self.current_wild_rank = 'Q'
        self.wild_card_history = []

    def add_player(self, session_id, player_name):
        """Add a new player with Stud-specific card fields."""
        player_id, message = super().add_player(session_id, player_name)
        if player_id is not None:
            # Initialize Stud-specific card fields
            player = self.players[player_id]
            player['down_cards'] = []
            player['up_cards'] = []
        return player_id, message

    def _reset_player_cards(self):
        """Reset down and up cards for all players."""
        for player in self.players:
            player['down_cards'] = []  # Face-down cards
            player['up_cards'] = []     # Face-up cards

    def _initialize_hand(self):
        """Initialize a Stud hand: post antes, deal initial cards, set bring-in."""
        # Reset wild cards for new hand
        self.current_wild_rank = 'Q'
        self.wild_card_history = []

        # Post antes
        self._post_antes()

        # Deal Third Street: 2 down, 1 up
        newly_dealt = []
        for player in self.players:
            # 2 down cards
            player['down_cards'].append(self.deck.pop())
            player['down_cards'].append(self.deck.pop())
            # 1 up card
            up_card = self.deck.pop()
            player['up_cards'].append(up_card)
            newly_dealt.append((player, up_card))

        # Check for Queens in up cards
        self._check_for_queens(newly_dealt)

        # Determine and post bring-in
        bring_in_player = self._determine_bring_in()
        self._post_bring_in(bring_in_player)

        # Set first to act (bring-in player)
        self.current_player = bring_in_player
        self._skip_folded_players()

    def _post_antes(self):
        """All players post ante."""
        for player in self.players:
            ante = min(self.ante_amount, player['chips'])
            player['chips'] -= ante
            self.pot += ante

    def _determine_bring_in(self):
        """Find player with lowest up card. Tiebreaker: suit (clubs < diamonds < hearts < spades)."""
        suit_order = {'clubs': 0, 'diamonds': 1, 'hearts': 2, 'spades': 3}
        lowest_player = None
        lowest_value = None
        lowest_suit = None

        for idx, player in enumerate(self.players):
            if player['folded'] or not player['up_cards']:
                continue

            card = player['up_cards'][0]  # First up card
            card_value = RANK_VALUES[card['rank']]
            card_suit_value = suit_order.get(card['suit'], 0)

            if lowest_player is None or card_value < lowest_value or \
               (card_value == lowest_value and card_suit_value < lowest_suit):
                lowest_player = idx
                lowest_value = card_value
                lowest_suit = card_suit_value

        return lowest_player if lowest_player is not None else 0

    def _post_bring_in(self, player_idx):
        """Force bring-in player to bet."""
        player = self.players[player_idx]
        bring_in = min(self.bring_in_amount, player['chips'])
        player['chips'] -= bring_in
        player['current_bet'] = bring_in
        self.pot += bring_in
        self.current_bet = bring_in
        self.last_raiser = player_idx

    def _check_for_queens(self, newly_dealt_cards):
        """
        Update wild rank when Queen is dealt face-up.

        Args:
            newly_dealt_cards: List of (player, card) tuples in deal order
        """
        # Find all Queens in newly dealt cards
        queens = [(p, c) for p, c in newly_dealt_cards if c['rank'] == 'Q']

        if not queens:
            return  # No wild card change

        # Process each Queen (last one wins if multiple)
        for queen_player, queen_card in queens:
            # Find next card dealt AFTER this Queen
            queen_index = newly_dealt_cards.index((queen_player, queen_card))

            if queen_index < len(newly_dealt_cards) - 1:
                # There's a card after the Queen
                next_player, next_card = newly_dealt_cards[queen_index + 1]
                new_wild_rank = next_card['rank']
            else:
                # Queen was last card dealt - only Queens are wild
                new_wild_rank = 'Q'

            # Update wild rank
            self.current_wild_rank = new_wild_rank

            # Record in history
            self.wild_card_history.append({
                'phase': self.phase,
                'trigger_card': queen_card.copy(),
                'new_wild_rank': new_wild_rank,
                'player_name': queen_player['name']
            })

    def advance_phase(self):
        """Move to the next phase and deal appropriate cards."""
        if not self.round_complete:
            return False

        # Reset for new betting round
        for player in self.players:
            player['current_bet'] = 0
        self.current_bet = 0
        self.round_complete = False

        # Deal cards based on phase
        if self.phase == 'third_street':
            self._deal_street_cards(1, face_up=True)  # Fourth street
            self.phase = 'fourth_street'

        elif self.phase == 'fourth_street':
            self._deal_street_cards(1, face_up=True)  # Fifth street
            self.phase = 'fifth_street'

        elif self.phase == 'fifth_street':
            self._deal_street_cards(1, face_up=True)  # Sixth street
            self.phase = 'sixth_street'

        elif self.phase == 'sixth_street':
            self._deal_street_cards(1, face_up=False)  # Seventh street (down)
            self.phase = 'seventh_street'

        elif self.phase == 'seventh_street':
            self.phase = 'showdown'
            self._evaluate_hands()
            return True

        # Set first to act (after dealer)
        self.current_player = (self.dealer_position + 1) % len(self.players)
        self._skip_folded_players()
        self.last_raiser = self.current_player

        # Check if only all-in players remain
        if len(self.get_players_to_act()) <= 1:
            self.round_complete = True

        return True

    def _deal_street_cards(self, count, face_up):
        """Deal cards for a street."""
        newly_dealt = []
        for player in self.players:
            if not player['folded']:
                for _ in range(count):
                    card = self.deck.pop()
                    if face_up:
                        player['up_cards'].append(card)
                        newly_dealt.append((player, card))
                    else:
                        player['down_cards'].append(card)

        # Check for Queens if face-up cards were dealt
        if face_up:
            self._check_for_queens(newly_dealt)

    def _evaluate_hands(self):
        """Evaluate all remaining players' hands with wild cards."""
        wild_ranks = ['Q']  # Queens always wild
        if self.current_wild_rank != 'Q':
            wild_ranks.append(self.current_wild_rank)

        for player in self.get_active_players():
            # Combine all 7 cards
            all_cards = player['down_cards'] + player['up_cards']

            # Evaluate best hand with wild cards
            best = WildCardEvaluator.best_hand_with_wilds(all_cards, wild_ranks)

            player['hand_result'] = {
                'rank': best[0],
                'tiebreakers': best[1],
                'name': best[2],
                'best_cards': best[3] if len(best) > 3 else [],
                'wild_ranks': wild_ranks
            }

    def get_state(self, for_session=None):
        """Get current game state for client."""
        player_id = self.player_sessions.get(for_session) if for_session else None

        players_state = []
        for p in self.players:
            player_data = {
                'id': p['id'],
                'name': p['name'],
                'chips': p['chips'],
                'current_bet': p['current_bet'],
                'folded': p['folded'],
                'is_all_in': p['is_all_in'],
                'is_human': p['is_human'],
                'is_dealer': self.players.index(p) == self.dealer_position
            }

            # Card visibility: show cards only to owner OR if player has revealed them
            # At showdown, cards stay hidden until player clicks to reveal
            is_owner = p['id'] == player_id
            has_revealed = p.get('cards_revealed', False)

            if is_owner or has_revealed:
                player_data['down_cards'] = p.get('down_cards', [])
                player_data['up_cards'] = p.get('up_cards', [])
                if p.get('hand_result'):
                    player_data['hand_result'] = p['hand_result']
                player_data['cards_revealed'] = has_revealed
            else:
                # Hide down cards from opponents until they reveal
                down_cards = p.get('down_cards', [])
                player_data['down_cards'] = [{'rank': '?', 'suit': 'back', 'symbol': ''}] * len(down_cards)
                player_data['up_cards'] = p.get('up_cards', [])  # Up cards always visible
                player_data['cards_revealed'] = False

            players_state.append(player_data)

        is_my_turn = False
        if self.players and player_id is not None:
            current_player_obj = self.players[self.current_player] if self.current_player < len(self.players) else None
            is_my_turn = current_player_obj is not None and current_player_obj['id'] == player_id

        return {
            'phase': self.phase,
            'pot': self.pot,
            'current_bet': self.current_bet,
            'players': players_state,
            'current_player': self.current_player,
            'is_my_turn': is_my_turn,
            'my_player_id': player_id,
            'dealer_position': self.dealer_position,
            'round_complete': self.round_complete,
            'game_started': self.game_started,
            'num_players': self.num_players,
            'game_mode': 'stud_follow_queen',
            'current_wild_rank': self.current_wild_rank,
            'wild_card_history': self.wild_card_history,
            'community_cards': [],  # No community cards in Stud
            'ante_amount': self.ante_amount,
            'bring_in_amount': self.bring_in_amount
        }


# Global game instance
# Start with Follow the Queen for testing
game = StudFollowQueenGame(num_players=8, starting_chips=1000, ante_amount=5, bring_in_amount=10)

# Available player names
PLAYER_NAMES = ['Alan K', 'Andy L', 'Michael H', 'Mark A', 'Ron R', 'Peter R', 'Chunk G', 'Andrew G', 'Bot 1', 'Bot 2']
taken_names = {}  # Maps session_id to player_name

def broadcast_name_availability():
    """Broadcast which names are available to all clients."""
    available = [name for name in PLAYER_NAMES if name not in taken_names.values()]
    taken = list(taken_names.values())
    socketio.emit('name_availability', {
        'available': available,
        'taken': taken,
        'all_names': PLAYER_NAMES
    }, room='poker_game')

# =============================================================================
# WEBSOCKET EVENTS
# =============================================================================

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
    game_mode = data.get('game_mode', 'holdem')
    num_players = data.get('num_players', 6)

    # Save existing players and their session mappings if any
    existing_players = []
    if game and len(game.players) > 0:
        existing_players = list(game.players)  # Make a copy

    if game_mode == 'stud_follow_queen':
        game = StudFollowQueenGame(
            num_players=num_players,
            starting_chips=1000,
            ante_amount=5,
            bring_in_amount=10
        )
    else:  # Default to Hold'em
        game = HoldemGame(
            num_players=num_players,
            starting_chips=1000,
            small_blind=10,
            big_blind=20
        )

    # Re-add existing players to the new game
    for player in existing_players:
        game.add_player(player['session_id'], player['name'])
        # Update taken_names to track this player
        taken_names[player['session_id']] = player['name']

    # NOTE: Auto-start removed. Use "Start Game" button when ready.
    # Players can now join until game is manually started.

    broadcast_game_state()
    broadcast_name_availability()

@socketio.on('start_game')
def handle_start_game():
    """Lock the game, prevent new players from joining, and auto-deal the first hand."""
    if len(game.players) < 2:
        emit('error', {'message': 'Need at least 2 players to start the game'})
        return

    game.game_started = True

    # Auto-deal the first hand
    game.new_hand()

    broadcast_game_state()
    socketio.emit('game_locked', {'message': 'Game has started! No more players can join.'}, room='poker_game')

@socketio.on('new_hand')
def handle_new_hand():
    """Handle dealing a new hand - only dealer can do this."""
    player_id = game.get_player_by_session(request.sid)

    # Check if this player is the dealer
    if player_id is None or player_id != game.dealer_position:
        emit('error', {'message': 'Only the dealer can deal a new hand'})
        return

    if len(game.players) < 2:
        emit('error', {'message': 'Need at least 2 players to start'})
        return

    game.new_hand()
    broadcast_game_state()

@socketio.on('reset_game')
def handle_reset_game():
    """Reset the entire game - only Michael H can do this. Restarts the server."""
    global game, taken_names

    player_id = game.get_player_by_session(request.sid)

    # Find the player and check if they are "Michael H"
    if player_id is None:
        emit('error', {'message': 'You are not in this game'})
        return

    player = game.players[player_id]
    if player['name'] != 'Michael H':
        emit('error', {'message': 'Only Michael H can reset the game'})
        return

    # Notify all clients that server is restarting
    socketio.emit('server_restart', {'message': 'Server is restarting... Please wait and refresh.'}, room='poker_game')

    print("\n" + "=" * 50)
    print("SERVER RESTART TRIGGERED BY MICHAEL H")
    print("=" * 50 + "\n")

    # Give clients a moment to receive the message
    import time
    time.sleep(0.5)

    # Restart the server by re-executing the script
    import sys
    import os
    os.execv(sys.executable, [sys.executable] + sys.argv)

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

@socketio.on('advance_phase')
def handle_advance_phase():
    """Advance to the next phase."""
    game.advance_phase()
    broadcast_game_state()

    if game.phase == 'showdown':
        handle_determine_winner()

@socketio.on('determine_winner')
def handle_determine_winner():
    """Determine the winner and distribute pot."""
    winners = game.determine_winners()
    socketio.emit('winners', {
        'winners': [{
            'player': {
                'name': w['player']['name'],
                'chips': w['player']['chips']
            },
            'amount': w['amount'],
            'hand': w['hand']
        } for w in winners]
    }, room='poker_game')
    broadcast_game_state()

    # Game stays at showdown - no auto-deal
    # Players can review cards and click "New Hand" when ready

def broadcast_game_state():
    """Broadcast game state to all connected clients."""
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
# HTML TEMPLATE
# =============================================================================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Texas Hold'em Poker</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #1a3a5a 0%, #0d1a2d 100%);
            min-height: 100vh;
            color: #fff;
            overflow-x: hidden;
        }
        
        .header {
            text-align: center;
            padding: 15px;
            background: rgba(0,0,0,0.3);
        }
        
        .header h1 {
            color: #ffd700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            font-size: 2rem;
        }
        
        .game-container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Poker Table */
        .poker-table {
            background: radial-gradient(ellipse at center, #2d4a6d 0%, #1a3555 70%);
            border: 15px solid #3d4d5c;
            border-radius: 150px;
            padding: 30px;
            margin: 20px auto;
            position: relative;
            box-shadow:
                inset 0 0 50px rgba(0,0,0,0.5),
                0 10px 30px rgba(0,0,0,0.5);
            min-height: 400px;
        }
        
        /* Pot Display */
        .pot-display {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .pot-amount {
            font-size: 1.5rem;
            color: #ffd700;
            background: rgba(0,0,0,0.5);
            padding: 10px 30px;
            border-radius: 25px;
            display: inline-block;
        }
        
        .phase-display {
            font-size: 1rem;
            color: #aaa;
            margin-top: 5px;
        }

        .wild-card-display {
            background: rgba(255, 105, 180, 0.2);
            border: 2px solid #ff69b4;
            border-radius: 10px;
            padding: 8px 20px;
            margin-top: 10px;
            display: inline-block;
        }

        /* Community Cards */
        .community-cards {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
            min-height: 100px;
        }
        
        /* Player Positions */
        .players-area {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 30px;
        }
        
        .player-spot {
            background: rgba(0,0,0,0.4);
            border-radius: 15px;
            padding: 15px;
            min-width: 180px;
            text-align: center;
            transition: all 0.3s ease;
            border: 3px solid transparent;
        }
        
        .player-spot.active {
            border-color: #ffd700;
            box-shadow: 0 0 20px rgba(255,215,0,0.5);
        }
        
        .player-spot.folded {
            opacity: 0.5;
        }
        
        .player-spot.human {
            background: rgba(0,70,140,0.4);
        }
        
        .player-name {
            font-weight: bold;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .dealer-chip {
            background: #fff;
            color: #000;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            font-size: 12px;
            font-weight: bold;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 2px solid #ffd700;
        }
        
        .player-chips {
            color: #ffd700;
            margin: 5px 0;
        }
        
        .player-bet {
            color: #ff9800;
            font-size: 0.9rem;
        }
        
        .player-cards {
            display: flex;
            justify-content: center;
            gap: 5px;
            margin-top: 10px;
        }
        
        .player-status {
            margin-top: 8px;
            font-size: 0.85rem;
            padding: 3px 10px;
            border-radius: 10px;
            display: inline-block;
        }
        
        .status-folded {
            background: #c0392b;
        }
        
        .status-all-in {
            background: #8e44ad;
        }
        
        .hand-result {
            margin-top: 8px;
            color: #ffd700;
            font-weight: bold;
            font-size: 0.9rem;
        }
        
        /* Cards */
        .card {
            width: 60px;
            height: 84px;
            background: #fff;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 4px;
            box-shadow: 0 3px 6px rgba(0,0,0,0.3);
            position: relative;
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        .card.back {
            background: linear-gradient(145deg, #1e3d59, #17435e);
            border: 2px solid #fff;
        }
        
        .card.back::after {
            content: '🂠';
            font-size: 40px;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        
        .card.community {
            width: 70px;
            height: 98px;
        }
        
        .card.placeholder {
            background: rgba(255,255,255,0.1);
            border: 2px dashed rgba(255,255,255,0.3);
        }
        
        .card-corner {
            display: flex;
            flex-direction: column;
            align-items: center;
            line-height: 1;
        }
        
        .card-corner.bottom {
            align-self: flex-end;
            transform: rotate(180deg);
        }
        
        .card-rank {
            font-size: 14px;
            font-weight: bold;
        }
        
        .card-suit {
            font-size: 12px;
        }
        
        .card.hearts, .card.diamonds {
            color: #cc0000;
        }
        
        .card.clubs, .card.spades {
            color: #000;
        }
        
        .card-center {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 24px;
        }
        
        /* Action Panel - Floating Toolbar */
        .action-panel {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(145deg, rgba(0,0,0,0.9), rgba(30,30,30,0.95));
            border-radius: 20px;
            padding: 20px 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5), 0 0 20px rgba(255,215,0,0.3);
            border: 2px solid rgba(255,215,0,0.5);
            z-index: 1000;
            animation: floatIn 0.3s ease-out;
        }

        @keyframes floatIn {
            from {
                opacity: 0;
                transform: translateX(-50%) translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateX(-50%) translateY(0);
            }
        }

        .action-panel::before {
            content: "🎯 YOUR TURN";
            display: block;
            text-align: center;
            color: #ffd700;
            font-weight: bold;
            font-size: 0.9rem;
            margin-bottom: 12px;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(255,215,0,0.5);
        }
        
        .action-buttons {
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
        }

        .btn {
            padding: 12px 25px;
            font-size: 1rem;
            font-weight: bold;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn:hover:not(:disabled) {
            transform: translateY(-2px);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Action button specific styles - larger for floating toolbar */
        .action-panel .btn {
            padding: 15px 30px;
            font-size: 1.1rem;
            min-width: 100px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }

        .action-panel .btn:hover:not(:disabled) {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.4);
        }

        .btn-fold {
            background: linear-gradient(145deg, #c0392b, #a93226);
            color: white;
        }

        .btn-check, .btn-call {
            background: linear-gradient(145deg, #27ae60, #229954);
            color: white;
        }

        .btn-raise {
            background: linear-gradient(145deg, #f39c12, #d68910);
            color: white;
        }
        
        .btn-allin {
            background: linear-gradient(145deg, #8e44ad, #7d3c98);
            color: white;
        }
        
        .btn-primary {
            background: linear-gradient(145deg, #ffd700, #ffaa00);
            color: #1a3555;
        }

        /* Player Name Dropdown */
        #playerName {
            font-size: 1rem;
        }

        #playerName option:disabled {
            color: #999 !important;
            font-style: italic !important;
            background: #f5f5f5 !important;
        }

        #playerName option:not(:disabled) {
            color: #1a3555;
            font-weight: bold;
        }

        .raise-controls {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-top: 15px;
        }
        
        .raise-input {
            width: 100px;
            padding: 10px;
            font-size: 1rem;
            border: none;
            border-radius: 5px;
            text-align: center;
        }
        
        .raise-slider {
            width: 200px;
        }
        
        /* Status Messages */
        .game-status {
            text-align: center;
            padding: 10px;
            font-size: 1.2rem;
            color: #ffd700;
            min-height: 40px;
        }
        
        /* Winner Announcement */
        .winner-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .winner-content {
            background: linear-gradient(145deg, #1a3555, #0d1a2d);
            border: 3px solid #ffd700;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            animation: popIn 0.5s ease;
        }
        
        @keyframes popIn {
            from { transform: scale(0.5); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        
        .winner-content h2 {
            color: #ffd700;
            font-size: 2rem;
            margin-bottom: 20px;
        }
        
        .winner-details {
            font-size: 1.2rem;
            margin: 15px 0;
        }
        
        /* Controls Bar */
        .controls-bar {
            display: flex;
            justify-content: center;
            gap: 15px;
            padding: 15px;
            background: rgba(0,0,0,0.3);
        }
        
        /* Animations */
        .card-deal {
            animation: dealCard 0.3s ease;
        }
        
        @keyframes dealCard {
            from {
                transform: translateY(-100px) rotate(180deg);
                opacity: 0;
            }
            to {
                transform: translateY(0) rotate(0);
                opacity: 1;
            }
        }
        
        /* Algorithm Info (from shuffle feature) */
        .algorithm-info {
            display: none;
            max-width: 900px;
            margin: 20px auto;
            padding: 25px;
            background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240,240,240,0.95));
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            color: #1a1a1a;
        }
        
        .algorithm-info h2 {
            text-align: center;
            color: #1a3555;
            margin-bottom: 20px;
            border-bottom: 3px solid #ffd700;
            padding-bottom: 10px;
        }

        .algorithm-info h3 {
            color: #1a3555;
            margin: 15px 0 10px;
        }

        .info-section {
            margin-bottom: 15px;
            padding: 15px;
            background: rgba(26, 53, 85, 0.05);
            border-radius: 10px;
            border-left: 4px solid #1a3555;
        }
        
        .code-block {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            overflow-x: auto;
            margin: 10px 0;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .poker-table {
                border-radius: 50px;
                padding: 15px;
            }
            .player-spot {
                min-width: 140px;
                padding: 10px;
            }
            .card {
                width: 50px;
                height: 70px;
            }
            .card.community {
                width: 55px;
                height: 77px;
            }
        }

        /* Game Mode Container Display */
        #holdemTable, #studTable {
            display: none;
        }

        [data-game-mode="holdem"] #holdemTable {
            display: block;
        }

        [data-game-mode="stud_follow_queen"] #studTable {
            display: block;
        }

        /* Wild Card Panel Prominence */
        #wildCardPanel {
            background: linear-gradient(135deg, #8b008b 0%, #ff1493 100%);
            border: 3px solid #ff69b4;
            border-radius: 15px;
            padding: 20px;
            margin: 20px auto;
            max-width: 1600px;
            box-shadow: 0 0 30px rgba(255, 105, 180, 0.6);
            animation: wildGlow 2s ease-in-out infinite;
        }

        @keyframes wildGlow {
            0%, 100% { box-shadow: 0 0 30px rgba(255, 105, 180, 0.6); }
            50% { box-shadow: 0 0 50px rgba(255, 105, 180, 1); }
        }

        #wildCardPanel .current-wild {
            font-size: 2.5rem;
            color: #ffd700;
            text-align: center;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }

        #wildCardPanel .wild-history {
            margin-top: 15px;
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .wild-change-badge {
            background: rgba(0,0,0,0.3);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
        }

        /* Stud Player Card Layout */
        .stud-players-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .stud-player-card {
            background: rgba(0,0,0,0.4);
            border-radius: 15px;
            padding: 20px;
            border: 3px solid transparent;
        }

        .stud-player-card.active {
            border-color: #ffd700;
            box-shadow: 0 0 20px rgba(255,215,0,0.5);
        }

        .stud-player-card.folded {
            opacity: 0.5;
        }

        .stud-player-card .player-info {
            margin-bottom: 15px;
        }

        .card-progression {
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }

        .down-cards-group, .up-cards-group {
            flex: 1;
            min-width: 140px;
        }

        .down-cards-group label, .up-cards-group label {
            display: block;
            text-align: center;
            color: #ffd700;
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .cards-vertical {
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
        }

        .cards-vertical .card {
            margin: 0;
        }

        /* Visual distinction for down cards group */
        .down-cards-group {
            background: rgba(139, 0, 0, 0.2);
            border: 2px dashed rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            padding: 15px;
        }

        /* Visual distinction for up cards group */
        .up-cards-group {
            background: rgba(0, 100, 0, 0.2);
            border: 2px solid rgba(0, 255, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
        }

        /* Street Indicators */
        .street-indicator {
            font-size: 0.7rem;
            color: #aaa;
            text-align: center;
            margin-top: 3px;
        }

        /* Current Hand Display */
        .current-hand-display {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid #ffd700;
            border-radius: 10px;
            padding: 10px 15px;
            margin-top: 15px;
            text-align: center;
            color: #ffd700;
            font-weight: bold;
            font-size: 1.1rem;
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
        }

        /* Clickable reveal for down cards at showdown */
        .clickable-reveal {
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .clickable-reveal:hover {
            transform: scale(1.05);
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.6);
            border-color: #ffd700;
        }

        .reveal-hint {
            text-align: center;
            color: #ffd700;
            font-size: 0.8rem;
            margin-top: 8px;
            animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 id="gameTitle">🃏 Texas Hold'em Poker - Multiplayer</h1>
    </div>

    <div id="joinSection" class="controls-bar" style="flex-direction: column; gap: 15px;">
        <div style="font-size: 1.2rem; color: #ffd700;">Join the Game</div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <label for="playerName" style="color: #ffd700;">Your Name:</label>
            <select id="playerName" style="padding: 10px; border-radius: 5px; border: none; min-width: 200px; background: white; color: #1a3555; font-weight: bold; cursor: pointer;">
                <option value="">-- Select Your Name --</option>
            </select>
            <button class="btn btn-primary" onclick="joinGame()">Join Game</button>
        </div>
        <div id="joinStatus" style="color: #ff6b6b;"></div>
    </div>

    <div class="controls-bar" id="gameControls" style="display: none;">
        <div style="display: flex; align-items: center; gap: 10px;">
            <label for="gameMode" style="color: #ffd700; font-weight: bold;">Game Type:</label>
            <select id="gameMode" class="btn" style="padding: 10px; background: rgba(255,255,255,0.9); color: #1a3555; cursor: pointer;">
                <option value="holdem">Texas Hold'em</option>
                <option value="stud_follow_queen" selected>Follow the Queen</option>
            </select>

            <label for="numPlayers" style="color: #ffd700; font-weight: bold;">Players:</label>
            <select id="numPlayers" class="btn" style="padding: 10px; background: rgba(255,255,255,0.9); color: #1a3555; cursor: pointer;">
                <option value="2" selected>2 Players</option>
                <option value="3">3 Players</option>
                <option value="4">4 Players</option>
                <option value="5">5 Players</option>
                <option value="6">6 Players</option>
                <option value="7">7 Players</option>
                <option value="8">8 Players</option>
                <option value="9">9 Players</option>
            </select>
        </div>
        <button class="btn btn-primary" onclick="newGame()">New Game</button>
        <button class="btn btn-primary" onclick="startGame()" id="startGameBtn" style="display: none;">Start Game</button>
        <button class="btn btn-primary" onclick="newHand()" id="newHandBtn" style="display: none;">New Hand</button>
        <button class="btn btn-primary" onclick="resetGame()" id="resetGameBtn" style="display: none; background: linear-gradient(145deg, #e74c3c, #c0392b);">🔄 Reset Game</button>
        <button class="btn btn-primary" onclick="toggleAlgorithmInfo()">📚 Shuffle Info</button>
    </div>
    
    <div class="game-container">
        <div class="game-status" id="gameStatus">Select your name and click "Join Game" to enter.</div>
        
        <div class="algorithm-info" id="algorithmInfo">
            <h2>🔀 Fisher-Yates Shuffle Algorithm</h2>
            
            <div class="info-section">
                <h3>History & Origins</h3>
                <p>The Fisher-Yates shuffle was originally described by <strong>Ronald Fisher</strong> and <strong>Frank Yates</strong> in their 1938 book "Statistical Tables for Biological, Agricultural and Medical Research." The modern computer-optimized version was developed by <strong>Richard Durstenfeld</strong> in 1964 and popularized by <strong>Donald Knuth</strong> in "The Art of Computer Programming."</p>
            </div>
            
            <div class="info-section">
                <h3>How It Works</h3>
                <p>The algorithm iterates from the last element to the first. For each position <em>i</em>, it randomly selects an element from positions 0 to <em>i</em> and swaps them.</p>
                <div class="code-block">
<pre>for i from n-1 down to 1:
    j = random integer where 0 ≤ j ≤ i
    swap array[i] with array[j]</pre>
                </div>
            </div>
            
            <div class="info-section">
                <h3>Python Implementation</h3>
                <div class="code-block">
<pre>def fisher_yates_shuffle(deck):
    for i in range(len(deck) - 1, 0, -1):
        j = random.randint(0, i)
        deck[i], deck[j] = deck[j], deck[i]
    return deck</pre>
                </div>
            </div>
            
            <div class="info-section">
                <h3>Why 7 Shuffles?</h3>
                <p>Mathematician <strong>Persi Diaconis</strong> proved that <strong>7 riffle shuffles</strong> are needed to adequately randomize a 52-card deck. This relates to mixing time in Markov chains.</p>
            </div>
            
            <div class="info-section">
                <h3>Mathematical Properties</h3>
                <p><strong>Time Complexity:</strong> O(n) | <strong>Space:</strong> O(1) | <strong>Permutations:</strong> 52! = 8.07 × 10<sup>67</sup></p>
            </div>
        </div>

        <!-- Wild Card Panel (Stud only) -->
        <div id="wildCardPanel" style="display: none;">
            <div class="current-wild" id="currentWild">
                🃏 Wild Cards: <span style="font-size: 3rem;">Queens Only</span>
            </div>
            <div class="wild-history" id="wildHistory">
                <div class="wild-change-badge">No wild card changes yet</div>
            </div>
        </div>

        <!-- Texas Hold'em Table -->
        <div id="holdemTable">
            <div class="poker-table" id="pokerTable">
                <div class="pot-display">
                    <div class="pot-amount">Pot: $<span id="potAmount">0</span></div>
                    <div class="phase-display">Phase: <span id="phaseDisplay">-</span></div>
                </div>

                <div class="community-cards" id="communityCards">
                    <!-- Community cards appear here -->
                </div>

                <div class="players-area" id="playersArea">
                    <!-- Player spots appear here -->
                </div>
            </div>
        </div>

        <!-- Follow the Queen (Stud) Table -->
        <div id="studTable">
            <div class="poker-table">
                <div class="pot-display">
                    <div class="pot-amount">Pot: $<span id="studPotAmount">0</span></div>
                    <div class="phase-display">Phase: <span id="studPhaseDisplay">-</span></div>
                </div>

                <div class="stud-players-grid" id="studPlayersGrid">
                    <!-- Stud player cards appear here -->
                </div>
            </div>
        </div>

        <div class="action-panel" id="actionPanel" style="display: none;">
            <div class="action-buttons" id="actionButtons">
                <button class="btn btn-fold" onclick="playerAction('fold')">Fold</button>
                <button class="btn btn-check" id="checkCallBtn" onclick="playerAction('check')">Check</button>
                <button class="btn btn-raise" onclick="showRaiseControls()">Raise</button>
                <button class="btn btn-allin" onclick="playerAction('all-in')">All In</button>
            </div>
            <div class="raise-controls" id="raiseControls" style="display: none;">
                <span>Raise to: $</span>
                <input type="number" id="raiseAmount" class="raise-input" value="0">
                <button class="btn btn-raise" onclick="playerAction('raise')">Confirm Raise</button>
                <button class="btn" onclick="hideRaiseControls()">Cancel</button>
            </div>
        </div>
    </div>
    
    <div class="winner-modal" id="winnerModal">
        <div class="winner-content">
            <h2>🏆 Winner!</h2>
            <div class="winner-details" id="winnerDetails"></div>
            <button class="btn btn-primary" id="winnerCloseBtn" onclick="closeWinnerModal()" disabled>
                Wait <span id="winnerCountdown">16</span>s...
            </button>
        </div>
    </div>

    <script>
        let socket = io();
        let gameState = null;
        let sessionId = null;
        let myPlayerName = null;

        // Socket.IO event listeners
        socket.on('connected', (data) => {
            sessionId = data.session_id;
            console.log('Connected with session:', sessionId);
        });

        socket.on('name_availability', (data) => {
            updatePlayerNameDropdown(data.all_names, data.taken);
        });

        socket.on('join_success', (data) => {
            myPlayerName = data.name;
            document.getElementById('joinSection').style.display = 'none';
            document.getElementById('gameControls').style.display = 'flex';
            document.getElementById('gameTitle').textContent = `🃏 Poker - Multiplayer - ${data.name}`;
            updateResetButtonVisibility();
            updateStatusMessage();
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
                players: playerInfo
            });

            updateDisplay();
            updateButtons();
            updateStatusMessage();
        });

        socket.on('game_locked', (data) => {
            console.log(data.message);
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
                    <h1 style="font-size: 3rem; margin-bottom: 20px;">🔄 Server Restarting</h1>
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
            // Display winner info in the game status area (no modal)
            let winnerText = '';
            data.winners.forEach(w => {
                winnerText += `${w.player.name} wins $${w.amount}`;
                if (w.hand) {
                    winnerText += ` with ${w.hand}`;
                }
                winnerText += '. ';
            });

            // Update status message with winner info
            const statusEl = document.getElementById('gameStatus');
            if (statusEl) {
                statusEl.innerHTML = `<strong style="color: #ffd700; font-size: 1.2rem;">🏆 ${winnerText}</strong><br><em>Click your down cards to reveal them to other players.</em>`;
            }

            // Game stays in showdown phase - no auto-reset
            console.log('Hand complete:', winnerText);
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
            const gameMode = document.getElementById('gameMode').value;
            const numPlayers = parseInt(document.getElementById('numPlayers').value);
            socket.emit('new_game', { game_mode: gameMode, num_players: numPlayers });
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
                amount = parseInt(document.getElementById('raiseAmount').value);
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

            // Show Start Game button if game hasn't started yet
            if (!gameState.game_started) {
                startGameBtn.style.display = 'inline-block';
                newHandBtn.style.display = 'none';
                startGameBtn.disabled = gameState.players.length < 2;
            } else {
                // Game has started - show New Hand button only for dealer
                startGameBtn.style.display = 'none';
                newHandBtn.style.display = 'inline-block';

                // Only enable if this player is the dealer
                if (gameState.my_player_id === gameState.dealer_position) {
                    newHandBtn.disabled = false;
                    newHandBtn.style.opacity = '1';
                } else {
                    newHandBtn.disabled = true;
                    newHandBtn.style.opacity = '0.5';
                }
            }
        }

        function updateResetButtonVisibility() {
            const resetBtn = document.getElementById('resetGameBtn');
            // Only show reset button for "Michael H"
            if (myPlayerName === 'Michael H') {
                resetBtn.style.display = 'inline-block';
            } else {
                resetBtn.style.display = 'none';
            }
        }

        function updateStatusMessage() {
            if (!gameState) return;

            const statusEl = document.getElementById('gameStatus');

            if (!gameState.game_started) {
                const playerCount = gameState.players ? gameState.players.length : 0;
                const maxPlayers = gameState.num_players || 6;
                statusEl.textContent = `Waiting for additional players (${playerCount}/${maxPlayers}). Click "Start Game" when ready (minimum 2 players).`;
            } else if (gameState.phase === 'showdown') {
                statusEl.textContent = 'Hand complete! Dealer can deal next hand.';
            } else if (gameState.is_my_turn) {
                statusEl.textContent = 'Your turn to act!';
            } else if (gameState.players && gameState.current_player >= 0) {
                const currentPlayer = gameState.players[gameState.current_player];
                statusEl.textContent = `Waiting for ${currentPlayer ? currentPlayer.name : 'player'}...`;
            }
        }

        function createCardHTML(card, extraClass = '') {
            if (!card || card.suit === 'back') {
                return `<div class="card back ${extraClass}"></div>`;
            }
            return `
                <div class="card ${card.suit} ${extraClass}">
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
            currentWildEl.innerHTML = `🃏 Wild Cards: <span style="font-size: 3rem;">${wildText}</span>`;

            // Wild card history
            if (gameState.wild_card_history && gameState.wild_card_history.length > 0) {
                let historyHTML = '';
                gameState.wild_card_history.forEach((change, i) => {
                    historyHTML += `
                        <div class="wild-change-badge">
                            ${change.phase.replace('_', ' ')}: ${change.player_name} → ${change.new_wild_rank}s wild
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

            // Count ranks and suits
            const rankOrder = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];
            const rankCounts = {};
            const suitCounts = {};
            let wildCount = 0;

            allCards.forEach(card => {
                // Check if this card is wild (Queen or the current wild rank)
                const isWild = card.rank === 'Q' || (wildRank && card.rank === wildRank);
                if (isWild) {
                    wildCount++;
                } else {
                    rankCounts[card.rank] = (rankCounts[card.rank] || 0) + 1;
                }
                suitCounts[card.suit] = (suitCounts[card.suit] || 0) + 1;
            });

            // Get pairs, trips, quads
            const counts = Object.values(rankCounts).sort((a, b) => b - a);
            const maxOfKind = (counts[0] || 0) + wildCount;
            const secondOfKind = counts[1] || 0;

            // Check for flush (5+ of same suit)
            const maxSuit = Math.max(...Object.values(suitCounts), 0);
            const hasFlush = maxSuit >= 5;

            // Evaluate hand
            if (maxOfKind >= 5) return "Five of a Kind!";
            if (maxOfKind >= 4) return "Four of a Kind";
            if (maxOfKind >= 3 && secondOfKind >= 2) return "Full House";
            if (hasFlush) return "Flush";
            if (maxOfKind >= 3) return "Three of a Kind";
            if (maxOfKind >= 2 && secondOfKind >= 2) return "Two Pair";
            if (maxOfKind >= 2) return "Pair";
            if (wildCount > 0) return "Wild Card";

            // High card
            const highRanks = Object.keys(rankCounts).sort((a, b) =>
                rankOrder.indexOf(b) - rankOrder.indexOf(a)
            );
            if (highRanks.length > 0) {
                const highCard = highRanks[0];
                const displayRank = highCard === 'A' ? 'Ace' :
                                   highCard === 'K' ? 'King' :
                                   highCard === 'Q' ? 'Queen' :
                                   highCard === 'J' ? 'Jack' : highCard;
                return `${displayRank} High`;
            }

            return "No Hand";
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

                // Hand result
                let handResultHTML = '';
                if (player.hand_result && gameState.phase === 'showdown') {
                    handResultHTML = `<div class="hand-result">${player.hand_result.name}</div>`;
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
                                ${player.name}
                                ${player.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
                            </div>
                            <div class="player-chips">$${player.chips}</div>
                            ${player.current_bet > 0 ? `<div class="player-bet">Bet: $${player.current_bet}</div>` : ''}
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

            if (studPotEl) studPotEl.textContent = gameState.pot;

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

            if (potEl) potEl.textContent = gameState.pot;

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
                    handResultHTML = `<div class="hand-result">${player.hand_result.name}</div>`;
                }

                const cardsHTML = player.hole_cards ? player.hole_cards.map(c => createCardHTML(c)).join('') : '';

                playersHTML += `
                    <div class="${classes}">
                        <div class="player-name">
                            ${player.name}
                            ${player.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
                        </div>
                        <div class="player-chips">$${player.chips}</div>
                        ${player.current_bet > 0 ? `<div class="player-bet">Bet: $${player.current_bet}</div>` : ''}
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
                    titleElement.textContent = `🃏 ${gameTitle} - Multiplayer - ${myPlayerName}`;
                } else if (titleElement) {
                    titleElement.textContent = `🃏 ${gameTitle} - Multiplayer`;
                }

                // Route to appropriate renderer based on game mode
                if (gameMode === 'holdem') {
                    renderHoldemTable(gameState);
                } else if (gameMode === 'stud_follow_queen') {
                    updateWildCardDisplay(gameState);
                    renderStudTable(gameState);
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
                checkCallBtn.textContent = `Call $${toCall}`;
                checkCallBtn.onclick = () => playerAction('call');
                checkCallBtn.className = 'btn btn-call';
            } else {
                checkCallBtn.textContent = 'Check';
                checkCallBtn.onclick = () => playerAction('check');
                checkCallBtn.className = 'btn btn-check';
            }

            // Set default raise amount
            document.getElementById('raiseAmount').value = gameState.current_bet * 2 || gameState.big_blind * 2;
        }
        
        function showRaiseControls() {
            document.getElementById('raiseControls').style.display = 'flex';
        }
        
        function hideRaiseControls() {
            document.getElementById('raiseControls').style.display = 'none';
        }
        
        function closeWinnerModal() {
            document.getElementById('winnerModal').style.display = 'none';
            document.getElementById('gameStatus').textContent = 'Click "New Hand" to continue!';
        }

        function revealMyCards() {
            // Send request to reveal down cards to all players
            socket.emit('reveal_cards');
            console.log('Revealing my cards to all players');
        }

        function toggleAlgorithmInfo() {
            const info = document.getElementById('algorithmInfo');
            info.style.display = info.style.display === 'none' ? 'block' : 'none';
        }
    </script>
</body>
</html>
'''

# =============================================================================
# API ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/new-game', methods=['POST'])
def api_new_game():
    global game
    data = request.get_json() or {}
    num_players = data.get('num_players', 6)
    game = PokerGame(num_players=num_players, starting_chips=1000, small_blind=10, big_blind=20)
    return jsonify(game.get_state())

@app.route('/api/new-hand', methods=['POST'])
def api_new_hand():
    game.new_hand()
    return jsonify(game.get_state())

@app.route('/api/action', methods=['POST'])
def api_action():
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
    game.advance_phase()
    return jsonify(game.get_state())

@app.route('/api/winner', methods=['POST'])
def api_winner():
    winners = game.determine_winners()
    return jsonify({
        'winners': [{
            'player': {
                'name': w['player']['name'],
                'chips': w['player']['chips']
            },
            'amount': w['amount'],
            'hand': w['hand']
        } for w in winners],
        'state': game.get_state()
    })

@app.route('/api/shuffle')
def api_shuffle():
    """Original shuffle endpoint for standalone shuffle view."""
    deck = create_deck()
    shuffled = shuffle_deck(deck)
    return jsonify(shuffled)

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)
