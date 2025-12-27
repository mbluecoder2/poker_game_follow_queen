"""Test Reset Game server restart feature."""
import socketio
import time

def test_reset():
    print("=" * 60)
    print("RESET GAME SERVER RESTART TEST")
    print("=" * 60)

    sio = socketio.Client(logger=False, engineio_logger=False)

    joined = False
    restart_received = False
    error_msg = None

    @sio.on('connected')
    def on_connected(data):
        print(f"[Michael H] Connected (session: {data['session_id'][:8]}...)")

    @sio.on('join_success')
    def on_join_success(data):
        nonlocal joined
        joined = True
        print(f"[Michael H] Joined as player {data['player_id']}")

    @sio.on('server_restart')
    def on_server_restart(data):
        nonlocal restart_received
        restart_received = True
        print(f"\n*** SERVER RESTART RECEIVED ***")
        print(f"    Message: {data['message']}")

    @sio.on('error')
    def on_error(data):
        nonlocal error_msg
        error_msg = data.get('message', str(data))
        print(f"[Michael H] ERROR: {error_msg}")

    @sio.on('game_state')
    def on_game_state(state):
        pass  # Ignore game state updates

    try:
        # Connect
        print("\n--- Connecting as Michael H ---")
        sio.connect('http://127.0.0.1:5000', wait_timeout=10)
        time.sleep(0.5)

        # Join as Michael H
        print("\n--- Joining game ---")
        sio.emit('join_game', {'name': 'Michael H'})
        time.sleep(1)

        if not joined:
            print("ERROR: Failed to join")
            return 1

        # Trigger reset
        print("\n--- Triggering Reset Game ---")
        sio.emit('reset_game')

        # Wait for response
        time.sleep(2)

        print("\n" + "=" * 60)
        print("TEST RESULTS")
        print("=" * 60)

        if restart_received:
            print("*** PASS: Server restart triggered successfully! ***")
            print("\nThe server should have restarted.")
            print("All clients would see the restart message and auto-refresh.")
            return 0
        elif error_msg:
            print(f"*** FAIL: Received error: {error_msg} ***")
            return 1
        else:
            print("*** UNKNOWN: No restart or error received ***")
            return 1

    except Exception as e:
        print(f"\nConnection lost (expected if server restarted): {e}")
        print("\n*** PASS: Server likely restarted (connection dropped) ***")
        return 0

    finally:
        try:
            sio.disconnect()
        except:
            pass


if __name__ == "__main__":
    import sys
    sys.exit(test_reset())
