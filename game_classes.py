"""
Poker game classes: BasePokerGame, HoldemGame, StudFollowQueenGame
"""

from evaluators import (
    create_deck, shuffle_deck, RANK_VALUES,
    HandEvaluator, WildCardEvaluator, LowHandEvaluator
)


# =============================================================================
# GAME STATE MANAGEMENT
# =============================================================================

class BasePokerGame:
    """ Base class for poker game variants. """

    PHASES: list[str] = []  # Subclasses define their phases

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
        name = player_name or f'Player {player_id + 1}'
        is_bot = name.lower().startswith('bot')
        self.players.append({
            'id': player_id,
            'name': name,
            'chips': self.starting_chips,
            'hole_cards': [],
            'current_bet': 0,
            'folded': False,
            'is_all_in': False,
            'is_human': not is_bot,
            'is_bot': is_bot,
            'session_id': session_id,
            'hand_result': None,
            'last_win': 0
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

        # Rebuild player_sessions mapping and update player ids after removal
        new_player_sessions = {}
        for new_idx, player in enumerate(self.players):
            player['id'] = new_idx
            session_id = player.get('session_id')
            if session_id:
                new_player_sessions[session_id] = new_idx
        self.player_sessions = new_player_sessions

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
            if amount is None:
                amount = self.current_bet * 2  # Default to min raise
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
            winner['last_win'] = self.pot
            # Allow new players to join after hand completes
            self.game_started = False
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
            player['last_win'] = amount
            results.append({
                'player': player,
                'amount': amount,
                'hand': player['hand_result']['name']
            })

        # Allow new players to join after hand completes
        self.game_started = False

        return results

    def ai_action(self):
        """Simple AI for computer players."""
        import random
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
                raise_amount = getattr(self, 'ante_amount', 10) * random.randint(2, 4)
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
                'is_dealer': self.players.index(p) == self.dealer_position,
                'last_win': p.get('last_win', 0)
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

    def __init__(self, num_players=5, starting_chips=1000, ante_amount=5):
        self.ante_amount = ante_amount
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
        """Initialize a Hold'em hand: post antes, deal hole cards."""
        # Post antes from all players
        self._post_antes()

        # Deal hole cards
        self._deal_hole_cards()

        # Set first player to act (left of dealer)
        self.current_player = (self.dealer_position + 1) % len(self.players)
        self._skip_folded_players()

    def _post_antes(self):
        """All players post ante."""
        for player in self.players:
            ante = min(self.ante_amount, player['chips'])
            player['chips'] -= ante
            self.pot += ante

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
        state['ante_amount'] = self.ante_amount
        return state


# =============================================================================
# SEVEN-CARD STUD FOLLOW THE QUEEN
# =============================================================================

class StudFollowQueenGame(BasePokerGame):
    """Seven-Card Stud Follow the Queen poker game."""

    PHASES = ['third_street', 'fourth_street', 'fifth_street',
              'sixth_street', 'seventh_street', 'showdown']

    def __init__(self, num_players=5, starting_chips=1000, ante_amount=5, bring_in_amount=10, hi_lo=False, two_natural_sevens_wins=False, deal_sevens_to_michael=False):
        self.ante_amount = ante_amount
        self.bring_in_amount = bring_in_amount
        self.current_wild_rank = 'Q'  # Always starts with Queens only
        self.wild_card_history = []
        self.hi_lo = hi_lo  # Hi-Lo mode: split pot between high and low hands
        self.two_natural_sevens_wins = two_natural_sevens_wins  # Instant win with 2 natural 7s
        self.deal_sevens_to_michael = deal_sevens_to_michael  # Debug: force deal 2 sevens to Michael H
        super().__init__(num_players, starting_chips)

    def reset_game(self):
        """Reset for a new game."""
        super().reset_game()
        self.current_wild_rank = 'Q'
        self.wild_card_history = []
        # hi_lo setting persists across hands

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

        # Debug: If deal_sevens_to_michael is enabled, find Michael H and prepare 7s
        michael_player = None
        if getattr(self, 'deal_sevens_to_michael', False):
            for player in self.players:
                if player['name'] == 'Michael H':
                    michael_player = player
                    break

        # Deal Third Street: 2 down, 1 up
        newly_dealt = []
        for player in self.players:
            # 2 down cards
            if player == michael_player:
                # Force deal two 7s to Michael H's hole cards
                sevens = [c for c in self.deck if c['rank'] == '7']
                if len(sevens) >= 2:
                    # Remove two 7s from deck and give to Michael
                    for seven in sevens[:2]:
                        self.deck.remove(seven)
                        player['down_cards'].append(seven)
                else:
                    # Not enough 7s, deal normally
                    player['down_cards'].append(self.deck.pop())
                    player['down_cards'].append(self.deck.pop())
            else:
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

    def _check_two_natural_sevens(self):
        """
        Check if any player has two natural (non-wild) 7s.

        Returns:
            Player dict if a player has two natural 7s, None otherwise.
        """
        if not getattr(self, 'two_natural_sevens_wins', False):
            return None

        # Skip instant win check in debug mode (deal_sevens_to_michael)
        # This allows the game to play out normally for testing
        if getattr(self, 'deal_sevens_to_michael', False):
            return None

        # 7s are natural only if current_wild_rank is NOT '7'
        if self.current_wild_rank == '7':
            return None  # No natural 7s possible when 7s are wild

        # Check each active player
        for player in self.players:
            if player['folded']:
                continue

            # Count 7s in up cards (face up) only for instant win
            # If 7s are in the hole, let game continue to showdown
            up_cards = player.get('up_cards', [])
            sevens_face_up = sum(1 for card in up_cards if card['rank'] == '7')

            # Only trigger instant win if BOTH 7s are face up
            if sevens_face_up >= 2:
                return player

        return None

    def _handle_two_natural_sevens_win(self, winner):
        """
        Handle instant win from two natural 7s.
        Awards entire pot to winner and ends the hand.

        Returns:
            Tuple of (results list, both_sevens_face_up boolean)
        """
        amount = self.pot
        winner['chips'] += amount
        winner['last_win'] = amount
        self.pot = 0

        # End the hand
        self.game_started = False
        self.phase = 'showdown'

        # Check if both 7s are face up
        sevens_in_hole = sum(1 for card in winner.get('down_cards', []) if card['rank'] == '7')
        both_sevens_face_up = (sevens_in_hole == 0)

        # Store winner id for auto-reveal (only if both 7s are face up)
        if both_sevens_face_up:
            self.two_sevens_winner_id = winner['id']
        else:
            self.two_sevens_winner_id = None

        results = [{
            'player': winner,
            'amount': amount,
            'hand': 'Two Natural 7s',
            'win_type': 'two_natural_sevens',
            'player_id': winner['id']
        }]

        return results, both_sevens_face_up

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

            # Evaluate best HIGH hand with wild cards
            best = WildCardEvaluator.best_hand_with_wilds(all_cards, wild_ranks)

            player['hand_result'] = {
                'rank': best[0],
                'tiebreakers': best[1],
                'name': best[2],
                'best_cards': best[3] if len(best) > 3 else [],
                'wild_ranks': wild_ranks
            }

            # Evaluate LOW hand if in Hi-Lo mode
            if self.hi_lo:
                low_result = LowHandEvaluator.best_low_hand_with_wilds(all_cards, wild_ranks)
                player['low_result'] = {
                    'qualifies': low_result[0],
                    'low_values': low_result[1],
                    'name': low_result[2],
                    'best_cards': low_result[3] if len(low_result) > 3 else []
                }

    def determine_winners(self):
        """
        Determine winners and distribute pot.
        In Hi-Lo mode, split pot between best high and best qualifying low.
        If no one qualifies for low, high hand wins entire pot.
        """
        active = self.get_active_players()

        if len(active) == 1:
            # Everyone else folded
            winner = active[0]
            winner['chips'] += self.pot
            winner['last_win'] = self.pot
            self.game_started = False
            return [{'player': winner, 'amount': self.pot, 'hand': None, 'win_type': 'fold'}]

        # Check for two natural 7s winner at showdown
        if getattr(self, 'two_natural_sevens_wins', False) and self.current_wild_rank != '7':
            for player in active:
                all_cards = player.get('down_cards', []) + player.get('up_cards', [])
                seven_count = sum(1 for card in all_cards if card['rank'] == '7')
                if seven_count >= 2:
                    # This player wins with two natural 7s
                    amount = self.pot
                    self.pot = 0
                    player['chips'] += amount
                    player['last_win'] = amount
                    player['cards_revealed'] = True  # Reveal their cards
                    self.game_started = False
                    # Store for special win type detection
                    return [{
                        'player': player,
                        'amount': amount,
                        'hand': 'Two Natural 7s',
                        'win_type': 'two_natural_sevens',
                        'player_id': player['id']
                    }]

        # Evaluate all hands
        self._evaluate_hands()

        # Find best HIGH hand(s)
        best_high_players = []
        best_high_hand = None

        for player in active:
            hr = player['hand_result']
            player_hand = (hr['rank'], hr['tiebreakers'])

            if best_high_hand is None:
                best_high_hand = player_hand
                best_high_players = [player]
            else:
                comparison = HandEvaluator.compare_hands(player_hand, best_high_hand)
                if comparison > 0:
                    best_high_hand = player_hand
                    best_high_players = [player]
                elif comparison == 0:
                    best_high_players.append(player)

        # If not Hi-Lo mode, high hand wins entire pot
        if not self.hi_lo:
            share = self.pot // len(best_high_players)
            remainder = self.pot % len(best_high_players)

            results = []
            for i, player in enumerate(best_high_players):
                amount = share + (1 if i < remainder else 0)
                player['chips'] += amount
                player['last_win'] = amount
                results.append({
                    'player': player,
                    'amount': amount,
                    'hand': player['hand_result']['name'],
                    'win_type': 'high'
                })

            self.game_started = False
            return results

        # Hi-Lo mode: Find best qualifying LOW hand(s)
        best_low_players = []
        best_low_hand = None

        for player in active:
            lr = player.get('low_result')
            if lr and lr['qualifies']:
                player_low = (lr['qualifies'], lr['low_values'])

                if best_low_hand is None:
                    best_low_hand = player_low
                    best_low_players = [player]
                else:
                    comparison = LowHandEvaluator.compare_low_hands(player_low, best_low_hand)
                    if comparison > 0:
                        best_low_hand = player_low
                        best_low_players = [player]
                    elif comparison == 0:
                        best_low_players.append(player)

        results = []

        if not best_low_players:
            # No qualifying low - high hand scoops entire pot
            share = self.pot // len(best_high_players)
            remainder = self.pot % len(best_high_players)

            for i, player in enumerate(best_high_players):
                amount = share + (1 if i < remainder else 0)
                player['chips'] += amount
                player['last_win'] = amount
                results.append({
                    'player': player,
                    'amount': amount,
                    'hand': player['hand_result']['name'],
                    'win_type': 'high (scoops - no qualifying low)'
                })
        else:
            # Split pot between high and low
            high_pot = self.pot // 2
            low_pot = self.pot - high_pot  # Low gets extra chip if odd

            # Distribute high half
            high_share = high_pot // len(best_high_players)
            high_remainder = high_pot % len(best_high_players)

            for i, player in enumerate(best_high_players):
                amount = high_share + (1 if i < high_remainder else 0)
                player['chips'] += amount
                player['last_win'] = amount
                results.append({
                    'player': player,
                    'amount': amount,
                    'hand': player['hand_result']['name'],
                    'win_type': 'high'
                })

            # Distribute low half
            low_share = low_pot // len(best_low_players)
            low_remainder = low_pot % len(best_low_players)

            for i, player in enumerate(best_low_players):
                amount = low_share + (1 if i < low_remainder else 0)
                player['chips'] += amount
                player['last_win'] = player.get('last_win', 0) + amount  # Add to existing (for scoops)

                # Check if this player also won high (scoop!)
                already_won_high = any(r['player'] == player and r['win_type'] == 'high' for r in results)
                if already_won_high:
                    # Update existing result to show scoop
                    for r in results:
                        if r['player'] == player and r['win_type'] == 'high':
                            r['amount'] += amount
                            r['win_type'] = 'SCOOP (high + low)'
                            r['low_hand'] = player['low_result']['name']
                            break
                else:
                    results.append({
                        'player': player,
                        'amount': amount,
                        'hand': player['low_result']['name'],
                        'win_type': 'low'
                    })

        self.game_started = False
        return results

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
                'is_dealer': self.players.index(p) == self.dealer_position,
                'last_win': p.get('last_win', 0)
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
                if p.get('low_result'):
                    player_data['low_result'] = p['low_result']
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
            'bring_in_amount': self.bring_in_amount,
            'hi_lo': self.hi_lo,
            'two_natural_sevens_wins': getattr(self, 'two_natural_sevens_wins', False),
            'deal_sevens_to_michael': getattr(self, 'deal_sevens_to_michael', False)
        }
