import pygame, random, platform, asyncio, heapq
from collections import deque

pygame.init()
pygame.display.set_caption('MAZOMETRIC')
screen = pygame.display.set_mode((900, 900), 0, 32)
display = pygame.Surface((300, 300))
clock = pygame.time.Clock()
font = pygame.font.SysFont('arial', 16)
title_font = pygame.font.SysFont('arial', 24, bold=True)

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

def select_mode():
    display.fill((37, 74, 92))
    
    title_surf = title_font.render("MAZOMETRIC - Select Mode", True, WHITE)
    title_rect = title_surf.get_rect(center=(150, 40))
    display.blit(title_surf, title_rect)
    
    subtitle_surf = font.render("Choose your pathfinding mode", True, (180, 180, 180))
    subtitle_rect = subtitle_surf.get_rect(center=(150, 70))
    display.blit(subtitle_surf, subtitle_rect)
    
    buttons = [
        Button(100, 90, 100, 40, "BFS", 'bfs'),
        Button(100, 140, 100, 40, "DFS", 'dfs'),
        Button(100, 190, 100, 40, "A*", 'a_star'),
        Button(100, 240, 100, 40, "Manual", 'manual'),
    ]
    
    while True:
        mouse_pos = pygame.mouse.get_pos()
        scaled_pos = (mouse_pos[0] / 3, mouse_pos[1] / 3)
        
        for button in buttons:
            button.check_hover(scaled_pos)
        
        for button in buttons:
            button.draw(display)
        
        screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
        pygame.display.update()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return None
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return 'bfs'
                if event.key == pygame.K_2:
                    return 'dfs'
                if event.key == pygame.K_3:
                    return 'a_star'
                if event.key == pygame.K_4:
                    return 'manual'
                if event.key == pygame.K_ESCAPE:
                    return None
            if event.type == pygame.MOUSEBUTTONDOWN:
                for button in buttons:
                    result = button.check_click(scaled_pos)
                    if result is not None:
                        return result

async def main():
    game_running = True
    while game_running:
        mode = select_mode()
        if not mode:
            game_running = False
            break
        
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
            
            draw_maze(display, maze, visited, path, character_pos, start, goal, mode, path_length, move_count, won)
            screen.blit(pygame.transform.scale(display, screen.get_size()), (0, 0))
            pygame.display.update()
            await asyncio.sleep(1.0 / 60)
    
    pygame.quit()

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())