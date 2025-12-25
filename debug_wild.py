"""Debug wild card evaluation."""
import sys
sys.path.insert(0, 'M:\\Projects\\poker_game - Follow-Queen')

from app import WildCardEvaluator, HandEvaluator

# Test with 4 Aces + 1 Queen (wild)
test_cards = [
    {'rank': 'Q', 'suit': 'hearts', 'symbol': '♥'},  # Wild
    {'rank': 'A', 'suit': 'spades', 'symbol': '♠'},
    {'rank': 'A', 'suit': 'hearts', 'symbol': '♥'},
    {'rank': 'A', 'suit': 'diamonds', 'symbol': '♦'},
    {'rank': 'A', 'suit': 'clubs', 'symbol': '♣'},
]

print("Test hand: 4 Aces + 1 Queen (wild)")
print("Expected: Five of a Kind (rank 11)")
print()

# Test the expansion
wild_ranks = ['Q']
expansions = WildCardEvaluator.expand_wild_cards(test_cards, wild_ranks)
print(f"Generated {len(expansions)} possible hands")
print()

# Evaluate a few
print("First 3 expanded hands:")
for i, hand in enumerate(expansions[:3]):
    result = HandEvaluator.evaluate_five(hand)
    print(f"  Hand {i+1}: {result[2]} (rank {result[0]})")
    print(f"    Cards: {[c['rank'] + c['suit'][0] for c in hand]}")

print()
print("The problem:")
print("  We have all 4 Aces, so the Queen can't become a 5th Ace")
print("  because there are only 4 Aces in a deck!")
print()
print("Solution: Special handling for 'impossible' Five of a Kind")
