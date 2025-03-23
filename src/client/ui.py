import pygame
import random
import sys
import os
import time

# import src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.common.models import GameObject
from src.client.controller import Controller
from src.client.view import View
from src.client.rpc_client import MindRollClient

pygame.init()
pygame.font.init()

# ------------------- client Setup------------------
server_ip = "127.0.0.1"
server_port = 8080
client = MindRollClient((server_ip, server_port))

# ------------------- Screen Setup -------------------
SCREEN_SIZE = (800, 600)
screen = pygame.display.set_mode(SCREEN_SIZE)
pygame.display.set_caption("MindRoll")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
RED = (255, 0, 0)

def get_font(size):
    return pygame.font.Font(None, size)

# ------------------- Game State -------------------
STATE_MAIN_MENU = "main_menu"
STATE_REGISTER = "register"
STATE_LOGIN = "login"
STATE_LOGIN_WAIT = "login_WAIT"
STATE_MOD_SCREEN = "mod_screen"
STATE_GAME = "game"
STATE_RULES = "rules"

current_state = STATE_MAIN_MENU

room_name = ""
selected_room = ""

register_account = ""
register_password = ""
login_account = ""
login_password = ""

player_score = 0
player_dice = ("red", 1)  # (dice_color, dice_number)

input_text = ""

active_input = "account"

# --------------- get winner state ---------------
last_pull_time = 0.0
PULL_INTERVAL = 1.0  


cached_game_state = None

# ------------------- Dice-------------------
DICE_COLORS = ["red", "yellow", "green", "blue", "black"]
DICE_SIZE = (300, 300)

def load_dice_images():
    images = {}
    for color in DICE_COLORS:
        images[color] = {}
        for number in range(1, 7):
            path = f"assets/dice/{color}{number}.png"
            img = pygame.image.load(path)
            img = pygame.transform.scale(img, DICE_SIZE)
            images[color][number] = img
    return images

dice_images = load_dice_images()

def show_message(message):
    popup_width, popup_height = 600, 100
    popup_x = (SCREEN_SIZE[0] - popup_width) // 2
    popup_y = (SCREEN_SIZE[1] - popup_height) // 2

    popup = pygame.Surface((popup_width, popup_height))
    popup.fill(WHITE)

    text_surface = get_font(30).render(message, True, RED)
    text_x = (popup_width - text_surface.get_width()) // 2
    text_y = (popup_height - text_surface.get_height()) // 2
    popup.blit(text_surface, (text_x, text_y))

    screen.blit(popup, (popup_x, popup_y))
    pygame.display.flip()
    pygame.time.delay(2000)

def draw_button(text, rect, color, font_size=36):
    pygame.draw.rect(screen, color, rect)
    font = get_font(font_size)
    text_surface = font.render(text, True, WHITE)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)

# ------------------- Main Menu -------------------
def main_menu():
    global current_state
    screen.fill(BLACK)
    title_text = get_font(50).render("MindRoll", True, WHITE)
    screen.blit(title_text, (SCREEN_SIZE[0] // 2 - 100, 50))

    register_button = pygame.Rect(300, 200, 200, 50)
    login_button = pygame.Rect(300, 300, 200, 50)
    rules_button = pygame.Rect(300, 400, 200, 50)
    exit_button = pygame.Rect(300, 500, 200, 50)

    draw_button("Register", register_button, BLUE)
    draw_button("Login", login_button, BLUE)
    draw_button("Game Rules", rules_button, BLUE)
    draw_button("Exit", exit_button, BLUE)

    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if register_button.collidepoint(event.pos):
                current_state = STATE_REGISTER
            elif login_button.collidepoint(event.pos):
                current_state = STATE_LOGIN
            elif rules_button.collidepoint(event.pos):
                current_state = STATE_RULES
            elif exit_button.collidepoint(event.pos):
                return False
    return True

def input_screen(title, account_var_name, password_var_name, next_state):
    global current_state, register_account, register_password, login_account, login_password, active_input

    screen.fill(BLACK)
    title_text = get_font(30).render(title, True, WHITE)
    screen.blit(title_text, (SCREEN_SIZE[0] // 2 - 100, 50))

    account_box = pygame.Rect(250, 150, 300, 50)
    password_box = pygame.Rect(250, 250, 300, 50)
    confirm_button = pygame.Rect(300, 350, 200, 50)
    back_button = pygame.Rect(300, 420, 200, 50)

    pygame.draw.rect(screen, GRAY, account_box)
    pygame.draw.rect(screen, WHITE, account_box, 2)
    pygame.draw.rect(screen, GRAY, password_box)
    pygame.draw.rect(screen, WHITE, password_box, 2)
    draw_button("Confirm", confirm_button, BLUE)
    draw_button("Back", back_button, BLUE)

    account_var = globals()[account_var_name]
    password_var = globals()[password_var_name]

    acc_text = get_font(30).render(account_var, True, BLACK)
    pwd_text = get_font(30).render("*" * len(password_var), True, BLACK)
    screen.blit(acc_text, (account_box.x + 10, account_box.y + 10))
    screen.blit(pwd_text, (password_box.x + 10, password_box.y + 10))

    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:
                active_input = "password" if active_input == "account" else "account"
            elif event.key == pygame.K_BACKSPACE:
                if active_input == "account" and len(globals()[account_var_name])>0:
                    globals()[account_var_name] = globals()[account_var_name][:-1]
                elif active_input == "password" and len(globals()[password_var_name])>0:
                    globals()[password_var_name] = globals()[password_var_name][:-1]
            elif event.key == pygame.K_RETURN:
                current_state = next_state
            elif event.unicode.isalnum():
                if active_input == "account" and len(globals()[account_var_name])<10:
                    globals()[account_var_name] += event.unicode
                elif active_input == "password" and len(globals()[password_var_name])<10:
                    globals()[password_var_name] += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            if account_box.collidepoint(event.pos):
                active_input = "account"
            elif password_box.collidepoint(event.pos):
                active_input = "password"
            elif back_button.collidepoint(event.pos):
                current_state = STATE_MAIN_MENU
            elif confirm_button.collidepoint(event.pos):
                if title == "Register":
                    resp = client.register(register_account, register_password)
                    if resp and not resp.error:
                        show_message("Successfully Registered!")
                        current_state = STATE_MAIN_MENU
                    else:
                        show_message("Register Failed: " + (resp.error if resp else "Unknown Error"))
                elif title == "Login":
                    resp = client.login(login_account, login_password)
                    if resp and not resp.error:
                        show_message("Successfully Login!")
                        current_state = next_state
                    else:
                        show_message("Login Failed: " + (resp.error if resp else "Unknown Error"))
    return True

def rules_screen():
    global current_state
    screen.fill(BLACK)
    rules_text = [
        "MindRoll Rules:",
        "1. Each player gets a random dice.",
        "2. Players take turns to Call a number.",
        "3. A player can choose to Reveal the result => resets for next round.",
        "4. If the call is greater than sum, that revealer wins, else loses.",
        "5. If a player times out 120s & doesn't reconnect, the game resets for others.",
        "6. If the game has started, new players cannot join until it resets or ends.",
        "Press Back to return."
    ]

    y_offset = 50
    for line in rules_text:
        text_surface = get_font(30).render(line, True, WHITE)
        screen.blit(text_surface, (50, y_offset))
        y_offset += 40

    back_button = pygame.Rect(300, 500, 200, 50)
    draw_button("Back", back_button, BLUE)

    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if back_button.collidepoint(event.pos):
                current_state = STATE_MAIN_MENU
    return True

def mod_screen():
    global current_state, room_name, selected_room

    screen.fill(BLACK)
    title_text = get_font(50).render("Select Game Mode", True, WHITE)
    screen.blit(title_text, (SCREEN_SIZE[0] // 2 - 150, 50))

    create_button = pygame.Rect(300, 250, 200, 50)
    join_button = pygame.Rect(300, 350, 200, 50)
    reconnect_button = pygame.Rect(300, 450, 200, 50)
    back_button = pygame.Rect(300, 540, 200, 50)

    draw_button("Create a Room", create_button, BLUE)
    draw_button("Join a Room", join_button, BLUE)
    draw_button("Reconnect", reconnect_button, BLUE)
    draw_button("Back", back_button, BLUE)

    input_box = pygame.Rect(250, 150, 300, 50)
    pygame.draw.rect(screen, GRAY, input_box)
    pygame.draw.rect(screen, WHITE, input_box, 2)
    text_surface = get_font(30).render(room_name, True, BLACK)
    screen.blit(text_surface, (input_box.x + 10, input_box.y + 10))

    pygame.display.flip()

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                room_name = room_name[:-1]
            elif event.key == pygame.K_RETURN:
                pass
            elif event.unicode.isalnum():
                room_name += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            if create_button.collidepoint(event.pos):
                resp_create = client.create_room(room_name)
                if resp_create and not resp_create.error:
                    show_message(f"Created room: {room_name}")
                    resp_join = client.join_room(room_name, login_account)
                    if resp_join and not resp_join.error:
                        show_message(f"Joined room: {room_name}")
                        selected_room = room_name
                        room_name = ""
                        current_state = STATE_GAME
                    else:
                        if resp_join and resp_join.error == "Cannot join: game already started!":
                            show_message("Cannot join: game already started!")
                        else:
                            show_message("Join created room failed: " + (resp_join.error if resp_join else "Unknown Error"))
                else:
                    show_message("Fail to Create Room: " + (resp_create.error if resp_create else "Unknown Error"))

            elif join_button.collidepoint(event.pos):
                resp_join = client.join_room(room_name, login_account)
                if resp_join and not resp_join.error:
                    show_message(f"Joined room: {room_name}")
                    selected_room = room_name
                    room_name = ""
                    current_state = STATE_GAME
                else:
                    if resp_join and resp_join.error == "Cannot join: game already started!":
                        show_message("Cannot join: game already started!")
                    else:
                        show_message("Fail to Join Room: " + (resp_join.error if resp_join else "Unknown Error"))

            elif reconnect_button.collidepoint(event.pos):
                if room_name.strip():
                    resp_reconn = client.reconnect(room_name, login_account)
                    if resp_reconn and not resp_reconn.error:
                        show_message(f"Reconnected to {room_name}")
                        selected_room = room_name
                        room_name = ""
                        current_state = STATE_GAME
                    else:
                        show_message("Reconnect failed: " + (resp_reconn.error if resp_reconn else "Unknown Error"))
                else:
                    show_message("Please input the room name to reconnect.")

            elif back_button.collidepoint(event.pos):
                current_state = STATE_MAIN_MENU

    return True

# ------------------- Queue Request-------------------
last_pull_time = 0.0
PULL_INTERVAL = 1.0
cached_game_state = None  #

def game_screen():
    global current_state, player_dice, input_text, selected_room, player_score
    global last_pull_time, cached_game_state

    screen.fill(BLACK)
    font = get_font(30)

    # -- PULL_INTERVAL --> get_game_state --
    now = time.time()
    if selected_room and (now - last_pull_time > PULL_INTERVAL):
        last_pull_time = now
        resp = client.get_game_state(selected_room)
        if resp and not resp.error:
            cached_game_state = resp.result

            last_result_str = cached_game_state.get("last_result_str", None)
            if last_result_str:
                show_message(last_result_str)

            # update player info
            if login_account in cached_game_state.get("players", {}):
                pinfo = cached_game_state["players"][login_account]
                player_dice = (pinfo["dice_color"], pinfo["dice_number"])
                player_score = pinfo["score"]

            # check if room is empty
            if not cached_game_state["players"]:
                show_message("Room is empty or removed; returning to menu.")
                current_state = STATE_MAIN_MENU
        else:
            show_message("Failed to get game state. Possibly room removed.")
            current_state = STATE_MAIN_MENU

    current_call_number = 0
    current_turn_player = "Unknown"
    players_in_room = 0
    if cached_game_state:
        current_call_number = cached_game_state.get("called_number", 0)
        current_turn_player = cached_game_state.get("current_turn", "Unknown")
        players_dict = cached_game_state.get("players", {})
        players_in_room = len(players_dict)

    room_info = font.render(f"Current Room: {selected_room if selected_room else 'None'}", True, WHITE)
    screen.blit(room_info, (20, 20))

    score_info = font.render(f"Your Score: {player_score}", True, WHITE)
    screen.blit(score_info, (20, 60))

    players_count_info = font.render(f"Players in Room: {players_in_room}", True, WHITE)
    screen.blit(players_count_info, (20, 100))

    call_info = font.render(f"Current Call: {current_call_number}", True, WHITE)
    screen.blit(call_info, (20, 140))

    turn_info = font.render(f"Current Turn: {current_turn_player}", True, WHITE)
    screen.blit(turn_info, (20, 180))

    player_info = font.render(f"User: {login_account}", True, WHITE)
    screen.blit(player_info, (400, 20))

    # current dice
    dice_color, dice_number = player_dice
    dice_image = dice_images[dice_color][dice_number]
    screen.blit(dice_image, (50, 230))

    # input box
    input_box = pygame.Rect(450, 200, 100, 50)
    pygame.draw.rect(screen, GRAY, input_box)
    pygame.draw.rect(screen, WHITE, input_box, 2)
    text_surface = font.render(input_text, True, BLACK)
    screen.blit(text_surface, (input_box.x + 10, input_box.y + 10))

    # buttons
    call_button = pygame.Rect(600, 200, 150, 50)
    reveal_button = pygame.Rect(600, 300, 150, 50)
    #back_button = pygame.Rect(600, 400, 150, 50)
    leave_button = pygame.Rect(600, 400, 150, 50)

    draw_button("Call", call_button, BLUE)
    draw_button("Reveal", reveal_button, BLUE)
    #draw_button("Back", back_button, BLUE)
    draw_button("Leave Room", leave_button, BLUE)

    pygame.display.flip()

    # ------------------- Handle Request -------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]
            elif event.key == pygame.K_RETURN:
                # Return => call
                try:
                    call_value = int(input_text)
                    if selected_room:
                        resp_call = client.call_number(selected_room, login_account, call_value)
                        if resp_call and not resp_call.error:
                            show_message(f"Call success: {call_value}")
                        else:
                            show_message(f"Call failed: {(resp_call.error if resp_call else 'Unknown error')}")
                    else:
                        show_message("No room selected!")
                except ValueError:
                    pass
                input_text = ""
            elif event.unicode.isdigit():
                input_text += event.unicode

        if event.type == pygame.MOUSEBUTTONDOWN:
            # if back_button.collidepoint(event.pos):
            #     current_state = STATE_MAIN_MENU

            if call_button.collidepoint(event.pos):
                if selected_room:
                    try:
                        call_value = int(input_text)
                        resp_call = client.call_number(selected_room, login_account, call_value)
                        if resp_call and not resp_call.error:
                            show_message(f"Call success: {call_value}")
                        else:
                            show_message(f"Call failed: {(resp_call.error if resp_call else 'Unknown error')}")
                    except ValueError:
                        show_message("Please input a valid number.")
                    input_text = ""
                else:
                    show_message("No room selected!")

            elif reveal_button.collidepoint(event.pos):
                if selected_room:
                    resp_reveal = client.reveal_result(selected_room, login_account)
                    if resp_reveal and not resp_reveal.error:
                        result_info = resp_reveal.result
                        # show local message
                        show_message(f"Reveal: {result_info['result_str']}")

                        # update player info
                        if login_account in result_info["players"]:
                            pinfo = result_info["players"][login_account]
                            player_score = pinfo["score"]
                            player_dice = (pinfo["dice_color"], pinfo["dice_number"])

                        # update cached game state
                        last_pull_time = 0
                    else:
                        show_message(f"Reveal failed: {(resp_reveal.error if resp_reveal else 'Unknown Error')}")
                else:
                    show_message("No room selected!")

            elif leave_button.collidepoint(event.pos):
                if selected_room:
                    resp_leave = client.leave_room(selected_room, login_account)
                    if resp_leave and not resp_leave.error:
                        show_message("Left the room successfully.")
                        current_state = STATE_MAIN_MENU
                    else:
                        show_message(f"Leave room failed: {(resp_leave.error if resp_leave else 'Unknown Error')}")
                else:
                    show_message("No room selected!")
    return True

def login_wait_screen():
    global current_state
    screen.fill(BLACK)
    waiting_text = get_font(50).render("Waiting for server...", True, WHITE)
    screen.blit(waiting_text, (SCREEN_SIZE[0] // 2 - 150, SCREEN_SIZE[1] // 2))
    pygame.display.flip()

    time.sleep(2)
    current_state = STATE_MOD_SCREEN
    return True

# ------------------- main -------------------
running = True
while running:
    if current_state == STATE_MAIN_MENU:
        running = main_menu()
    elif current_state == STATE_REGISTER:
        running = input_screen("Register", "register_account", "register_password", STATE_MAIN_MENU)
    elif current_state == STATE_LOGIN:
        running = input_screen("Login", "login_account", "login_password", STATE_MOD_SCREEN)
    elif current_state == STATE_LOGIN_WAIT:
        running = login_wait_screen()
    elif current_state == STATE_MOD_SCREEN:
        running = mod_screen()
    elif current_state == STATE_GAME:
        running = game_screen()
    elif current_state == STATE_RULES:
        running = rules_screen()

pygame.quit()
