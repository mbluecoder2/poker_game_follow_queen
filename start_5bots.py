""" Start a game with all 5 bots. """
import socketio
import time

# Create separate connections for each bot
bots = []
for i in range(5):
    sio = socketio.Client(logger=False, engineio_logger=False)
    bots.append(sio)

# Track joins
joined = []

def make_join_handler(name):
    def handler(d):
        joined.append(name)
        print(f"Joined: {name}")
    return handler

for i, sio in enumerate(bots):
    sio.on('join_success', make_join_handler(f'Bot {i+1}'))

# Connect all bots
print("Connecting 5 bots...")
for sio in bots:
    sio.connect('http://127.0.0.1:5000', wait_timeout=10)
    time.sleep(0.1)

time.sleep(0.3)

# Create new game from first bot
print("Creating Follow the Queen game...")
bots[0].emit('new_game', {'game_mode': 'stud_follow_queen', 'num_players': 8})
time.sleep(0.5)

# Each bot joins with their own connection
for i, sio in enumerate(bots):
    sio.emit('join_game', {'name': f'Bot {i+1}'})
    time.sleep(0.3)

time.sleep(0.5)

# Start the game
print("Starting game with 5 bots...")
bots[0].emit('start_game')
time.sleep(2)

print(f"Game started with {len(joined)} bots! Watch in browser.")

# Disconnect all
for sio in bots:
    sio.disconnect()
