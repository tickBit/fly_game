import pygame
import math
import random

# =============================================================
#  - Road curvature influencing ship movement naturally
#  - Fixed and smooth center line rendering
#  - No globals (except constants)
#  - Predictable and stable steering physics
#
#  - some global variables used, though
# =============================================================

pygame.init()
screen = pygame.display.set_mode((800, 600))
clock = pygame.time.Clock()

# -------------------------------------------------------------
# CONSTANTS
# -------------------------------------------------------------
WAIT = 0
PLAY = 1
GAME_OVER = 2

NUM_SEGMENTS = 80
ROAD_WIDTH = 420
ROAD_HALF_WIDTH = 40.0
SEGMENT_RANDOM_TURN = 2.0
SEGMENT_PLAYER_INFLUENCE = 7.5
MAX_ROAD_OFFSET = 900

CAMERA_SPEED = 0.45
SHIP_MAX_X = 320
SHIP_STEER_FORCE = 0.8
SHIP_DRAG = 0.12

# -------------------------------------------------------------
# LOAD SHIP
# -------------------------------------------------------------
ship_img = pygame.image.load('./gfx/ship.png').convert_alpha()

# -------------------------------------------------------------
# ROAD GENERATION
# Persistent turning
TURN_PERSISTENCE = 120
current_turn = 0.0
turn_frames = 0
# -------------------------------------------------------------

def spawn_segment(prev_offset, player_influence):
    global current_turn, turn_frames
    """Create next segment with long, consistent turns."""
    if turn_frames <= 0:
        current_turn = random.uniform(-SEGMENT_RANDOM_TURN, SEGMENT_RANDOM_TURN)
        current_turn += player_influence * SEGMENT_PLAYER_INFLUENCE
        turn_frames = TURN_PERSISTENCE
    turn_frames -= 1
    new = prev_offset + current_turn
    return max(-MAX_ROAD_OFFSET, min(MAX_ROAD_OFFSET, new))



def update_segments(segments, cam_pos, player_influence):
    """Advance camera and add/remove segments accordingly."""
    while cam_pos >= 1.0:
        cam_pos -= 1.0
        last = segments[-1]
        segments.pop(0)
        segments.append(spawn_segment(last, player_influence))

    return cam_pos


# -------------------------------------------------------------
# PROJECTION
# -------------------------------------------------------------

def project_scale(z):
    return 1.0 / (z * 0.06 + 0.001)


# -------------------------------------------------------------
# RENDERING
# -------------------------------------------------------------

def draw_road(screen, segments, cam_pos, ship_x):
    sw, sh = screen.get_width(), screen.get_height()
    horizon = int(sh * 0.25)

    # Sky gradient
    for y in range(horizon):
        t = y / (horizon - 1)
        screen.fill((int(10 + 40*t), int(10 + 20*t), int(40 + 80*t)), (0, y, sw, 1))

    # Draw from back to front
    for i in range(NUM_SEGMENTS - 1, 0, -1):
        z1 = (i - cam_pos)
        z2 = (i - 1 - cam_pos)
        if z2 <= 0:
            continue

        s1 = project_scale(z1)
        s2 = project_scale(z2)

        # vertical mirroring
        y1 = sh - (horizon + (1 - s1) * (sh - horizon))
        y2 = sh - (horizon + (1 - s2) * (sh - horizon))

        hw1 = ROAD_WIDTH * s1 * 0.5
        hw2 = ROAD_WIDTH * s2 * 0.5

        cx1 = sw//2 + segments[i] + ship_x * s1 * -0.7
        cx2 = sw//2 + segments[i-1] + ship_x * s2 * -0.7

        left1, right1 = cx1 - hw1, cx1 + hw1
        left2, right2 = cx2 - hw2, cx2 + hw2

        shade = max(0, min(255, int(110 + (1 - s1) * 80)))
        road_col = (shade, shade, shade)

        pygame.draw.polygon(screen, road_col,
            [(left2, y2), (right2, y2), (right1, y1), (left1, y1)])

        # compute line width in screen space and interpolate cleanly.
        if (i % 6) < 3:   # longer dashes
            lw1 = max(2, hw1 * 0.07)
            lw2 = max(2, hw2 * 0.07)

            pygame.draw.polygon(screen, (255,220,0), [
                (cx2 - lw2, y2), (cx2 + lw2, y2),
                (cx1 + lw1, y1), (cx1 - lw1, y1)
            ])

    # side darkening (vignette)
    vign = pygame.Surface((sw, sh), pygame.SRCALPHA)
    for x in range(sw):
        alpha = int(120 * abs((x - sw/2) / (sw/2)))
        vign.fill((0, 0, 0, alpha), (x, 0, 1, sh))
    screen.blit(vign, (0, 0))


# -------------------------------------------------------------
# SHIP RENDERING
# -------------------------------------------------------------

def draw_ship(screen, ship_x, angle):
    sw, sh = screen.get_size()
    w, h = 96, 96
    sx = sw//2 + int(ship_x) - w//2
    sy = sh - h - 60
    img = pygame.transform.scale(ship_img, (w, h))
    img = pygame.transform.rotate(img, angle)
    screen.blit(img, (sx, sy))


# -------------------------------------------------------------
# MAIN GAME
# -------------------------------------------------------------
segments = [math.sin(i * 0.12) * 40 for i in range(NUM_SEGMENTS)]
cam_pos = 0
ship_x = 0
ship_speed = 0
steer = 0
turn_memory = 0             # smoothed curvature detected near the player
turn_smoothing = 0.12

state = PLAY
debug = False

running = True
while running:
    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            running = False
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_LEFT:  steer = -1
            elif e.key == pygame.K_RIGHT: steer = 1
            elif e.key == pygame.K_d: debug = True
        elif e.type == pygame.KEYUP:
            debug = False
            if e.key in (pygame.K_LEFT, pygame.K_RIGHT): steer = 0
            elif e.key == pygame.K_SPACE:
                state = PLAY
                segments = [math.sin(i * 0.12) * 40 for i in range(NUM_SEGMENTS)]
                cam_pos = 0
                ship_x = 0
                ship_speed = 0
                steer = 0
                turn_memory = 0             # smoothed curvature detected near the player
                turn_smoothing = 0.12

    if state == PLAY:
        
        # Road curvature that affects ship movement
        # Use the front few segments to estimate curvature
        road_turn = (segments[2] - segments[5]) * 0.01
        turn_memory = turn_memory * (1 - turn_smoothing) + road_turn * turn_smoothing

        # Update camera position
        cam_pos += CAMERA_SPEED
        cam_pos = update_segments(segments, cam_pos, steer * 0.4)

        
        
        # Ship movement relative to player steering and road curvature
        ship_speed += steer * SHIP_STEER_FORCE
        ship_speed -= ship_speed * SHIP_DRAG
        ship_speed = ship_speed * 0.4
    
        # Ship auto-correction vs. road turning
        ship_x += ship_speed + turn_memory * 14
        ship_x = max(-SHIP_MAX_X, min(SHIP_MAX_X, ship_x))

        # Ship steering physics
        ship_speed += steer * SHIP_STEER_FORCE
        ship_speed -= ship_speed * SHIP_DRAG

        # road should slide opposite of steering
        road_shift = steer * 5       # adjust strength as needed

        # Apply to visual offset of segments only:
        for i in range(len(segments)):
            segments[i] -= road_shift

        # Rendering
        screen.fill((0, 0, 0))
        draw_road(screen, segments, cam_pos, ship_x)
        bob = math.sin(pygame.time.get_ticks() * 0.004) * 2
        draw_ship(screen, ship_x, -ship_speed * 3 + bob)

    if state == GAME_OVER:
        font = pygame.font.SysFont(None, 80)
        text = font.render("GAME OVER", True, (255, 235, 255))
        rect = text.get_rect(center=(screen.get_width() // 2, screen.get_height() // 2))
        screen.blit(text, rect)
    
    if state == PLAY:

        target_z = 12  # 12 is a good value for the ship
        i = int(cam_pos + target_z)

        if 1 <= i < NUM_SEGMENTS:
            z = i - cam_pos
            s = project_scale(z)

            sw = screen.get_width()
            sh = screen.get_height()
            screen_center = sw // 2

            road_center_screen = screen_center + segments[i] + ship_x * s * -0.7

            half_width_screen = ROAD_WIDTH * s * 0.5

            left = road_center_screen - half_width_screen
            right = road_center_screen + half_width_screen

            ship_screen_x = screen_center + ship_x

            # --- DEBUG LINES ---
            if debug == True:
                pygame.draw.line(screen, (255, 50, 50), (left, 0), (left, sh), 3)
                pygame.draw.line(screen, (255, 50, 50), (right, 0), (right, sh), 3)
                pygame.draw.line(screen, (255,255,0), (ship_screen_x, 0), (ship_screen_x, sh), 2)

            # --- GAME OVER ---
            if not (left < ship_screen_x < right):
                state = GAME_OVER
              
    pygame.display.flip()
    clock.tick(60)

pygame.quit()
