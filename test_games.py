"""Quick test script to verify both game modes work."""
import sys
import os
sys.path.insert(0, 'M:\\Projects\\poker_game - Follow-Queen')

# Set UTF-8 encoding for Windows console
if os.name == 'nt':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

from app import HoldemGame, StudFollowQueenGame, WildCardEvaluator

print("=" * 60)
print("Testing Follow the Queen Implementation")
print("=" * 60)

# Test 1: Create Hold'em game
print("\n[+] Test 1: Creating Texas Hold'em game...")
holdem = HoldemGame(num_players=4, starting_chips=1000, small_blind=10, big_blind=20)
holdem.add_player('session1', 'Alice')
holdem.add_player('session2', 'Bob')
print(f"  Players: {len(holdem.players)}")
print(f"  Game mode: {holdem.get_state()['game_mode']}")
print(f"  Phases: {holdem.PHASES}")
assert len(holdem.players) == 2
assert holdem.get_state()['game_mode'] == 'holdem'
print("  [OK] Hold'em game created successfully!")

# Test 2: Create Follow the Queen game
print("\n[+] Test 2: Creating Follow the Queen game...")
ftq = StudFollowQueenGame(num_players=4, starting_chips=1000, ante_amount=5, bring_in_amount=10)
ftq.add_player('session1', 'Charlie')
ftq.add_player('session2', 'Diana')
print(f"  Players: {len(ftq.players)}")
print(f"  Game mode: {ftq.get_state()['game_mode']}")
print(f"  Phases: {ftq.PHASES}")
print(f"  Current wild rank: {ftq.current_wild_rank}")
assert len(ftq.players) == 2
assert ftq.get_state()['game_mode'] == 'stud_follow_queen'
assert ftq.current_wild_rank == 'Q'
print("  [OK] Follow the Queen game created successfully!")

# Test 3: Test wild card evaluation
print("\n[+] Test 3: Testing wild card hand evaluation...")
test_cards = [
    {'rank': 'Q', 'suit': 'hearts', 'symbol': '♥'},  # Wild
    {'rank': 'A', 'suit': 'spades', 'symbol': '♠'},
    {'rank': 'A', 'suit': 'hearts', 'symbol': '♥'},
    {'rank': 'A', 'suit': 'diamonds', 'symbol': '♦'},
    {'rank': 'A', 'suit': 'clubs', 'symbol': '♣'},
    {'rank': '2', 'suit': 'hearts', 'symbol': '♥'},
    {'rank': '3', 'suit': 'hearts', 'symbol': '♥'}
]

wild_ranks = ['Q']
result = WildCardEvaluator.best_hand_with_wilds(test_cards, wild_ranks)
print(f"  Hand rank: {result[0]} (11 = Five of a Kind)")
print(f"  Hand name: {result[2]}")
assert result[0] == 11  # Five of a Kind
assert result[2] == 'Five of a Kind'
print("  [OK] Five of a Kind detected correctly!")

# Test 4: Test Stud dealing
print("\n[+] Test 4: Testing Stud card dealing...")
ftq.game_started = True
ftq.new_hand()
for player in ftq.players:
    print(f"  {player['name']}: {len(player['down_cards'])} down, {len(player['up_cards'])} up")
    assert len(player['down_cards']) == 2  # Third street: 2 down
    assert len(player['up_cards']) == 1    # Third street: 1 up
print("  [OK] Third street dealing correct!")

# Test 5: Test wild card tracking
print("\n[+] Test 5: Testing wild card tracking...")
print(f"  Initial wild rank: {ftq.current_wild_rank}")
print(f"  Wild card history entries: {len(ftq.wild_card_history)}")
print("  [OK] Wild card tracking initialized!")

# Test 6: Test Hold'em dealing
print("\n[+] Test 6: Testing Hold'em dealing...")
holdem.game_started = True
holdem.new_hand()
for player in holdem.players:
    print(f"  {player['name']}: {len(player['hole_cards'])} hole cards")
    assert len(player['hole_cards']) == 2
print(f"  Community cards: {len(holdem.community_cards)}")
assert len(holdem.community_cards) == 0  # Pre-flop
print("  [OK] Hold'em dealing correct!")

print("\n" + "=" * 60)
print("*** ALL TESTS PASSED! ***")
print("=" * 60)
print("\n** Both game modes are working correctly!")
print("   - Texas Hold'em [OK]")
print("   - Follow the Queen [OK]")
print("   - Wild card evaluation [OK]")
print("   - Card dealing [OK]")
print("   - Wild card tracking [OK]")
