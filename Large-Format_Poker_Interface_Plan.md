# Large-Format Poker Interface Plan

## Project Overview
Redesign the poker game UI to be accessible for elderly users with vision difficulties. The interface will feature large, readable static elements with smart player visibility management.

## Design Constraints
- **Maximum players:** 7 (typical: 4-5)
- **Target users:** Elderly players who need large, high-contrast displays
- **Opponent display slots:** 3-4 active players shown in detail at once
- **Auto-hide:** Folded players collapse to minimal indicators
- **Stack-based priority:** Show opponents with largest chip stacks

---

## Phase 1: Layout Foundation (2-3 hours)

### Goal
Create the container structure with fixed, large display zones

### Tasks
1. **Design the main layout grid:**
   - Bottom: Your player zone (25% height)
   - Center: Community cards + pot (40% height)
   - Top/Sides: 3-4 opponent slots (35% height)
   - Edge: Folded players strip (collapsible sidebar)

2. **Set base font sizes and spacing:**
   - Minimum 20pt for body text
   - 28-32pt for critical info (chip counts, pot)
   - Card dimensions: at least 120px wide (vs typical 80px)

### Deliverable
HTML/CSS skeleton with placeholder divs

---

## Phase 2: Player Display System (3-4 hours)

### Goal
Implement smart showing/hiding of players based on game state

### Tasks
1. **Create player state tracking:**
   - `active_players[]` - still in hand
   - `folded_players[]` - out this hand
   - `chip_stacks{}` - for sorting by stack size

2. **Build display logic:**
   - Sort active players by chip stack size
   - Display top 3-4 in full opponent slots
   - Render remaining active players in minimal mode if >4 active
   - Move folded players to collapsed strip

3. **Add manual pin/unpin controls:**
   - Small "📌 pin" button on each opponent card
   - Pinned players stay visible regardless of stack size
   - Max 3-4 pins at once

### Deliverable
Dynamic player visibility that updates on fold/all-in actions

---

## Phase 3: Large-Format Components (3-4 hours)

### Goal
Build oversized, high-contrast UI elements

### Tasks

1. **Your Player Zone:**
   - Extra-large hole cards (150px wide minimum)
   - Giant action buttons (80px tall, full-width text)
   - Huge chip display with $ amount

2. **Community Cards:**
   - 140px card width
   - Clear spacing between flop/turn/river
   - Pot display above in 32pt bold

3. **Opponent Slots:**
   - 100px card backs (face-down cards)
   - Name + chip count in 24pt
   - Status indicators (dealer button, folded, all-in) with icons

4. **Folded Players Strip:**
   - Minimal: avatar/initial + name + chips
   - Collapsible with "▼ Show Folded (3)" toggle

### Deliverable
Fully styled components with accessibility in mind

---

## Phase 4: Responsive Behavior (2 hours)

### Goal
Handle different screen sizes gracefully

### Tasks

1. **Set breakpoints:**
   - Desktop (1920px+): 4 opponent slots
   - Laptop (1366px): 3 opponent slots
   - Tablet (1024px): 2 opponent slots, vertical orientation

2. Scale card sizes proportionally

3. Ensure touch targets are 60px+ for tablets

### Deliverable
CSS media queries for responsive scaling

---

## Phase 5: Integration & Testing (2-3 hours)

### Goal
Connect to existing poker game logic

### Tasks

1. Wire up game state to UI updates
2. Test with 4, 5, and 7 player scenarios
3. Verify folded player transitions work smoothly
4. Get feedback from target users (elderly players)

### Deliverable
Fully functional large-format poker game

---

## Total Estimated Time: 12-16 hours

---

## Key Design Decisions

### Player Visibility Priority
1. **First priority:** Show opponents still in the hand (haven't folded)
2. **Second priority:** Among active players, show those with largest chip stacks
3. **Manual override:** Allow user to pin specific opponents to always show
4. **Folded players:** Collapse to minimal strip showing name + chips only

### Accessibility Features
- **Font sizes:** 20pt minimum, 28-32pt for critical info
- **Card sizes:** 120-150px wide (50-90% larger than standard)
- **Button sizes:** 80px tall with large touch targets
- **High contrast:** Clear visual hierarchy
- **Simplified layout:** Fewer simultaneous on-screen elements

### Base Technology
- Starting from existing Texas Hold'em Flask application
- Modifications to HTML templates for new layout
- CSS updates for large-format styling
- JavaScript for dynamic player visibility management

---

## Pre-Development Questions

Before starting implementation:

1. **Color scheme preferences?**
   - Traditional green felt with red/black cards?
   - Higher contrast dark mode?
   - Enhanced colors for colorblind users?

2. **Build approach?**
   - Incremental (Phase 1 → test → Phase 2 → test)?
   - Complete redesign all at once?

3. **Existing codebase:**
   - Pull from previous Texas Hold'em Flask conversation?
   - Start fresh with new implementation?

---

## Success Metrics

The redesign will be considered successful when:
- Elderly users can read all text without straining
- Card suits and ranks are clearly distinguishable
- Game state (who's in/out, chip counts, pot) is obvious at a glance
- Interface works smoothly with 4-7 players
- Folded player transitions don't cause confusion
- Manual pin/unpin controls are intuitive

---

*Plan created: January 25, 2026*
*Ready for implementation when at computer*
