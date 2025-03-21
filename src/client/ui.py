import pygame
import random
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.common.models import GameObject
from src.client.controller import Controller
from src.client.view import View
from src.client.rpc_client import MindRollClient


#initialize the client
server_ip = "127.0.0.1"
server_port = 8080
client = MindRollClient((server_ip, server_port))
    
# 初始化 Pygame
pygame.init()

# 设定窗口
SCREEN_SIZE = (800, 600)
screen = pygame.display.set_mode(SCREEN_SIZE)
pygame.display.set_caption("MindRoll")

# 颜色定义
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
GRAY = (200, 200, 200)
RED = (255, 0, 0)

# 字体
pygame.font.init()
def get_font(size):
    return pygame.font.Font(None, size)

# 游戏状态
STATE_MAIN_MENU = "main_menu"
STATE_REGISTER = "register"
STATE_LOGIN = "login"
STATE_LOGIN_WAIT = "login_WAIT"  # 等待服务器信号
STATE_MOD_SCREEN = "mod_screen"
STATE_GAME = "game"
STATE_RULES = "rules"
current_state = STATE_MAIN_MENU

# 颜色列表
DICE_COLORS = ["red", "yellow", "green", "blue", "black"]
DICE_SIZE = (300, 300)

# 加载骰子图片
def load_dice_images():
    images = {}
    for color in DICE_COLORS:
        images[color] = {}
        for number in range(1, 7):  # 1~6
            path = f"assets/dice/{color}{number}.png"  # 确保路径正确
            image = pygame.image.load(path)
            image = pygame.transform.scale(image, DICE_SIZE)  # 缩放到指定大小
            images[color][number] = image
    return images

# 载入图片
dice_images = load_dice_images()


# 获取随机骰子
def get_random_dice():
    color = random.choice(DICE_COLORS)  # 随机颜色
    number = random.randint(1, 6)  # 随机点数
    return color, number

# 弹窗函数
def show_message(message):
    popup_width, popup_height = 600, 100
    popup_x = (SCREEN_SIZE[0] - popup_width) // 2
    popup_y = (SCREEN_SIZE[1] - popup_height) // 2
    
    popup = pygame.Surface((popup_width, popup_height))
    popup.fill(WHITE)

    text_surface = get_font(30).render(message, True, RED)
    
    # 计算文本居中
    text_x = (popup_width - text_surface.get_width()) // 2
    text_y = (popup_height - text_surface.get_height()) // 2
    popup.blit(text_surface, (text_x, text_y))

    screen.blit(popup, (popup_x, popup_y))
    pygame.display.flip()
    pygame.time.delay(2000)  # 显示 2 秒



# 用户注册/登录信息
register_account = ""
register_password = ""
login_account = ""
login_password = ""
#number_of_players = 2  # 默认游戏玩家数（1v1）
# current_call = 3 * number_of_players  # 初始 Call 数字
# 游戏状态变量
player_name = "You"
player_score = 0
player_dice = get_random_dice()  # 初始随机骰子
# number_of_players = 3  # 默认游戏玩家数
#current_call = 3 * number_of_players  # 初始 Call 数字
input_text = ""  # 存储玩家输入的数字
is_1v1_mode = False  # 1v1 模式识别信号



# 输入框焦点
active_input = "account"  # 默认焦点在用户名输入框

# 按钮类
def draw_button(text, rect, color, font_size=36):
    pygame.draw.rect(screen, color, rect)
    font = get_font(font_size)
    text_surface = font.render(text, True, WHITE)
    text_rect = text_surface.get_rect(center=rect.center)
    screen.blit(text_surface, text_rect)


# 主菜单界面
def main_menu():
    global current_state
    screen.fill(BLACK)
    font = get_font(50)
    title_text = font.render("MindRoll", True, WHITE)
    screen.blit(title_text, (SCREEN_SIZE[0] // 2 - 100, 50))
    
    register_button = pygame.Rect(300, 200, 200, 50)
    login_button = pygame.Rect(300, 300, 200, 50)
    rules_button = pygame.Rect(300, 400, 200, 50)
    exit_button = pygame.Rect(300, 500, 200, 50)

    
    draw_button("Register", register_button, BLUE)
    draw_button("Login", login_button, BLUE)
    draw_button("Exit", exit_button, BLUE)
    draw_button("Game Rules", rules_button, BLUE)    


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


# 用户输入界面
def input_screen(title, account_var_name, password_var_name, next_state):
    global current_state, register_account, register_password, login_account, login_password, active_input, client
    screen.fill(BLACK)
    font = get_font(30)
    
    title_text = font.render(title, True, WHITE)
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
    
    account_text = get_font(30).render(account_var, True, BLACK)
    password_text = get_font(30).render("*" * len(password_var), True, BLACK)
    screen.blit(account_text, (account_box.x + 10, account_box.y + 10))
    screen.blit(password_text, (password_box.x + 10, password_box.y + 10))
    
    pygame.display.flip()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_TAB:  # 切换输入框
                active_input = "password" if active_input == "account" else "account"
            elif event.key == pygame.K_BACKSPACE:
                if active_input == "account" and len(globals()[account_var_name]) > 0:
                    globals()[account_var_name] = globals()[account_var_name][:-1]
                elif active_input == "password" and len(globals()[password_var_name]) > 0:
                    globals()[password_var_name] = globals()[password_var_name][:-1]
            elif event.key == pygame.K_RETURN:
                current_state = next_state
            elif event.unicode.isalnum():
                if active_input == "account" and len(globals()[account_var_name]) < 10:
                    globals()[account_var_name] += event.unicode
                elif active_input == "password" and len(globals()[password_var_name]) < 10:
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
                    # 调用客户端的注册方法
                    response = client.register(register_account, register_password)
                    if response and not response.error:
                        show_message("Successfully Registered！")
                        current_state = STATE_MAIN_MENU
                    else:
                        show_message("Register Failed:" + (response.error if response else "Unknown Error"))
                elif title == "Login":
                    # 调用客户端的登录方法
                    response = client.login(login_account, login_password)
                    join_response = client.join_room("room1", login_account)
                    if response and not response.error:
                        show_message("Successfully Login！")
                        current_state = next_state
                    else:
                        show_message("Login Failed：" + (response.error if response else "Unknown Error"))
    return True


# 规则界面
def rules_screen():
    global current_state
    screen.fill(BLACK)
    font = get_font(30)
    
    rules_text = [
        "MindRoll Rules:",
        "1. Each player gets a random dice.",
        "2. Players take turns to Call a number.",
        "3. A player can choose to Reveal the result.",
        "4. If the call is greater than sum of all dice, the one chose to reveal win.",
        "   If the call is less than sum of all dice, the one was asked to reveal win.",
        "   And if the number or color of their two dice is same, the one was asked",
        "   to reveal win.",
        "Press Back to return."
    ]

    y_offset = 50
    for line in rules_text:
        text_surface = font.render(line, True, WHITE)
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



# 选择游戏模式界面
def mod_screen():
    global current_state, number_of_players, new_room_flag, client
    screen.fill(BLACK)
    font = get_font(50)
    title_text = font.render("Select Game Mode", True, WHITE)
    screen.blit(title_text, (SCREEN_SIZE[0] // 2 - 150, 50))
    
    one_vs_one_button = pygame.Rect(300, 200, 200, 50)
    multiplayer_button = pygame.Rect(300, 300, 200, 50)
    back_button = pygame.Rect(300, 420, 200, 50)  
    
    draw_button("create a room", one_vs_one_button, BLUE)
    draw_button("join a room", multiplayer_button, BLUE)
    draw_button("Back", back_button, BLUE)
    
    pygame.display.flip()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if one_vs_one_button.collidepoint(event.pos):
                number_of_players = 2  # 服务器决定实际人数
                new_room_flag = True  # 识别信号，进入创建新房间
                response = client.create_room("room1")  # 创建房间
                if response and not response.error:
                    show_message("Create Room Succeed!")
                    current_state = STATE_GAME
                else:
                    show_message("Fail to Create Room:" + (response.error if response else "Unknown Error"))
            elif multiplayer_button.collidepoint(event.pos):
                number_of_players = 3  # 服务器决定实际人数
                new_room_flag = False
                response = client.join_room("room1", login_account)  # 加入房间
                if response and not response.error:
                    show_message("Join Room Succeed!")
                    current_state = STATE_GAME
                else:
                    show_message("Fail to Join Room:" + (response.error if response else "Unknown Error"))
            elif back_button.collidepoint(event.pos):
                current_state = STATE_MAIN_MENU
    return True


# 游戏界面
def game_screen():
    global current_state, player_name, player_score, player_dice, current_call, input_text, number_of_players
    screen.fill(BLACK)
    font = get_font(30)
    
    # 显示玩家信息
    player_info = font.render(f"Your Score: {player_score}       |      Player: {player_name} ", True, WHITE)
    screen.blit(player_info, (20, 20))
    
    # 显示当前玩家人数
    num_players_info = font.render(f"Players: {number_of_players}", True, WHITE)
    screen.blit(num_players_info, (20, 60))
    current_call = 3 * number_of_players  # 初始 Call 数字
    # 显示骰子图片
    dice_color, dice_number = player_dice
    dice_image = dice_images[dice_color][dice_number]
    screen.blit(dice_image, (50, 170))  # 画到屏幕上
    
    # 显示当前 Call（动态更新）
    call_info = font.render(f"Current Call: {current_call}", True, WHITE)
    screen.blit(call_info, (450, 20))
    
    # 绘制输入框
    input_box = pygame.Rect(450, 200, 100, 50)
    pygame.draw.rect(screen, GRAY, input_box)
    pygame.draw.rect(screen, WHITE, input_box, 2)
    text_surface = get_font(36).render(input_text, True, BLACK)
    screen.blit(text_surface, (input_box.x + 10, input_box.y + 10))
    
    # 按钮
    call_button = pygame.Rect(600, 200, 150, 50)
    reveal_button = pygame.Rect(600, 300, 150, 50)
    back_button = pygame.Rect(600, 400, 150, 50)
    
    draw_button("Call", call_button, BLUE)
    draw_button("Reveal", reveal_button, BLUE)
    draw_button("Back", back_button, BLUE)
    
    pygame.display.flip()
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                input_text = input_text[:-1]  # 删除最后一个字符
            elif event.key == pygame.K_RETURN:
                try:
                    call_value = int(input_text)
                    if call_value <= current_call:
                        show_message("Your call is less than current call")
                    elif call_value > 6 * number_of_players:
                        show_message("Your call is out of range")
                    else:
                        current_call = call_value  # 保存输入的数字
                except ValueError:
                    pass  # 忽略非数字输入
                input_text = ""  # 清空输入框
            elif event.unicode.isdigit():
                input_text += event.unicode  # 添加数字输入
        if event.type == pygame.MOUSEBUTTONDOWN:
            if back_button.collidepoint(event.pos):
                current_state = STATE_MAIN_MENU
            elif call_button.collidepoint(event.pos):
                try:
                    call_value = int(input_text)
                    if call_value <= current_call:
                        show_message("Your call is less than current call")
                    elif call_value > 6 * number_of_players:
                        show_message("Your call is out of range")
                    else:
                        current_call = call_value
                except ValueError:
                    pass
                input_text = ""
    return True

# server_login_success = True
# 模拟服务器认证成功 (实际应该通过网络接收服务器响应)
import time

def login_wait_screen():
    global current_state, server_login_success
    screen.fill(BLACK)
    font = get_font(50)

    waiting_text = font.render("Waiting for server...", True, WHITE)
    screen.blit(waiting_text, (SCREEN_SIZE[0] // 2 - 150, SCREEN_SIZE[1] // 2))

    pygame.display.flip()

    # 模拟服务器在2秒后返回成功信号
    time.sleep(2)  # 等待2秒
    response = client.login(login_account, login_password)
    server_login_success = response   # 这里你需要改成实际服务器返回的状态

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            return False

    # 服务器返回成功，跳转到模式选择界面
    if server_login_success:
        current_state = STATE_MOD_SCREEN
    else:
        show_message("Your password is incorrect")
        current_state = STATE_LOGIN  # 返回登录界面

    return True




# 游戏循环
running = True
while running:
    if current_state == STATE_MAIN_MENU:
        running = main_menu()
    elif current_state == STATE_REGISTER:
        running = input_screen("Register", "register_account", "register_password", STATE_MOD_SCREEN)
    elif current_state == STATE_LOGIN:
        running = input_screen("Login", "login_account", "login_password", STATE_LOGIN_WAIT)
    elif current_state == STATE_LOGIN_WAIT:
        running = login_wait_screen()        
    elif current_state == STATE_MOD_SCREEN:
        running = mod_screen()
    elif current_state == STATE_GAME:
        running = game_screen()
    elif current_state == STATE_RULES:
        running = rules_screen()

pygame.quit()