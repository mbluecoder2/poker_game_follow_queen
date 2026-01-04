# Poker Game Rules & Documentation

## Table of Contents
1. [Getting Started](#getting-started)
2. [Texas Hold'em Rules](#texas-holdem-rules)
3. [Follow the Queen Rules](#follow-the-queen-rules)
4. [Hand Rankings](#hand-rankings)
5. [Betting Actions](#betting-actions)
6. [Bot Players](#bot-players)
7. [Game Controls](#game-controls)

---

## Getting Started

### Joining a Game
1. Open your browser to `http://127.0.0.1:5000`
2. Select your name from the dropdown menu
3. Click **"Join Game"**
4. Once joined, you'll see the game controls

### Starting a Game
1. Select the **Game Type**: Texas Hold'em or Follow the Queen
2. Select the **Number of Players** (2-9)
3. Click **"New Game"** to create the game
4. Wait for other players to join (or add bots)
5. Click **"Start Game"** when ready

### Game Settings
- **Buy-in**: $10.00 per player
- **Ante** (Follow the Queen): $0.05
- **Bring-in** (Follow the Queen): $0.10
- **Small Blind** (Texas Hold'em): $0.05
- **Big Blind** (Texas Hold'em): $0.10

---

## Texas Hold'em Rules

Texas Hold'em is the most popular form of poker, using community cards shared by all players.

### Overview
- Each player receives **2 private hole cards**
- **5 community cards** are dealt face-up in the center
- Players make the best 5-card hand using any combination of their hole cards and community cards
- The player with the best hand (or last player remaining) wins the pot

### Game Flow

#### 1. Blinds
- The player to the left of the dealer posts the **Small Blind** ($0.05)
- The next player posts the **Big Blind** ($0.10)
- Blinds are forced bets that create action

#### 2. Pre-Flop
- Each player receives 2 hole cards face down
- Betting begins with the player left of the big blind
- Players can fold, call the big blind, or raise

#### 3. The Flop
- 3 community cards are dealt face-up
- Betting begins with the first active player left of the dealer
- Players can check (if no bet) or bet

#### 4. The Turn
- 1 more community card is dealt (4 total)
- Another round of betting

#### 5. The River
- The final community card is dealt (5 total)
- Final round of betting

#### 6. Showdown
- If multiple players remain, hands are compared
- Best 5-card hand wins the pot
- Pot is split if hands are equal

### Example Hand
```
Your Hole Cards: A♠ K♠
Community Cards: Q♠ J♠ 10♠ 5♥ 2♣

Your Best Hand: Royal Flush (A♠ K♠ Q♠ J♠ 10♠)
```

---

## Follow the Queen Rules

Follow the Queen is a Seven-Card Stud variant with wild cards that can change during the hand!

### Overview
- Each player receives **7 cards** total (3 down, 4 up)
- **Queens are always wild**
- When a Queen is dealt face-up, the **next card's rank becomes wild** too
- No community cards - each player has their own cards
- Best 5-card hand wins (can include wild cards)

### Wild Cards
- **Queens (Q)** are ALWAYS wild
- When a Queen appears face-up, the very next face-up card determines an additional wild rank
- If another Queen appears, the wild rank changes to whatever follows that Queen
- Wild cards can represent ANY card to complete your hand
- **Five of a Kind** is possible with wild cards (beats Four of a Kind!)

### Game Flow

#### 1. Ante
- All players post the ante ($0.05) before cards are dealt

#### 2. Third Street (Initial Deal)
- Each player receives 3 cards: **2 face-down, 1 face-up**
- The player with the **lowest up-card** must post the bring-in ($0.10)
- Betting proceeds clockwise
- **Watch for Queens!** If a Queen is dealt up, the next up-card's rank becomes wild

#### 3. Fourth Street
- Each player receives 1 card face-up
- Player with the **best visible hand** acts first
- Standard betting round
- Wild cards may change if a Queen appears

#### 4. Fifth Street
- Each player receives 1 card face-up
- Player with best visible hand acts first
- Standard betting round

#### 5. Sixth Street
- Each player receives 1 card face-up (4 up-cards total)
- Player with best visible hand acts first
- Standard betting round

#### 6. Seventh Street (The River)
- Each player receives their final card **face-down**
- Final betting round
- Player with best visible hand acts first

#### 7. Showdown
- Players reveal all cards
- Best 5-card hand wins (using any 5 of your 7 cards)
- Click on your down cards to reveal them to other players

### Card Layout
```
Down Cards (Hidden):    Up Cards (Visible):
  [??] [??]              [3rd] [4th] [5th] [6th]

Final Down Card: [7th - hidden]
```

### Wild Card Example
```
Player 1 up-card: 7♥
Player 2 up-card: Q♦  <-- Queen! Next card determines wild
Player 3 up-card: 9♠  <-- 9s are now wild!

Current Wilds: Queens AND 9s

Later...
Player 1 up-card: Q♣  <-- Another Queen! Wild changes
Player 2 up-card: K♥  <-- Kings are now wild!

Current Wilds: Queens AND Kings (9s no longer wild)
```

### Example Winning Hand
```
Your Cards: Q♠(wild) 9♥ 9♦ 9♣ 7♥ 7♦ 2♠
Wild Rank: 9s

Best Hand: Five 9s! (Three natural 9s + Queen as wild 9 + one more 9)
          This beats Four of a Kind!
```

---

## Hand Rankings

### Standard Rankings (Lowest to Highest)

| Rank | Hand | Description | Example |
|------|------|-------------|---------|
| 1 | High Card | No matching cards | A♠ K♥ 9♦ 7♣ 2♠ |
| 2 | One Pair | Two cards of same rank | K♠ K♥ 9♦ 7♣ 2♠ |
| 3 | Two Pair | Two different pairs | K♠ K♥ 9♦ 9♣ 2♠ |
| 4 | Three of a Kind | Three cards of same rank | 9♠ 9♥ 9♦ K♣ 2♠ |
| 5 | Straight | Five consecutive ranks | 5♠ 6♥ 7♦ 8♣ 9♠ |
| 6 | Flush | Five cards of same suit | A♠ K♠ 9♠ 7♠ 2♠ |
| 7 | Full House | Three of a kind + pair | 9♠ 9♥ 9♦ K♣ K♠ |
| 8 | Four of a Kind | Four cards of same rank | 9♠ 9♥ 9♦ 9♣ K♠ |
| 9 | Straight Flush | Straight + flush | 5♠ 6♠ 7♠ 8♠ 9♠ |
| 10 | Royal Flush | A-K-Q-J-10 flush | A♠ K♠ Q♠ J♠ 10♠ |

### Special: Five of a Kind (Follow the Queen Only)
With wild cards, you can make **Five of a Kind** - five cards of the same rank.
This is the **highest possible hand**, beating even a Royal Flush!

```
Example: K♠ K♥ K♦ K♣ Q♠(wild as K) = Five Kings!
```

---

## Betting Actions

When it's your turn, the action panel appears at the bottom of the screen:

### Fold
- Surrender your hand and forfeit any chips in the pot
- Use when your hand is weak and the cost to continue is too high

### Check
- Pass the action without betting (only if no one has bet)
- Free way to see more cards

### Call
- Match the current bet to stay in the hand
- Button shows the amount: "Call $0.10"

### Raise
- Increase the bet amount
- Click "Raise" then enter your raise amount
- Minimum raise is typically 2x the current bet

### All-In
- Bet all your remaining chips
- You can still win the pot up to the amount you contributed
- Cannot be forced to fold if you can't match a bet

---

## Bot Players

### Adding Bots
Any player whose name starts with "Bot" will automatically play as a robot:
- Bot 1, Bot 2, Bot 3, etc.
- Bots make decisions based on hand strength and pot odds

### Bot Intelligence
Bots evaluate their hands considering:
- **Pairs, trips, straights, flushes** - standard hand strength
- **Wild cards** - Queens and the current wild rank
- **Pot odds** - ratio of bet to pot size
- **Randomness** - slight unpredictability for realism

### Bot Behavior
- **Strong hands**: Bots bet and raise aggressively
- **Medium hands**: Bots call or make small bets
- **Weak hands**: Bots check when free, fold to large bets
- Bots take 1-2 seconds to "think" before acting

---

## Game Controls

### Main Buttons
| Button | Function |
|--------|----------|
| **New Game** | Create a new game with selected settings |
| **Start Game** | Begin dealing cards (need 2+ players) |
| **New Hand** | Deal a new hand after showdown |
| **Reset Game** | Hard reset (Michael H only) - restarts server |
| **Shuffle Info** | View Fisher-Yates shuffle algorithm details |

### During Showdown
- Click on your **down cards** to reveal them to other players
- This is optional - you can keep them hidden
- Winner is automatically determined

### Game Status
The status bar shows:
- Current phase (Pre-Flop, Flop, Third Street, etc.)
- Pot amount
- Whose turn it is
- Winner announcement

---

## Tips for New Players

### Texas Hold'em Tips
1. **Position matters** - acting last gives you information
2. **Starting hands** - pairs and high cards (A, K, Q) are strong
3. **Don't chase** - folding bad hands saves money
4. **Watch the board** - community cards help everyone

### Follow the Queen Tips
1. **Track the wild cards** - know what's wild at all times!
2. **Queens are gold** - they're always wild
3. **Watch opponents' up-cards** - you can see 4 of their 7 cards
4. **Wild cards change everything** - a weak hand can become strong instantly
5. **Five of a Kind** - with wilds, this is possible and beats everything!

---

## Glossary

| Term | Definition |
|------|------------|
| **Ante** | Forced bet from all players before deal |
| **Blinds** | Forced bets from 2 players before deal |
| **Community Cards** | Shared cards in Hold'em |
| **Down Cards** | Face-down cards only you can see |
| **Up Cards** | Face-up cards everyone can see |
| **Wild Card** | Card that can represent any other card |
| **Pot** | Total chips bet during the hand |
| **Showdown** | Final reveal of hands to determine winner |
| **Street** | A round of dealing and betting |

---

*Game created for the Friday night poker group. Have fun and good luck!*
