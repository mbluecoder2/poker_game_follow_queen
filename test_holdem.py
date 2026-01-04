"""Test Texas Hold'em mode still works."""
import socketio
import time

print('Testing Texas Hold\'em mode...')
print('=' * 60)

sio1 = socketio.Client(logger=False, engineio_logger=False)
sio2 = socketio.Client(logger=False, engineio_logger=False)
sio3 = socketio.Client(logger=False, engineio_logger=False)

game_state = None
hands_completed = 0
phases_seen = set()

@sio1.on('game_state')
def on_state(state):
    global game_state
    game_state = state

    if state.get('phase'):
        phases_seen.add(state['phase'])

    # Print game info
    if state.get('players') and state.get('game_started'):
        print(f"\nGame Mode: {state.get('game_mode')} | Phase: {state.get('phase')}")

        # Show community cards for Hold'em
        comm = state.get('community_cards', [])
        if comm:
            comm_str = ', '.join([f"{c.get('rank')}{c.get('suit', '?')[0]}" for c in comm])
            print(f"Community Cards: [{comm_str}]")

        # Show player hole cards
        for p in state['players']:
            if p.get('folded'):
                continue
            holes = p.get('hole_cards', [])
            if holes:
                hole_str = ', '.join([f"{c.get('rank','?')}{c.get('suit','?')[0]}" if not c.get('hidden') else '??' for c in holes])
                print(f"  {p['name']}: [{hole_str}] - ${p['chips']:.2f}")

@sio1.on('join_success')
def j1(d): print(f'Bot 1 joined')
@sio2.on('join_success')
def j2(d): print(f'Bot 2 joined')
@sio3.on('join_success')
def j3(d): print(f'Bot 3 joined')

@sio1.on('winners')
def on_win(data):
    global hands_completed
    hands_completed += 1
    print(f'\n*** WINNER ***')
    for w in data['winners']:
        hand = w.get('hand') or 'everyone folded'
        print(f'  {w["player"]["name"]} wins ${w["amount"]:.2f} ({hand})')

try:
    sio1.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.2)
    sio2.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.2)
    sio3.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.5)

    # Create HOLDEM game (not stud_follow_queen)
    print('\nCreating Texas Hold\'em game...')
    sio1.emit('new_game', {'game_mode': 'holdem', 'num_players': 8})
    time.sleep(0.5)

    sio1.emit('join_game', {'name': 'Bot 1'})
    time.sleep(0.3)
    sio2.emit('join_game', {'name': 'Bot 2'})
    time.sleep(0.3)
    sio3.emit('join_game', {'name': 'Bot 3'})
    time.sleep(1)

    print('\nStarting Texas Hold\'em game...')
    print('=' * 60)

    sio1.emit('start_game')

    # Wait for hand to complete
    for _ in range(60):
        time.sleep(1)
        if hands_completed >= 1:
            break

    time.sleep(2)

    print('\n' + '=' * 60)
    print('TEST RESULTS:')
    print('=' * 60)
    print(f'Game Mode: {game_state.get("game_mode") if game_state else "?"}')
    print(f'Phases seen: {sorted(phases_seen)}')
    print(f'Hands completed: {hands_completed}')

    # Verify Hold'em specific features
    is_holdem = game_state and game_state.get('game_mode') == 'holdem'
    has_community = game_state and len(game_state.get('community_cards', [])) > 0
    has_hole_cards = game_state and any(len(p.get('hole_cards', [])) > 0 for p in game_state.get('players', []))

    print(f'\nHold\'em mode active: {is_holdem}')
    print(f'Has community cards: {has_community}')
    print(f'Has hole cards: {has_hole_cards}')

    if is_holdem and hands_completed > 0:
        print('\n*** TEST PASSED: Texas Hold\'em mode works! ***')
    else:
        print('\n*** TEST FAILED ***')
    print('=' * 60)

finally:
    sio1.disconnect()
    sio2.disconnect()
    sio3.disconnect()
