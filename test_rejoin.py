"""Test joining game after a hand ends."""
import socketio
import time

print('Testing: Join game after hand completes')
print('=' * 60)

sio1 = socketio.Client(logger=False, engineio_logger=False)
sio2 = socketio.Client(logger=False, engineio_logger=False)
sio3 = socketio.Client(logger=False, engineio_logger=False)
sio4 = socketio.Client(logger=False, engineio_logger=False)  # Late joiner

game_state = None
hands_completed = 0
join_messages = []

@sio1.on('game_state')
def on_state(state):
    global game_state
    game_state = state

@sio1.on('join_success')
def j1(d):
    join_messages.append(f"Bot 1 joined successfully")
    print(f'Bot 1 joined')

@sio2.on('join_success')
def j2(d):
    join_messages.append(f"Bot 2 joined successfully")
    print(f'Bot 2 joined')

@sio3.on('join_success')
def j3(d):
    join_messages.append(f"Bot 3 joined successfully")
    print(f'Bot 3 joined')

@sio4.on('join_success')
def j4(d):
    join_messages.append(f"Late Joiner joined successfully AFTER hand!")
    print(f'*** Late Joiner joined AFTER hand completed! ***')

@sio4.on('join_failed')
def j4_fail(d):
    join_messages.append(f"Late Joiner FAILED: {d.get('message')}")
    print(f'Late Joiner failed: {d.get("message")}')

@sio1.on('winners')
def on_win(data):
    global hands_completed
    hands_completed += 1
    print(f'\n*** HAND {hands_completed} COMPLETE ***')
    for w in data['winners']:
        print(f'  {w["player"]["name"]} wins ${w["amount"]:.2f}')

try:
    # Connect all clients
    sio1.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.2)
    sio2.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.2)
    sio3.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.2)
    sio4.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.5)

    # Create game
    sio1.emit('new_game', {'game_mode': 'stud_follow_queen', 'num_players': 8})
    time.sleep(0.5)

    # Join first 3 players
    print('\n--- Phase 1: Initial players join ---')
    sio1.emit('join_game', {'name': 'Bot 1'})
    time.sleep(0.3)
    sio2.emit('join_game', {'name': 'Bot 2'})
    time.sleep(0.3)
    sio3.emit('join_game', {'name': 'Bot 3'})
    time.sleep(1)

    # Start game
    print('\n--- Phase 2: Start game ---')
    sio1.emit('start_game')

    # Wait for hand to complete
    print('Waiting for hand to complete...')
    for _ in range(45):
        time.sleep(1)
        if hands_completed >= 1:
            break

    time.sleep(2)

    # Now try to join with 4th player AFTER hand completes
    print('\n--- Phase 3: Late joiner tries to join AFTER hand ---')
    sio4.emit('join_game', {'name': 'Late Joiner'})
    time.sleep(2)

    # Summary
    print('\n' + '=' * 60)
    print('TEST RESULTS:')
    print('=' * 60)
    for msg in join_messages:
        status = "PASS" if "successfully" in msg else "FAIL"
        print(f'  [{status}] {msg}')

    # Check if late joiner succeeded
    late_success = any("Late Joiner joined successfully" in m for m in join_messages)
    print('\n' + '=' * 60)
    if late_success:
        print('TEST PASSED: Players can join after hand completes!')
    else:
        print('TEST FAILED: Late joiner could not join after hand')
    print('=' * 60)

finally:
    sio1.disconnect()
    sio2.disconnect()
    sio3.disconnect()
    sio4.disconnect()
