"""Test Follow the Queen (Stud) layout with bots."""
import socketio
import time

print('Testing STUD layout with bots...')
print('=' * 60)

sio1 = socketio.Client(logger=False, engineio_logger=False)
sio2 = socketio.Client(logger=False, engineio_logger=False)
sio3 = socketio.Client(logger=False, engineio_logger=False)

game_state = None
hands_completed = 0

@sio1.on('game_state')
def on_state(state):
    global game_state
    game_state = state

    # Print layout-relevant info
    if state.get('players'):
        print(f"\n--- Game Mode: {state.get('game_mode')} ---")
        print(f"Phase: {state.get('phase')}")
        print(f"Wild Rank: {state.get('current_wild_rank', 'Q')}")

        for p in state['players']:
            if p.get('folded'):
                continue
            down_count = len(p.get('down_cards', []))
            up_count = len(p.get('up_cards', []))
            print(f"  {p['name']}: {down_count} down + {up_count} up cards")

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
        print(f'  {w["player"]["name"]} wins ${w["amount"]:.2f} with {w.get("hand", "?")}')

try:
    sio1.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.2)
    sio2.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.2)
    sio3.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.5)

    # Create Follow the Queen game (stud_follow_queen)
    sio1.emit('new_game', {'game_mode': 'stud_follow_queen', 'num_players': 8})
    time.sleep(0.5)

    sio1.emit('join_game', {'name': 'Bot 1'})
    time.sleep(0.3)
    sio2.emit('join_game', {'name': 'Bot 2'})
    time.sleep(0.3)
    sio3.emit('join_game', {'name': 'Bot 3'})
    time.sleep(1)

    print('\nStarting Follow the Queen game...')
    print('(Stud layout: down cards on left, up cards on right)')
    print('=' * 60)

    sio1.emit('start_game')

    # Wait for hand to complete
    for _ in range(45):
        time.sleep(1)
        if hands_completed >= 1:
            break

    time.sleep(2)

    print('\n' + '=' * 60)
    print('LAYOUT VERIFICATION:')
    if game_state:
        print(f"Game Mode: {game_state.get('game_mode')}")
        print(f"Wild Cards History: {len(game_state.get('wild_card_history', []))} changes")

        if game_state.get('players'):
            print("\nPlayer card layout:")
            for p in game_state['players']:
                down = p.get('down_cards', [])
                up = p.get('up_cards', [])
                down_str = ', '.join([f"{c.get('rank','?')}{c.get('suit','?')[0]}" if not c.get('hidden') else '??' for c in down])
                up_str = ', '.join([f"{c.get('rank','?')}{c.get('suit','?')[0]}" for c in up])
                fold_status = ' (folded)' if p.get('folded') else ''
                print(f"  {p['name']}{fold_status}:")
                print(f"    Down: [{down_str}]")
                print(f"    Up:   [{up_str}]")
    print('=' * 60)

finally:
    sio1.disconnect()
    sio2.disconnect()
    sio3.disconnect()
