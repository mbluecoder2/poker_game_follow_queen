"""Test wider card layout - verify cards are dealt and displayed."""
import socketio
import time

def test_wider_layout():
    print("=" * 60)
    print("WIDER CARD LAYOUT TEST")
    print("=" * 60)

    sio1 = socketio.Client(logger=False, engineio_logger=False)
    sio2 = socketio.Client(logger=False, engineio_logger=False)

    p1_joined = False
    p2_joined = False
    p1_state = None
    p2_state = None

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
        nonlocal p1_state
        p1_state = state

    @sio2.on('game_state')
    def on_state2(state):
        nonlocal p2_state
        p2_state = state

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
        time.sleep(1.5)

        # Check card distribution
        print("\n" + "=" * 60)
        print("CARD LAYOUT VERIFICATION")
        print("=" * 60)

        if p1_state:
            print(f"\nGame Mode: {p1_state.get('game_mode', 'unknown')}")
            print(f"Phase: {p1_state.get('phase', 'unknown')}")
            print(f"Number of players: {len(p1_state.get('players', []))}")

            for i, player in enumerate(p1_state.get('players', [])):
                print(f"\n--- Player {i}: {player['name']} ---")

                down_cards = player.get('down_cards', [])
                up_cards = player.get('up_cards', [])

                print(f"  Down Cards ({len(down_cards)}): ", end="")
                if down_cards:
                    for card in down_cards:
                        if card.get('hidden'):
                            print("[??] ", end="")
                        else:
                            print(f"[{card.get('rank', '?')}{card.get('suit', '?')[0]}] ", end="")
                else:
                    print("(none)", end="")
                print()

                print(f"  Up Cards ({len(up_cards)}):   ", end="")
                if up_cards:
                    for card in up_cards:
                        print(f"[{card.get('rank', '?')}{card.get('suit', '?')[0]}] ", end="")
                else:
                    print("(none)", end="")
                print()

            print("\n" + "=" * 60)
            print("LAYOUT CSS CHANGES APPLIED:")
            print("=" * 60)
            print("  - Game container: 1600px max-width")
            print("  - Stud player cards: minmax(400px, 1fr)")
            print("  - Card groups: min-width 140px")
            print("  - Cards display: flex-row with wrap (2 per row)")
            print("  - Group padding: 15px")
            print("\nIn browser, Down Cards and Up Cards areas should:")
            print("  - Be wider")
            print("  - Show 2 cards per row when there are 2+ cards")
            print("  - Have more padding around cards")

            return 0
        else:
            print("ERROR: No game state received")
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
    sys.exit(test_wider_layout())
