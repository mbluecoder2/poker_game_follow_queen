"""Direct unit test for wild card logic - no socket.io."""
import sys
sys.path.insert(0, 'M:/Projects/poker_game - Follow-Queen')

from app import StudFollowQueenGame

def test_wild_cards():
    print("=" * 60)
    print("DIRECT WILD CARD TEST")
    print("=" * 60)

    total_games = 20
    games_with_wild_change = 0
    total_queens_dealt = 0

    for game_num in range(total_games):
        game = StudFollowQueenGame(num_players=3, starting_chips=1000, ante_amount=5, bring_in_amount=10)

        # Add players
        game.add_player('session1', 'Alice')
        game.add_player('session2', 'Bob')
        game.add_player('session3', 'Carol')

        # Start game
        game.game_started = True
        game.new_hand()

        # Count Queens in up cards at third street
        queens_in_game = 0
        for player in game.players:
            for card in player.get('up_cards', []):
                if card['rank'] == 'Q':
                    queens_in_game += 1
                    print(f"  Game {game_num+1} Third Street: {player['name']} has Q of {card['suit']} face-up")

        # Play through streets
        streets = ['fourth_street', 'fifth_street', 'sixth_street']
        for street in streets:
            # Simulate betting round completion
            game.round_complete = True
            for p in game.players:
                p['current_bet'] = 0
            game.current_bet = 0

            # Advance phase (deals cards)
            game.advance_phase()

            # Count new Queens
            for player in game.players:
                for card in player.get('up_cards', []):
                    if card['rank'] == 'Q':
                        # Check if this is a new Queen (we've seen it before)
                        pass

        # Check for Queens across all up cards
        for player in game.players:
            for card in player.get('up_cards', []):
                if card['rank'] == 'Q':
                    queens_in_game += 1

        total_queens_dealt += queens_in_game

        # Check wild card status
        if game.current_wild_rank != 'Q':
            games_with_wild_change += 1
            print(f"  Game {game_num+1}: WILD CHANGED to {game.current_wild_rank}")
            for change in game.wild_card_history:
                print(f"    - {change['phase']}: {change['player_name']} dealt Q -> {change['new_wild_rank']}s wild")
        elif game.wild_card_history:
            games_with_wild_change += 1
            print(f"  Game {game_num+1}: Wild changes occurred (final: {game.current_wild_rank})")
            for change in game.wild_card_history:
                print(f"    - {change['phase']}: {change['player_name']} dealt Q -> {change['new_wild_rank']}s wild")

    print()
    print("=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Games played: {total_games}")
    print(f"Games with wild card changes: {games_with_wild_change}")
    print(f"Total Queens dealt face-up (estimate): {total_queens_dealt}")

    if games_with_wild_change > 0:
        print("\n*** PASS: Wild card changes working! ***")
        return 0
    else:
        print("\n*** FAIL: No wild card changes detected - bug suspected ***")
        return 1


if __name__ == "__main__":
    sys.exit(test_wild_cards())
