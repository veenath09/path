import pygame
import sys
import random
from collections import deque

# === GAME SETTINGS ===
GRID_SIZE = 14   # grid size
TILE_SIZE = 36   # tile size
RIGHT_PANEL_WIDTH = 320
WIDTH = GRID_SIZE * TILE_SIZE + RIGHT_PANEL_WIDTH
HEIGHT = GRID_SIZE * TILE_SIZE + 280  # taller window

# Colors
WHITE = (240, 240, 240)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)       # Start
BLUE = (0, 100, 255)      # Rover
RED = (200, 0, 0)         # End
GRAY = (160, 160, 160)    # Blocked
YELLOW = (255, 215, 0)    # Astronomical items
DARKGREEN = (0, 150, 0)   # Toxic gas
LIGHTGRAY = (230, 230, 230)
LIGHTBLUE = (173, 216, 230)

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Rover Pathway - Hard Mode (REPL)")
clock = pygame.time.Clock()
font = pygame.font.SysFont("Arial", 18)
big_font = pygame.font.SysFont("Arial", 24, bold=True)

# === TEXT CONTENT ===
INTRO_TEXT = (
    "You and your team are traveling on a spacecraft called UOP-25.\n"
    "When the spacecraft is traveling near a planet called 'Dawn', it collides with a small asteroid.\n"
    "Several scientific instruments are thrown off the spacecraft and fall onto Dawn's surface.\n"
    "Your mission — 'Hours of Dawn' — is to send a rover to collect the instruments and clear toxic hazards.\n"
)

INSTRUCTIONS_TEXT = (
    "Available Commands:\n"
    "  move(n);         => move forward by n steps (e.g. move(3);)\n"
    "  turn(90);        => turn right 90 degrees\n"
    "  turn(270);       => turn left 90 degrees\n"
    "  collect;         => collect an astronomical item on the current square\n"
    "  destroy;         => destroy toxic material on the square AHEAD (or current square)\n"
    "  repeat(k){ ... } => repeat the enclosed commands k times\n"
    "  end.             => finish program early (clears the queue)\n\n"
    "Rules:\n"
    "  - Rover can only move through white/open squares.\n"
    "  - Destroy gas ahead with destroy; before moving into it.\n"
    "  - Items (I) must be collected with collect; while standing on them.\n"
    "  - Use repeat to avoid long sequences. Example:\n"
    "      repeat(2){ destroy; move(1); }\n"
)

# === TEXT WRAPPING (supports explicit newlines) ===
def wrap_text_multiline(text, font, max_width):
    paragraphs = text.split('\n')
    out_lines = []
    for p in paragraphs:
        if p.strip() == "":
            out_lines.append("")
            continue
        words = p.split(" ")
        current_line = ""
        for word in words:
            test_line = (current_line + " " + word).strip() if current_line else word
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                out_lines.append(current_line)
                current_line = word
        if current_line:
            out_lines.append(current_line)
    return out_lines

# Pre-wrap the text
INTRO_LINES = wrap_text_multiline(INTRO_TEXT, font, RIGHT_PANEL_WIDTH - 80)
INSTRUCTION_LINES = wrap_text_multiline(INSTRUCTIONS_TEXT, font, RIGHT_PANEL_WIDTH - 80)

# === EXECUTION / PARSING STATE (REPL) ===
action_queue = deque()     # queue of pending instructions (strings like 'move(3);')
current_move_remaining = 0
collected_items_global = set()
destroyed_gases_global = set()
status_message = ""

# === GRID GENERATION ===
def generate_grid():
    grid = [["." for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    start = (0, 0)
    end = (GRID_SIZE-1, GRID_SIZE-1)
    grid[start[1]][start[0]] = "S"
    grid[end[1]][end[0]] = "E"

    # Create a guaranteed path
    path = [start]
    x, y = start
    while (x, y) != end:
        if x < GRID_SIZE - 1 and y < GRID_SIZE - 1:
            if random.choice([True, False]):
                x += 1
            else:
                y += 1
        elif x < GRID_SIZE - 1:
            x += 1
        elif y < GRID_SIZE - 1:
            y += 1
        path.append((x, y))

    # Place challenges on path
    for px, py in path[1:-1]:
        choice = random.choices(
            [".", "G", "I"],
            weights=[0.3, 0.5, 0.2]  # more toxic gas
        )[0]
        grid[py][px] = choice

    # Fill rest with blocked tiles randomly
    for j in range(GRID_SIZE):
        for i in range(GRID_SIZE):
            if (i, j) not in path and grid[j][i] == ".":
                if random.random() < 0.45:
                    grid[j][i] = "X"

    return grid, start, end

# === BUTTONS ===
def draw_button(text, x, y, w, h):
    rect = pygame.Rect(x, y, w, h)
    pygame.draw.rect(screen, GRAY, rect)
    pygame.draw.rect(screen, BLACK, rect, 2)
    label = big_font.render(text, True, BLACK)
    screen.blit(label, (x + (w - label.get_width()) // 2, y + (h - label.get_height()) // 2))
    return rect

def draw_panel(title, lines, rect, scroll_offset):
    pygame.draw.rect(screen, LIGHTGRAY, rect)
    pygame.draw.rect(screen, BLACK, rect, 2)
    screen.blit(big_font.render(title, True, BLACK), (rect.x + 10, rect.y + 5))

    line_height = 22
    visible_height = rect.height - 40
    text_height = len(lines) * line_height

    # Clamp scrolling
    min_scroll = min(0, visible_height - text_height)
    scroll_offset = max(min_scroll, min(0, scroll_offset))

    y_start = rect.y + 35 + scroll_offset
    for i, line in enumerate(lines):
        if rect.y + 30 <= y_start + i * line_height <= rect.y + rect.height - 20:
            label = font.render(line, True, BLACK)
            screen.blit(label, (rect.x + 10, y_start + i * line_height))

    return scroll_offset

# === GRID RENDERING ===
def draw_grid(grid, rover, code_lines, current_input, message, visited,
              intro_scroll, instr_scroll, scroll_offset, rover_direction):
    screen.fill(WHITE)

    # Title
    title = big_font.render("Rover Pathway - Hard Mode", True, BLACK)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 10))

    # Center grid
    grid_x = 20
    grid_y = 50
    for j in range(GRID_SIZE):
        for i in range(GRID_SIZE):
            rect = pygame.Rect(grid_x + i * TILE_SIZE, grid_y + j * TILE_SIZE, TILE_SIZE, TILE_SIZE)
            tile = grid[j][i]

            if (i, j) in visited:
                pygame.draw.rect(screen, LIGHTBLUE, rect)

            # Check if gas has been destroyed
            if tile == "G" and (i, j) in destroyed_gases_global:
                pygame.draw.rect(screen, LIGHTGRAY, rect)
            elif tile == "S":
                pygame.draw.rect(screen, GREEN, rect)
            elif tile == "E":
                pygame.draw.rect(screen, RED, rect)
            elif tile == "X":
                pygame.draw.rect(screen, GRAY, rect)
            elif tile == "G":
                pygame.draw.rect(screen, DARKGREEN, rect)
            elif tile == "I" and (i, j) not in collected_items_global:
                pygame.draw.rect(screen, YELLOW, rect)
            elif tile == "I" and (i, j) in collected_items_global:
                pygame.draw.rect(screen, LIGHTGRAY, rect)

            pygame.draw.rect(screen, BLACK, rect, 1)

    # Rover with direction indicator
    rover_rect = pygame.Rect(grid_x + rover[0] * TILE_SIZE, grid_y + rover[1] * TILE_SIZE, TILE_SIZE, TILE_SIZE)
    pygame.draw.rect(screen, BLUE, rover_rect)

    # Draw direction arrow on rover
    center_x = rover_rect.centerx
    center_y = rover_rect.centery
    arrow_length = TILE_SIZE // 3

    if rover_direction == 0:      # Right
        end_x, end_y = center_x + arrow_length, center_y
    elif rover_direction == 90:   # Down
        end_x, end_y = center_x, center_y + arrow_length
    elif rover_direction == 180:  # Left
        end_x, end_y = center_x - arrow_length, center_y
    elif rover_direction == 270:  # Up
        end_x, end_y = center_x, center_y - arrow_length
    else:                         # Default to right
        end_x, end_y = center_x + arrow_length, center_y

    pygame.draw.line(screen, WHITE, (center_x, center_y), (end_x, end_y), 3)

    # Panels
    intro_rect = pygame.Rect(GRID_SIZE * TILE_SIZE + 40, 50, RIGHT_PANEL_WIDTH - 60, 160)
    instr_rect = pygame.Rect(GRID_SIZE * TILE_SIZE + 40, 220, RIGHT_PANEL_WIDTH - 60, 200)
    intro_scroll = draw_panel("Mission Story", INTRO_LINES, intro_rect, intro_scroll)
    instr_scroll = draw_panel("Instructions", INSTRUCTION_LINES, instr_rect, instr_scroll)

    # Status counters
    stats_x = GRID_SIZE * TILE_SIZE + 40
    stats_y = instr_rect.bottom + 10
    screen.blit(big_font.render("Status", True, BLACK), (stats_x, stats_y))
    screen.blit(font.render(f"Collected: {len(collected_items_global)}", True, BLACK), (stats_x, stats_y + 30))
    screen.blit(font.render(f"Destroyed: {len(destroyed_gases_global)}", True, BLACK), (stats_x, stats_y + 50))

    # Show current direction
    direction_names = {0: "Right →", 90: "Down ↓", 180: "Left ←", 270: "Up ↑"}
    current_dir = direction_names.get(rover_direction, f"Unknown ({rover_direction}°)")
    screen.blit(font.render(f"Direction: {current_dir}", True, BLACK), (stats_x, stats_y + 70))

    # Console
    console_rect = pygame.Rect(20, GRID_SIZE * TILE_SIZE + 70, WIDTH - 40, 110)
    pygame.draw.rect(screen, LIGHTGRAY, console_rect)
    pygame.draw.rect(screen, BLACK, console_rect, 2)

    screen.blit(font.render("Console:", True, BLACK), (console_rect.x + 10, console_rect.y + 5))
    visible_height = console_rect.height - 40
    line_height = 20
    max_visible_lines = visible_height // line_height

    # Clamp scroll offset
    max_scroll = max(0, len(code_lines) - max_visible_lines)
    scroll_offset = max(0, min(scroll_offset, max_scroll))

    # Render lines inside console
    start_idx = scroll_offset
    end_idx = start_idx + max_visible_lines
    for i, line in enumerate(code_lines[start_idx:end_idx]):
        screen.blit(font.render(line, True, BLACK),
                    (console_rect.x + 10, console_rect.y + 25 + i * line_height))

    # Input line pinned at bottom
    screen.blit(font.render("> " + current_input, True, BLACK),
                (console_rect.x + 10, console_rect.bottom - 25))

    # Scrollbar indicator
    if len(code_lines) > max_visible_lines:
        bar_height = max(15, (visible_height / (len(code_lines) * line_height)) * visible_height)
        bar_y = console_rect.y + 25 + (scroll_offset / max_scroll) * (visible_height - bar_height)
        pygame.draw.rect(screen, BLACK, (console_rect.right - 6, bar_y, 4, bar_height))

    # Message box above buttons
    msg_rect = pygame.Rect(20, console_rect.bottom + 5, WIDTH - 40, 35)
    pygame.draw.rect(screen, WHITE, msg_rect)
    pygame.draw.rect(screen, BLACK, msg_rect, 1)
    if message:
        msg_txt = big_font.render(message, True, BLACK)
        screen.blit(msg_txt, (msg_rect.x + 10, msg_rect.y + 5))

    # Buttons at bottom: Step, Run/Pause, Reset, Exit
    btn_y = HEIGHT - 55
    btn_w = 80
    spacing = (WIDTH - (btn_w * 4)) // 5
    step_btn = draw_button("Step", spacing, btn_y, btn_w, 40)
    run_btn = draw_button("Run", spacing * 2 + btn_w, btn_y, btn_w, 40)
    reset_btn = draw_button("Reset", spacing * 3 + btn_w * 2, btn_y, btn_w, 40)
    exit_btn = draw_button("Exit", spacing * 4 + btn_w * 3, btn_y, btn_w, 40)

    # Tooltip for hovered tile
    mx, my = pygame.mouse.get_pos()
    tooltip = None
    if grid_x <= mx <= grid_x + GRID_SIZE * TILE_SIZE and grid_y <= my <= GRID_SIZE * TILE_SIZE:
        tx = (mx - grid_x) // TILE_SIZE
        ty = (my - grid_y) // TILE_SIZE
        if 0 <= tx < GRID_SIZE and 0 <= ty < GRID_SIZE:
            t = grid[ty][tx]
            desc = "Empty"
            if t == 'S': desc = "Start"
            elif t == 'E': desc = "Goal"
            elif t == 'X': desc = "Blocked"
            elif t == 'G':
                if (tx, ty) in destroyed_gases_global:
                    desc = "Toxic gas (DESTROYED)"
                else:
                    desc = "Toxic gas (use destroy;)"
            elif t == 'I':
                if (tx, ty) in collected_items_global:
                    desc = "Item (COLLECTED)"
                else:
                    desc = "Item (use collect;)"
            tooltip = f"({tx},{ty}): {desc}"

    if tooltip:
        tw = font.size(tooltip)[0] + 8
        th = 24
        pygame.draw.rect(screen, LIGHTGRAY, (mx+12, my+12, tw, th))
        pygame.draw.rect(screen, BLACK, (mx+12, my+12, tw, th), 1)
        screen.blit(font.render(tooltip, True, BLACK), (mx+16, my+16))

    pygame.display.flip()
    return step_btn, run_btn, reset_btn, exit_btn, intro_scroll, instr_scroll, scroll_offset

# === Rover helpers ===
def move(pos, direction, steps):
    x, y = pos
    if direction == 0: x += steps
    elif direction == 90: y += steps
    elif direction == 180: x -= steps
    elif direction == 270: y -= steps
    return (x, y)

def parse_code(lines):
    """Parse code lines into a flat list of instructions. Supports repeat(k){ ... } blocks."""
    src = "\n".join(lines)
    i = 0
    n = len(src)

    def read_while(cond):
        nonlocal i
        s = ""
        while i < n and cond(src[i]):
            s += src[i]
            i += 1
        return s

    def skip_ws():
        nonlocal i
        while i < n and src[i].isspace(): i += 1

    def parse_block():
        nonlocal i
        skip_ws()
        if i < n and src[i:i+6].lower().startswith("repeat"):
            i += 6
            skip_ws()
            if i >= n or src[i] != '(':
                raise ValueError("Expected ( after repeat")
            i += 1
            num = read_while(lambda c: c.isdigit())
            if not num:
                raise ValueError("repeat(count) requires a number")
            k = int(num)
            skip_ws()
            if i >= n or src[i] != ')':
                raise ValueError("Expected ) after repeat(count)")
            i += 1
            skip_ws()
            if i >= n or src[i] != '{':
                raise ValueError("Expected { after repeat(count)")
            i += 1
            # capture block content
            start = i
            depth = 1
            while i < n and depth > 0:
                if src[i] == '{': depth += 1
                elif src[i] == '}': depth -= 1
                i += 1
            block = src[start:i-1].strip()
            inner_lines = [l.strip() for l in block.split(';') if l.strip()]
            expanded = []
            for _ in range(k):
                for il in inner_lines:
                    expanded.append(il + (';' if not il.endswith(';') and not il.endswith('.') else ''))
            return expanded
        else:
            stmt = read_while(lambda c: c != ';' and c != '\n')
            if i < n and src[i] == ';':
                i += 1
                stmt = stmt.strip() + ';'
            else:
                stmt = stmt.strip()
            return [stmt]

    parsed = []
    while i < n:
        skip_ws()
        if i >= n: break
        parsed.extend(parse_block())
    parsed = [p for p in parsed if p]
    return parsed

def step_execution(grid, pos, direction):
    """Perform a single micro-step using the live action_queue (REPL).
       Returns (pos, direction, status, finished_bool_for_step_batch)"""
    global current_move_remaining, action_queue, collected_items_global, destroyed_gases_global

    # Continue an in-progress move
    if current_move_remaining > 0:
        if not action_queue:
            current_move_remaining = 0
            return pos, direction, "Move canceled (queue cleared).", True

        instr = action_queue[0].strip().lower()
        if instr.startswith("move("):
            newpos = move(pos, direction, 1)

            # bounds check
            if newpos[0] < 0 or newpos[1] < 0 or newpos[0] >= GRID_SIZE or newpos[1] >= GRID_SIZE:
                current_move_remaining = 0
                action_queue.popleft()
                return pos, direction, "Out of bounds!", True

            tile = grid[newpos[1]][newpos[0]]
            if tile == 'X':
                current_move_remaining = 0
                action_queue.popleft()
                return pos, direction, "Hit blocked tile!", True

            if tile == 'G' and newpos not in destroyed_gases_global:
                current_move_remaining = 0
                action_queue.popleft()
                return pos, direction, "Toxic gas ahead — use destroy; then move(1);", True

            pos = newpos
            current_move_remaining -= 1

            if current_move_remaining == 0:
                action_queue.popleft()
            return pos, direction, f"Moved 1 step. {current_move_remaining} remaining", False

        else:
            current_move_remaining = 0  # safety

    # If nothing queued, we're done for now
    if not action_queue:
        return pos, direction, "No commands queued.", True

    instr = action_queue[0].strip().lower()

    # Start of a move(...)
    if instr.startswith("move("):
        try:
            steps = int(instr[instr.find('(')+1:instr.find(')')])
        except:
            action_queue.popleft()
            return pos, direction, "Invalid move argument", True

        if steps <= 0:
            action_queue.popleft()
            return pos, direction, "Zero move ignored", False

        current_move_remaining = steps
        return pos, direction, f"Starting move of {steps} steps", False

    # Turn(...)
    if instr.startswith("turn("):
        try:
            angle = int(instr[instr.find('(')+1:instr.find(')')])
        except:
            action_queue.popleft()
            return pos, direction, "Invalid turn argument", True

        direction = (direction + angle) % 360
        action_queue.popleft()
        return pos, direction, f"Turned {angle}°", False

    # collect;
    if instr in ("collect;", "collect"):
        if grid[pos[1]][pos[0]] == 'I':
            collected_items_global.add(pos)
            action_queue.popleft()
            return pos, direction, "Collected item", False
        else:
            action_queue.popleft()
            return pos, direction, "Nothing to collect here!", True

    # destroy; — destroys gas on the tile AHEAD (preferred), or on current tile
    if instr in ("destroy;", "destroy"):
        ahead = move(pos, direction, 1)  # tile in front
        ax, ay = ahead
        destroyed = False
        where = None

        # Try to destroy ahead
        if 0 <= ax < GRID_SIZE and 0 <= ay < GRID_SIZE:
            if grid[ay][ax] == 'G':
                destroyed_gases_global.add((ax, ay))
                destroyed = True
                where = (ax, ay)

        # Fallback: current tile
        if not destroyed and grid[pos[1]][pos[0]] == 'G':
            destroyed_gases_global.add(pos)
            destroyed = True
            where = pos

        action_queue.popleft()
        if destroyed:
            return pos, direction, f"Destroyed gas at {where}", False
        else:
            return pos, direction, "No gas ahead or underfoot to destroy.", True

    # end.
    if instr in ("end.", "end"):
        action_queue.clear()
        current_move_remaining = 0
        return pos, direction, "Program ended", True

    # Unknown -> skip
    action_queue.popleft()
    return pos, direction, f"Unknown instr '{instr}' skipped", False

# (Optional run tester — not used by REPL)
def run_code(grid, start, end, code):
    pos = start
    direction = 0
    visited = [pos]
    collected_items = set()
    destroyed_gases = set()
    move_count = 0

    for line in code:
        line = line.strip().lower()

        if line.startswith("move("):
            steps = int(line[line.find("(")+1:line.find(")")])
            for _ in range(steps):
                pos = move(pos, direction, 1)
                move_count += 1
                if pos[0] < 0 or pos[1] < 0 or pos[0] >= GRID_SIZE or pos[1] >= GRID_SIZE:
                    return False, visited, "Out of bounds!"
                tile = grid[pos[1]][pos[0]]
                if tile == "X":
                    return False, visited, "Blocked tile!"
                if tile == "G" and pos not in destroyed_gases:
                    return False, visited, "Toxic gas not destroyed!"
                if tile == "I" and pos not in collected_items:
                    return False, visited, "Item not collected!"
                visited.append(pos)

        elif line.startswith("turn("):
            angle = int(line[line.find("(")+1:line.find(")")])
            direction = (direction + angle) % 360

        elif line == "collect;":
            if grid[pos[1]][pos[0]] == "I":
                collected_items.add(pos)
            else:
                return False, visited, "Nothing to collect!"

        elif line == "destroy;":
            if grid[pos[1]][pos[0]] == "G":
                destroyed_gases.add(pos)
            else:
                return False, visited, "Nothing to destroy!"

        elif line == "end.":
            break

    if pos == end:
        return True, visited, f"Good job! Mission complete in {move_count} moves!"
    return False, visited, "Rover did not reach the goal!"

# === MAIN ===
current_input, code_lines, message, visited = "", [], "", []
intro_scroll, instr_scroll = 0, 0
scroll_offset = 0

# Execution runtime state
is_running = False
is_paused = False
run_delay_ms = 300   # delay between micro-steps when running
last_run_time = 0
rover_direction = 0  # 0 = right, 90 = down, 180 = left, 270 = up

def main():
    global current_input, code_lines, message, visited, intro_scroll, instr_scroll, scroll_offset
    grid, start, end = generate_grid()
    rover = start
    visited = [rover]

    global is_running, is_paused, last_run_time, rover_direction, status_message
    while True:
        step_btn, run_btn, reset_btn, exit_btn, intro_scroll, instr_scroll, scroll_offset = draw_grid(
            grid, rover, code_lines, current_input, status_message or message, visited, intro_scroll, instr_scroll, scroll_offset, rover_direction
        )

        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    line = current_input.strip()
                    if line:
                        code_lines.append(line)
                        try:
                            new_actions = parse_code([line])
                            for a in new_actions:
                                action_queue.append(a)
                            status_message = "Queued."
                        except Exception as e:
                            status_message = f"Parse error: {e}"
                        # Auto-scroll to bottom of console
                        visible_height = 110 - 40
                        line_height = 20
                        max_visible_lines = visible_height // line_height
                        scroll_offset = max(0, len(code_lines) - max_visible_lines)
                    current_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    current_input = current_input[:-1]
                elif event.key == pygame.K_UP:
                    scroll_offset = max(0, scroll_offset - 1)
                elif event.key == pygame.K_DOWN:
                    visible_height = 110 - 40
                    line_height = 20
                    max_visible_lines = visible_height // line_height
                    scroll_offset = min(max(0, len(code_lines) - max_visible_lines), scroll_offset + 1)
                else:
                    current_input += event.unicode

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if step_btn.collidepoint(event.pos):
                    rover, rover_direction, status, _ = step_execution(grid, rover, rover_direction)
                    status_message = status
                    if rover not in visited:
                        visited.append(rover)
                    if rover == end:
                        status_message = "Mission complete! All objectives achieved!"
                        is_running = False

                elif run_btn.collidepoint(event.pos):
                    if is_running:
                        is_running = False
                        is_paused = True
                        status_message = "Paused"
                    else:
                        is_running = True
                        is_paused = False
                        last_run_time = now
                        status_message = "Running..."

                elif reset_btn.collidepoint(event.pos):
                    grid, start, end = generate_grid()
                    rover = start
                    rover_direction = 0
                    visited = [rover]
                    code_lines, current_input, message = [], "", ""
                    action_queue.clear()
                    global current_move_remaining
                    current_move_remaining = 0
                    collected_items_global.clear()
                    destroyed_gases_global.clear()
                    status_message = ""
                    is_running = False
                    is_paused = False
                    scroll_offset = 0

                elif exit_btn.collidepoint(event.pos):
                    pygame.quit(); sys.exit()

            elif event.type == pygame.MOUSEWHEEL:
                mx, my = pygame.mouse.get_pos()
                if GRID_SIZE*TILE_SIZE+40 <= mx <= WIDTH-20:
                    if 50 <= my <= 210:  # Intro panel
                        intro_scroll += event.y * 10
                    elif 220 <= my <= 420:  # Instructions panel
                        instr_scroll += event.y * 10
                else:
                    # Console scrolling
                    visible_height = 110 - 40
                    line_height = 20
                    max_visible_lines = visible_height // line_height
                    scroll_offset -= event.y
                    scroll_offset = max(0, min(max(0, len(code_lines) - max_visible_lines), scroll_offset))

        # Run mode: advance micro-step every run_delay_ms
        if is_running and not is_paused and now - last_run_time >= run_delay_ms:
            last_run_time = now
            rover, rover_direction, status, _ = step_execution(grid, rover, rover_direction)
            if rover not in visited:
                visited.append(rover)
            status_message = status
            if rover == end:
                status_message = "Mission complete! All objectives achieved!"
                is_running = False

        clock.tick(60)

if __name__ == "__main__":
    main()
