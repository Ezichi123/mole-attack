import pygame
import pygame_menu
import random
import sys

# ---------------------------
# Window / grid configuration
# ---------------------------

WINDOW_WIDTH = 800
WINDOW_HEIGHT = 600
FPS = 60

GRID_ROWS = 3
GRID_COLS = 3

# ---------------------------
# Colors / Theme
# ---------------------------

# Fallback background (we mostly use the gradient instead of this)
BACKGROUND_COLOR = (20, 40, 40)  # deep teal fallback

TEXT_COLOR = (245, 245, 235)  # soft off-white

# Tropical theme for mole + holes (used for Default theme circles)
MOLE_COLOR = (150, 90, 50)   # warm brown (mole "fur")
HOLE_COLOR = (90, 55, 30)    # earthy soil brown

# ---------------------------
# Difficulty presets
# ---------------------------
# mole_visible_ms: how long a mole stays up
# spawn_interval_ms: how often a mole appears
# game_length_seconds: total game time

DIFFICULTIES = {
    "Easy":   (1200, 900, 30),
    "Medium": (900, 700, 25),
    "Hard":   (650, 550, 20),
}

# These are set via the menu callbacks
player_name = "Player1"
selected_difficulty = "Easy"

# ---------------------------
# Theme presets
# ---------------------------
# Each theme can define:
# - bg_type: "gradient" or "image"
# - bg_colors: gradient colors (fallback if image missing)
# - bg_image_path: background image file (optional)
# - bg_music_path: background music file (optional)
# - mole_image_path: sprite for the mole (optional)
# - hole_image_path: sprite for the burrow/hole (optional)
# Runtime surfaces (bg_image_surface, mole_image_surface_raw, hole_image_surface_raw)
# are filled in main() after pygame.init().

THEMES = {
    "Default": {
        "bg_type": "gradient",
        "bg_colors": ((10, 70, 50), (230, 140, 70)),  # your current sunset gradient
        "bg_image_path": None,                        # no image, use gradient
        "bg_music_path": "assets/sounds/bg_music.mp3",
        "mole_image_path": None,                      # use circle
        "hole_image_path": None,                      # use circle
        "bg_image_surface": None,
        "mole_image_surface_raw": None,
        "hole_image_surface_raw": None,
    },
    "Jungle": {
        "bg_type": "image",
        "bg_colors": ((10, 60, 40), (40, 100, 60)),   # fallback gradient
        "bg_image_path": "assets/images/jungle_bg.png",
        "bg_music_path": "assets/sounds/jungle_bg.mp3",
        "mole_image_path": "assets/images/jungle_mole.png",
        "hole_image_path": "assets/images/jungle_hole.png",
        "bg_image_surface": None,
        "mole_image_surface_raw": None,
        "hole_image_surface_raw": None,
    },
    "Beach": {
        "bg_type": "image",
        "bg_colors": ((30, 140, 200), (240, 220, 160)),
        "bg_image_path": "assets/images/beach_bg.png",
        "bg_music_path": "assets/sounds/beach_bg.mp3",
        "mole_image_path": "assets/images/beach_mole.png",
        "hole_image_path": "assets/images/beach_hole.png",
        "bg_image_surface": None,
        "mole_image_surface_raw": None,
        "hole_image_surface_raw": None,
    },
    "Desert": {
        "bg_type": "image",
        "bg_colors": ((180, 140, 80), (240, 200, 130)),
        "bg_image_path": "assets/images/desert_bg.png",
        "bg_music_path": "assets/sounds/desert_bg.mp3",
        "mole_image_path": "assets/images/desert_mole.png",
        "hole_image_path": "assets/images/desert_hole.png",
        "bg_image_surface": None,
        "mole_image_surface_raw": None,
        "hole_image_surface_raw": None,
    },
}

# currently selected theme name (changed from the menu)
selected_theme = "Default"


# ---------------------------
# Helper functions
# ---------------------------

def draw_vertical_gradient(surface, color_top, color_bottom):
    """
    Draw a vertical gradient from color_top at the top
    to color_bottom at the bottom of the given surface.
    """
    width = surface.get_width()
    height = surface.get_height()

    for y in range(height):
        t = y / height  # 0 at top, 1 at bottom
        r = int(color_top[0] * (1 - t) + color_bottom[0] * t)
        g = int(color_top[1] * (1 - t) + color_bottom[1] * t)
        b = int(color_top[2] * (1 - t) + color_bottom[2] * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))


def compute_exit_button_rect(font):
    """
    Compute the rectangle for the in-game 'Exit' button based on the font.

    We use this BOTH for:
      - drawing the button
      - click detection

    so that the clickable area always matches what you see.
    """
    temp_surf = font.render("Exit", True, TEXT_COLOR)
    padding_x, padding_y = 10, 6

    rect = temp_surf.get_rect()
    rect.width += padding_x * 2
    rect.height += padding_y * 2
    rect.topright = (WINDOW_WIDTH - 10, 70)  # 10px from top-right corner

    return rect


# ---------------------------
# Game objects
# ---------------------------

class Mole(pygame.sprite.Sprite):
    """
    A single mole that can appear at a fixed hole position.

    If mole_image_surface is provided, we draw that sprite.
    Otherwise, we draw a simple colored circle.
    """

    def __init__(self, pos, radius, visible_ms, mole_image_surface=None):
        super().__init__()
        self.base_radius = radius
        self.visible_ms = visible_ms

        self.use_sprite = mole_image_surface is not None

        if self.use_sprite:
            # Use the provided image (already scaled for this radius)
            self.image = mole_image_surface
        else:
            # We'll draw a circle on this surface when active.
            self.image = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)

        self.rect = self.image.get_rect(center=pos)
        self.active = False
        self.spawn_time = 0  # in ms

    def activate(self, now_ms):
        """Show the mole starting from the given time."""
        self.active = True
        self.spawn_time = now_ms

    def deactivate(self):
        """Hide the mole."""
        self.active = False

    def update(self, now_ms):
        """
        Auto-hide the mole after it's been visible longer than visible_ms.
        Called from the main game loop every frame.
        """
        if self.active and (now_ms - self.spawn_time) > self.visible_ms:
            self.deactivate()

    def draw(self, surface):
        """Draw the mole if active (sprite or circle)."""
        if not self.active:
            return

        if self.use_sprite:
            surface.blit(self.image, self.rect)
        else:
            # Clear mole surface
            self.image.fill((0, 0, 0, 0))
            # Draw a simple circle representing the mole
            pygame.draw.circle(
                self.image,
                MOLE_COLOR,
                (self.base_radius, self.base_radius),
                self.base_radius,
            )
            surface.blit(self.image, self.rect)


# ---------------------------
# Board layout helpers
# ---------------------------

def create_holes():
    """
    Create positions for the holes in a GRID_ROWS x GRID_COLS layout.

    Returns:
        positions: list[(x, y)]
        radius:    int radius for holes/moles
    """
    margin_x = WINDOW_WIDTH // 8
    margin_y = WINDOW_HEIGHT // 6

    available_width = WINDOW_WIDTH - 2 * margin_x
    available_height = WINDOW_HEIGHT - 2 * margin_y

    cell_w = available_width // GRID_COLS
    cell_h = available_height // GRID_ROWS

    positions = []
    for row in range(GRID_ROWS):
        for col in range(GRID_COLS):
            x = margin_x + cell_w * col + cell_w // 2
            y = margin_y + cell_h * row + cell_h // 2
            positions.append((x, y))

    radius = min(cell_w, cell_h) // 3
    return positions, radius


def draw_holes(surface, positions, radius):
    """
    Draw the static 'holes' as slightly larger dark circles.
    """
    for pos in positions:
        pygame.draw.circle(surface, HOLE_COLOR, pos, radius + 8)


def draw_holes_with_theme(surface, positions, radius, hole_image_surface=None):
    """
    Draw the holes using a sprite if provided; otherwise use simple circles.
    """
    if hole_image_surface is None:
        draw_holes(surface, positions, radius)
        return

    for pos in positions:
        rect = hole_image_surface.get_rect(center=pos)
        surface.blit(hole_image_surface, rect)


# ---------------------------
# Main game loop
# ---------------------------

def run_game(screen, clock, difficulty_name, player_name_value,
             splat_sound, click_sound, game_over_sound,
             theme_name):
    """
    One full game session:
      - handles score, lives, time
      - spawns moles
      - handles clicks
      - draws theme background + HUD + Exit button

    Returns to the main menu when:
      - time is up, player hits ESC from game over
      - or player clicks the in-game Exit button
    """
    # Unpack difficulty
    mole_visible_ms, spawn_interval_ms, game_length_seconds = DIFFICULTIES[difficulty_name]

    # Get hole positions
    positions, hole_radius = create_holes()

    # --- Theme setup ---
    theme = THEMES.get(theme_name, THEMES["Default"])

    # Background image (already loaded & scaled in main, if available)
    bg_image = theme.get("bg_image_surface")

    # Scale mole + hole sprites for this radius (if provided)
    mole_sprite = None
    hole_sprite = None

    raw_mole = theme.get("mole_image_surface_raw")
    raw_hole = theme.get("hole_image_surface_raw")

    if raw_mole is not None:
        mole_sprite = pygame.transform.smoothscale(
            raw_mole,
            (hole_radius * 2, hole_radius * 2),
        )
    if raw_hole is not None:
        hole_sprite = pygame.transform.smoothscale(
            raw_hole,
            (hole_radius * 2 + 16, hole_radius * 2 + 16),
        )

    # Theme-specific background music
    theme_music_path = theme.get("bg_music_path")
    if theme_music_path:
        try:
            pygame.mixer.music.load(theme_music_path)
            pygame.mixer.music.play(-1)
            pygame.mixer.music.set_volume(0.5)
        except Exception as e:
            print("Error loading theme music:", e)

    # Create moles (one per hole)
    moles = pygame.sprite.Group()
    mole_list = []
    for pos in positions:
        # Each Mole shares the same sprite (already scaled), if provided
        mole = Mole(pos, hole_radius, mole_visible_ms, mole_image_surface=mole_sprite)
        moles.add(mole)
        mole_list.append(mole)

    # Game state
    score = 0
    lives = 3
    last_spawn_time = 0
    active_mole = None
    game_over = False

    # Fonts
    font = pygame.font.SysFont("arial", 28)
    big_font = pygame.font.SysFont("arial", 48)

    # Time tracking
    start_time_ms = pygame.time.get_ticks()

    def spawn_new_mole(now_ms):
        """Deactivate old mole (if any), pick a random one, and activate it."""
        nonlocal active_mole
        if active_mole is not None:
            active_mole.deactivate()

        active_mole = random.choice(mole_list)
        active_mole.visible_ms = mole_visible_ms
        active_mole.activate(now_ms)

    # ---------------
    # Game loop
    # ---------------
    while True:
        dt = clock.tick(FPS)  # not heavily used here but keeps framerate
        now_ms = pygame.time.get_ticks()

        # Compute remaining time
        elapsed_s = (now_ms - start_time_ms) / 1000.0
        remaining_s = max(0, int(game_length_seconds - elapsed_s))

        # Game over condition
        if (remaining_s <= 0 or lives <= 0) and not game_over:
            game_over = True
            pygame.mixer.music.stop()         # stop bg music
            game_over_sound.play()            # play game over sound

        # ----------------
        # Event handling
        # ----------------
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                # Full program exit if window X is clicked
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = pygame.mouse.get_pos()

                # 1) Check in-game Exit button click (works even if game_over)
                exit_rect = compute_exit_button_rect(font)
                if exit_rect.collidepoint(mouse_pos):
                    if click_sound:
                        click_sound.play()
                    # Return to menu
                    return

                # 2) Otherwise, only check mole hits if game still active
                if not game_over:
                    hit_any = False
                    for mole in mole_list:
                        if mole.active and mole.rect.collidepoint(mouse_pos):
                            score += 1
                            mole.deactivate()
                            splat_sound.play()
                            hit_any = True
                            break

                    if not hit_any:
                        lives -= 1

            # After game over, pressing ESC returns to menu
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return

        # ----------------
        # Game logic
        # ----------------
        if not game_over and (now_ms - last_spawn_time) > spawn_interval_ms:
            spawn_new_mole(now_ms)
            last_spawn_time = now_ms

        moles.update(now_ms)

        # ----------------
        # Drawing
        # ----------------

        # 1) Background: image if available, else theme gradient
        if bg_image is not None:
            screen.blit(bg_image, (0, 0))
        else:
            bg_top, bg_bottom = theme.get("bg_colors", ((10, 70, 50), (230, 140, 70)))
            draw_vertical_gradient(screen, bg_top, bg_bottom)

        # 2) Draw holes (sprite or circles) + moles
        draw_holes_with_theme(screen, positions, hole_radius, hole_sprite)
        for mole in mole_list:
            mole.draw(screen)

        # 3) HUD text surfaces
        score_surf = font.render(f"Score: {score}", True, TEXT_COLOR)
        lives_surf = font.render(f"Lives: {lives}", True, TEXT_COLOR)
        time_surf = font.render(f"Time: {remaining_s:02d}", True, TEXT_COLOR)

        small_font = pygame.font.SysFont("arial", 22)
        name_surf = small_font.render(f"Player: {player_name_value}", True, TEXT_COLOR)
        diff_surf = small_font.render(f"Difficulty: {difficulty_name}", True, TEXT_COLOR)

        # 4) Smaller HUD card in top-left (Score, Lives, Time only)
        hud_padding_x = 14
        hud_padding_y = 10
        hud_width = 230
        hud_height = 110

        hud_rect = pygame.Rect(10, 10, hud_width, hud_height)

        hud_surface = pygame.Surface((hud_width, hud_height), pygame.SRCALPHA)
        pygame.draw.rect(
            hud_surface,
            (20, 80, 40, 170),  # jungle green with alpha
            pygame.Rect(0, 0, hud_width, hud_height),
            border_radius=16,
        )
        pygame.draw.rect(
            hud_surface,
            (255, 230, 140, 220),  # golden sunlight border
            pygame.Rect(0, 0, hud_width, hud_height),
            width=2,
            border_radius=16,
        )
        screen.blit(hud_surface, hud_rect.topleft)

        # Inside HUD card
        base_x = hud_rect.x + hud_padding_x
        base_y = hud_rect.y + hud_padding_y
        line_spacing = 30

        screen.blit(score_surf, (base_x, base_y))
        screen.blit(lives_surf, (base_x, base_y + line_spacing))
        screen.blit(time_surf, (base_x, base_y + line_spacing * 2))

        # 5) Player + Difficulty labels at top-right (no card)
        top_right_y = 12
        diff_rect = diff_surf.get_rect(topright=(WINDOW_WIDTH - 15, top_right_y + 24))
        name_rect = name_surf.get_rect(topright=(WINDOW_WIDTH - 15, top_right_y))

        screen.blit(name_surf, name_rect.topleft)
        screen.blit(diff_surf, diff_rect.topleft)

        # 6) In-game Exit button
        exit_rect = compute_exit_button_rect(font)

        exit_surface = pygame.Surface((exit_rect.width, exit_rect.height), pygame.SRCALPHA)
        pygame.draw.rect(
            exit_surface,
            (10, 60, 40, 210),  # darker green
            pygame.Rect(0, 0, exit_rect.width, exit_rect.height),
            border_radius=10,
        )
        pygame.draw.rect(
            exit_surface,
            (255, 220, 130, 255),
            pygame.Rect(0, 0, exit_rect.width, exit_rect.height),
            width=2,
            border_radius=10,
        )
        exit_text_surf = font.render("Exit", True, TEXT_COLOR)
        exit_text_rect = exit_text_surf.get_rect(center=(exit_rect.width // 2, exit_rect.height // 2))
        exit_surface.blit(exit_text_surf, exit_text_rect.topleft)
        screen.blit(exit_surface, exit_rect.topleft)

        # 7) Game over overlay
        if game_over:
            overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (0, 0))

            go_text = big_font.render("GAME OVER", True, (255, 100, 90))
            final_score = font.render(f"Final Score: {score}", True, TEXT_COLOR)
            hint_text = font.render("Press ESC to return to menu", True, TEXT_COLOR)

            screen.blit(go_text, go_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 - 40)))
            screen.blit(final_score, final_score.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 10)))
            screen.blit(hint_text, hint_text.get_rect(center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2 + 50)))

        pygame.display.flip()


# ---------------------------
# Main menu entry point
# ---------------------------

def main():
    """
    Entry point:
      - initializes pygame
      - loads theme assets
      - builds tropical-themed menu using pygame_menu
      - handles starting the game and quitting
    """
    pygame.init()
    pygame.mixer.init()

    # ---- Load sound effects ----
    click_sound = pygame.mixer.Sound("assets/sounds/click.wav")
    splat_sound = pygame.mixer.Sound("assets/sounds/splat.wav")
    game_over_sound = pygame.mixer.Sound("assets/sounds/game_over.wav")

    pygame.display.set_caption("Mole Attack - Whack-a-Mole Themes")

    screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
    clock = pygame.time.Clock()

    # ----- Load menu background image -----
    # try:
    menu_bg = pygame.image.load("assets/images/menu_bg.png").convert()
    menu_bg = pygame.transform.scale(menu_bg, (WINDOW_WIDTH, WINDOW_HEIGHT))
    # except Exception as e:
    #     print("Menu background not found, using gradient instead.", e)
    #     menu_bg = None



    # We want to update these from menu callbacks
    global player_name, selected_difficulty, selected_theme

    # ---- Preload theme images (backgrounds, moles, holes) ----
    for name, theme in THEMES.items():
        # Background image (scaled to window)
        bg_path = theme.get("bg_image_path")
        if bg_path:
            try:
                img = pygame.image.load(bg_path).convert()
                theme["bg_image_surface"] = pygame.transform.scale(
                    img, (WINDOW_WIDTH, WINDOW_HEIGHT)
                )
            except Exception as e:
                print(f"Error loading bg for theme {name}:", e)
                theme["bg_image_surface"] = None
        else:
            theme["bg_image_surface"] = None

        # Mole sprite (keep raw; scale later in run_game)
        mole_path = theme.get("mole_image_path")
        if mole_path:
            try:
                theme["mole_image_surface_raw"] = pygame.image.load(mole_path).convert_alpha()
            except Exception as e:
                print(f"Error loading mole for theme {name}:", e)
                theme["mole_image_surface_raw"] = None
        else:
            theme["mole_image_surface_raw"] = None

        # Hole sprite (keep raw; scale later)
        hole_path = theme.get("hole_image_path")
        if hole_path:
            try:
                theme["hole_image_surface_raw"] = pygame.image.load(hole_path).convert_alpha()
            except Exception as e:
                print(f"Error loading hole for theme {name}:", e)
                theme["hole_image_surface_raw"] = None
        else:
            theme["hole_image_surface_raw"] = None

    # ---- Default background music for menu (Default theme) ----
    default_music_path = THEMES["Default"]["bg_music_path"]
    if default_music_path:
        try:
            pygame.mixer.music.load(default_music_path)
            pygame.mixer.music.play(-1)   # loop forever
            pygame.mixer.music.set_volume(0.5)
        except Exception as e:
            print("Error loading default music:", e)
    # ---- 3-2-1 countdown before starting the game ----
    def show_countdown():
        """
        Show a 3–2–1 countdown using the currently selected theme's background
        before starting the game.
        """
        countdown_font = pygame.font.SysFont("arial", 96, bold=True)

        for number in [3, 2, 1]:
            start_ms = pygame.time.get_ticks()
            # Stay on this number for ~1 second
            while pygame.time.get_ticks() - start_ms < 1000:
                # Allow quitting during countdown
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                # Get the current theme
                theme = THEMES.get(selected_theme, THEMES["Default"])
                bg_image = theme.get("bg_image_surface")

                # Draw theme background: image if available, else gradient
                if bg_image is not None:
                    screen.blit(bg_image, (0, 0))
                else:
                    bg_top, bg_bottom = theme.get(
                        "bg_colors",
                        ((10, 70, 50), (230, 140, 70)),
                    )
                    draw_vertical_gradient(screen, bg_top, bg_bottom)

                # Dark overlay on top
                overlay = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
                overlay.fill((0, 0, 0, 150))
                screen.blit(overlay, (0, 0))

                # Big countdown number in the center
                text_surf = countdown_font.render(str(number), True, (255, 255, 255))
                text_rect = text_surf.get_rect(
                    center=(WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
                )
                screen.blit(text_surf, text_rect)

                pygame.display.flip()
                clock.tick(FPS)


    # ---- Menu callbacks ----

    def set_player_name(value: str):
        """Update global player_name from text input."""
        global player_name
        player_name = value

    def set_difficulty(selected, difficulty_index):
        """Update global difficulty based on selector."""
        global selected_difficulty
        selected_difficulty = selected[0][0]  # "Easy" / "Medium" / "Hard"

    def set_theme(selected, index):
        """Update the selected theme name from the menu selector."""
        global selected_theme
        selected_theme = selected[0][0]  # "Default", "Jungle", "Beach", "Desert"

    def quit_game():
        """Play click sound and quit the game."""
        if click_sound:
            click_sound.play()
        pygame.quit()
        sys.exit()

    def start_the_game():
        """
        Called by the 'Play' button.
        Runs a 3-2-1 countdown, then a single game session,
        then returns to this menu loop.
        """
        if click_sound:
            click_sound.play()

        # 3–2–1 countdown with the currently selected theme background
        show_countdown()

        # Now start the actual game
        run_game(
            screen,
            clock,
            selected_difficulty,
            player_name,
            splat_sound,
            click_sound,
            game_over_sound,
            selected_theme,
        )

        # When game returns, restore default background music
        if default_music_path:
            try:
                pygame.mixer.music.load(default_music_path)
                pygame.mixer.music.play(-1)
                pygame.mixer.music.set_volume(0.5)
            except Exception as e:
                print("Error restoring default music:", e)


    # ---- Tropical menu theme ----

    base_theme = pygame_menu.themes.THEME_DARK.copy()
    base_theme.background_color = (0, 0, 0, 0)  # fully transparent so our image shows


    base_theme.title_font = pygame_menu.font.FONT_NEVIS
    base_theme.title_font_size = 64
    base_theme.title_font_color = (255, 230, 150)
    base_theme.title_background_color = (30, 90, 60)

    base_theme.widget_font = pygame_menu.font.FONT_MUNRO
    base_theme.widget_font_size = 40
    base_theme.widget_font_color = (240, 240, 230)
    base_theme.widget_margin = (0, 15)
    base_theme.widget_padding = 14
    base_theme.selection_color = (255, 220, 130)
    base_theme.widget_alignment = pygame_menu.locals.ALIGN_CENTER

    # ---- Create menu ----
    menu = pygame_menu.Menu(
        "Mole Attack",
        WINDOW_WIDTH,
        WINDOW_HEIGHT,
        theme=base_theme,
    )

    menu.add.label("Welcome!!!", max_char=-1, font_size=40)
    menu.add.vertical_margin(30)

    menu.add.text_input(
        "Name: ",
        default=player_name,
        onchange=set_player_name,
    )

    menu.add.selector(
        "Difficulty: ",
        [("Easy", 1), ("Medium", 2), ("Hard", 3)],
        onchange=set_difficulty,
    )

    menu.add.selector(
        "Theme: ",
        [("Default", 1), ("Jungle", 2), ("Beach", 3), ("Desert", 4)],
        onchange=set_theme,
    )

    menu.add.vertical_margin(30)
    menu.add.button("Play", start_the_game)
    menu.add.button("Quit", quit_game)

    # ---- Menu loop ----
    while True:
        # Tropical gradient background behind the menu
       # Draw dedicated menu background image
        if menu_bg is not None:
            screen.blit(menu_bg, (0, 0))
        else:
            # Fallback: use the original gradient
            draw_vertical_gradient(
                screen,
                (5, 60, 45),
                (220, 135, 75),
            )


        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        if menu.is_enabled():
            menu.update(events)
            menu.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)


if __name__ == "__main__":
    main()
