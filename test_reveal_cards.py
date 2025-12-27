"""Test click to reveal cards feature at showdown."""
import socketio
import time

def test_reveal_cards():
    print("=" * 60)
    print("CLICK TO REVEAL CARDS TEST")
    print("=" * 60)

    sio1 = socketio.Client(logger=False, engineio_logger=False)
    sio2 = socketio.Client(logger=False, engineio_logger=False)

    p1_joined = False
    p2_joined = False
    p1_state = None
    p2_state = None
    p1_turn = False
    p2_turn = False
    cards_revealed_by = []

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
        print(f"\n*** HAND COMPLETE ***")
        for w in data['winners']:
            print(f"    {w['player']['name']} wins ${w['amount']} with {w.get('hand', 'unknown')}")

    @sio1.on('cards_revealed')
    def on_cards_revealed1(data):
        cards_revealed_by.append(data['player_name'])
        print(f"\n*** {data['player_name']} REVEALED THEIR CARDS ***")
        print(f"    Down cards: ", end="")
        for card in data['cards']:
            print(f"[{card['rank']}{card['suit'][0]}] ", end="")
        print()

    @sio2.on('cards_revealed')
    def on_cards_revealed2(data):
        print(f"[Bob sees] {data['player_name']}'s cards revealed")

    @sio1.on('error')
    def on_error1(data):
        print(f"[Alice] ERROR: {data.get('message', data)}")

    @sio2.on('error')
    def on_error2(data):
        print(f"[Bob] ERROR: {data.get('message', data)}")

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

        # Start game
        print("\n--- Starting game ---")
        sio1.emit('start_game')
        time.sleep(1.5)

        # Play to showdown
        print("\n--- Playing hand to showdown ---")
        max_actions = 30
        actions = 0

        while actions < max_actions:
            time.sleep(0.3)

            phase = p1_state.get('phase', '') if p1_state else ''

            if phase == 'showdown' or (p1_state and p1_state.get('round_complete')):
                print(f"\n*** SHOWDOWN REACHED ***")
                break

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

        time.sleep(1)

        # Verify we're at showdown
        if p1_state and p1_state.get('phase') == 'showdown':
            print("\n--- Testing card reveal ---")

            # Alice reveals her cards
            print("\n[Alice] Clicking to reveal down cards...")
            sio1.emit('reveal_cards')
            time.sleep(1)

            # Bob reveals his cards
            print("\n[Bob] Clicking to reveal down cards...")
            sio2.emit('reveal_cards')
            time.sleep(1)

            print("\n" + "=" * 60)
            print("TEST RESULTS")
            print("=" * 60)

            if len(cards_revealed_by) >= 1:
                print(f"*** PASS: Cards revealed by: {', '.join(cards_revealed_by)} ***")
                print("\nIn browser:")
                print("  - At showdown, your Down Cards area shows 'Click to reveal'")
                print("  - Clicking reveals your cards to ALL other players")
                print("  - Other players see your actual down cards")
                return 0
            else:
                print("*** FAIL: No cards were revealed ***")
                return 1
        else:
            print("ERROR: Did not reach showdown")
            return 1

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
    sys.exit(test_reveal_cards())
