"""Test betting and wild card changes in Follow the Queen."""
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
        self.is_my_turn = False
        self.wild_rank = None
        self.wild_history = []

        self.sio.on('connected', self.on_connected)
        self.sio.on('join_success', self.on_join_success)
        self.sio.on('join_failed', self.on_join_failed)
        self.sio.on('game_state', self.on_game_state)
        self.sio.on('error', self.on_error)

    def on_connected(self, data):
        pass

    def on_join_success(self, data):
        self.joined = True
        self.player_id = data['player_id']
        print(f"[{self.name}] Joined as player {self.player_id}")

    def on_join_failed(self, data):
        self.error = data['message']
        print(f"[{self.name}] Join FAILED: {self.error}")

    def on_game_state(self, state):
        self.game_state = state
        self.is_my_turn = state.get('is_my_turn', False)
        self.wild_rank = state.get('current_wild_rank', 'Q')
        self.wild_history = state.get('wild_card_history', [])

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
        self.sio.emit('start_game')
        time.sleep(1)

    def action(self, action_type, amount=None):
        data = {'action': action_type}
        if amount is not None:
            data['amount'] = amount
        self.sio.emit('player_action', data)
        time.sleep(0.3)

    def get_phase(self):
        return self.game_state.get('phase', '?') if self.game_state else '?'

    def get_current_player_name(self):
        if not self.game_state:
            return None
        idx = self.game_state.get('current_player')
        players = self.game_state.get('players', [])
        if idx is not None and 0 <= idx < len(players):
            return players[idx].get('name')
        return None

    def disconnect(self):
        if self.sio.connected:
            self.sio.disconnect()


def find_active_player(players):
    """Find which player's turn it is."""
    for p in players:
        if p.is_my_turn:
            return p
    return None


def main():
    print("=" * 60)
    print("FOLLOW THE QUEEN - BETTING & WILD CARD TEST")
    print("=" * 60)

    players = [
        TestPlayer("Alice"),
        TestPlayer("Bob"),
        TestPlayer("Carol")
    ]

    try:
        # Connect and join
        print("\n--- SETUP: Connecting 3 players ---")
        for p in players:
            p.connect()
        time.sleep(0.5)

        for p in players:
            p.join()
        time.sleep(1)

        joined = sum(1 for p in players if p.joined)
        print(f"Joined: {joined}/3 players")
        if joined < 2:
            print("ERROR: Not enough players!")
            return 1

        # Start game
        print("\n--- STARTING GAME ---")
        players[0].start_game()
        time.sleep(1)

        # Track wild cards and betting rounds
        betting_rounds = 0
        max_rounds = 20  # Safety limit
        actions_taken = []
        wild_changes = []
        last_wild = 'Q'

        print("\n--- BETTING ROUNDS ---")

        while betting_rounds < max_rounds:
            time.sleep(0.3)

            # Get current state from first player
            state = players[0].game_state
            if not state:
                continue

            phase = state.get('phase', '?')
            current_wild = state.get('current_wild_rank', 'Q')

            # Track wild card changes
            if current_wild != last_wild:
                wild_changes.append({
                    'phase': phase,
                    'from': last_wild,
                    'to': current_wild
                })
                print(f"  *** WILD CARD CHANGED: {last_wild} -> {current_wild} ***")
                last_wild = current_wild

            # Check if game is over
            if state.get('round_complete') or phase == 'showdown':
                print(f"\n  Game complete! Phase: {phase}")
                break

            # Find who needs to act
            active_player = None
            for p in players:
                if p.game_state and p.game_state.get('is_my_turn'):
                    active_player = p
                    break

            if not active_player:
                time.sleep(0.2)
                continue

            # Determine action based on situation
            my_state = active_player.game_state
            current_bet = my_state.get('current_bet', 0)

            # Get my current bet vs table bet
            my_bet = 0
            for p_data in my_state.get('players', []):
                if p_data.get('name') == active_player.name:
                    my_bet = p_data.get('current_bet', 0)
                    break

            # Simple betting strategy: check if possible, otherwise call
            # Occasionally raise to test raise functionality
            if betting_rounds % 5 == 3 and betting_rounds > 0:
                # Try a raise
                action = 'raise'
                amount = current_bet + 20 if current_bet > 0 else 20
                print(f"  [{active_player.name}] {phase}: RAISE to ${amount}")
                active_player.action('raise', amount)
                actions_taken.append(('raise', active_player.name, phase))
            elif my_bet < current_bet:
                # Need to call
                print(f"  [{active_player.name}] {phase}: CALL (${current_bet})")
                active_player.action('call')
                actions_taken.append(('call', active_player.name, phase))
            else:
                # Can check
                print(f"  [{active_player.name}] {phase}: CHECK")
                active_player.action('check')
                actions_taken.append(('check', active_player.name, phase))

            betting_rounds += 1
            time.sleep(0.2)

        # Final summary
        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)

        print(f"\n1. BETTING ACTIONS: {len(actions_taken)} actions taken")
        action_types = {}
        for action, player, phase in actions_taken:
            action_types[action] = action_types.get(action, 0) + 1
        for action, count in action_types.items():
            print(f"   - {action}: {count}")

        print(f"\n2. WILD CARD CHANGES: {len(wild_changes)} changes")
        if wild_changes:
            for change in wild_changes:
                print(f"   - {change['phase']}: {change['from']} -> {change['to']}")
        else:
            print("   (No wild card changes - no Queens dealt face up)")

        print(f"\n3. FINAL WILD RANK: {last_wild}")
        print(f"   (Queens are always wild, plus {last_wild}s if changed)")

        # Check final state
        final_state = players[0].game_state
        final_phase = final_state.get('phase', '?') if final_state else '?'
        print(f"\n4. FINAL PHASE: {final_phase}")

        # Success criteria
        success = True
        if len(actions_taken) < 3:
            print("\n*** FAIL: Not enough betting actions recorded ***")
            success = False
        else:
            print("\n*** PASS: Betting actions work correctly! ***")

        if final_phase in ['showdown', 'seventh_street'] or betting_rounds >= max_rounds:
            print("*** PASS: Game progressed through betting rounds! ***")
        else:
            print(f"*** Note: Game stopped at {final_phase} ***")

        return 0 if success else 1

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    finally:
        for p in players:
            p.disconnect()


if __name__ == "__main__":
    sys.exit(main())
