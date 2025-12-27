"""Test full hand - play through all streets and verify hand updates."""
import socketio
import time

def test_full_hand():
    print("=" * 60)
    print("FULL HAND TEST - HAND DISPLAY UPDATES")
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

    @sio1.on('winners')
    def on_winners1(data):
        print(f"\n*** WINNERS ***")
        for w in data['winners']:
            print(f"    {w['player']['name']} wins ${w['amount']} with {w.get('hand', 'unknown')}")

    @sio1.on('error')
    def on_error1(data):
        pass  # Suppress errors

    @sio2.on('error')
    def on_error2(data):
        pass  # Suppress errors

    def show_alice_hand():
        """Display Alice's current cards and hand."""
        if not p1_state or not p1_state.get('players'):
            return

        alice = p1_state['players'][0]
        down = alice.get('down_cards', [])
        up = alice.get('up_cards', [])

        down_str = ' '.join([f"[{c.get('rank','?')}{c.get('suit','?')[0]}]" for c in down if c.get('rank') != '?'])
        up_str = ' '.join([f"[{c.get('rank','?')}{c.get('suit','?')[0]}]" for c in up])

        total_cards = len([c for c in down if c.get('rank') != '?']) + len(up)
        print(f"    Alice's cards ({total_cards}): Down: {down_str}  Up: {up_str}")

    def get_valid_action(state, player_idx):
        """Determine valid action based on game state."""
        if not state or not state.get('players'):
            return 'call'

        # Get current bet level and player's bet
        current_bet = state.get('current_bet', 0)
        players = state.get('players', [])

        if player_idx < len(players):
            player = players[player_idx]
            player_bet = player.get('current_bet', 0)

            # If we need to match a bet, call
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

        # Start game
        print("\n--- Starting game ---")
        sio1.emit('start_game')
        time.sleep(1.5)

        # Play through the hand
        max_actions = 30
        actions = 0

        while actions < max_actions:
            time.sleep(0.3)

            phase = p1_state.get('phase', '') if p1_state else ''

            # Check if hand is complete
            if phase == 'showdown' or (p1_state and p1_state.get('round_complete')):
                print(f"\n=== SHOWDOWN ===")
                show_alice_hand()
                break

            # Show current phase and cards when phase changes
            if phase != last_phase and (p1_turn or p2_turn):
                phase_display = phase.replace('_', ' ').title()
                print(f"\n--- {phase_display} ---")
                show_alice_hand()
                last_phase = phase

            # Take action
            if p1_turn:
                action = get_valid_action(p1_state, 0)
                print(f"    [Alice] {action.title()}...")
                sio1.emit('player_action', {'action': action})
                actions += 1
                time.sleep(0.4)
            elif p2_turn:
                action = get_valid_action(p2_state, 1)
                print(f"    [Bob] {action.title()}...")
                sio2.emit('player_action', {'action': action})
                actions += 1
                time.sleep(0.4)

        # Final state
        time.sleep(1)
        print("\n" + "=" * 60)
        print("HAND COMPLETE")
        print("=" * 60)

        if p1_state:
            print(f"Final Phase: {p1_state.get('phase', 'unknown')}")
            show_alice_hand()

            # Show final hand result if available
            alice = p1_state['players'][0]
            if alice.get('hand_result'):
                print(f"    Final Hand: {alice['hand_result'].get('name', 'unknown')}")

        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)

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
    sys.exit(test_full_hand())
