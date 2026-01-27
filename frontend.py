"""
HTML template for the poker game frontend.
"""

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Texas Hold'em Poker</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        /* ===========================================
           CONFIGURABLE SETTINGS
           =========================================== */
        :root {
            --card-hover-scale: 1.55;  /* Card enlargement on hover (1.55 = 55% larger) */

            /* Card dimensions */
            --card-width: 60px;
            --card-height: 84px;
            --card-community-width: 70px;
            --card-community-height: 98px;

            /* Font sizes */
            --font-body: 14px;
            --font-critical: 16px;
            --font-pot: 1.5rem;

            /* Colors - Traditional Green Felt (default) */
            --bg-body: linear-gradient(135deg, #1a4d2e 0%, #0d2818 100%);
            --bg-table: radial-gradient(ellipse at center, #35654d 0%, #1e4d35 70%);
            --bg-player-spot: rgba(0,0,0,0.4);
            --border-table: #8b4513;
            --text-primary: #fff;
            --text-accent: #ffd700;
            --card-red: #cc0000;
            --card-black: #000;
        }

        /* High Contrast Dark Mode */
        [data-theme="dark"] {
            --bg-body: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
            --bg-table: radial-gradient(ellipse at center, #1a1a1a 0%, #0d0d0d 70%);
            --text-accent: #ffff00;
            --card-red: #ff3333;
            --card-black: #ffffff;
        }

        /* Colorblind Enhanced Mode */
        [data-theme="colorblind"] {
            --card-red: #ff6600;   /* Orange instead of red */
            --card-black: #000000; /* Keep black as black */
        }

        /* Large Format Mode */
        [data-display-mode="large"] {
            --card-width: 120px;
            --card-height: 168px;
            --card-community-width: 140px;
            --card-community-height: 196px;
            --font-body: 20px;
            --font-critical: 30px;
            --font-pot: 2rem;
        }

        .royal-flush-icon {
            display: inline-block;
            width: 1.2em;
            height: 1.2em;
            background-image: url('/royal-flush-icon.png');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            vertical-align: middle;
            margin-right: 0.2em;
            transition: transform 0.2s ease;
        }

        .royal-flush-icon:hover {
            transform: scale(1.5);
        }

        .royal-flush-icon.large {
            width: 2em;
            height: 2em;
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: var(--bg-body);
            min-height: 100vh;
            color: var(--text-primary);
            font-size: var(--font-body);
            overflow-x: hidden;
        }
        
        .header {
            text-align: center;
            padding: 15px;
            background: rgba(0,0,0,0.3);
        }
        
        .header h1 {
            color: #ffd700;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            font-size: 2rem;
        }

        .token-info {
            color: #90EE90;
            font-size: 0.9rem;
            margin-top: 5px;
        }

        .dollar-equiv {
            color: #90EE90;
            font-size: 0.85em;
        }
        
        .game-container {
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
        }
        
        /* Poker Table */
        .poker-table {
            background: var(--bg-table);
            border: 15px solid var(--border-table);
            border-radius: 150px;
            padding: 30px;
            margin: 20px auto;
            position: relative;
            box-shadow:
                inset 0 0 50px rgba(0,0,0,0.5),
                0 10px 30px rgba(0,0,0,0.5);
            min-height: 400px;
        }
        
        /* Pot Display */
        .pot-display {
            text-align: center;
            margin-bottom: 20px;
        }
        
        .pot-amount {
            font-size: var(--font-pot);
            color: var(--text-accent);
            background: rgba(0,0,0,0.5);
            padding: 10px 30px;
            border-radius: 25px;
            display: inline-block;
        }
        
        .phase-display {
            font-size: 1rem;
            color: #aaa;
            margin-top: 5px;
        }

        .wild-card-display {
            background: rgba(255, 105, 180, 0.2);
            border: 2px solid #ff69b4;
            border-radius: 10px;
            padding: 8px 20px;
            margin-top: 10px;
            display: inline-block;
        }

        /* Community Cards */
        .community-cards {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 20px 0;
            min-height: 100px;
        }
        
        /* Player Positions */
        .players-area {
            display: flex;
            justify-content: space-around;
            flex-wrap: wrap;
            gap: 20px;
            margin-top: 30px;
        }
        
        .player-spot {
            background: var(--bg-player-spot);
            border-radius: 15px;
            padding: 15px;
            min-width: 180px;
            text-align: center;
            transition: all 0.3s ease;
            border: 3px solid transparent;
        }
        
        .player-spot.active {
            border-color: #ffd700;
            box-shadow: 0 0 20px rgba(255,215,0,0.5);
        }
        
        .player-spot.folded {
            opacity: 0.5;
        }
        
        .player-spot.human {
            background: rgba(0,70,140,0.4);
        }
        
        .player-name {
            font-weight: bold;
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
        
        .dealer-chip {
            background: #fff;
            color: #000;
            width: 24px;
            height: 24px;
            border-radius: 50%;
            font-size: 12px;
            font-weight: bold;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border: 2px solid #ffd700;
        }
        
        .player-chips {
            color: #ffd700;
            margin: 5px 0;
        }
        
        .player-bet {
            color: #ff9800;
            font-size: 0.9rem;
        }
        
        .player-cards {
            display: flex;
            justify-content: center;
            gap: 5px;
            margin-top: 10px;
        }
        
        .player-status {
            margin-top: 8px;
            font-size: 0.85rem;
            padding: 3px 10px;
            border-radius: 10px;
            display: inline-block;
        }
        
        .status-folded {
            background: #c0392b;
        }
        
        .status-all-in {
            background: #8e44ad;
        }
        
        .hand-result {
            margin-top: 8px;
            color: #ffd700;
            font-weight: bold;
            font-size: 0.9rem;
        }
        
        /* Cards */
        .card {
            width: var(--card-width);
            height: var(--card-height);
            background: #fff;
            border-radius: 6px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            padding: 4px;
            box-shadow: 0 3px 6px rgba(0,0,0,0.3);
            position: relative;
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }

        /* Face-up cards (and revealed down cards) enlarge on hover */
        .up-cards-group .card:not(.back):hover,
        .down-cards-group .card:not(.back):hover,
        .community-cards .card:not(.back):hover {
            transform: scale(var(--card-hover-scale));
            z-index: 100;
            box-shadow: 0 8px 20px rgba(0,0,0,0.5);
        }

        .card.wild {
            border: 5px solid #ffd700;
            box-shadow: 0 0 12px rgba(255, 215, 0, 0.7), 0 3px 6px rgba(0,0,0,0.3);
        }
        
        .card.back {
            background: linear-gradient(145deg, #1e3d59, #17435e);
            border: 2px solid #fff;
        }
        
        .card.back::after {
            content: '🂠';
            font-size: 40px;
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
        }
        
        .card.community {
            width: var(--card-community-width);
            height: var(--card-community-height);
        }
        
        .card.placeholder {
            background: rgba(255,255,255,0.1);
            border: 2px dashed rgba(255,255,255,0.3);
        }
        
        .card-corner {
            display: flex;
            flex-direction: column;
            align-items: center;
            line-height: 1;
        }
        
        .card-corner.bottom {
            align-self: flex-end;
            transform: rotate(180deg);
        }
        
        .card-rank {
            font-size: 14px;
            font-weight: bold;
        }
        
        .card-suit {
            font-size: 12px;
        }
        
        .card.hearts, .card.diamonds {
            color: var(--card-red);
        }

        .card.clubs, .card.spades {
            color: var(--card-black);
        }
        
        .card-center {
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            font-size: 24px;
        }
        
        /* Action Panel - Floating Toolbar */
        .action-panel {
            position: fixed;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            background: linear-gradient(145deg, rgba(0,0,0,0.9), rgba(30,30,30,0.95));
            border-radius: 20px;
            padding: 20px 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.5), 0 0 20px rgba(255,215,0,0.3);
            border: 2px solid rgba(255,215,0,0.5);
            z-index: 1000;
            animation: floatIn 0.3s ease-out;
            transition: opacity 0.15s ease-out;
        }

        @keyframes floatIn {
            from {
                opacity: 0;
                transform: translateX(-50%) translateY(20px);
            }
            to {
                opacity: 1;
                transform: translateX(-50%) translateY(0);
            }
        }

        .action-panel::before {
            content: "🎯 YOUR TURN";
            display: block;
            text-align: center;
            color: #ffd700;
            font-weight: bold;
            font-size: 0.9rem;
            margin-bottom: 12px;
            letter-spacing: 2px;
            text-shadow: 0 0 10px rgba(255,215,0,0.5);
        }
        
        .action-buttons {
            display: flex;
            justify-content: center;
            gap: 15px;
            flex-wrap: wrap;
        }

        .btn {
            padding: 12px 25px;
            font-size: 1rem;
            font-weight: bold;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .btn:hover:not(:disabled) {
            transform: translateY(-2px);
        }

        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        /* Action button specific styles - larger for floating toolbar */
        .action-panel .btn {
            padding: 15px 30px;
            font-size: 1.1rem;
            min-width: 100px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        }

        .action-panel .btn:hover:not(:disabled) {
            transform: translateY(-3px);
            box-shadow: 0 6px 20px rgba(0,0,0,0.4);
        }

        .btn-fold {
            background: linear-gradient(145deg, #c0392b, #a93226);
            color: white;
        }

        .btn-check, .btn-call {
            background: linear-gradient(145deg, #27ae60, #229954);
            color: white;
        }

        .btn-raise {
            background: linear-gradient(145deg, #f39c12, #d68910);
            color: white;
        }
        
        .btn-allin {
            background: linear-gradient(145deg, #8e44ad, #7d3c98);
            color: white;
        }
        
        .btn-primary {
            background: linear-gradient(145deg, #ffd700, #ffaa00);
            color: #1a3555;
        }

        .btn-primary:disabled,
        .btn-primary.disabled {
            background: linear-gradient(145deg, #666, #555);
            color: #999;
            cursor: not-allowed;
            opacity: 0.6;
        }

        .btn-bet-amount {
            background: linear-gradient(145deg, #3498db, #2980b9);
            color: white;
            padding: 8px 12px;
            min-width: 45px;
            font-weight: bold;
        }

        .btn-bet-amount:hover {
            background: linear-gradient(145deg, #5dade2, #3498db);
        }

        .bet-buttons {
            display: flex;
            gap: 5px;
            justify-content: center;
        }

        .btn-clear-bet {
            background: linear-gradient(145deg, #e74c3c, #c0392b);
            color: white;
            padding: 8px 12px;
            font-weight: bold;
        }

        .btn-clear-bet:hover {
            background: linear-gradient(145deg, #ec7063, #e74c3c);
        }

        /* Player Name Dropdown */
        #playerName {
            font-size: 1rem;
        }

        #playerName option:disabled {
            color: #999 !important;
            font-style: italic !important;
            background: #f5f5f5 !important;
        }

        #playerName option:not(:disabled) {
            color: #1a3555;
            font-weight: bold;
        }

        .raise-controls {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
            margin-top: 15px;
        }
        
        .raise-input {
            width: 100px;
            padding: 10px;
            font-size: 1rem;
            border: none;
            border-radius: 5px;
            text-align: center;
        }
        
        .raise-slider {
            width: 200px;
        }
        
        /* Status Messages */
        .game-status {
            text-align: center;
            padding: 10px;
            font-size: 1.5rem;
            color: #ffffff;
            min-height: 55px;
        }
        
        /* Winner Announcement */
        .winner-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.8);
            z-index: 1000;
            justify-content: center;
            align-items: center;
        }
        
        .winner-content {
            background: linear-gradient(145deg, #1a3555, #0d1a2d);
            border: 3px solid #ffd700;
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            animation: popIn 0.5s ease;
        }
        
        @keyframes popIn {
            from { transform: scale(0.5); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        
        .winner-content h2 {
            color: #ffd700;
            font-size: 2rem;
            margin-bottom: 20px;
        }
        
        .winner-details {
            font-size: 1.2rem;
            margin: 15px 0;
        }

        .winner-entry {
            margin: 15px 0;
            padding: 15px;
            background: rgba(255, 215, 0, 0.1);
            border-radius: 10px;
        }

        .winner-name {
            font-size: 1.8rem;
            color: #ffd700;
            font-weight: bold;
            margin-bottom: 10px;
        }

        .winner-amount {
            font-size: 1.3rem;
            color: #90EE90;
            margin-bottom: 8px;
        }

        .winner-hand {
            font-size: 1.5rem;
            color: #fff;
            font-style: italic;
        }

        /* Controls Bar */
        .controls-bar {
            display: flex;
            justify-content: center;
            gap: 15px;
            padding: 15px;
            background: rgba(0,0,0,0.3);
        }
        
        /* Animations */
        .card-deal {
            animation: dealCard 0.3s ease;
        }
        
        @keyframes dealCard {
            from {
                transform: translateY(-100px) rotate(180deg);
                opacity: 0;
            }
            to {
                transform: translateY(0) rotate(0);
                opacity: 1;
            }
        }
        
        /* Algorithm Info (from shuffle feature) */
        .algorithm-info {
            display: none;
            max-width: 900px;
            margin: 20px auto;
            padding: 25px;
            background: linear-gradient(145deg, rgba(255,255,255,0.95), rgba(240,240,240,0.95));
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            color: #1a1a1a;
        }
        
        .algorithm-info h2 {
            text-align: center;
            color: #1a3555;
            margin-bottom: 20px;
            border-bottom: 3px solid #ffd700;
            padding-bottom: 10px;
        }

        .algorithm-info h3 {
            color: #1a3555;
            margin: 15px 0 10px;
        }

        .info-section {
            margin-bottom: 15px;
            padding: 15px;
            background: rgba(26, 53, 85, 0.05);
            border-radius: 10px;
            border-left: 4px solid #1a3555;
        }
        
        .code-block {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 15px;
            border-radius: 8px;
            font-family: monospace;
            overflow-x: auto;
            margin: 10px 0;
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .poker-table {
                border-radius: 50px;
                padding: 15px;
            }
            .player-spot {
                min-width: 140px;
                padding: 10px;
            }
            .card {
                width: 50px;
                height: 70px;
            }
            .card.community {
                width: 55px;
                height: 77px;
            }
        }

        /* Game Mode Container Display */
        #holdemTable, #studTable {
            display: none;
        }

        [data-game-mode="holdem"] #holdemTable {
            display: block;
        }

        [data-game-mode="stud_follow_queen"] #studTable {
            display: block;
        }

        /* Wild Card Panel Prominence */
        #wildCardPanel {
            background: linear-gradient(135deg, #8b008b 0%, #ff1493 100%);
            border: 3px solid #ff69b4;
            border-radius: 15px;
            padding: 20px;
            margin: 20px auto;
            max-width: 1600px;
            box-shadow: 0 0 30px rgba(255, 105, 180, 0.6);
            animation: wildGlow 2s ease-in-out infinite;
        }

        @keyframes wildGlow {
            0%, 100% { box-shadow: 0 0 30px rgba(255, 105, 180, 0.6); }
            50% { box-shadow: 0 0 50px rgba(255, 105, 180, 1); }
        }

        #wildCardPanel .current-wild {
            font-size: 2.5rem;
            color: #ffd700;
            text-align: center;
            font-weight: bold;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.8);
        }

        #wildCardPanel .wild-history {
            margin-top: 15px;
            display: flex;
            gap: 10px;
            justify-content: center;
            flex-wrap: wrap;
        }

        .wild-change-badge {
            background: rgba(0,0,0,0.3);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.9rem;
        }

        /* Stud Player Card Layout */
        .stud-players-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 20px;
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .stud-player-card {
            background: rgba(0,0,0,0.4);
            border-radius: 15px;
            padding: 20px;
            border: 3px solid transparent;
        }

        .stud-player-card.active {
            border-color: #ffd700;
            box-shadow: 0 0 20px rgba(255,215,0,0.5);
        }

        .stud-player-card.folded {
            opacity: 0.5;
        }

        .stud-player-card .player-info {
            margin-bottom: 15px;
        }

        .card-progression {
            display: flex;
            gap: 20px;
            margin-top: 15px;
        }

        .down-cards-group, .up-cards-group {
            flex: 1;
            min-width: 140px;
        }

        .down-cards-group label, .up-cards-group label {
            display: block;
            text-align: center;
            color: #ffd700;
            font-weight: bold;
            margin-bottom: 10px;
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }

        .cards-vertical {
            display: flex;
            flex-direction: row;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
        }

        .cards-vertical .card {
            margin: 0;
        }

        /* Visual distinction for down cards group */
        .down-cards-group {
            background: rgba(139, 0, 0, 0.2);
            border: 2px dashed rgba(255, 255, 255, 0.3);
            border-radius: 10px;
            padding: 15px;
        }

        /* Visual distinction for up cards group */
        .up-cards-group {
            background: rgba(0, 100, 0, 0.2);
            border: 2px solid rgba(0, 255, 0, 0.3);
            border-radius: 10px;
            padding: 15px;
        }

        /* Street Indicators */
        .street-indicator {
            font-size: 0.7rem;
            color: #aaa;
            text-align: center;
            margin-top: 3px;
        }

        /* Current Hand Display */
        .current-hand-display {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border: 2px solid #ffd700;
            border-radius: 10px;
            padding: 10px 15px;
            margin-top: 15px;
            text-align: center;
            color: #ffd700;
            font-weight: bold;
            font-size: 1.1rem;
            text-shadow: 0 0 10px rgba(255, 215, 0, 0.5);
            box-shadow: 0 0 15px rgba(255, 215, 0, 0.3);
        }

        /* Clickable reveal for down cards at showdown */
        .clickable-reveal {
            cursor: pointer;
            transition: all 0.3s ease;
        }

        .clickable-reveal:hover {
            transform: scale(1.05);
            box-shadow: 0 0 20px rgba(255, 215, 0, 0.6);
            border-color: #ffd700;
        }

        .reveal-hint {
            text-align: center;
            color: #ffd700;
            font-size: 0.8rem;
            margin-top: 8px;
            animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
            0%, 100% { opacity: 0.6; }
            50% { opacity: 1; }
        }

        /* =============================================
           LARGE FORMAT MODE STYLES
           ============================================= */
        .large-format-wrapper {
            display: none;
        }

        [data-display-mode="large"] .large-format-wrapper {
            display: grid;
            grid-template-rows: 35% 30%;
            height: calc(100vh - 120px);
            gap: 10px;
            padding: 10px;
        }

        [data-display-mode="large"] #holdemTable,
        [data-display-mode="large"] #studTable {
            display: none !important;
        }

        /* Large Format Card Text - doubled sizes */
        [data-display-mode="large"] .card-rank {
            font-size: 28px;
        }

        [data-display-mode="large"] .card-suit {
            font-size: 24px;
        }

        [data-display-mode="large"] .card-center {
            font-size: 48px;
        }

        /* Large Format Zones */
        .lf-opponents-zone {
            display: flex;
            justify-content: center;
            align-items: flex-start;
            gap: 20px;
            flex-wrap: wrap;
            padding: 10px;
            overflow-y: auto;
        }

        .lf-center-zone {
            display: flex;
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-table);
            border-radius: 30px;
            padding: 20px 40px;
            border: 8px solid var(--border-table);
        }

        .lf-center-content {
            display: flex;
            flex-direction: column;
            align-items: center;
            flex: 1;
        }

        .lf-player-zone {
            display: none;
        }

        [data-display-mode="large"] .lf-player-zone-inline {
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            padding: 15px 25px;
            margin-left: 30px;
            background: rgba(0, 100, 200, 0.3);
            border-radius: 20px;
            border: 3px solid rgba(0, 170, 255, 0.5);
        }

        .lf-folded-strip {
            position: fixed;
            bottom: 100px;
            right: 20px;
            z-index: 500;
        }

        .lf-folded-toggle {
            background: rgba(0,0,0,0.7);
            color: var(--text-accent);
            border: 2px solid var(--text-accent);
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: var(--font-body);
            font-weight: bold;
        }

        .lf-folded-players {
            display: none;
            flex-direction: column;
            gap: 5px;
            margin-top: 10px;
            background: rgba(0,0,0,0.8);
            padding: 10px;
            border-radius: 10px;
            max-height: 200px;
            overflow-y: auto;
        }

        .lf-folded-strip:hover .lf-folded-players,
        .lf-folded-strip.expanded .lf-folded-players {
            display: flex;
        }

        .lf-folded-player {
            font-size: 14px;
            color: #888;
            padding: 4px 8px;
            background: rgba(255,255,255,0.1);
            border-radius: 5px;
        }

        /* Large Format Player Spot */
        .lf-player-spot {
            background: var(--bg-player-spot);
            border-radius: 20px;
            padding: 20px;
            min-width: 250px;
            text-align: center;
            border: 4px solid transparent;
        }

        .lf-player-spot.active {
            border-color: var(--text-accent);
            box-shadow: 0 0 30px rgba(255,215,0,0.5);
        }

        .lf-player-spot.current-player {
            background: rgba(0,100,200,0.4);
            border-color: #00aaff;
        }

        .lf-player-spot .player-name {
            font-size: var(--font-critical);
            font-weight: bold;
            margin-bottom: 10px;
        }

        .lf-player-spot .player-chips {
            font-size: calc(var(--font-critical) * 0.8);
            color: var(--text-accent);
            margin-bottom: 10px;
        }

        .lf-player-spot .player-cards {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin-top: 15px;
        }

        /* Large format pot display */
        .lf-pot-display {
            font-size: var(--font-critical);
            color: var(--text-accent);
            background: rgba(0,0,0,0.6);
            padding: 15px 40px;
            border-radius: 30px;
            margin-bottom: 20px;
        }

        .lf-community-cards {
            display: flex;
            justify-content: center;
            gap: 15px;
            margin: 20px 0;
        }

        /* Theme dropdown styling */
        .theme-select, .display-mode-select {
            padding: 8px 12px;
            background: rgba(255,255,255,0.9);
            color: #1a3555;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: bold;
            font-size: 0.9rem;
        }

        .theme-select:hover, .display-mode-select:hover {
            background: #fff;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1 id="gameTitle"><span class="royal-flush-icon"></span> The Royal Flushers - Multiplayer</h1>
        <div class="token-info">💰 100 tokens = $1.00</div>
    </div>

    <div id="joinSection" class="controls-bar" style="flex-direction: column; gap: 15px;">
        <div style="font-size: 1.2rem; color: #ffd700;">Join the Game</div>
        <div style="display: flex; align-items: center; gap: 10px;">
            <label for="playerName" style="color: #ffd700;">Your Name:</label>
            <select id="playerName" style="padding: 10px; border-radius: 5px; border: none; min-width: 200px; background: white; color: #1a3555; font-weight: bold; cursor: pointer;">
                <option value="">-- Select Your Name --</option>
            </select>
            <button class="btn btn-primary" onclick="joinGame()" style="color: white;">Join Game</button>
            <button class="btn btn-primary" onclick="resetGame()" style="background: linear-gradient(145deg, #8fe73c, #c0392b); color: white;">🔄 Reset Server</button>
        </div>
        <div id="joinStatus" style="color: #ff6b6b;"></div>
    </div>

    <div class="controls-bar" id="gameControls" style="display: none;">
        <div style="display: flex; align-items: center; gap: 8px;">
            <input type="checkbox" id="hiLoMode" style="width: 18px; height: 18px; cursor: pointer;">
            <label for="hiLoMode" style="color: #ffd700; font-weight: bold; cursor: pointer;" title="Split pot between best high and best qualifying low hand (8-or-better)">Hi-Lo</label>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <input type="checkbox" id="twoSevensMode" style="width: 18px; height: 18px; cursor: pointer;">
            <label for="twoSevensMode" style="color: #ff6b6b; font-weight: bold; cursor: pointer;" title="Two natural (non-wild) 7s wins the pot instantly">2x7 Wins</label>
        </div>
        <div style="display: flex; align-items: center; gap: 8px;">
            <input type="checkbox" id="dealSevensToMichael" style="width: 18px; height: 18px; cursor: pointer;">
            <label for="dealSevensToMichael" style="color: #9b59b6; font-weight: bold; cursor: pointer;" title="Debug: Deal two 7s to Michael H">7s-MH</label>
        </div>
        <button class="btn btn-primary" onclick="newGame()" id="newGameBtn" style="color: white;">New Game</button>
        <button class="btn btn-primary" onclick="startGame()" id="startGameBtn" style="display: none; color: white;">Start Game</button>
        <button class="btn btn-primary" onclick="newHand()" id="newHandBtn" style="display: none; color: white;">New Hand</button>
        <button class="btn btn-primary" onclick="resetGame()" id="resetGameBtn" style="background: linear-gradient(145deg, #8fe73c, #c0392b); color: white;">🔄 Reset Server</button>
        <button class="btn btn-primary" onclick="toggleAlgorithmInfo()" style="color: white;">📚 Shuffle Info</button>
        <button class="btn btn-primary" onclick="toggleHandRankings()" style="background: linear-gradient(145deg, #9b59b6, #8e44ad); color: white;">🏆 Hand Rankings</button>
        <div style="display: flex; align-items: center; gap: 8px; margin-left: 10px;">
            <select id="displayMode" class="display-mode-select" onchange="setDisplayMode(this.value)" title="Display Mode">
                <option value="standard">Standard</option>
                <option value="large">Large Format</option>
            </select>
            <select id="themeSelect" class="theme-select" onchange="setTheme(this.value)" title="Color Theme">
                <option value="green">Green Felt</option>
                <option value="dark">Dark Mode</option>
                <option value="colorblind">Colorblind</option>
            </select>
        </div>
    </div>
    
    <div class="game-container">
        <div class="game-status" id="gameStatus">Select your name and click "Join Game" to enter.</div>
        
        <div class="algorithm-info" id="algorithmInfo">
            <h2>🔀 Fisher-Yates Shuffle Algorithm</h2>
            
            <div class="info-section">
                <h3>History & Origins</h3>
                <p>The Fisher-Yates shuffle was originally described by <strong>Ronald Fisher</strong> and <strong>Frank Yates</strong> in their 1938 book "Statistical Tables for Biological, Agricultural and Medical Research." The modern computer-optimized version was developed by <strong>Richard Durstenfeld</strong> in 1964 and popularized by <strong>Donald Knuth</strong> in "The Art of Computer Programming."</p>
            </div>
            
            <div class="info-section">
                <h3>How It Works</h3>
                <p>The algorithm iterates from the last element to the first. For each position <em>i</em>, it randomly selects an element from positions 0 to <em>i</em> and swaps them.</p>
                <div class="code-block">
<pre>for i from n-1 down to 1:
    j = random integer where 0 ≤ j ≤ i
    swap array[i] with array[j]</pre>
                </div>
            </div>
            
            <div class="info-section">
                <h3>Python Implementation</h3>
                <div class="code-block">
<pre>def fisher_yates_shuffle(deck):
    for i in range(len(deck) - 1, 0, -1):
        j = random.randint(0, i)
        deck[i], deck[j] = deck[j], deck[i]
    return deck</pre>
                </div>
            </div>
            
            <div class="info-section">
                <h3>Why 7 Shuffles?</h3>
                <p>Mathematician <strong>Persi Diaconis</strong> proved that <strong>7 riffle shuffles</strong> are needed to adequately randomize a 52-card deck. This relates to mixing time in Markov chains.</p>
            </div>
            
            <div class="info-section">
                <h3>Mathematical Properties</h3>
                <p><strong>Time Complexity:</strong> O(n) | <strong>Space:</strong> O(1) | <strong>Permutations:</strong> 52! = 8.07 × 10<sup>67</sup></p>
            </div>
        </div>

        <!-- Hand Rankings Info -->
        <div class="algorithm-info" id="handRankingsInfo">
            <h2>🏆 Poker Hand Rankings</h2>
            <p style="text-align: center; color: #666; margin-bottom: 20px;">Ranked from lowest (1) to highest (11). Higher beats lower!</p>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px;">
                <div class="info-section" style="border-left-color: #95a5a6;">
                    <h3>1. High Card</h3>
                    <p>No matching cards. Highest card plays.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:black;">♠</span> K<span style="color:red;">♥</span> 9<span style="color:red;">♦</span> 7<span style="color:black;">♣</span> 2<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #3498db;">
                    <h3>2. One Pair</h3>
                    <p>Two cards of the same rank.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">K<span style="color:black;">♠</span> K<span style="color:red;">♥</span> 9<span style="color:red;">♦</span> 7<span style="color:black;">♣</span> 2<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #2ecc71;">
                    <h3>3. Two Pair</h3>
                    <p>Two different pairs.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">K<span style="color:black;">♠</span> K<span style="color:red;">♥</span> 9<span style="color:red;">♦</span> 9<span style="color:black;">♣</span> 2<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #f39c12;">
                    <h3>4. Three of a Kind</h3>
                    <p>Three cards of the same rank.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">9<span style="color:black;">♠</span> 9<span style="color:red;">♥</span> 9<span style="color:red;">♦</span> K<span style="color:black;">♣</span> 2<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #e74c3c;">
                    <h3>5. Straight</h3>
                    <p>Five consecutive ranks (any suits).</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">5<span style="color:black;">♠</span> 6<span style="color:red;">♥</span> 7<span style="color:red;">♦</span> 8<span style="color:black;">♣</span> 9<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #9b59b6;">
                    <h3>6. Flush</h3>
                    <p>Five cards of the same suit.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:black;">♠</span> K<span style="color:black;">♠</span> 9<span style="color:black;">♠</span> 7<span style="color:black;">♠</span> 2<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #1abc9c;">
                    <h3>7. Full House</h3>
                    <p>Three of a kind + a pair.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">9<span style="color:black;">♠</span> 9<span style="color:red;">♥</span> 9<span style="color:red;">♦</span> K<span style="color:black;">♣</span> K<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #e67e22;">
                    <h3>8. Four of a Kind</h3>
                    <p>Four cards of the same rank.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">9<span style="color:black;">♠</span> 9<span style="color:red;">♥</span> 9<span style="color:red;">♦</span> 9<span style="color:black;">♣</span> K<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #c0392b;">
                    <h3>9. Straight Flush</h3>
                    <p>Straight + flush combined.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">5<span style="color:black;">♠</span> 6<span style="color:black;">♠</span> 7<span style="color:black;">♠</span> 8<span style="color:black;">♠</span> 9<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #f1c40f;">
                    <h3>10. Royal Flush</h3>
                    <p>A-K-Q-J-10 all same suit. <strong>Rarest hand!</strong></p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:black;">♠</span> K<span style="color:black;">♠</span> Q<span style="color:black;">♠</span> J<span style="color:black;">♠</span> 10<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #ff69b4; background: rgba(255,105,180,0.1);">
                    <h3>11. Five of a Kind <span class="royal-flush-icon"></span></h3>
                    <p><strong>Wild cards only!</strong> Five cards of same rank.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">K<span style="color:black;">♠</span> K<span style="color:red;">♥</span> K<span style="color:red;">♦</span> K<span style="color:black;">♣</span> Q<span style="color:red;">♥</span><span style="color:#ff69b4;">(wild)</span></div>
                    <p style="font-size: 0.85rem; color: #ff69b4; margin-top: 5px;">Queens are always wild in Follow the Queen!</p>
                </div>
            </div>

            <div class="info-section" style="margin-top: 20px; background: rgba(255,215,0,0.1); border-left-color: #ffd700;">
                <h3><span class="royal-flush-icon"></span> Wild Cards in Follow the Queen</h3>
                <p><strong>Queens are always wild.</strong> When a Queen is dealt face-up, the next face-up card's rank also becomes wild. Wild cards can substitute for ANY card to make the best hand!</p>
            </div>

            <h2 style="margin-top: 30px;">📉 Low Hand Rankings (Hi-Lo & Lo Games)</h2>
            <p style="text-align: center; color: #666; margin-bottom: 20px;">In low games, the <strong>lowest</strong> hand wins. Aces play low. Straights and flushes don't count against you!</p>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 15px;">
                <div class="info-section" style="border-left-color: #27ae60; background: rgba(39,174,96,0.1);">
                    <h3>1. The Wheel (Best Low) 🏆</h3>
                    <p>A-2-3-4-5 — The perfect low hand!</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:black;">♠</span> 2<span style="color:red;">♥</span> 3<span style="color:red;">♦</span> 4<span style="color:black;">♣</span> 5<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #2ecc71;">
                    <h3>2. Six-Four Low</h3>
                    <p>A-2-3-4-6 — Second best low.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:red;">♥</span> 2<span style="color:black;">♠</span> 3<span style="color:black;">♣</span> 4<span style="color:red;">♦</span> 6<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #3498db;">
                    <h3>3. Six-Five Low</h3>
                    <p>A-2-3-5-6 or A-2-4-5-6</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:black;">♣</span> 2<span style="color:red;">♥</span> 3<span style="color:black;">♠</span> 5<span style="color:red;">♦</span> 6<span style="color:red;">♥</span></div>
                </div>

                <div class="info-section" style="border-left-color: #9b59b6;">
                    <h3>4. Seven Low</h3>
                    <p>Any 5 unpaired cards, 7-high.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:black;">♠</span> 2<span style="color:red;">♦</span> 3<span style="color:black;">♣</span> 4<span style="color:red;">♥</span> 7<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #e67e22;">
                    <h3>5. Eight Low (Qualifier)</h3>
                    <p>Any 5 unpaired cards, 8-high. Required to qualify in most Hi-Lo games!</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:red;">♥</span> 2<span style="color:black;">♠</span> 4<span style="color:red;">♦</span> 6<span style="color:black;">♣</span> 8<span style="color:black;">♠</span></div>
                </div>

                <div class="info-section" style="border-left-color: #e74c3c;">
                    <h3>No Low / No Qualifier</h3>
                    <p>Pairs, or cards 9+ disqualify a low hand in "8-or-better" games.</p>
                    <div style="font-family: monospace; font-size: 1.1rem;">A<span style="color:black;">♠</span> 2<span style="color:red;">♥</span> 3<span style="color:red;">♦</span> 3<span style="color:black;">♣</span> 5<span style="color:black;">♠</span> ❌</div>
                </div>
            </div>

            <div class="info-section" style="margin-top: 20px; background: rgba(46,204,113,0.1); border-left-color: #2ecc71;">
                <h3>📖 How Low Hands Work</h3>
                <p><strong>Reading low hands:</strong> Compare from highest card down. A-2-3-4-6 beats A-2-3-5-6 because 4 < 5.</p>
                <p style="margin-top: 10px;"><strong>Eight-or-better:</strong> To qualify for low, all 5 cards must be 8 or lower with no pairs. If no one qualifies, the high hand wins the entire pot.</p>
                <p style="margin-top: 10px;"><strong>Scooping:</strong> The same hand can win both high and low! A-2-3-4-5 is both the best low AND a straight for high.</p>
            </div>
        </div>

        <!-- Wild Card Panel (Stud only) -->
        <div id="wildCardPanel" style="display: none;">
            <div class="current-wild" id="currentWild">
                <span class="royal-flush-icon large"></span> Wild Cards: <span style="font-size: 3rem;">Queens Only</span>
            </div>
            <div class="wild-history" id="wildHistory">
                <div class="wild-change-badge">No wild card changes yet</div>
            </div>
        </div>

        <!-- Texas Hold'em Table -->
        <div id="holdemTable">
            <div class="poker-table" id="pokerTable">
                <div class="pot-display">
                    <div class="pot-amount">Pot: <span id="potAmount">0</span> tokens <span class="dollar-equiv">($<span id="potDollars">0.00</span>)</span></div>
                    <div class="phase-display">Phase: <span id="phaseDisplay">-</span></div>
                </div>

                <div class="community-cards" id="communityCards">
                    <!-- Community cards appear here -->
                </div>

                <div class="players-area" id="playersArea">
                    <!-- Player spots appear here -->
                </div>
            </div>
        </div>

        <!-- Follow the Queen (Stud) Table -->
        <div id="studTable">
            <div class="poker-table">
                <div class="pot-display">
                    <div class="pot-amount">Pot: <span id="studPotAmount">0</span> tokens <span class="dollar-equiv">($<span id="studPotDollars">0.00</span>)</span></div>
                    <div class="phase-display">
                        Phase: <span id="studPhaseDisplay">-</span>
                        <span id="hiLoBadge" style="display: none; margin-left: 10px; background: linear-gradient(145deg, #e74c3c, #27ae60); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold;">HI-LO</span>
                        <span id="twoSevensBadge" style="display: none; margin-left: 10px; background: linear-gradient(145deg, #ff6b6b, #c0392b); color: white; padding: 2px 8px; border-radius: 4px; font-size: 0.85rem; font-weight: bold;">2x7 WINS</span>
                    </div>
                </div>

                <div class="stud-players-grid" id="studPlayersGrid">
                    <!-- Stud player cards appear here -->
                </div>
            </div>
        </div>

        <!-- Large Format Layout (for elderly/vision-impaired users) -->
        <div class="large-format-wrapper" id="largeFormatWrapper">
            <div class="lf-opponents-zone" id="lfOpponentsZone">
                <!-- Top 3-4 active opponents appear here -->
            </div>
            <div class="lf-center-zone" id="lfCenterZone">
                <!-- Pot and community cards -->
                <div class="lf-center-content">
                    <div class="lf-pot-display" id="lfPotDisplay">Pot: 0 tokens</div>
                    <div class="lf-community-cards" id="lfCommunityCards"></div>
                    <div class="phase-display" id="lfPhaseDisplay">Phase: -</div>
                </div>
                <!-- Current player's cards on the right -->
                <div class="lf-player-zone-inline" id="lfPlayerZone">
                </div>
            </div>
            <div class="lf-player-zone" id="lfPlayerZoneOld" style="display:none;">
            </div>
            <div class="lf-folded-strip" id="lfFoldedStrip">
                <button class="lf-folded-toggle" onclick="toggleFoldedStrip()">Folded (<span id="foldedCount">0</span>)</button>
                <div class="lf-folded-players" id="lfFoldedPlayers"></div>
            </div>
        </div>

        <div class="action-panel" id="actionPanel" style="display: none;">
            <div class="action-buttons" id="actionButtons">
                <button class="btn btn-fold" onclick="playerAction('fold')">Fold</button>
                <button class="btn btn-check" id="checkCallBtn" onclick="playerAction('check')">Check</button>
                <button class="btn btn-raise" onclick="showRaiseControls()">Raise</button>
                <button class="btn btn-allin" onclick="playerAction('all-in')">All In</button>
            </div>
            <div class="raise-controls" id="raiseControls" style="display: none;">
                <div class="bet-buttons" style="margin-bottom: 8px;">
                    <button class="btn btn-bet-amount" onclick="addToBet(5)">+5</button>
                    <button class="btn btn-bet-amount" onclick="addToBet(10)">+10</button>
                    <button class="btn btn-bet-amount" onclick="addToBet(25)">+25</button>
                    <button class="btn btn-bet-amount" onclick="addToBet(50)">+50</button>
                    <button class="btn btn-bet-amount" onclick="addToBet(100)">+100</button>
                    <button class="btn btn-clear-bet" onclick="clearBet()">Clear</button>
                </div>
                <span>Raise to:</span>
                <input type="number" id="raiseAmount" class="raise-input" value="0" min="0">
                <button class="btn btn-raise" onclick="playerAction('raise')">Confirm Raise</button>
                <button class="btn" onclick="hideRaiseControls()">Cancel</button>
            </div>
        </div>
    </div>
    
    <div class="winner-modal" id="winnerModal">
        <div class="winner-content">
            <h2>🏆 Winner!</h2>
            <div class="winner-details" id="winnerDetails"></div>
            <button class="btn btn-primary" id="winnerCloseBtn" onclick="closeWinnerModal()">
                Continue (<span id="winnerCountdown">35</span>s)
            </button>
        </div>
    </div>

    <script>
        let socket = io({
            transports: ['websocket', 'polling'],
            reconnection: true,
            reconnectionAttempts: 10,
            reconnectionDelay: 1000,
            reconnectionDelayMax: 5000,
            timeout: 20000
        });
        let gameState = null;
        let sessionId = null;
        let myPlayerName = null;

        // Display mode and theme preferences
        let currentDisplayMode = 'standard';
        let currentTheme = 'green';

        function setDisplayMode(mode) {
            currentDisplayMode = mode;
            document.body.setAttribute('data-display-mode', mode);
            savePreferences();
            if (gameState) updateDisplay();
        }

        function setTheme(theme) {
            currentTheme = theme;
            document.body.setAttribute('data-theme', theme);
            savePreferences();
        }

        function savePreferences() {
            if (!myPlayerName) return;
            localStorage.setItem(`poker_prefs_${myPlayerName}`,
                JSON.stringify({ theme: currentTheme, displayMode: currentDisplayMode }));
        }

        function loadPreferences() {
            if (!myPlayerName) return;
            const saved = localStorage.getItem(`poker_prefs_${myPlayerName}`);
            if (saved) {
                try {
                    const prefs = JSON.parse(saved);
                    if (prefs.theme) {
                        currentTheme = prefs.theme;
                        document.body.setAttribute('data-theme', prefs.theme);
                        document.getElementById('themeSelect').value = prefs.theme;
                    }
                    if (prefs.displayMode) {
                        currentDisplayMode = prefs.displayMode;
                        document.body.setAttribute('data-display-mode', prefs.displayMode);
                        document.getElementById('displayMode').value = prefs.displayMode;
                    }
                } catch (e) {
                    console.log('Error loading preferences:', e);
                }
            }
        }

        function toggleFoldedStrip() {
            const strip = document.getElementById('lfFoldedStrip');
            if (strip) strip.classList.toggle('expanded');
        }

        // Show loading state in dropdown initially
        function setDropdownLoading(loading) {
            const dropdown = document.getElementById('playerName');
            const joinStatus = document.getElementById('joinStatus');
            if (loading) {
                dropdown.innerHTML = '<option value="">⏳ Connecting to server...</option>';
                dropdown.disabled = true;
                if (joinStatus) joinStatus.textContent = 'Waiting for server connection...';
            } else {
                dropdown.disabled = false;
                if (joinStatus) joinStatus.textContent = '';
            }
        }

        // Set loading state on page load
        setDropdownLoading(true);

        // Socket.IO connection event handlers
        socket.on('connect', () => {
            console.log('Socket connected');
            setDropdownLoading(false);
        });

        socket.on('connect_error', (error) => {
            console.log('Connection error:', error);
            const dropdown = document.getElementById('playerName');
            dropdown.innerHTML = '<option value="">❌ Connection failed - retrying...</option>';
            const joinStatus = document.getElementById('joinStatus');
            if (joinStatus) joinStatus.textContent = 'Server may be starting up, please wait...';
        });

        socket.on('disconnect', (reason) => {
            console.log('Disconnected:', reason);
            const joinStatus = document.getElementById('joinStatus');
            if (joinStatus && !myPlayerName) {
                joinStatus.textContent = 'Disconnected - reconnecting...';
            }
        });

        socket.on('reconnect', (attemptNumber) => {
            console.log('Reconnected after', attemptNumber, 'attempts');
            const joinStatus = document.getElementById('joinStatus');
            if (joinStatus) joinStatus.textContent = '';
        });

        // Socket.IO event listeners
        socket.on('connected', (data) => {
            sessionId = data.session_id;
            console.log('Connected with session:', sessionId);
        });

        socket.on('name_availability', (data) => {
            setDropdownLoading(false);
            updatePlayerNameDropdown(data.all_names, data.taken);
        });

        socket.on('join_success', (data) => {
            myPlayerName = data.name;
            document.getElementById('joinSection').style.display = 'none';
            document.getElementById('gameControls').style.display = 'flex';
            document.getElementById('gameTitle').innerHTML = `<span class="royal-flush-icon"></span> Poker - Multiplayer - ${data.name}`;
            updateResetButtonVisibility();
            updateStatusMessage();
            loadPreferences();
        });

        socket.on('join_failed', (data) => {
            document.getElementById('joinStatus').textContent = data.message;
        });

        socket.on('game_state', (state) => {
            gameState = state;

            // Safe logging with null checks
            const playerInfo = state.players ? state.players.map(p => {
                const cardCount = p.hole_cards ? p.hole_cards.length :
                                 (p.down_cards && p.up_cards ? p.down_cards.length + p.up_cards.length : 0);
                return { id: p.id, name: p.name, cards: cardCount };
            }) : [];

            console.log('Game state received:', {
                myPlayerId: state.my_player_id,
                currentPlayer: state.current_player,
                isMyTurn: state.is_my_turn,
                gameStarted: state.game_started,
                gameMode: state.game_mode,
                hiLo: state.hi_lo,
                players: playerInfo
            });

            // Sync Hi-Lo checkbox with current game state
            const hiLoCheckbox = document.getElementById('hiLoMode');
            if (hiLoCheckbox && state.hi_lo !== undefined) {
                hiLoCheckbox.checked = state.hi_lo;
            }

            // Sync Two Sevens checkbox with current game state
            const twoSevensCheckbox = document.getElementById('twoSevensMode');
            if (twoSevensCheckbox && state.two_natural_sevens_wins !== undefined) {
                twoSevensCheckbox.checked = state.two_natural_sevens_wins;
            }

            // Sync Deal Sevens to Michael checkbox with current game state
            const dealSevensCheckbox = document.getElementById('dealSevensToMichael');
            if (dealSevensCheckbox && state.deal_sevens_to_michael !== undefined) {
                dealSevensCheckbox.checked = state.deal_sevens_to_michael;
            }

            updateDisplay();
            updateButtons();
            updateStatusMessage();
        });

        socket.on('game_locked', (data) => {
            console.log(data.message);
        });

        socket.on('new_game_button_disabled', () => {
            const newGameBtn = document.getElementById('newGameBtn');
            if (newGameBtn) {
                newGameBtn.disabled = true;
            }
        });

        socket.on('new_game_button_enabled', () => {
            const newGameBtn = document.getElementById('newGameBtn');
            if (newGameBtn) {
                newGameBtn.disabled = false;
            }
        });

        socket.on('game_reset', (data) => {
            // Game has been reset - reload the page to start fresh
            alert(data.message);
            location.reload();
        });

        socket.on('server_restart', (data) => {
            // Server is restarting - show message and auto-reload after delay
            document.body.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: linear-gradient(135deg, #1a3555 0%, #2c5a8f 100%); color: white; font-family: Arial, sans-serif;">
                    <h1 style="font-size: 3rem; margin-bottom: 20px;">🔄 Server Restarting</h1>
                    <p style="font-size: 1.5rem; color: #ffd700;">${data.message}</p>
                    <p style="font-size: 1.2rem; margin-top: 30px;">Page will refresh automatically in <span id="countdown">5</span> seconds...</p>
                </div>
            `;
            let seconds = 5;
            const countdown = setInterval(() => {
                seconds--;
                const el = document.getElementById('countdown');
                if (el) el.textContent = seconds;
                if (seconds <= 0) {
                    clearInterval(countdown);
                    location.reload();
                }
            }, 1000);
        });

        socket.on('winners', (data) => {
            // Build winner display HTML with Hi-Lo support
            let winnerHTML = '';
            const isHiLo = data.hi_lo || false;

            data.winners.forEach(w => {
                // Determine win type badge styling
                let winTypeBadge = '';
                let winTypeColor = '#ffd700';

                if (w.win_type === 'low') {
                    winTypeBadge = '📉 LOW';
                    winTypeColor = '#2ecc71';
                } else if (w.win_type === 'SCOOP (high + low)') {
                    winTypeBadge = '🎯 SCOOP!';
                    winTypeColor = '#e74c3c';
                } else if (w.win_type === 'high (scoops - no qualifying low)') {
                    winTypeBadge = '📈 HIGH (No Low)';
                    winTypeColor = '#ffd700';
                } else if (w.win_type === 'high' && isHiLo) {
                    winTypeBadge = '📈 HIGH';
                    winTypeColor = '#ffd700';
                }

                // Build hand description
                let handDesc = w.hand || '';
                if (w.win_type === 'SCOOP (high + low)' && w.low_hand) {
                    handDesc = `${w.hand} + ${w.low_hand}`;
                }

                winnerHTML += `<div class="winner-entry">
                    <div class="winner-name">${w.player.name}</div>
                    ${winTypeBadge ? `<div style="color: ${winTypeColor}; font-weight: bold; font-size: 0.9rem;">${winTypeBadge}</div>` : ''}
                    <div class="winner-amount">Wins ${formatMoney(w.amount)} tokens ($${tokensToDollars(w.amount)})</div>
                    ${handDesc ? `<div class="winner-hand">${handDesc}</div>` : ''}
                </div>`;
            });

            // Show the winner modal
            const winnerDetails = document.getElementById('winnerDetails');
            const winnerModal = document.getElementById('winnerModal');
            if (winnerDetails && winnerModal) {
                winnerDetails.innerHTML = winnerHTML;
                winnerModal.style.display = 'flex';

                // Start countdown timer
                let countdown = 35;
                const countdownEl = document.getElementById('winnerCountdown');
                if (countdownEl) countdownEl.textContent = countdown;

                // Clear any existing countdown
                if (winnerCountdownInterval) {
                    clearInterval(winnerCountdownInterval);
                }

                winnerCountdownInterval = setInterval(() => {
                    countdown--;
                    if (countdownEl) countdownEl.textContent = countdown;
                    if (countdown <= 0) {
                        closeWinnerModal(true);  // true = auto-closed, will start new hand
                    }
                }, 1000);
            }

            // Also update status message
            let winnerText = data.winners.map(w => {
                let typeLabel = '';
                if (isHiLo && w.win_type !== 'fold') {
                    if (w.win_type === 'low') typeLabel = ' (Low)';
                    else if (w.win_type === 'SCOOP (high + low)') typeLabel = ' (SCOOP!)';
                    else if (w.win_type.includes('high')) typeLabel = ' (High)';
                }
                return `${w.player.name} wins ${formatMoney(w.amount)} tokens${typeLabel}${w.hand ? ` with ${w.hand}` : ''}`;
            }).join('. ');
            const statusEl = document.getElementById('gameStatus');
            if (statusEl) {
                statusEl.innerHTML = `<strong style="color: #ffd700; font-size: 1.2rem;">🏆 ${winnerText}</strong><br><em>Click your down cards to reveal them to other players.</em>`;
            }

            // Game stays in showdown phase - no auto-reset
            console.log('Hand complete:', winnerText);
        });

        // Handle two natural 7s instant win
        socket.on('two_sevens_win', (data) => {
            let winnerHTML = '';

            data.winners.forEach(w => {
                winnerHTML += `<div class="winner-entry">
                    <div class="winner-name" style="color: #ff6b6b;">${w.player.name}</div>
                    <div style="color: #ff6b6b; font-weight: bold; font-size: 1.2rem;">🎰 TWO NATURAL 7s! 🎰</div>
                    <div class="winner-amount">Wins ${formatMoney(w.amount)} tokens ($${tokensToDollars(w.amount)})</div>
                    <div class="winner-hand" style="color: #ff6b6b;">Instant Win - Two Natural 7s</div>
                </div>`;
            });

            // Show the winner modal with special styling
            const winnerDetails = document.getElementById('winnerDetails');
            const winnerModal = document.getElementById('winnerModal');
            if (winnerDetails && winnerModal) {
                winnerDetails.innerHTML = winnerHTML;
                winnerModal.style.display = 'flex';

                // Start countdown timer
                let countdown = 35;
                const countdownEl = document.getElementById('winnerCountdown');
                if (countdownEl) countdownEl.textContent = countdown;

                if (winnerCountdownInterval) {
                    clearInterval(winnerCountdownInterval);
                }

                winnerCountdownInterval = setInterval(() => {
                    countdown--;
                    if (countdownEl) countdownEl.textContent = countdown;
                    if (countdown <= 0) {
                        closeWinnerModal(true);
                    }
                }, 1000);
            }

            // Update status message
            const w = data.winners[0];
            const statusEl = document.getElementById('gameStatus');
            if (statusEl) {
                statusEl.innerHTML = `<strong style="color: #ff6b6b; font-size: 1.3rem;">🎰 ${w.player.name} WINS WITH TWO NATURAL 7s! 🎰</strong><br>Wins ${formatMoney(w.amount)} tokens instantly!`;
            }

            // Auto-reveal the winner's cards after a delay (3 seconds)
            setTimeout(() => {
                socket.emit('reveal_two_sevens_winner');
            }, 3000);

            console.log('Two Natural 7s Win:', w.player.name);
        });

        // Handle card reveal from other players
        socket.on('cards_revealed', (data) => {
            console.log('Cards revealed by player:', data.player_name, data.cards);
            // Refresh game state to show revealed cards
            if (gameState) {
                // Update the player's down cards to be visible
                const playerIdx = data.player_id;
                if (gameState.players && gameState.players[playerIdx]) {
                    gameState.players[playerIdx].down_cards = data.cards;
                    gameState.players[playerIdx].cards_revealed = true;
                    updateDisplay();
                }
            }
        });

        socket.on('error', (data) => {
            alert(data.message);
        });

        // Game functions
        function updatePlayerNameDropdown(allNames, takenNames) {
            const dropdown = document.getElementById('playerName');
            const currentSelection = dropdown.value;

            // Clear existing options except the first placeholder
            dropdown.innerHTML = '<option value="">-- Select Your Name --</option>';

            // Add all names
            allNames.forEach(name => {
                const option = document.createElement('option');
                option.value = name;
                option.textContent = name;

                // Disable and style taken names
                if (takenNames.includes(name)) {
                    option.disabled = true;
                    option.style.color = '#999';
                    option.style.fontStyle = 'italic';
                    option.textContent = `${name} (taken)`;
                }

                dropdown.appendChild(option);
            });

            // Restore selection if it's still available
            if (currentSelection && !takenNames.includes(currentSelection)) {
                dropdown.value = currentSelection;
            }
        }

        function joinGame() {
            console.log('joinGame() called');  // DEBUG
            const playerName = document.getElementById('playerName').value.trim();
            console.log('Player name:', playerName);  // DEBUG

            if (!playerName || playerName === '') {
                console.log('No player name selected');  // DEBUG
                document.getElementById('joinStatus').textContent = 'Please select a name';
                return;
            }

            document.getElementById('joinStatus').textContent = '';
            console.log('Emitting join_game event with name:', playerName);  // DEBUG
            socket.emit('join_game', { name: playerName });
            console.log('join_game event emitted');  // DEBUG
        }

        function newGame() {
            const hiLo = document.getElementById('hiLoMode').checked;
            const twoSevens = document.getElementById('twoSevensMode').checked;
            const dealSevensToMichael = document.getElementById('dealSevensToMichael').checked;
            socket.emit('new_game', {
                game_mode: 'stud_follow_queen',
                num_players: 7,
                hi_lo: hiLo,
                two_natural_sevens_wins: twoSevens,
                deal_sevens_to_michael: dealSevensToMichael
            });
        }

        function startGame() {
            socket.emit('start_game');
        }

        function newHand() {
            socket.emit('new_hand');
        }

        function resetGame() {
            if (confirm('Are you sure you want to reset the entire game? This will clear all players and start fresh.')) {
                socket.emit('reset_game');
            }
        }

        function playerAction(action) {
            let amount = 0;
            if (action === 'raise') {
                amount = parseInt(document.getElementById('raiseAmount').value) || 0;
                if (amount < 0) amount = 0;
            }

            hideRaiseControls();
            socket.emit('player_action', { action, amount });
        }

        function updateButtons() {
            const startGameBtn = document.getElementById('startGameBtn');
            const newHandBtn = document.getElementById('newHandBtn');

            if (!gameState || gameState.my_player_id === null || gameState.my_player_id === undefined) {
                startGameBtn.style.display = 'none';
                newHandBtn.style.display = 'none';
                return;
            }

            const isDealer = gameState.my_player_id === gameState.dealer_position;

            // Show Start Game button if game hasn't started yet
            if (!gameState.game_started) {
                startGameBtn.style.display = 'inline-block';
                newHandBtn.style.display = 'none';
                // Only dealer can start game, and need at least 2 players
                if (isDealer && gameState.players.length >= 2) {
                    startGameBtn.disabled = false;
                    startGameBtn.style.opacity = '1';
                } else {
                    startGameBtn.disabled = true;
                    startGameBtn.style.opacity = '0.5';
                }
            } else {
                // Game has started - show New Hand button only for dealer
                startGameBtn.style.display = 'none';
                newHandBtn.style.display = 'inline-block';

                // Only enable if this player is the dealer
                if (isDealer) {
                    newHandBtn.disabled = false;
                    newHandBtn.style.opacity = '1';
                } else {
                    newHandBtn.disabled = true;
                    newHandBtn.style.opacity = '0.5';
                }
            }

            // Reset Server button - dealer can use it (or anyone if not yet joined)
            const resetBtn = document.getElementById('resetGameBtn');
            if (resetBtn) {
                if (isDealer) {
                    resetBtn.disabled = false;
                    resetBtn.style.opacity = '1';
                } else {
                    resetBtn.disabled = true;
                    resetBtn.style.opacity = '0.5';
                }
            }
        }

        function updateResetButtonForJoinScreen() {
            // On join screen (before joining), anyone can reset
            const resetBtn = document.getElementById('resetGameBtn');
            if (resetBtn) {
                resetBtn.disabled = false;
                resetBtn.style.opacity = '1';
            }
        }

        function updateResetButtonVisibility() {
            const resetBtn = document.getElementById('resetGameBtn');
            resetBtn.style.display = 'inline-block';
            // On join screen (not yet in game), enable for everyone
            // Once in game, updateButtons() will restrict to dealer only
            if (!gameState || gameState.my_player_id === null || gameState.my_player_id === undefined) {
                resetBtn.disabled = false;
                resetBtn.style.opacity = '1';
            }
        }

        function updateStatusMessage() {
            if (!gameState) return;

            const statusEl = document.getElementById('gameStatus');

            if (!gameState.game_started) {
                const playerCount = gameState.players ? gameState.players.length : 0;
                const maxPlayers = gameState.num_players || 6;
                statusEl.textContent = `Waiting for additional players (${playerCount}/${maxPlayers}). Click "Start Game" when ready (minimum 2 players).`;
            } else if (gameState.phase === 'showdown') {
                statusEl.textContent = 'Hand complete! Dealer can deal next hand.';
            } else if (gameState.is_my_turn) {
                statusEl.textContent = 'Your turn to act!';
            } else if (gameState.players && gameState.current_player >= 0) {
                const currentPlayer = gameState.players[gameState.current_player];
                statusEl.textContent = `Waiting for ${currentPlayer ? currentPlayer.name : 'player'}...`;
            }
        }

        function createCardHTML(card, extraClass = '') {
            if (!card || card.suit === 'back') {
                return `<div class="card back ${extraClass}"></div>`;
            }
            // Check if card is wild (Queens always wild, plus current wild rank)
            const wildRank = gameState ? gameState.current_wild_rank : 'Q';
            const isWild = card.rank === 'Q' || card.rank === wildRank;
            const wildClass = isWild ? 'wild' : '';
            return `
                <div class="card ${card.suit} ${extraClass} ${wildClass}">
                    <div class="card-corner top">
                        <span class="card-rank">${card.rank}</span>
                        <span class="card-suit">${card.symbol}</span>
                    </div>
                    <div class="card-center">${card.symbol}</div>
                    <div class="card-corner bottom">
                        <span class="card-rank">${card.rank}</span>
                        <span class="card-suit">${card.symbol}</span>
                    </div>
                </div>
            `;
        }

        function updateWildCardDisplay(gameState) {
            try {
                const wildPanel = document.getElementById('wildCardPanel');
                const currentWildEl = document.getElementById('currentWild');
                const wildHistoryEl = document.getElementById('wildHistory');

                if (!wildPanel || !currentWildEl || !wildHistoryEl) return;

                if (gameState.game_mode !== 'stud_follow_queen') {
                    wildPanel.style.display = 'none';
                    return;
                }

                wildPanel.style.display = 'block';

            // Current wild rank
            const wildRank = gameState.current_wild_rank;
            const wildText = wildRank === 'Q' ? 'Queens Only' : `Queens and ${wildRank}s`;
            currentWildEl.innerHTML = `<span class="royal-flush-icon large"></span> Wild Cards: <span style="font-size: 3rem;">${wildText}</span>`;

            // Wild card history
            if (gameState.wild_card_history && gameState.wild_card_history.length > 0) {
                let historyHTML = '';
                gameState.wild_card_history.forEach((change, i) => {
                    historyHTML += `
                        <div class="wild-change-badge">
                            ${change.phase.replace('_', ' ')}: ${change.player_name} → ${change.new_wild_rank}s wild
                        </div>
                    `;
                });
                wildHistoryEl.innerHTML = historyHTML;
            } else {
                wildHistoryEl.innerHTML = '<div class="wild-change-badge">No wild card changes yet</div>';
            }
            } catch (error) {
                console.error('Error in updateWildCardDisplay:', error);
            }
        }

        // Evaluate current poker hand from visible cards
        function evaluateCurrentHand(downCards, upCards, wildRank) {
            // Combine all visible cards (not hidden)
            const allCards = [];

            (downCards || []).forEach(card => {
                if (!card.hidden && card.rank && card.suit) {
                    allCards.push(card);
                }
            });

            (upCards || []).forEach(card => {
                if (card.rank && card.suit) {
                    allCards.push(card);
                }
            });

            if (allCards.length < 2) return null;

            // Count ranks and suits, track cards by rank
            const rankOrder = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A'];
            const rankCounts = {};
            const cardsByRank = {};
            const suitCounts = {};
            const cardsBySuit = {};
            const wildCards = [];

            allCards.forEach(card => {
                // Check if this card is wild (Queen or the current wild rank)
                const isWild = card.rank === 'Q' || (wildRank && card.rank === wildRank);
                if (isWild) {
                    wildCards.push(card);
                } else {
                    rankCounts[card.rank] = (rankCounts[card.rank] || 0) + 1;
                    if (!cardsByRank[card.rank]) cardsByRank[card.rank] = [];
                    cardsByRank[card.rank].push(card);
                }
                suitCounts[card.suit] = (suitCounts[card.suit] || 0) + 1;
                if (!cardsBySuit[card.suit]) cardsBySuit[card.suit] = [];
                cardsBySuit[card.suit].push(card);
            });

            const wildCount = wildCards.length;

            // Find the rank with most cards
            const sortedRanks = Object.keys(rankCounts).sort((a, b) => {
                if (rankCounts[b] !== rankCounts[a]) return rankCounts[b] - rankCounts[a];
                return rankOrder.indexOf(b) - rankOrder.indexOf(a);
            });

            const bestRank = sortedRanks[0];
            const secondRank = sortedRanks[1];
            const maxOfKind = (rankCounts[bestRank] || 0) + wildCount;
            const secondOfKind = rankCounts[secondRank] || 0;

            // Check for flush (5+ of same suit)
            const flushSuit = Object.keys(suitCounts).find(s => suitCounts[s] >= 5);
            const hasFlush = !!flushSuit;

            // Helper to format result with cards
            function result(name, cards) {
                const cardsStr = cardsToShortNotation(cards);
                return cardsStr ? `${name} (${cardsStr})` : name;
            }

            // Get hand cards for of-a-kind hands
            function getOfAKindCards(rank, count) {
                const cards = [...(cardsByRank[rank] || [])];
                // Add wild cards to complete the hand
                for (let i = 0; i < wildCards.length && cards.length < count; i++) {
                    cards.push(wildCards[i]);
                }
                return cards;
            }

            // Check for straight (including with wild cards)
            function checkStraight(cards, wilds) {
                // Get unique rank indices of non-wild cards
                const nonWildRankIndices = [];
                cards.forEach(card => {
                    const isWild = card.rank === 'Q' || (wildRank && card.rank === wildRank);
                    if (!isWild) {
                        const idx = rankOrder.indexOf(card.rank);
                        if (idx !== -1 && !nonWildRankIndices.includes(idx)) {
                            nonWildRankIndices.push(idx);
                        }
                    }
                });
                nonWildRankIndices.sort((a, b) => a - b);

                const numWilds = wilds.length;
                const numNonWilds = nonWildRankIndices.length;

                // Need at least 5 total cards to make a straight
                if (numNonWilds + numWilds < 5) return null;

                // Try to find a 5-card straight window
                // Check each possible starting position (0=2 through 9=10 for regular, or wheel A-5)
                for (let start = 9; start >= 0; start--) {
                    // Check if we can make a straight from 'start' to 'start+4'
                    let gaps = 0;
                    let straightCards = [];
                    for (let i = start; i <= start + 4; i++) {
                        if (nonWildRankIndices.includes(i)) {
                            // Find a card with this rank
                            const rank = rankOrder[i];
                            const card = cards.find(c => c.rank === rank && !straightCards.includes(c));
                            if (card) straightCards.push(card);
                        } else {
                            gaps++;
                        }
                    }
                    if (gaps <= numWilds) {
                        // We can make this straight with wilds
                        for (let i = 0; i < gaps && i < wilds.length; i++) {
                            straightCards.push(wilds[i]);
                        }
                        return { highCard: start + 4, cards: straightCards };
                    }
                }

                // Check for wheel (A-2-3-4-5) - Ace is index 12
                let wheelGaps = 0;
                let wheelCards = [];
                const wheelIndices = [12, 0, 1, 2, 3]; // A, 2, 3, 4, 5
                for (const i of wheelIndices) {
                    if (nonWildRankIndices.includes(i)) {
                        const rank = rankOrder[i];
                        const card = cards.find(c => c.rank === rank && !wheelCards.includes(c));
                        if (card) wheelCards.push(card);
                    } else {
                        wheelGaps++;
                    }
                }
                if (wheelGaps <= numWilds) {
                    for (let i = 0; i < wheelGaps && i < wilds.length; i++) {
                        wheelCards.push(wilds[i]);
                    }
                    return { highCard: 3, cards: wheelCards }; // 5-high straight
                }

                return null;
            }

            // Check for straight flush
            function checkStraightFlush() {
                for (const suit of Object.keys(cardsBySuit)) {
                    const suitCards = cardsBySuit[suit];
                    // Include wild cards of this suit
                    const wildsInSuit = wildCards.filter(c => c.suit === suit);
                    if (suitCards.length + wildsInSuit.length >= 5) {
                        const straightResult = checkStraight(suitCards, wildsInSuit);
                        if (straightResult) {
                            return { ...straightResult, suit: suit };
                        }
                    }
                }
                return null;
            }

            // Evaluate hand (check in order of hand strength)
            if (maxOfKind >= 5) {
                return result("Five of a Kind!", getOfAKindCards(bestRank, 5));
            }

            // Check for straight flush (before regular flush or straight)
            const straightFlush = checkStraightFlush();
            if (straightFlush) {
                if (straightFlush.highCard === 12) {
                    return result("Royal Flush!", straightFlush.cards);
                }
                return result("Straight Flush", straightFlush.cards);
            }

            if (maxOfKind >= 4) {
                return result("Four of a Kind", getOfAKindCards(bestRank, 4));
            }
            if (maxOfKind >= 3 && secondOfKind >= 2) {
                const tripCards = getOfAKindCards(bestRank, 3);
                const pairCards = (cardsByRank[secondRank] || []).slice(0, 2);
                return result("Full House", [...tripCards, ...pairCards]);
            }
            if (hasFlush) {
                return result("Flush", cardsBySuit[flushSuit].slice(0, 5));
            }

            // Check for regular straight
            const straight = checkStraight(allCards, wildCards);
            if (straight) {
                return result("Straight", straight.cards);
            }

            if (maxOfKind >= 3) {
                return result("Three of a Kind", getOfAKindCards(bestRank, 3));
            }
            if (maxOfKind >= 2 && secondOfKind >= 2) {
                const pair1 = getOfAKindCards(bestRank, 2);
                const pair2 = (cardsByRank[secondRank] || []).slice(0, 2);
                return result("Two Pair", [...pair1, ...pair2]);
            }
            if (maxOfKind >= 2) {
                return result("Pair", getOfAKindCards(bestRank, 2));
            }
            if (wildCount > 0) {
                return result("Wild Card", wildCards);
            }

            // High card
            if (sortedRanks.length > 0) {
                const highCard = sortedRanks[0];
                const displayRank = highCard === 'A' ? 'Ace' :
                                   highCard === 'K' ? 'King' :
                                   highCard === 'Q' ? 'Queen' :
                                   highCard === 'J' ? 'Jack' : highCard;
                return result(`${displayRank} High`, [cardsByRank[highCard][0]]);
            }

            return "No Hand";
        }

        // Format a card to 2-character notation (e.g., "A♥" for Ace of hearts)
        function cardToShortNotation(card) {
            if (!card || !card.rank || !card.suit) return '??';
            const rankChar = card.rank === '10' ? 'T' : card.rank;
            const suitSymbols = { hearts: '♥', diamonds: '♦', clubs: '♣', spades: '♠' };
            const suitChar = suitSymbols[card.suit] || card.suit.charAt(0);
            return rankChar + suitChar;
        }

        // Format an array of cards to 2-character notation string
        function cardsToShortNotation(cards) {
            if (!cards || !Array.isArray(cards) || cards.length === 0) return '';
            return cards.map(cardToShortNotation).join(' ');
        }

        // Format tokens as integer
        function formatMoney(amount) {
            return Math.floor(amount);
        }

        // Convert tokens to dollars (100 tokens = $1)
        function tokensToDollars(tokens) {
            return (tokens / 100).toFixed(2);
        }

        function renderStudTable(gameState) {
            try {
                // Safety check for players array
                if (!gameState || !gameState.players || !Array.isArray(gameState.players)) {
                    console.warn('Invalid gameState in renderStudTable', {
                        hasGameState: !!gameState,
                        hasPlayers: !!gameState?.players,
                        isArray: Array.isArray(gameState?.players),
                        playersLength: gameState?.players?.length,
                        gameState: gameState
                    });
                    return;
                }

                // New Stud-specific rendering
                console.log('renderStudTable called with', gameState.players.length, 'players');  // DEBUG
                const studPlayersGrid = document.getElementById('studPlayersGrid');
                console.log('studPlayersGrid element found:', !!studPlayersGrid);  // DEBUG
                if (!studPlayersGrid) {
                    console.error('studPlayersGrid element not found!');  // DEBUG
                    return;
                }

            let playersHTML = '';
            gameState.players.forEach((player, idx) => {
                const isActive = idx === gameState.current_player && !gameState.round_complete;

                // Build down cards HTML (vertical)
                let downCardsHTML = '';
                (player.down_cards || []).forEach((card, i) => {
                    downCardsHTML += createCardHTML(card);
                    downCardsHTML += `<div class="street-indicator">Down ${i + 1}</div>`;
                });

                // Build up cards HTML (vertical with street labels)
                let upCardsHTML = '';
                (player.up_cards || []).forEach((card, i) => {
                    upCardsHTML += createCardHTML(card);
                    const street = i === 0 ? '3rd' : i === 1 ? '4th' : i === 2 ? '5th' : '6th';
                    upCardsHTML += `<div class="street-indicator">${street} Street</div>`;
                });

                // Player status
                let statusHTML = '';
                if (player.folded) {
                    statusHTML = '<span class="player-status status-folded">FOLDED</span>';
                } else if (player.is_all_in) {
                    statusHTML = '<span class="player-status status-all-in">ALL IN</span>';
                }

                // Hand result (high and low in Hi-Lo mode)
                let handResultHTML = '';
                if (player.hand_result && gameState.phase === 'showdown') {
                    const cardsStr = player.hand_result.best_cards ? cardsToShortNotation(player.hand_result.best_cards) : '';
                    const highLabel = gameState.hi_lo ? '<span style="color: #ffd700;">HIGH:</span> ' : '';
                    handResultHTML = `<div class="hand-result">${highLabel}${player.hand_result.name}${cardsStr ? ' (' + cardsStr + ')' : ''}</div>`;

                    // Show low hand if Hi-Lo mode
                    if (gameState.hi_lo && player.low_result) {
                        if (player.low_result.qualifies) {
                            const lowCardsStr = player.low_result.best_cards ? cardsToShortNotation(player.low_result.best_cards) : '';
                            handResultHTML += `<div class="hand-result" style="color: #2ecc71;"><span>LOW:</span> ${player.low_result.name}${lowCardsStr ? ' (' + lowCardsStr + ')' : ''}</div>`;
                        } else {
                            handResultHTML += `<div class="hand-result" style="color: #e74c3c; opacity: 0.7;"><span>LOW:</span> No Qualifier</div>`;
                        }
                    }
                }

                // Check if this player's down cards are visible (not hidden)
                // Only show hand evaluation for the current viewer's own cards
                // Hidden cards have rank='?' or hidden=true
                const canSeeDownCards = (player.down_cards || []).some(card => !card.hidden && card.rank !== '?');
                let currentHandHTML = '';
                if (canSeeDownCards && !player.folded) {
                    const handName = evaluateCurrentHand(
                        player.down_cards,
                        player.up_cards,
                        gameState.current_wild_rank
                    );
                    if (handName) {
                        currentHandHTML = `<div class="current-hand-display">${handName}</div>`;
                    }
                }

                // Check if this is the current player's own cards and it's showdown
                const isMyCards = idx === gameState.my_player_id;
                const isShowdown = gameState.phase === 'showdown';
                const canReveal = isMyCards && isShowdown && !player.cards_revealed;
                const revealClass = canReveal ? 'clickable-reveal' : '';
                const revealClick = canReveal ? 'onclick="revealMyCards()"' : '';
                const revealHint = canReveal ? '<div class="reveal-hint">Click to reveal</div>' : '';

                playersHTML += `
                    <div class="stud-player-card ${isActive ? 'active' : ''} ${player.folded ? 'folded' : ''}">
                        <div class="player-info">
                            <div class="player-name">
                                ${player.name}
                                ${player.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
                            </div>
                            <div class="player-chips">${formatMoney(player.chips)} tokens <span class="dollar-equiv">($${tokensToDollars(player.chips)})</span></div>
                            ${player.last_win > 0 ? `<div class="player-last-win" style="color: #2ecc71; font-size: 0.85rem;">Last win: +${formatMoney(player.last_win)}</div>` : ''}
                            ${player.current_bet > 0 ? `<div class="player-bet">Bet: ${formatMoney(player.current_bet)}</div>` : ''}
                            ${statusHTML}
                            ${handResultHTML}
                        </div>
                        <div class="card-progression">
                            <div class="down-cards-group ${revealClass}" ${revealClick}>
                                <label>Down Cards</label>
                                <div class="cards-vertical">
                                    ${downCardsHTML || '<div style="color: #666;">No cards yet</div>'}
                                </div>
                                ${revealHint}
                            </div>
                            <div class="up-cards-group">
                                <label>Up Cards</label>
                                <div class="cards-vertical">
                                    ${upCardsHTML || '<div style="color: #666;">No cards yet</div>'}
                                </div>
                            </div>
                        </div>
                        ${currentHandHTML}
                    </div>
                `;
            });

            studPlayersGrid.innerHTML = playersHTML;

            // Update Stud pot and phase
            const studPotEl = document.getElementById('studPotAmount');
            const studPhaseEl = document.getElementById('studPhaseDisplay');

            if (studPotEl) studPotEl.textContent = formatMoney(gameState.pot);
            const studPotDollarsEl = document.getElementById('studPotDollars');
            if (studPotDollarsEl) studPotDollarsEl.textContent = tokensToDollars(gameState.pot);

            if (studPhaseEl) {
                const PHASE_NAMES = {
                    'third_street': 'Third Street',
                    'fourth_street': 'Fourth Street',
                    'fifth_street': 'Fifth Street',
                    'sixth_street': 'Sixth Street',
                    'seventh_street': 'Seventh Street',
                    'showdown': 'Showdown'
                };
                studPhaseEl.textContent = PHASE_NAMES[gameState.phase] || gameState.phase;
            }

            // Show/hide Hi-Lo badge
            const hiLoBadge = document.getElementById('hiLoBadge');
            if (hiLoBadge) {
                hiLoBadge.style.display = gameState.hi_lo ? 'inline-block' : 'none';
            }

            // Show/hide Two Sevens badge
            const twoSevensBadge = document.getElementById('twoSevensBadge');
            if (twoSevensBadge) {
                twoSevensBadge.style.display = gameState.two_natural_sevens_wins ? 'inline-block' : 'none';
            }
            } catch (error) {
                console.error('Error in renderStudTable:', error);
            }
        }

        function renderHoldemTable(gameState) {
            try {
            // Safety check for players array
            if (!gameState || !gameState.players || !Array.isArray(gameState.players)) {
                console.warn('Invalid gameState in renderHoldemTable');
                return;
            }

            // Update pot and phase
            const potEl = document.getElementById('potAmount');
            const phaseEl = document.getElementById('phaseDisplay');

            if (potEl) potEl.textContent = formatMoney(gameState.pot);
            const potDollarsEl = document.getElementById('potDollars');
            if (potDollarsEl) potDollarsEl.textContent = tokensToDollars(gameState.pot);

            if (phaseEl) {
                const PHASE_NAMES = {
                    'pre-flop': 'Pre-Flop',
                    'flop': 'Flop',
                    'turn': 'Turn',
                    'river': 'River',
                    'showdown': 'Showdown'
                };
                phaseEl.textContent = PHASE_NAMES[gameState.phase] || gameState.phase;
            }

            // Update community cards
            const communityDiv = document.getElementById('communityCards');
            if (communityDiv) {
                let communityHTML = '';

                if (gameState.community_cards) {
                    const totalCommunity = 5;
                    const revealed = gameState.community_cards.length;

                    for (let i = 0; i < totalCommunity; i++) {
                        if (i < revealed) {
                            communityHTML += createCardHTML(gameState.community_cards[i], 'community card-deal');
                        } else {
                            communityHTML += '<div class="card community placeholder"></div>';
                        }
                    }
                }
                communityDiv.innerHTML = communityHTML;
            }

            // Update players
            const playersDiv = document.getElementById('playersArea');
            if (!playersDiv) return;
            let playersHTML = '';

            gameState.players.forEach((player, idx) => {
                const isActive = idx === gameState.current_player && !gameState.round_complete;
                const classes = [
                    'player-spot',
                    isActive ? 'active' : '',
                    player.folded ? 'folded' : '',
                    player.is_human ? 'human' : ''
                ].filter(Boolean).join(' ');

                let statusHTML = '';
                if (player.folded) {
                    statusHTML = '<span class="player-status status-folded">FOLDED</span>';
                } else if (player.is_all_in) {
                    statusHTML = '<span class="player-status status-all-in">ALL IN</span>';
                }

                let handResultHTML = '';
                if (player.hand_result && gameState.phase === 'showdown') {
                    const cardsStr = player.hand_result.best_cards ? cardsToShortNotation(player.hand_result.best_cards) : '';
                    handResultHTML = `<div class="hand-result">${player.hand_result.name}${cardsStr ? ' (' + cardsStr + ')' : ''}</div>`;
                }

                const cardsHTML = player.hole_cards ? player.hole_cards.map(c => createCardHTML(c)).join('') : '';

                playersHTML += `
                    <div class="${classes}">
                        <div class="player-name">
                            ${player.name}
                            ${player.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
                        </div>
                        <div class="player-chips">${formatMoney(player.chips)} tokens <span class="dollar-equiv">($${tokensToDollars(player.chips)})</span></div>
                        ${player.last_win > 0 ? `<div class="player-last-win" style="color: #2ecc71; font-size: 0.85rem;">Last win: +${formatMoney(player.last_win)}</div>` : ''}
                        ${player.current_bet > 0 ? `<div class="player-bet">Bet: ${formatMoney(player.current_bet)}</div>` : ''}
                        <div class="player-cards">
                            ${cardsHTML}
                        </div>
                        ${statusHTML}
                        ${handResultHTML}
                    </div>
                `;
            });
            playersDiv.innerHTML = playersHTML;
            } catch (error) {
                console.error('Error in renderHoldemTable:', error);
            }
        }

        // Large Format Mode Rendering
        function renderLargeFormatTable() {
            if (!gameState) return;

            try {
                const gameMode = gameState.game_mode || 'holdem';
                const myPlayer = gameState.players.find(p => p.id === gameState.my_player_id);

                // Separate active and folded players
                const activePlayers = gameState.players.filter(p => !p.folded && p.id !== gameState.my_player_id);
                const foldedPlayers = gameState.players.filter(p => p.folded);

                // Sort active opponents by chip stack (highest first)
                activePlayers.sort((a, b) => b.chips - a.chips);

                // Take top 3-4 opponents
                const displayOpponents = activePlayers.slice(0, 4);

                // Render opponents zone
                const opponentsZone = document.getElementById('lfOpponentsZone');
                if (opponentsZone) {
                    let opponentsHTML = '';
                    displayOpponents.forEach((player, idx) => {
                        const isActive = gameState.players.indexOf(player) === gameState.current_player && !gameState.round_complete;
                        opponentsHTML += renderLargeFormatPlayer(player, isActive, gameMode);
                    });
                    opponentsZone.innerHTML = opponentsHTML;
                }

                // Render center zone (pot + community cards)
                const potDisplay = document.getElementById('lfPotDisplay');
                if (potDisplay) {
                    potDisplay.innerHTML = `Pot: ${formatMoney(gameState.pot)} tokens ($${tokensToDollars(gameState.pot)})`;
                }

                const phaseDisplay = document.getElementById('lfPhaseDisplay');
                if (phaseDisplay) {
                    const phaseNames = {
                        'pre_deal': 'Waiting',
                        'pre_flop': 'Pre-Flop',
                        'flop': 'Flop',
                        'turn': 'Turn',
                        'river': 'River',
                        'showdown': 'Showdown',
                        'ante': 'Ante',
                        'third_street': '3rd Street',
                        'fourth_street': '4th Street',
                        'fifth_street': '5th Street',
                        'sixth_street': '6th Street',
                        'seventh_street': '7th Street'
                    };
                    phaseDisplay.innerHTML = `Phase: ${phaseNames[gameState.phase] || gameState.phase}`;
                }

                // Render community cards (for Hold'em) or wild card info (for Stud)
                const communityCards = document.getElementById('lfCommunityCards');
                if (communityCards) {
                    if (gameMode === 'holdem' && gameState.community_cards) {
                        let cardsHTML = '';
                        for (let i = 0; i < 5; i++) {
                            if (gameState.community_cards[i]) {
                                cardsHTML += createCardHTML(gameState.community_cards[i], true);
                            } else {
                                cardsHTML += '<div class="card community placeholder"></div>';
                            }
                        }
                        communityCards.innerHTML = cardsHTML;
                    } else if (gameMode === 'stud_follow_queen') {
                        // Show wild card info for stud
                        const wildRank = gameState.current_wild_rank;
                        const wildText = wildRank === 'Q' ? 'Queens Only' : `Queens + ${wildRank}s`;
                        const wildCardInfo = `<div style="font-size: var(--font-critical); color: #ff69b4;">Wild: ${wildText}</div>`;
                        communityCards.innerHTML = wildCardInfo;
                    }
                }

                // Render player zone (my cards)
                const playerZone = document.getElementById('lfPlayerZone');
                if (playerZone && myPlayer) {
                    const isMyTurn = gameState.is_my_turn && !gameState.round_complete;
                    playerZone.innerHTML = renderLargeFormatPlayer(myPlayer, isMyTurn, gameMode, true);
                }

                // Update folded strip
                const foldedCount = document.getElementById('foldedCount');
                if (foldedCount) {
                    foldedCount.textContent = foldedPlayers.length;
                }

                const foldedPlayersDiv = document.getElementById('lfFoldedPlayers');
                if (foldedPlayersDiv) {
                    let foldedHTML = '';
                    foldedPlayers.forEach(player => {
                        foldedHTML += `<div class="lf-folded-player">${player.name} (${formatMoney(player.chips)})</div>`;
                    });
                    foldedPlayersDiv.innerHTML = foldedHTML || '<div class="lf-folded-player">No folded players</div>';
                }
            } catch (error) {
                console.error('Error in renderLargeFormatTable:', error);
            }
        }

        function renderLargeFormatPlayer(player, isActive, gameMode, isCurrentPlayer = false) {
            const classes = [
                'lf-player-spot',
                isActive ? 'active' : '',
                isCurrentPlayer ? 'current-player' : '',
                player.folded ? 'folded' : ''
            ].filter(Boolean).join(' ');

            let statusHTML = '';
            if (player.folded) {
                statusHTML = '<span class="player-status status-folded">FOLDED</span>';
            } else if (player.is_all_in) {
                statusHTML = '<span class="player-status status-all-in">ALL IN</span>';
            }

            let handResultHTML = '';
            if (player.hand_result && gameState.phase === 'showdown') {
                handResultHTML = `<div class="hand-result" style="font-size: calc(var(--font-critical) * 0.7);">${player.hand_result.name}</div>`;
            }

            // Render cards based on game mode
            let cardsHTML = '';
            if (gameMode === 'holdem') {
                cardsHTML = player.hole_cards ? player.hole_cards.map(c => createCardHTML(c)).join('') : '';
            } else if (gameMode === 'stud_follow_queen') {
                // Stud mode: show down cards and up cards
                if (player.down_cards) {
                    cardsHTML += '<div class="down-cards-group" style="display: flex; gap: 5px;">';
                    cardsHTML += player.down_cards.map(c => createCardHTML(c)).join('');
                    cardsHTML += '</div>';
                }
                if (player.up_cards) {
                    cardsHTML += '<div class="up-cards-group" style="display: flex; gap: 5px; margin-top: 5px;">';
                    cardsHTML += player.up_cards.map(c => createCardHTML(c)).join('');
                    cardsHTML += '</div>';
                }
            }

            return `
                <div class="${classes}">
                    <div class="player-name">
                        ${player.name}
                        ${player.is_dealer ? '<span class="dealer-chip">D</span>' : ''}
                    </div>
                    <div class="player-chips">${formatMoney(player.chips)} tokens</div>
                    ${player.current_bet > 0 ? `<div class="player-bet" style="font-size: calc(var(--font-body) * 0.9);">Bet: ${formatMoney(player.current_bet)}</div>` : ''}
                    <div class="player-cards">
                        ${cardsHTML}
                    </div>
                    ${statusHTML}
                    ${handResultHTML}
                </div>
            `;
        }

        function updateDisplay() {
            if (!gameState) return;

            try {
                const gameMode = gameState.game_mode || 'holdem';
                console.log('updateDisplay called with gameMode:', gameMode);  // DEBUG

                // Set game mode attribute on container for CSS switching
                const container = document.querySelector('.game-container');
                console.log('Container found:', !!container);  // DEBUG
                if (container) {
                    container.setAttribute('data-game-mode', gameMode);
                    console.log('Set data-game-mode to:', gameMode);  // DEBUG
                }

                // Update title based on game mode
                const gameTitle = gameMode === 'holdem' ? "Texas Hold'em Poker" : "Follow the Queen Poker";
                const titleElement = document.getElementById('gameTitle');
                if (titleElement && myPlayerName) {
                    titleElement.innerHTML = `<span class="royal-flush-icon"></span> ${gameTitle} - Multiplayer - ${myPlayerName}`;
                } else if (titleElement) {
                    titleElement.innerHTML = `<span class="royal-flush-icon"></span> ${gameTitle} - Multiplayer`;
                }

                // Route to appropriate renderer based on display mode and game mode
                if (currentDisplayMode === 'large') {
                    // Large format mode - use simplified layout for both game types
                    if (gameMode === 'stud_follow_queen') {
                        updateWildCardDisplay(gameState);
                    }
                    renderLargeFormatTable();
                } else {
                    // Standard mode - use original renderers
                    if (gameMode === 'holdem') {
                        renderHoldemTable(gameState);
                    } else if (gameMode === 'stud_follow_queen') {
                        updateWildCardDisplay(gameState);
                        renderStudTable(gameState);
                    }
                }

                // Update action panel (common to both)
                updateActionPanel();
            } catch (error) {
                console.error('Error in updateDisplay:', error);
            }
        }
        
        function updateActionPanel() {
            const panel = document.getElementById('actionPanel');
            const checkCallBtn = document.getElementById('checkCallBtn');

            if (!gameState || gameState.phase === 'showdown' || !gameState.is_my_turn ||
                gameState.my_player_id === null || gameState.my_player_id === undefined) {
                panel.style.display = 'none';
                return;
            }

            panel.style.display = 'block';

            const myPlayer = gameState.players.find(p => p.id === gameState.my_player_id);
            if (!myPlayer) {
                panel.style.display = 'none';
                return;
            }

            const toCall = gameState.current_bet - myPlayer.current_bet;

            if (toCall > 0) {
                checkCallBtn.textContent = `Call ${toCall}`;
                checkCallBtn.onclick = () => playerAction('call');
                checkCallBtn.className = 'btn btn-call';
            } else {
                checkCallBtn.textContent = 'Check';
                checkCallBtn.onclick = () => playerAction('check');
                checkCallBtn.className = 'btn btn-check';
            }

            // Set default raise amount
            document.getElementById('raiseAmount').value = gameState.current_bet * 2 || gameState.ante_amount * 2 || 10;
        }
        
        function showRaiseControls() {
            document.getElementById('raiseControls').style.display = 'flex';
        }
        
        function hideRaiseControls() {
            document.getElementById('raiseControls').style.display = 'none';
        }

        function addToBet(amount) {
            const input = document.getElementById('raiseAmount');
            const currentValue = parseInt(input.value) || 0;
            const newValue = currentValue + amount;
            input.value = Math.max(0, newValue);
        }

        function clearBet() {
            document.getElementById('raiseAmount').value = 0;
        }

        let winnerCountdownInterval = null;
        let newHandTimeout = null;

        function closeWinnerModal(autoClose = false) {
            if (winnerCountdownInterval) {
                clearInterval(winnerCountdownInterval);
                winnerCountdownInterval = null;
            }
            // If manually closed, cancel any pending new hand timer
            if (!autoClose && newHandTimeout) {
                clearTimeout(newHandTimeout);
                newHandTimeout = null;
            }
            document.getElementById('winnerModal').style.display = 'none';

            // Auto-start new hand disabled for now
            // if (autoClose) {
            //     // Auto-closed: start new hand in 8 seconds
            //     document.getElementById('gameStatus').textContent = 'New hand starting in 8 seconds...';
            //     newHandTimeout = setTimeout(() => {
            //         newHandTimeout = null;
            //         newHand();
            //     }, 8000);
            // } else {
            //     document.getElementById('gameStatus').textContent = 'Click "New Game" to continue!';
            // }
            document.getElementById('gameStatus').textContent = 'Click "New Game" to continue!';
        }

        function revealMyCards() {
            // Send request to reveal down cards to all players
            socket.emit('reveal_cards');
            console.log('Revealing my cards to all players');
        }

        function toggleAlgorithmInfo() {
            const info = document.getElementById('algorithmInfo');
            const handRankings = document.getElementById('handRankingsInfo');
            // Hide hand rankings when showing algorithm info
            if (handRankings) handRankings.style.display = 'none';
            info.style.display = info.style.display === 'none' ? 'block' : 'none';
        }

        function toggleHandRankings() {
            const info = document.getElementById('handRankingsInfo');
            const algorithmInfo = document.getElementById('algorithmInfo');
            // Hide algorithm info when showing hand rankings
            if (algorithmInfo) algorithmInfo.style.display = 'none';
            info.style.display = info.style.display === 'none' ? 'block' : 'none';
        }

        // Proximity-based opacity for action panel
        (function() {
            const MIN_OPACITY = 0.12;  // Minimum opacity when far away
            const MAX_OPACITY = 1.0;   // Full opacity when close
            const MAX_DISTANCE = 400;  // Distance (px) at which minimum opacity is reached

            document.addEventListener('mousemove', function(e) {
                const panel = document.getElementById('actionPanel');
                if (!panel || panel.style.display === 'none') return;

                // Get panel bounding rect
                const rect = panel.getBoundingClientRect();

                // Check if mouse is directly over the panel - if so, full opacity
                if (e.clientX >= rect.left && e.clientX <= rect.right &&
                    e.clientY >= rect.top && e.clientY <= rect.bottom) {
                    panel.style.opacity = MAX_OPACITY;
                    return;
                }

                // Get panel center position
                const panelCenterX = rect.left + rect.width / 2;
                const panelCenterY = rect.top + rect.height / 2;

                // Calculate distance from mouse to panel center
                const dx = e.clientX - panelCenterX;
                const dy = e.clientY - panelCenterY;
                const distance = Math.sqrt(dx * dx + dy * dy);

                // Calculate opacity based on distance
                // Closer = more opaque, farther = more transparent
                const normalizedDistance = Math.min(distance / MAX_DISTANCE, 1);
                const opacity = MAX_OPACITY - (normalizedDistance * (MAX_OPACITY - MIN_OPACITY));

                panel.style.opacity = opacity;
            });

            // Ensure full opacity when hovering directly over the panel
            document.addEventListener('DOMContentLoaded', function() {
                const panel = document.getElementById('actionPanel');
                if (panel) {
                    panel.addEventListener('mouseenter', function() {
                        this.style.opacity = MAX_OPACITY;
                    });
                }
            });
        })();
    </script>
</body>
</html>
'''
