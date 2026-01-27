"""
Card utilities and hand evaluation classes for poker games.
"""

import random
from itertools import combinations
from collections import Counter

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
    """ Evaluates poker hands with wild cards. """

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
# LOW HAND EVALUATION (FOR HI-LO GAMES)
# =============================================================================

class LowHandEvaluator:
    """
    Evaluates poker hands for low (8-or-better qualifying).

    Rules:
    - Aces count as low (A = 1)
    - Straights and flushes don't count against you
    - No pairs allowed - all 5 cards must be different ranks
    - All 5 cards must be 8 or lower to qualify
    - Best low is A-2-3-4-5 ("The Wheel")
    - Hands are compared from highest card down
    """

    # Map ranks to low values (A=1, 2=2, ..., 8=8)
    LOW_RANK_VALUES = {
        'A': 1, '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
        '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13
    }

    @staticmethod
    def card_low_value(card):
        """Get low value of a card (A=1, 2=2, etc.)."""
        return LowHandEvaluator.LOW_RANK_VALUES.get(card['rank'], 99)

    @staticmethod
    def evaluate_low(cards):
        """
        Evaluate a 5-card hand for low.

        Returns:
            (qualifies, low_values, display_name) where:
            - qualifies: True if hand qualifies for low (8-or-better, no pairs)
            - low_values: Tuple of card values sorted high to low for comparison
                          Lower tuple = better low hand
            - display_name: String description like "8-6-4-3-A low"
        """
        if len(cards) != 5:
            return (False, (99, 99, 99, 99, 99), "No Low")

        # Get low values for all cards
        low_values = [LowHandEvaluator.card_low_value(c) for c in cards]

        # Check for pairs (all cards must be different ranks)
        ranks = [c['rank'] for c in cards]
        if len(set(ranks)) != 5:
            return (False, (99, 99, 99, 99, 99), "No Low (paired)")

        # Check 8-or-better qualifier
        if max(low_values) > 8:
            return (False, (99, 99, 99, 99, 99), "No Low (9+ card)")

        # Sort values from high to low for comparison
        sorted_values = tuple(sorted(low_values, reverse=True))

        # Build display name
        rank_names = {1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8'}
        display = '-'.join(rank_names.get(v, str(v)) for v in sorted_values)

        # Special names for common lows
        if sorted_values == (5, 4, 3, 2, 1):
            display_name = "The Wheel (A-2-3-4-5)"
        elif sorted_values == (6, 4, 3, 2, 1):
            display_name = "Six-Four Low"
        elif sorted_values == (6, 5, 3, 2, 1) or sorted_values == (6, 5, 4, 2, 1) or sorted_values == (6, 5, 4, 3, 1):
            display_name = f"Six Low ({display})"
        elif sorted_values[0] == 7:
            display_name = f"Seven Low ({display})"
        elif sorted_values[0] == 8:
            display_name = f"Eight Low ({display})"
        else:
            display_name = f"{display} Low"

        return (True, sorted_values, display_name)

    @staticmethod
    def best_low_hand(all_cards):
        """
        Find the best qualifying low hand from available cards.

        Args:
            all_cards: List of cards (typically 7 in stud)

        Returns:
            (qualifies, low_values, display_name, best_5_cards) or
            (False, (99,99,99,99,99), "No Low", None) if no qualifying low
        """
        best_low = None
        best_cards = None

        for combo in combinations(all_cards, 5):
            combo_list = list(combo)
            qualifies, low_values, display_name = LowHandEvaluator.evaluate_low(combo_list)

            if qualifies:
                if best_low is None or low_values < best_low[1]:
                    best_low = (qualifies, low_values, display_name)
                    best_cards = combo_list

        if best_low is None:
            return (False, (99, 99, 99, 99, 99), "No Low", None)

        return (*best_low, best_cards)

    @staticmethod
    def best_low_hand_with_wilds(all_cards, wild_ranks):
        """
        Find the best qualifying low hand with wild cards.
        Wild cards can substitute for any card to make a low.

        Args:
            all_cards: List of cards (typically 7 in stud)
            wild_ranks: List of ranks that are wild (e.g., ['Q', '7'])

        Returns:
            (qualifies, low_values, display_name, best_5_cards)
        """
        if not wild_ranks:
            return LowHandEvaluator.best_low_hand(all_cards)

        best_low = None
        best_cards = None

        for combo in combinations(all_cards, 5):
            combo_list = list(combo)

            # Count wild cards in this combo
            wild_indices = [i for i, c in enumerate(combo_list) if c['rank'] in wild_ranks]
            non_wild_cards = [c for c in combo_list if c['rank'] not in wild_ranks]

            if not wild_indices:
                # No wilds, evaluate normally
                qualifies, low_values, display_name = LowHandEvaluator.evaluate_low(combo_list)
                if qualifies and (best_low is None or low_values < best_low[1]):
                    best_low = (qualifies, low_values, display_name)
                    best_cards = combo_list
            else:
                # Try to make best low with wilds
                # Get ranks already used by non-wild cards
                used_ranks = set(c['rank'] for c in non_wild_cards)
                non_wild_values = [LowHandEvaluator.card_low_value(c) for c in non_wild_cards]

                # Check if non-wild cards already disqualify (9+ card)
                if any(v > 8 for v in non_wild_values):
                    continue

                # Check for pairs among non-wild cards
                if len(used_ranks) != len(non_wild_cards):
                    continue

                # Find best available low ranks for wild cards
                # Ranks A-8 that aren't already used, sorted lowest first
                available_low_ranks = [r for r in ['A', '2', '3', '4', '5', '6', '7', '8']
                                       if r not in used_ranks]

                if len(available_low_ranks) < len(wild_indices):
                    # Not enough unique low ranks available
                    continue

                # Use the lowest available ranks for wilds
                wild_values = [LowHandEvaluator.LOW_RANK_VALUES[r] for r in available_low_ranks[:len(wild_indices)]]

                # Combine and sort
                all_values = non_wild_values + wild_values
                sorted_values = tuple(sorted(all_values, reverse=True))

                # Build display name
                rank_names = {1: 'A', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8'}
                display = '-'.join(rank_names.get(v, str(v)) for v in sorted_values)

                if sorted_values == (5, 4, 3, 2, 1):
                    display_name = "The Wheel (A-2-3-4-5)"
                elif sorted_values[0] <= 8:
                    high_card = rank_names[sorted_values[0]]
                    display_name = f"{high_card} Low ({display})"
                else:
                    display_name = f"{display} Low"

                if best_low is None or sorted_values < best_low[1]:
                    best_low = (True, sorted_values, display_name)
                    best_cards = combo_list

        if best_low is None:
            return (False, (99, 99, 99, 99, 99), "No Low", None)

        return (*best_low, best_cards)

    @staticmethod
    def compare_low_hands(low1, low2):
        """
        Compare two low hands.

        Args:
            low1, low2: Tuples of (qualifies, low_values, ...)

        Returns:
            1 if low1 is better, -1 if low2 is better, 0 for tie
        """
        # Non-qualifying hands lose to qualifying hands
        if low1[0] and not low2[0]:
            return 1
        if low2[0] and not low1[0]:
            return -1
        if not low1[0] and not low2[0]:
            return 0  # Both don't qualify

        # Both qualify - lower tuple wins
        if low1[1] < low2[1]:
            return 1
        elif low2[1] < low1[1]:
            return -1
        return 0
