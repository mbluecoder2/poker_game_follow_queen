"""Test script for multiplayer poker game with 3 players."""
import socketio
import time
import sys

class TestPlayer:
    def __init__(self, name):
        self.name = name
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.joined = False
        self.player_id = None
        self.game_state = None
        self.error = None
        self.cards_dealt = False

        # Register event handlers
        self.sio.on('connected', self.on_connected)
        self.sio.on('join_success', self.on_join_success)
        self.sio.on('join_failed', self.on_join_failed)
        self.sio.on('game_state', self.on_game_state)
        self.sio.on('error', self.on_error)

    def on_connected(self, data):
        print(f"[{self.name}] Connected")

    def on_join_success(self, data):
        self.joined = True
        self.player_id = data['player_id']
        print(f"[{self.name}] Joined as player {self.player_id}")

    def on_join_failed(self, data):
        self.error = data['message']
        print(f"[{self.name}] Join FAILED: {self.error}")

    def on_game_state(self, state):
        self.game_state = state
        players = len(state.get('players', []))
        phase = state.get('phase', '?')
        started = state.get('game_started', False)

        # Find my cards
        my_down = 0
        my_up = 0
        for p in state.get('players', []):
            if p.get('name') == self.name:
                my_down = len(p.get('down_cards', []))
                my_up = len(p.get('up_cards', []))
                if my_down > 0 or my_up > 0:
                    self.cards_dealt = True
                break

        print(f"[{self.name}] State: {players} players, phase={phase}, started={started}, cards={my_down}down/{my_up}up")

    def on_error(self, data):
        self.error = data.get('message', str(data))
        print(f"[{self.name}] ERROR: {self.error}")

    def connect(self):
        self.sio.connect('http://127.0.0.1:5000', wait_timeout=10)
        time.sleep(0.3)

    def join(self):
        self.sio.emit('join_game', {'name': self.name})
        time.sleep(0.5)

    def start_game(self):
        print(f"[{self.name}] Sending start_game...")
        self.sio.emit('start_game')
        time.sleep(1)

    def disconnect(self):
        if self.sio.connected:
            self.sio.disconnect()


def main():
    print("=" * 50)
    print("MULTIPLAYER POKER TEST - 3 PLAYERS")
    print("=" * 50)

    # Create 3 test players
    players = [
        TestPlayer("Test_Alice"),
        TestPlayer("Test_Bob"),
        TestPlayer("Test_Carol")
    ]

    try:
        # Phase 1: Connect all players
        print("\n--- PHASE 1: Connecting ---")
        for p in players:
            p.connect()
        time.sleep(1)

        # Phase 2: Join all players
        print("\n--- PHASE 2: Joining Game ---")
        for p in players:
            p.join()
        time.sleep(1)

        # Check joins
        joined_count = sum(1 for p in players if p.joined)
        print(f"\nJoined: {joined_count}/3 players")

        if joined_count < 2:
            print("ERROR: Not enough players joined!")
            return 1

        # Phase 3: Start game
        print("\n--- PHASE 3: Starting Game ---")
        players[0].start_game()
        time.sleep(2)

        # Phase 4: Check results
        print("\n--- FINAL RESULTS ---")
        success = True
        for p in players:
            if p.joined:
                state = p.game_state or {}
                for player_data in state.get('players', []):
                    if player_data.get('name') == p.name:
                        down = player_data.get('down_cards', [])
                        up = player_data.get('up_cards', [])
                        total_cards = len(down) + len(up)
                        status = "OK" if total_cards > 0 else "NO CARDS"
                        print(f"  {p.name}: {len(down)} down, {len(up)} up cards - {status}")
                        if total_cards == 0:
                            success = False
                        break
            else:
                print(f"  {p.name}: FAILED TO JOIN - {p.error}")
                success = False

        if success:
            print("\n*** TEST PASSED: All players joined and received cards! ***")
            return 0
        else:
            print("\n*** TEST FAILED ***")
            return 1

    finally:
        # Cleanup
        for p in players:
            p.disconnect()


if __name__ == "__main__":
    sys.exit(main())
