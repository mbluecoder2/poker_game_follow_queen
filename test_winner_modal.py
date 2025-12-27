"""Test Winner Modal 16-second countdown."""
import socketio
import time

def test_winner_modal():
    print("=" * 60)
    print("WINNER MODAL 16-SECOND COUNTDOWN TEST")
    print("=" * 60)

    sio1 = socketio.Client(logger=False, engineio_logger=False)
    sio2 = socketio.Client(logger=False, engineio_logger=False)

    p1_joined = False
    p2_joined = False
    p1_turn = False
    p2_turn = False
    winner_received = False
    winner_data = None

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

    @sio1.on('winners')
    def on_winners1(data):
        nonlocal winner_received, winner_data
        winner_received = True
        winner_data = data
        print(f"\n*** WINNER EVENT RECEIVED ***")
        for w in data['winners']:
            print(f"    Winner: {w['player']['name']} wins ${w['amount']}")
            if w.get('hand'):
                print(f"    Hand: {w['hand']}")

    @sio1.on('game_state')
    def on_state1(state):
        nonlocal p1_turn
        p1_turn = state.get('is_my_turn', False)

    @sio2.on('game_state')
    def on_state2(state):
        nonlocal p2_turn
        p2_turn = state.get('is_my_turn', False)

    @sio1.on('error')
    def on_error1(data):
        print(f"[Alice] ERROR: {data}")

    @sio2.on('error')
    def on_error2(data):
        print(f"[Bob] ERROR: {data}")

    try:
        # Connect both players
        print("\n--- Connecting players ---")
        sio1.connect('http://127.0.0.1:5000', wait_timeout=10)
        sio2.connect('http://127.0.0.1:5000', wait_timeout=10)
        time.sleep(0.5)

        # Join game
        print("\n--- Joining game ---")
        sio1.emit('join_game', {'name': 'Alice'})
        time.sleep(0.5)
        sio2.emit('join_game', {'name': 'Bob'})
        time.sleep(1)

        if not p1_joined or not p2_joined:
            print("ERROR: Players failed to join")
            return 1

        # Start game
        print("\n--- Starting game ---")
        sio1.emit('start_game')
        time.sleep(1)

        # Check who has the turn and have them fold
        print("\n--- Active player FOLDS to trigger winner ---")
        if p1_turn:
            print("[Alice] has the action - FOLDING")
            sio1.emit('player_action', {'action': 'fold'})
        elif p2_turn:
            print("[Bob] has the action - FOLDING")
            sio2.emit('player_action', {'action': 'fold'})
        else:
            print("WARNING: Neither player has the turn yet, waiting...")
            time.sleep(1)
            if p1_turn:
                sio1.emit('player_action', {'action': 'fold'})
            elif p2_turn:
                sio2.emit('player_action', {'action': 'fold'})

        time.sleep(2)

        # Check results
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)

        if winner_received:
            print("*** PASS: Winner event received! ***")
            print("\nIn the browser, you should see:")
            print("  1. Winner modal appears with winner details")
            print("  2. Close button shows 'Wait 16s...' and is DISABLED")
            print("  3. Countdown decrements every second (15, 14, 13...)")
            print("  4. After 16 seconds, button becomes 'Close' and is ENABLED")
            print("  5. Modal only closes when user clicks the button")
            return 0
        else:
            print("*** FAIL: No winner event received ***")
            return 1

    except Exception as e:
        print(f"\nError: {e}")
        return 1

    finally:
        try:
            sio1.disconnect()
            sio2.disconnect()
        except:
            pass


if __name__ == "__main__":
    import sys
    sys.exit(test_winner_modal())
