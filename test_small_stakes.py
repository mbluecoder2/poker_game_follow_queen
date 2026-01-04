"""Test bots with small stakes."""
import socketio
import time

print('Testing SMART bots with small stakes...')
print('Buy-in: $10.00 | Ante: $0.05 | Bring-in: $0.10')
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

    sio1.emit('new_game', {'game_mode': 'stud_follow_queen', 'num_players': 8})
    time.sleep(0.5)

    sio1.emit('join_game', {'name': 'Bot 1'})
    time.sleep(0.3)
    sio2.emit('join_game', {'name': 'Bot 2'})
    time.sleep(0.3)
    sio3.emit('join_game', {'name': 'Bot 3'})
    time.sleep(1)

    print('\nStarting all-bot game...')
    print('(Check server console for bot reasoning)')
    print('=' * 60)

    sio1.emit('start_game')

    # Wait for hand to complete
    for _ in range(45):
        time.sleep(1)
        if hands_completed >= 1:
            break

    time.sleep(2)

    print('\n' + '=' * 60)
    print('FINAL RESULTS:')
    if game_state and game_state.get('players'):
        for p in game_state['players']:
            f = ' (folded)' if p.get('folded') else ''
            print(f'  {p["name"]}: ${p["chips"]:.2f}{f}')
    print('=' * 60)

finally:
    sio1.disconnect()
    sio2.disconnect()
    sio3.disconnect()
