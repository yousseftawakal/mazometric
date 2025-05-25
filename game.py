import pygame, random, platform, asyncio, heapq
from collections import deque
import cv2
import numpy as np
import os

pygame.init()
pygame.display.set_caption('MAZOMETRIC')
screen = pygame.display.set_mode((900, 900), 0, 32)
display = pygame.Surface((300, 300))
clock = pygame.time.Clock()
font = pygame.font.SysFont('arial', 16)
title_font = pygame.font.SysFont('arial', 24, bold=True)

# Load and prepare video background
video = None
if os.path.exists('background.mp4'):
    video = cv2.VideoCapture('background.mp4')
    if video.isOpened():
        video_width = int(video.get(cv2.CAP_PROP_FRAME_WIDTH))
        video_height = int(video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        video_fps = video.get(cv2.CAP_PROP_FPS)
    else:
        video = None

grass = pygame.image.load('grass.png').convert()
grass.set_colorkey((0, 0, 0))
brick = pygame.image.load('brick.png').convert()
brick.set_colorkey((0, 0, 0))
ball = pygame.image.load('ball.png').convert()
ball.set_colorkey((0, 0, 0))

GRAY = (150, 150, 150)
LIGHT = (255, 255, 200)
GREEN = (100, 255, 100)
HOVER_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
WHITE = (255, 255, 255)
SHADOW = (30, 30, 30)

ROWS, COLS = 15, 14
TILE_WIDTH = 20
TILE_HEIGHT = 10
DIRECTIONS = [(0, -1), (0, 1), (-1, 0), (1, 0)]

class Button:
    def __init__(self, x, y, width, height, text, mode):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.mode = mode
        self.hovered = False
    
    def draw(self, surface):
        shadow_rect = self.rect.copy()
        shadow_rect.x += 3
        shadow_rect.y += 3
        pygame.draw.rect(surface, SHADOW, shadow_rect, border_radius=10)
        
        color = HOVER_GRAY if self.hovered else GRAY
        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        
        pygame.draw.rect(surface, DARK_GRAY, self.rect, 2, border_radius=10)
        
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def check_hover(self, mouse_pos):
        self.hovered = self.rect.collidepoint(mouse_pos)
    
    def check_click(self, mouse_pos):
        return self.mode if self.rect.collidepoint(mouse_pos) else None

def get_next_frame():
    if video is None:
        # Return a black surface if no video is available
        return pygame.Surface((300, 300))
    
    ret, frame = video.read()
    if not ret:
        video.set(cv2.CAP_PROP_POS_FRAMES, 0)  # Reset video to start
        ret, frame = video.read()
    frame = cv2.resize(frame, (300, 300))  # Resize to match display size
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)  # Convert BGR to RGB
    return pygame.surfarray.make_surface(frame.swapaxes(0, 1))

def generate_maze(rows, cols):
    maze = [[1] * cols for _ in range(rows)]
    stack = [(0, 0)]
    visited = set(stack)
    
    while stack:
        x, y = stack[-1]
        neighbors = [(x + dx, y + dy) for dx, dy in DIRECTIONS
                     if 0 <= x + dx < cols and 0 <= y + dy < rows]
        neighbors = [(nx, ny) for nx, ny in neighbors if (nx, ny) not in visited]
        
        if neighbors:
            nx, ny = random.choice(neighbors)
            maze[y][x] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))
            visited.add((nx, ny))
        else:
            stack.pop()
    
    for _ in range((rows * cols) // 4):
        while True:
            ox, oy = random.randint(0, cols - 1), random.randint(0, rows - 1)
            if (ox, oy) not in [(0, 0), (cols - 1, rows - 1)] and \
               (ox, oy) not in [(0, 1), (1, 0), (cols - 2, rows - 1), (cols - 1, rows - 2)]:
                maze[oy][ox] = 1
                break
    
    return maze

def tint_surface(surface, color):
    tinted = surface.copy()
    tinted.fill(color, special_flags=pygame.BLEND_MULT)
    return tinted

def bfs_step(maze, queue, visited, goal):
    if not queue:
        return None, visited, queue
    
    (x, y), path = queue.popleft()
    
    if (x, y) == goal:
        return path, visited, queue
    
    for dx, dy in DIRECTIONS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS and maze[ny][nx] == 0 and (nx, ny) not in visited:
            visited.add((nx, ny))
            queue.append(((nx, ny), path + [(nx, ny)]))
    
    return False, visited, queue

def dfs_step(maze, stack, visited, goal):
    if not stack:
        return None, visited, stack
    
    (x, y), path = stack.pop()
    
    if (x, y) == goal:
        return path, visited, stack
    
    for dx, dy in DIRECTIONS:
        nx, ny = x + dx, y + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS and maze[ny][nx] == 0 and (nx, ny) not in visited:
            visited.add((nx, ny))
            stack.append(((nx, ny), path + [(nx, ny)]))
    
    return False, visited, stack

def heuristic(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def a_star_step(maze, open_set, came_from, g_score, f_score, goal, visited):
    if not open_set:
        return None, came_from, open_set, visited
    
    _, current = heapq.heappop(open_set)
    visited.add(current)
    
    if current == goal:
        path = []
        temp = current
        while temp in came_from:
            path.append(temp)
            temp = came_from[temp]
        path.append(goal)
        return path[::-1], came_from, open_set, visited
    
    for dx, dy in DIRECTIONS:
        neighbor = (current[0] + dx, current[1] + dy)
        if 0 <= neighbor[0] < COLS and 0 <= neighbor[1] < ROWS and maze[neighbor[1]][neighbor[0]] == 0:
            tentative_g_score = g_score[current] + 1
            
            if neighbor not in g_score or tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g_score
                f_score[neighbor] = g_score[neighbor] + heuristic(neighbor, goal)
                heapq.heappush(open_set, (f_score[neighbor], neighbor))
    
    return False, came_from, open_set, visited

def draw_maze(display, maze, visited, path, character_pos, start, goal, mode, path_length, move_count, won):
    display.fill((0, 0, 0))
    for y, row in enumerate(maze):
        for x, tile in enumerate(row):
            pos_x = 150 + TILE_WIDTH // 2 * (x - y)
            pos_y = 100 + TILE_HEIGHT // 2 * (x + y)

            display.blit(grass, (pos_x, pos_y))

            if (x, y) == goal:
                display.blit(tint_surface(grass, GREEN), (pos_x, pos_y))
            elif ((x, y) in visited) and ((x, y) != goal):
                display.blit(tint_surface(grass, GRAY), (pos_x, pos_y))
            elif maze[y][x] == 1:
                display.blit(brick, (pos_x, pos_y - 14))

            if (path and (x, y) in path) and ((x, y) != goal):
                display.blit(tint_surface(grass, LIGHT), (pos_x, pos_y))

            if (x, y) == character_pos:
                display.blit(ball, (pos_x, pos_y - 14))
    
    mode_text = f"Mode: {'BFS' if mode == 'bfs' else 'DFS' if mode == 'dfs' else 'A*' if mode == 'a_star' else 'Manual'}"
    display.blit(font.render(mode_text, True, (255, 255, 255)), (10, 10))
    if mode == 'manual':
        move_text = f"Moves: {move_count}"
        display.blit(font.render(move_text, True, (255, 255, 255)), (10, 30))
    elif path_length is not None:
        length_text = f"Path Length: {path_length}"
        display.blit(font.render(length_text, True, (255, 255, 255)), (10, 30))
    display.blit(font.render("Press Enter to Restart", True, (255, 255, 255)), (10, 270))
    if won:
        display.blit(font.render("You Won!", True, (255, 255, 255)), (120, 70))

def cleanup_video():
    global video
    if video is not None:
        video.release()
        video = None

def select_mode():
    display.fill((20, 20, 20))  # Dark background
    
    # Get and display video frame
    frame = get_next_frame()
    display.blit(frame, (0, 0))
    
    # Add semi-transparent overlay
    overlay = pygame.Surface((300, 300), pygame.SRCALPHA)
    overlay.fill((20, 20, 20, 128))  # Semi-transparent dark overlay
    display.blit(overlay, (0, 0))
    
    # Draw background grid effect first
    for i in range(0, 300, 20):
        pygame.draw.line(display, (30, 30, 30), (i, 0), (i, 300))
        pygame.draw.line(display, (30, 30, 30), (0, i), (300, i))
    
    # Title with neon effect
    title_surf = title_font.render("MAZOMETRIC", True, (255, 255, 255))
    title_shadow = title_font.render("MAZOMETRIC", True, (0, 195, 255))
    title_rect = title_surf.get_rect(center=(150, 30))
    display.blit(title_shadow, (title_rect.x + 2, title_rect.y + 2))
    display.blit(title_surf, title_rect)
    
    # Subtitle with modern styling
    subtitle_surf = font.render("Select Mode", True, (200, 200, 200))
    subtitle_rect = subtitle_surf.get_rect(center=(150, 55))
    display.blit(subtitle_surf, subtitle_rect)
    
    # Modern button layout
    buttons = [
        Button(75, 80, 150, 40, "BFS", 'bfs'),
        Button(75, 130, 150, 40, "DFS", 'dfs'),
        Button(75, 180, 150, 40, "A*", 'a_star'),
        Button(75, 230, 150, 40, "Manual", 'manual'),
    ]
    
    while True:
        mouse_pos = pygame.mouse.get_pos()
        scaled_pos = (mouse_pos[0] / 3, mouse_pos[1] / 3)
        
        # Update video frame
        frame = get_next_frame()
        display.blit(frame, (0, 0))
        display.blit(overlay, (0, 0))
        
        # Redraw grid
        for i in range(0, 300, 20):
            pygame.draw.line(display, (30, 30, 30), (i, 0), (i, 300))
            pygame.draw.line(display, (30, 30, 30), (0, i), (300, i))
        
        # Redraw UI elements
        display.blit(title_shadow, (title_rect.x + 2, title_rect.y + 2))
        display.blit(title_surf, title_rect)
        display.blit(subtitle_surf, subtitle_rect)
        
        for button in buttons:
            button.check_hover(scaled_pos)
            button.draw(display)
        
        screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
        pygame.display.update()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cleanup_video()
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    cleanup_video()
                    return 'bfs'
                if event.key == pygame.K_2:
                    cleanup_video()
                    return 'dfs'
                if event.key == pygame.K_3:
                    cleanup_video()
                    return 'a_star'
                if event.key == pygame.K_4:
                    cleanup_video()
                    return 'manual'
                if event.key == pygame.K_ESCAPE:
                    cleanup_video()
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons:
                    result = button.check_click(scaled_pos)
                    if result is not None:
                        cleanup_video()
                        return result

async def main():
    game_running = True
    while game_running:
        mode = select_mode()
        if not mode:
            game_running = False
            break
        
        # Reinitialize video for the new game
        global video
        if os.path.exists('background.mp4'):
            video = cv2.VideoCapture('background.mp4')
            if not video.isOpened():
                video = None
        
        maze = generate_maze(ROWS, COLS)
        start = (0, 0)
        goal = (COLS - 1, ROWS - 1)
        character_pos = start
        queue = deque([(start, [start])]) if mode == 'bfs' else None
        stack = [(start, [start])] if mode == 'dfs' else None
        open_set = [(0, start)] if mode == 'a_star' else None
        came_from = {start: None} if mode == 'a_star' else None
        g_score = {start: 0} if mode == 'a_star' else None
        f_score = {start: heuristic(start, goal)} if mode == 'a_star' else None
        visited = set([start]) if mode in ['bfs', 'dfs', 'a_star'] else set()
        path = None
        path_index = 0
        path_length = None
        move_count = 0
        step_delay = 30
        move_delay = 80
        last_step_time = pygame.time.get_ticks()
        last_move_time = pygame.time.get_ticks()
        won = False
        searching = True
        
        running = True
        while running:
            current_time = pygame.time.get_ticks()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    game_running = False
                    running = False
                    break
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        game_running = False
                        running = False
                        break
                    if event.key == pygame.K_RETURN:
                        running = False
                    if mode == 'manual' and not won:
                        new_x, new_y = character_pos
                        if event.key == pygame.K_UP:
                            new_y -= 1
                        elif event.key == pygame.K_DOWN:
                            new_y += 1
                        elif event.key == pygame.K_LEFT:
                            new_x -= 1
                        elif event.key == pygame.K_RIGHT:
                            new_x += 1
                        if (0 <= new_x < COLS and 0 <= new_y < ROWS and maze[new_y][new_x] == 0):
                            character_pos = (new_x, new_y)
                            move_count += 1
                            visited.add(character_pos)
            
            if not won and searching:
                if mode == 'bfs' and not path and queue and (current_time - last_step_time >= step_delay):
                    result, visited, queue = bfs_step(maze, queue, visited, goal)
                    if result:
                        path = result
                        path_length = len(path)
                        searching = False
                    last_step_time = current_time
                
                if mode == 'dfs' and not path and stack and (current_time - last_step_time >= step_delay):
                    result, visited, stack = dfs_step(maze, stack, visited, goal)
                    if result:
                        path = result
                        path_length = len(path)
                        searching = False
                    last_step_time = current_time
                
                if mode == 'a_star' and not path and open_set and (current_time - last_step_time >= step_delay):
                    result, came_from, open_set, visited = a_star_step(maze, open_set, came_from, g_score, f_score, goal, visited)
                    if result:
                        path = result
                        path_length = len(path)
                        searching = False
                    last_step_time = current_time
            
            if not searching and path and path_index < len(path) and (current_time - last_move_time >= move_delay):
                character_pos = path[path_index]
                path_index += 1
                visited.add(character_pos)
                last_move_time = current_time
            
            if character_pos == goal:
                won = True
            
            # Get and display video frame
            frame = get_next_frame()
            display.blit(frame, (0, 0))
            
            # Add semi-transparent overlay
            overlay = pygame.Surface((300, 300), pygame.SRCALPHA)
            overlay.fill((20, 20, 20, 128))  # Semi-transparent dark overlay
            display.blit(overlay, (0, 0))
            
            draw_maze(display, maze, visited, path, character_pos, start, goal, mode, path_length, move_count, won)
            screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
            pygame.display.update()
            await asyncio.sleep(1.0 / 60)
    
    cleanup_video()
    pygame.quit()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())