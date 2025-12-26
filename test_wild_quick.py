"""Quick test to find wild card changes across multiple games."""
import socketio
import time

def run_game():
    """Run one game and return wild card info."""
    players = []

    for name in ['P1', 'P2', 'P3']:
        sio = socketio.Client(logger=False, engineio_logger=False)
        result = {'name': name, 'wild_changes': [], 'wild_rank': 'Q', 'joined': False}

        def make_handlers(s, r):
            @s.on('game_state')
            def on_state(state):
                r['wild_rank'] = state.get('current_wild_rank', 'Q')
                r['wild_changes'] = state.get('wild_card_history', [])

            @s.on('connected')
            def on_conn(data):
                s.emit('join_game', {'name': r['name']})

            @s.on('join_success')
            def on_join(data):
                r['joined'] = True

        make_handlers(sio, result)
        sio.connect('http://127.0.0.1:5000', wait_timeout=5)
        players.append((sio, result))
        time.sleep(0.2)

    time.sleep(0.5)

    # Start game
    players[0][0].emit('start_game')
    time.sleep(0.5)

    # Play through betting rounds quickly
    for _ in range(30):
        for sio, r in players:
            sio.emit('player_action', {'action': 'check'})
            time.sleep(0.05)
        for sio, r in players:
            sio.emit('player_action', {'action': 'call'})
            time.sleep(0.05)

    time.sleep(0.3)

    # Get results
    wild_rank = players[0][1]['wild_rank']
    wild_changes = players[0][1]['wild_changes']

    # Cleanup
    for sio, _ in players:
        try:
            sio.disconnect()
        except:
            pass

    return wild_rank, wild_changes


print("Running 10 games to find wild card changes...")
print("-" * 50)

total_changes = 0
for i in range(10):
    wild_rank, changes = run_game()
    change_count = len(changes)
    total_changes += change_count

    if change_count > 0:
        print(f"Game {i+1}: WILD CHANGED! Final wild: {wild_rank}")
        for c in changes:
            print(f"  - {c.get('phase')}: Queen dealt by {c.get('player_name')} -> {c.get('new_wild_rank')}s wild")
    else:
        print(f"Game {i+1}: No changes (wild = Q)")

    time.sleep(0.5)

print("-" * 50)
print(f"Total wild card changes across 10 games: {total_changes}")
