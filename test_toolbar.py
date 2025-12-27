"""Test floating toolbar with 2 players."""
import socketio
import time

class TestPlayer:
    def __init__(self, name):
        self.name = name
        self.sio = socketio.Client(logger=False, engineio_logger=False)
        self.joined = False
        self.is_my_turn = False
        self.game_state = None
        self.phase = None

        self.sio.on('connected', self.on_connected)
        self.sio.on('join_success', self.on_join_success)
        self.sio.on('game_state', self.on_game_state)
        self.sio.on('error', self.on_error)

    def on_connected(self, data):
        print(f"[{self.name}] Connected")

    def on_join_success(self, data):
        self.joined = True
        print(f"[{self.name}] Joined as player {data['player_id']}")

    def on_game_state(self, state):
        self.game_state = state
        self.is_my_turn = state.get('is_my_turn', False)
        self.phase = state.get('phase', '?')

    def on_error(self, data):
        print(f"[{self.name}] ERROR: {data}")

    def connect(self):
        self.sio.connect('http://127.0.0.1:5000', wait_timeout=10)
        time.sleep(0.3)

    def join(self):
        self.sio.emit('join_game', {'name': self.name})
        time.sleep(0.5)

    def start_game(self):
        self.sio.emit('start_game')
        time.sleep(1)

    def action(self, action_type):
        print(f"[{self.name}] Taking action: {action_type}")
        self.sio.emit('player_action', {'action': action_type})
        time.sleep(0.5)

    def disconnect(self):
        if self.sio.connected:
            self.sio.disconnect()


def main():
    print("=" * 60)
    print("FLOATING TOOLBAR TEST - 2 PLAYERS")
    print("=" * 60)

    p1 = TestPlayer("Alice")
    p2 = TestPlayer("Bob")

    try:
        # Connect and join
        print("\n--- Connecting players ---")
        p1.connect()
        p2.connect()
        time.sleep(0.5)

        print("\n--- Joining game ---")
        p1.join()
        p2.join()
        time.sleep(1)

        if not p1.joined or not p2.joined:
            print("ERROR: Players failed to join")
            return 1

        # Start game
        print("\n--- Starting game ---")
        p1.start_game()
        time.sleep(1)

        # Check who has the action
        print("\n--- Checking turn status ---")
        print(f"Phase: {p1.phase}")

        rounds = 0
        max_rounds = 10

        while rounds < max_rounds:
            time.sleep(0.3)

            # Check current state
            if p1.game_state and p1.game_state.get('round_complete'):
                print(f"\nRound complete at phase: {p1.phase}")
                break

            if p1.is_my_turn:
                print(f"\n*** ALICE'S TURN *** (Phase: {p1.phase})")
                print("    -> Floating toolbar should be VISIBLE for Alice")
                print("    -> Floating toolbar should be HIDDEN for Bob")
                p1.action('check')
                rounds += 1
            elif p2.is_my_turn:
                print(f"\n*** BOB'S TURN *** (Phase: {p2.phase})")
                print("    -> Floating toolbar should be VISIBLE for Bob")
                print("    -> Floating toolbar should be HIDDEN for Alice")
                p2.action('check')
                rounds += 1
            else:
                time.sleep(0.2)

        print("\n" + "=" * 60)
        print("TEST COMPLETE")
        print("=" * 60)
        print(f"Rounds played: {rounds}")
        print("\nThe floating toolbar should appear:")
        print("  - At the bottom center of the screen")
        print("  - With a '🎯 YOUR TURN' header")
        print("  - With Fold, Check, Raise, All In buttons")
        print("  - Only when it's that player's turn")

        return 0

    finally:
        p1.disconnect()
        p2.disconnect()


if __name__ == "__main__":
    import sys
    sys.exit(main())
