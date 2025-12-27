"""Test wild cards in hand evaluation."""
import socketio
import time

def test_wild_hand():
    print("=" * 60)
    print("WILD CARD HAND EVALUATION TEST")
    print("=" * 60)

    sio1 = socketio.Client(logger=False, engineio_logger=False)
    sio2 = socketio.Client(logger=False, engineio_logger=False)

    p1_joined = False
    p2_joined = False
    p1_state = None
    p2_state = None
    p1_turn = False
    p2_turn = False
    last_phase = None
    wild_changes = []

    @sio1.on('connected')
    def on_connected1(data):
        print(f"[Alice] Connected")

    @sio2.on('connected')
    def on_connected2(data):
        print(f"[Bob] Connected")

    @sio1.on('join_success')
    def on_join1(data):
        nonlocal p1_joined
        p1_joined = True
        print(f"[Alice] Joined as player {data['player_id']}")

    @sio2.on('join_success')
    def on_join2(data):
        nonlocal p2_joined
        p2_joined = True
        print(f"[Bob] Joined as player {data['player_id']}")

    @sio1.on('game_state')
    def on_state1(state):
        nonlocal p1_state, p1_turn
        p1_state = state
        p1_turn = state.get('is_my_turn', False)

    @sio2.on('game_state')
    def on_state2(state):
        nonlocal p2_state, p2_turn
        p2_state = state
        p2_turn = state.get('is_my_turn', False)

    @sio1.on('wild_card_change')
    def on_wild_change(data):
        wild_changes.append(data)
        print(f"\n*** WILD CARD CHANGE: {data.get('new_wild_rank', '?')}s are now wild! ***")

    @sio1.on('winners')
    def on_winners1(data):
        print(f"\n*** WINNERS ***")
        for w in data['winners']:
            print(f"    {w['player']['name']} wins ${w['amount']} with {w.get('hand', 'unknown')}")

    @sio1.on('error')
    def on_error1(data):
        pass

    @sio2.on('error')
    def on_error2(data):
        pass

    def analyze_alice_hand():
        """Analyze Alice's cards for wild cards."""
        if not p1_state or not p1_state.get('players'):
            return

        alice = p1_state['players'][0]
        down = alice.get('down_cards', [])
        up = alice.get('up_cards', [])
        wild_rank = p1_state.get('current_wild_rank', 'Q')

        all_cards = []
        wild_count = 0

        # Collect down cards
        for c in down:
            if c.get('rank') and c.get('rank') != '?':
                rank = c.get('rank')
                suit = c.get('suit', '?')[0]
                is_wild = rank == 'Q' or rank == wild_rank
                all_cards.append(f"[{rank}{suit}]{'*' if is_wild else ''}")
                if is_wild:
                    wild_count += 1

        # Collect up cards
        for c in up:
            rank = c.get('rank', '?')
            suit = c.get('suit', '?')[0]
            is_wild = rank == 'Q' or rank == wild_rank
            all_cards.append(f"[{rank}{suit}]{'*' if is_wild else ''}")
            if is_wild:
                wild_count += 1

        print(f"    Wild Rank: {wild_rank}s (Queens always wild)")
        print(f"    Cards: {' '.join(all_cards)}")
        print(f"    Wild cards: {wild_count}")

    def get_valid_action(state, player_idx):
        if not state or not state.get('players'):
            return 'call'
        current_bet = state.get('current_bet', 0)
        players = state.get('players', [])
        if player_idx < len(players):
            player = players[player_idx]
            player_bet = player.get('current_bet', 0)
            if current_bet > player_bet:
                return 'call'
        return 'check'

    try:
        # Connect both players
        print("\n--- Connecting players ---")
        sio1.connect('http://127.0.0.1:5000', wait_timeout=10)
        time.sleep(0.3)
        sio2.connect('http://127.0.0.1:5000', wait_timeout=10)
        time.sleep(0.5)

        # Join game
        print("\n--- Joining game ---")
        sio1.emit('join_game', {'name': 'Alice'})
        time.sleep(1)
        sio2.emit('join_game', {'name': 'Bob'})
        time.sleep(1.5)

        if not p1_joined or not p2_joined:
            print("ERROR: Players failed to join")
            return 1

        # Play multiple hands to catch wild cards
        hands_played = 0
        max_hands = 5

        while hands_played < max_hands:
            hands_played += 1
            print(f"\n{'='*60}")
            print(f"HAND #{hands_played}")
            print(f"{'='*60}")

            # Start game
            sio1.emit('start_game')
            time.sleep(1.5)

            last_phase = None
            max_actions = 30
            actions = 0

            while actions < max_actions:
                time.sleep(0.3)

                phase = p1_state.get('phase', '') if p1_state else ''

                if phase == 'showdown' or (p1_state and p1_state.get('round_complete')):
                    print(f"\n--- Showdown ---")
                    analyze_alice_hand()
                    break

                if phase != last_phase and (p1_turn or p2_turn):
                    phase_display = phase.replace('_', ' ').title()
                    print(f"\n--- {phase_display} ---")
                    analyze_alice_hand()
                    last_phase = phase

                if p1_turn:
                    action = get_valid_action(p1_state, 0)
                    sio1.emit('player_action', {'action': action})
                    actions += 1
                    time.sleep(0.3)
                elif p2_turn:
                    action = get_valid_action(p2_state, 1)
                    sio2.emit('player_action', {'action': action})
                    actions += 1
                    time.sleep(0.3)

            # Wait for next hand
            time.sleep(1)

            # Check if we found any wild cards
            if p1_state:
                wild_rank = p1_state.get('current_wild_rank', 'Q')
                alice = p1_state['players'][0]
                down = alice.get('down_cards', [])
                up = alice.get('up_cards', [])

                has_wild = False
                for c in down + up:
                    rank = c.get('rank', '?')
                    if rank == 'Q' or rank == wild_rank:
                        has_wild = True
                        break

                if has_wild or wild_rank != 'Q':
                    print(f"\n*** Found wild cards or Follow the Queen trigger! ***")

            # Deal new hand
            sio1.emit('new_hand')
            time.sleep(1)

        print("\n" + "=" * 60)
        print("WILD CARD TEST COMPLETE")
        print("=" * 60)
        print(f"Hands played: {hands_played}")
        print(f"Wild card changes detected: {len(wild_changes)}")
        print("\nIn browser, cards marked with * are wild.")
        print("The hand evaluation should improve when you have wild cards.")
        print("Example: A pair + 1 wild = Three of a Kind")

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        try:
            sio1.disconnect()
            sio2.disconnect()
        except:
            pass


if __name__ == "__main__":
    import sys
    sys.exit(test_wild_hand())
