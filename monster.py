import pygame
import random
import heapq
from settings import *

# Cooldown base para el movimiento del monstruo, en milisegundos.
BASE_COOLDOWN = 250 

class Monster(pygame.sprite.Sprite):
    def __init__(self, pos, groups, obstacle_sprites, blocked_tiles, map_size_tiles, initial_speed, ai_algorithm, vision_radius, sprite_name, fury_percent=20):
        super().__init__(groups)
        
        # --- Atributos Generales ---
        self.sprite_name = sprite_name
        self.id = 0
        self.frame_index = 0
        self.animation_speed = 0.15
        self.status = 'idle'
        self.spawn_pos = pygame.math.Vector2(pos)
        self.held_item = None
        self.remembered_items = set() 
        self.remembered_player_spawns = set() # Nueva memoria para spawns del jugador
        self.vision_radius = vision_radius
        self._state = 'exploring' 
        self.target_monster = None 
        self.detected_player = None 
        self.pause_end_time = 0
        self.carry_role = 'none' 
        self.fury_percent = fury_percent
        self.is_furious = False
        
        # --- Carga de Assets ---
        self.import_monster_assets()
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10)

        self.obstacle_sprites = obstacle_sprites
        self.blocked_tiles = blocked_tiles

        # --- Memoria Individual (Niebla) ---
        self.map_width_tiles, self.map_height_tiles = map_size_tiles
        self.fog_grid = [[True for _ in range(self.map_width_tiles)] for _ in range(self.map_height_tiles)]
        map_pixel_size = (self.map_width_tiles * TILESIZE, self.map_height_tiles * TILESIZE)
        self.fog_surface = pygame.Surface(map_pixel_size, pygame.SRCALPHA)
        
        cloud_sheet = pygame.image.load('../assets/tilesets/forge/TilesetFloorB.png').convert_alpha()
        self.cloud_tiles = {}
        cols = 11
        for id_tile in [0, 1, 2, 11, 12, 13, 22, 23, 24]:
            row = id_tile // cols
            col = id_tile % cols
            rect = pygame.Rect(col * 16, row * 16, 16, 16)
            surf = cloud_sheet.subsurface(rect)
            self.cloud_tiles[id_tile] = pygame.transform.scale(surf, (TILESIZE, TILESIZE))
        
        self.rebuild_fog_surface()

        # --- Sistema de Movimiento e IA ---
        self.ai_algorithm = ai_algorithm
        self.pos = pygame.math.Vector2(self.hitbox.center)
        self.path = []  
        self.target_tile_pos = None
        self.is_moving = False
        self.last_move_time = 0
        self.update_speed(initial_speed)

    @property
    def state(self): return self._state
    @state.setter
    def state(self, new_state): self._state = new_state

    def import_monster_assets(self):
        filename = 'SpriteSheet.png'
        if self.sprite_name in ['Snake', 'Snake2', 'Snake4', 'Lizard', 'Slime', 'Eye']:
            filename = f'{self.sprite_name}.png'
        
        path = f'../assets/sprites/Monsters/{self.sprite_name}/{filename}'
        sheet = pygame.image.load(path).convert_alpha()
        frames, original_size, scale_size = [], 16, TILESIZE
        cols, rows = int(sheet.get_width() / original_size), int(sheet.get_height() / original_size)
        for row in range(rows):
            for col in range(cols):
                cut_rect = pygame.Rect(col * original_size, row * original_size, original_size, original_size)
                frames.append(pygame.transform.scale(sheet.subsurface(cut_rect), (scale_size, scale_size)))
        self.animations = {
            'down': [frames[0], frames[4], frames[8], frames[12]],
            'up': [frames[1], frames[5], frames[9], frames[13]],
            'left': [frames[2], frames[6], frames[10], frames[14]],
            'right': [frames[3], frames[7], frames[11], frames[15]],
            'idle': [frames[0]]
        }

    def detect_player(self, player):
        current_tile = (int(self.hitbox.centerx // TILESIZE), int(self.hitbox.centery // TILESIZE))
        player_tile = (int(player.hitbox.centerx // TILESIZE), int(player.hitbox.centery // TILESIZE))
        if self.manhattan_distance(current_tile, player_tile) <= self.vision_radius:
            self.detected_player = player
            return True
        self.detected_player = None
        return False

    def discover_objects(self, spawn_sprites):
        """Busca spawns del jugador en el área ya explorada (fuera de la niebla)."""
        if not spawn_sprites: return
        for sp in spawn_sprites:
            if sp.spawn_type == 'player':
                tx, ty = int(sp.rect.x // TILESIZE), int(sp.rect.y // TILESIZE)
                if not self.fog_grid[ty][tx]:
                    # Si no hay niebla, el monstruo sabe si hay un item o no
                    if not sp.is_empty():
                        self.remembered_player_spawns.add((tx, ty))
                    elif (tx, ty) in self.remembered_player_spawns:
                        # Si lo ve vacío, lo olvida (temporalmente)
                        self.remembered_player_spawns.remove((tx, ty))

    def find_closest_known_player_spawn(self):
        if not self.remembered_player_spawns: return None
        current_tile = (int(self.hitbox.centerx // TILESIZE), int(self.hitbox.centery // TILESIZE))
        best_tile, min_dist = None, float('inf')
        for st in self.remembered_player_spawns:
            dist = self.manhattan_distance(current_tile, st)
            if dist < min_dist: min_dist, best_tile = dist, st
        return best_tile

    def get_new_path(self, spawn_sprites=None, level=None):
        current_tile = (int(self.hitbox.centerx // TILESIZE), int(self.hitbox.centery // TILESIZE))

        # 1. Llevar al jugador capturado
        if self.state == 'carrying' and spawn_sprites:
            best_spawn = self.find_closest_enemy_spawn(spawn_sprites, current_tile)
            if best_spawn:
                target_tile = (best_spawn.rect.x // TILESIZE, best_spawn.rect.y // TILESIZE)
                self.path = self.astar_to_target(target_tile, respect_fog=False)
                return

        # 2. Dejar objeto en base
        if self.held_item and spawn_sprites:
            self.state = 'returning_item'
            best_spawn = self.find_closest_enemy_spawn(spawn_sprites, current_tile)
            if best_spawn:
                target_tile = (best_spawn.rect.x // TILESIZE, best_spawn.rect.y // TILESIZE)
                if current_tile == target_tile: return
                self.path = self.astar_to_target(target_tile, respect_fog=False)
                if self.path: return

        # 3. Perseguir al jugador
        target_player_tile = None
        if self.detected_player:
            target_player_tile = (int(self.detected_player.hitbox.centerx // TILESIZE), int(self.detected_player.hitbox.centery // TILESIZE))
        elif level and level.player_last_seen_pos:
            target_player_tile = level.player_last_seen_pos
        
        if target_player_tile:
            self.state = 'chasing'
            if current_tile != target_player_tile:
                self.path = self.astar_to_target(target_player_tile, respect_fog=False, allow_target_solid=True)
                if self.path: return

        # 3.5 ROBAR AL JUGADOR (Nueva prioridad alta)
        if not self.held_item:
            target_spawn_tile = self.find_closest_known_player_spawn()
            if target_spawn_tile:
                if current_tile == target_spawn_tile: return
                self.path = self.astar_to_target(target_spawn_tile, respect_fog=True, allow_target_solid=True)
                if self.path:
                    self.state = 'stealing'
                    return

        # 4. IR A POR COFRES (Prioridad sobre exploración libre)
        if not self.held_item:
            chest = self.find_closest_chest()
            if chest:
                chest_tile = (chest.rect.x // TILESIZE, chest.rect.y // TILESIZE)
                target_tile = self.find_reachable_adjacent(chest_tile)
                if not target_tile: target_tile = chest_tile
                if self.manhattan_distance(current_tile, chest_tile) <= 1: return
                self.path = self.astar_to_target(target_tile, respect_fog=True, allow_target_solid=True)
                if self.path: return

        # 5. Ayudar a compañero
        if self.state == 'helping' and self.target_monster:
            if self.target_monster.state not in ['chasing', 'carrying']:
                self.state = 'exploring'
                self.target_monster = None
            else:
                target_tile = (int(self.target_monster.hitbox.centerx // TILESIZE), int(self.target_monster.hitbox.centery // TILESIZE))
                if self.manhattan_distance(current_tile, target_tile) > 1:
                    self.path = self.astar_to_target(target_tile, respect_fog=False, allow_target_solid=True)
                    if self.path: return

        # 6. Exploración y Patrulla
        self.state = 'exploring'
        monsters = level.monsters if level else []
        if self.ai_algorithm == 'territorial': self.path = self.territorial_path()
        elif self.ai_algorithm == 'repulsion': self.path = self.repulsion_path(monsters)
        elif self.ai_algorithm == 'noise': self.path = self.noise_path()
        elif self.ai_algorithm == 'boids': self.path = self.boids_path(monsters)

        if not self.path:
            self.path = self.patrol_path()

    def find_closest_enemy_spawn(self, spawn_sprites, current_tile):
        best_spawn, min_dist = None, float('inf')
        for s in spawn_sprites:
            if s.spawn_type == 'enemy' and s.is_empty():
                dist = self.manhattan_distance(current_tile, (s.rect.x // TILESIZE, s.rect.y // TILESIZE))
                if dist < min_dist: min_dist, best_spawn = dist, s
        return best_spawn

    def call_for_help(self, monsters):
        for monster in monsters:
            if monster != self and monster.state == 'exploring':
                monster.state = 'helping'
                monster.target_monster = self
                monster.path = []

    def respond_to_call(self, target_monster):
        self.state, self.target_monster, self.path = 'helping', target_monster, []

    def find_closest_stealable_item(self, spawn_sprites):
        closest_spawn, min_dist = None, float('inf')
        current_tile = (int(self.hitbox.centerx // TILESIZE), int(self.hitbox.centery // TILESIZE))
        for s in spawn_sprites:
            if s.spawn_type == 'player' and not s.is_empty():
                tx, ty = s.rect.x // TILESIZE, s.rect.y // TILESIZE
                if 0 <= tx < self.map_width_tiles and 0 <= ty < self.map_height_tiles:
                    if not self.fog_grid[ty][tx]:
                        dist = self.manhattan_distance(current_tile, (tx, ty))
                        if dist < min_dist: min_dist, closest_spawn = dist, s
        return closest_spawn

    def patrol_path(self):
        walkable_explored = [(x, y) for y in range(self.map_height_tiles) for x in range(self.map_width_tiles) if not self.fog_grid[y][x] and (x, y) not in self.blocked_tiles]
        if walkable_explored:
            return self.astar_to_target(random.choice(walkable_explored), respect_fog=True)
        return []

    def find_closest_chest(self):
        closest_chest, min_dist = None, float('inf')
        from item import Cofre
        current_tile = (int(self.hitbox.centerx // TILESIZE), int(self.hitbox.centery // TILESIZE))
        for sprite in self.obstacle_sprites:
            if isinstance(sprite, Cofre) and sprite.valor > 0:
                tx, ty = sprite.rect.x // TILESIZE, sprite.rect.y // TILESIZE
                if 0 <= tx < self.map_width_tiles and 0 <= ty < self.map_height_tiles:
                    if not self.fog_grid[ty][tx]:
                        dist = self.manhattan_distance(current_tile, (tx, ty))
                        if dist < min_dist: min_dist, closest_chest = dist, sprite
        return closest_chest

    def find_reachable_adjacent(self, tile):
        neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        random.shuffle(neighbors)
        for dx, dy in neighbors:
            adj = (tile[0] + dx, tile[1] + dy)
            if 0 <= adj[0] < self.map_width_tiles and 0 <= adj[1] < self.map_height_tiles:
                if adj not in self.blocked_tiles: return adj
        return None

    def astar_to_target(self, target_tile, respect_fog=False, allow_target_solid=False):
        start_tile = (int(self.hitbox.centerx // TILESIZE), int(self.hitbox.centery // TILESIZE))
        if start_tile == target_tile: return []
        open_set = []
        heapq.heappush(open_set, (0, self.manhattan_distance(start_tile, target_tile), [start_tile]))
        visited, max_iterations, iterations = {start_tile}, 5000, 0
        while open_set and iterations < max_iterations:
            iterations += 1
            f, h, path = heapq.heappop(open_set)
            current = path[-1]
            if current == target_tile: return path[1:]
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt not in visited and 0 <= nxt[0] < self.map_width_tiles and 0 <= nxt[1] < self.map_height_tiles:
                    if respect_fog and self.fog_grid[nxt[1]][nxt[0]] and nxt != target_tile: continue
                    if nxt not in self.blocked_tiles or (allow_target_solid and nxt == target_tile):
                        visited.add(nxt)
                        heapq.heappush(open_set, (len(path) + 1 + self.manhattan_distance(nxt, target_tile), self.manhattan_distance(nxt, target_tile), path + [nxt]))
        return []

    def territorial_path(self):
        start_tile = (self.hitbox.centerx // TILESIZE, self.hitbox.centery // TILESIZE)
        sector = self.id % 4
        mid_x, mid_y = self.map_width_tiles // 2, self.map_height_tiles // 2
        def is_in_sector(t):
            if sector == 0: return t[0] < mid_x and t[1] < mid_y
            if sector == 1: return t[0] >= mid_x and t[1] < mid_y
            if sector == 2: return t[0] < mid_x and t[1] >= mid_y
            return t[0] >= mid_x and t[1] >= mid_y
        target = self.find_closest_unexplored(start_tile, condition=is_in_sector)
        if not target: target = self.find_closest_unexplored(start_tile)
        return self.astar_to_target(target) if target else []

    def repulsion_path(self, monsters):
        start_tile = (self.hitbox.centerx // TILESIZE, self.hitbox.centery // TILESIZE)
        target = self.find_closest_unexplored(start_tile)
        if not target: return []
        open_set = []
        heapq.heappush(open_set, (0, self.manhattan_distance(start_tile, target), [start_tile]))
        visited, others = {start_tile}, [(m.hitbox.centerx // TILESIZE, m.hitbox.centery // TILESIZE) for m in monsters if m != self]
        while open_set:
            f, h, path = heapq.heappop(open_set)
            current = path[-1]
            if current == target: return path[1:]
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt not in visited and 0 <= nxt[0] < self.map_width_tiles and 0 <= nxt[1] < self.map_height_tiles and nxt not in self.blocked_tiles:
                    visited.add(nxt)
                    cost = len(path) + 1 + self.manhattan_distance(nxt, target)
                    for ox, oy in others:
                        dist = abs(nxt[0]-ox) + abs(nxt[1]-oy)
                        if dist < 3: cost += (5 - dist) * 10
                    heapq.heappush(open_set, (cost, self.manhattan_distance(nxt, target), path + [nxt]))
        return []

    def noise_path(self):
        start_tile = (self.hitbox.centerx // TILESIZE, self.hitbox.centery // TILESIZE)
        candidates, queue, visited = [], [(start_tile, 0)], {start_tile}
        while queue and len(candidates) < 5:
            curr, dist = queue.pop(0)
            if self.fog_grid[curr[1]][curr[0]]: candidates.append(curr)
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nxt = (curr[0]+dx, curr[1]+dy)
                if nxt not in visited and 0 <= nxt[0] < self.map_width_tiles and 0 <= nxt[1] < self.map_height_tiles and nxt not in self.blocked_tiles:
                    visited.add(nxt)
                    queue.append((nxt, dist+1))
        return self.astar_to_target(random.choice(candidates)) if candidates else []

    def boids_path(self, monsters):
        start_tile = (self.hitbox.centerx // TILESIZE, self.hitbox.centery // TILESIZE)
        target = self.find_closest_unexplored(start_tile)
        if not target: return []
        sep_vec = pygame.math.Vector2(0, 0)
        for other in monsters:
            if other != self:
                other_t = (other.hitbox.centerx // TILESIZE, other.hitbox.centery // TILESIZE)
                dist = self.manhattan_distance(start_tile, other_t)
                if 0 < dist < 4:
                    diff = pygame.math.Vector2(start_tile) - pygame.math.Vector2(other_t)
                    if diff.length() > 0: sep_vec += diff.normalize() / dist
        best_nxt, min_score = None, float('inf')
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nxt = (start_tile[0]+dx, start_tile[1]+dy)
            if 0 <= nxt[0] < self.map_width_tiles and 0 <= nxt[1] < self.map_height_tiles and nxt not in self.blocked_tiles:
                score = self.manhattan_distance(nxt, target) - pygame.math.Vector2(dx, dy).dot(sep_vec) * 2
                if score < min_score: min_score, best_nxt = score, nxt
        return [best_nxt] if best_nxt else []

    def manhattan_distance(self, start, end): return abs(start[0] - end[0]) + abs(start[1] - end[1])

    def find_closest_unexplored(self, start_tile, condition=None):
        if self.fog_grid[start_tile[1]][start_tile[0]] and (not condition or condition(start_tile)): return start_tile
        queue, visited = [start_tile], {start_tile}
        while queue:
            current = queue.pop(0)
            neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
            random.shuffle(neighbors)
            for dx, dy in neighbors:
                nxt = (current[0] + dx, current[1] + dy)
                if nxt not in visited and 0 <= nxt[0] < self.map_width_tiles and 0 <= nxt[1] < self.map_height_tiles and nxt not in self.blocked_tiles:
                    if self.fog_grid[nxt[1]][nxt[0]] and (not condition or condition(nxt)): return nxt
                    visited.add(nxt)
                    queue.append(nxt)
        return None

    def update_fog_tile(self, x, y):
        if not (0 <= x < self.map_width_tiles and 0 <= y < self.map_height_tiles): return
        rect = pygame.Rect(x * TILESIZE, y * TILESIZE, TILESIZE, TILESIZE)
        self.fog_surface.fill((0, 0, 0, 0), rect)
        if not self.fog_grid[y][x]: return
        t, b, l, r = (self.fog_grid[y-1][x] if y > 0 else True), (self.fog_grid[y+1][x] if y < self.map_height_tiles - 1 else True), (self.fog_grid[y][x-1] if x > 0 else True), (self.fog_grid[y][x+1] if x < self.map_width_tiles - 1 else True)
        tile_id = 12
        if not t and not l: tile_id = 0
        elif not t and not r: tile_id = 2
        elif not b and not l: tile_id = 22
        elif not b and not r: tile_id = 24
        elif not t: tile_id = 1
        elif not b: tile_id = 23
        elif not l: tile_id = 11
        elif not r: tile_id = 13
        self.fog_surface.blit(self.cloud_tiles[tile_id], (x * TILESIZE, y * TILESIZE))

    def reveal_my_tiles(self):
        tx, ty = self.hitbox.centerx // TILESIZE, self.hitbox.centery // TILESIZE
        changed, rad = set(), self.vision_radius
        for yo in range(-rad, rad + 1):
            for xo in range(-rad, rad + 1):
                if xo**2 + yo**2 <= (rad + 0.5)**2:
                    rx, ry = tx + xo, ty + yo
                    if 0 <= rx < self.map_width_tiles and 0 <= ry < self.map_height_tiles and self.fog_grid[ry][rx]:
                        self.fog_grid[ry][rx] = False
                        for dx in range(-1, 2):
                            for dy in range(-1, 2):
                                nx, ny = rx + dx, ry + dy
                                if 0 <= nx < self.map_width_tiles and 0 <= ny < self.map_height_tiles: changed.add((nx, ny))
        for x, y in changed: self.update_fog_tile(x, y)

    def update_vision_radius(self, nr): self.vision_radius = nr

    def share_memory(self, others):
        for o in others:
            if o == self: continue
            for y in range(self.map_height_tiles):
                for x in range(self.map_width_tiles):
                    if not o.fog_grid[y][x]: self.fog_grid[y][x] = False
            # Compartir ubicaciones de items y spawns del jugador
            self.remembered_items.update(o.remembered_items)
            self.remembered_player_spawns.update(o.remembered_player_spawns)

    def rebuild_fog_surface(self):
        for y in range(self.map_height_tiles):
            for x in range(self.map_width_tiles): self.update_fog_tile(x, y)

    def animate(self):
        anim = self.animations.get(self.status, self.animations['idle'])
        self.frame_index = (self.frame_index + self.animation_speed) % len(anim)
        self.image = anim[int(self.frame_index)]
        self.rect = self.image.get_rect(center=self.hitbox.center)

    def move(self):
        if not self.is_moving: return
        dir_vec = self.target_tile_pos - self.pos
        if dir_vec.magnitude() > self.speed: self.pos += dir_vec.normalize() * self.speed
        else: self.pos, self.is_moving = self.target_tile_pos, False
        self.hitbox.center = self.pos
        self.rect.center = self.hitbox.center

    def update(self, player=None, monsters=None, spawn_sprites=None, level=None):
        current_time = pygame.time.get_ticks()
        if current_time < self.pause_end_time:
            self.status, self.is_moving = 'idle', False
            self.animate()
            return

        if spawn_sprites:
            self.discover_objects(spawn_sprites)

        if player:
            if player.is_being_carried and self.hitbox.colliderect(player.hitbox): self.state = 'carrying'
            if player.just_recovered:
                if self.state in ['chasing', 'helping', 'carrying']:
                    self.pause_end_time, self.state, self.path = current_time + 3000, 'exploring', []
                    player.is_being_carried = False
            if self.detect_player(player):
                if not self.is_furious:
                    self.is_furious = True
                    self.update_speed(self.base_speed)
                if self.state != 'carrying':
                    self.state = 'chasing'
                    if level: level.player_last_seen_pos = (int(player.hitbox.centerx // TILESIZE), int(player.hitbox.centery // TILESIZE))
                    self.call_for_help(monsters)
            elif self.state == 'chasing':
                if self.is_furious:
                    self.is_furious = False
                    self.update_speed(self.base_speed)
                self.state = 'exploring'
        
        if self.state == 'chasing' and player and self.hitbox.colliderect(player.hitbox):
            if not player.is_stunned and player.get_stunned():
                if level:
                    level.player_last_stun_pos = (int(player.hitbox.centerx // TILESIZE), int(player.hitbox.centery // TILESIZE))
                    level.play_stun_sound()
                    level.start_shake(12, 500)
                for m in monsters:
                    if m != self: m.share_memory([self])
            
            helpers = [m for m in monsters if m.manhattan_distance((m.hitbox.centerx // TILESIZE, m.hitbox.centery // TILESIZE), (player.hitbox.centerx // TILESIZE, player.hitbox.centery // TILESIZE)) <= 1]
            if len(helpers) >= 2:
                if not player.is_being_carried: player.is_being_carried = True
                for i, m in enumerate(helpers):
                    m.state = 'carrying'
                    if i == 0: m.carry_role = 'left'
                    elif i == 1: m.carry_role = 'right'
                    elif i == 2: m.carry_role = 'top'
                    elif i == 3: m.carry_role = 'bottom'
                    else: m.carry_role = 'none'

        if not self.is_moving and current_time - self.last_move_time >= self.move_cooldown:
            if self.state in ['chasing', 'helping', 'carrying'] or not self.path: self.get_new_path(spawn_sprites, level)
            if not self.path: self.status = 'idle'
            else:
                if self.path[0] in self.blocked_tiles and self.state not in ['chasing', 'helping', 'carrying']:
                    self.path = []
                    return
                nt = self.path.pop(0)
                self.target_tile_pos = pygame.math.Vector2(nt[0]*TILESIZE + TILESIZE/2, nt[1]*TILESIZE + TILESIZE/2)
                self.is_moving, self.last_move_time = True, current_time
        
        if self.is_moving and self.target_tile_pos:
            dv = self.target_tile_pos - self.pos
            if abs(dv.x) > abs(dv.y): self.status = 'right' if dv.x > 0 else 'left'
            else: self.status = 'down' if dv.y > 0 else 'up'
        else: self.status = 'idle'

        self.move()
        self.reveal_my_tiles()
        self.animate()

        if self.state == 'carrying' and player:
            if not player.is_being_carried:
                self.state, self.path, self.carry_role = 'exploring', [], 'none'
                return
            if self.carry_role == 'left': player.hitbox.center = player.rect.center = self.hitbox.center
            off = 18
            if self.carry_role == 'left': self.rect.centerx = player.rect.centerx - off
            elif self.carry_role == 'right': self.rect.centerx = player.rect.centerx + off
            elif self.carry_role == 'top': self.rect.centery = player.rect.centery - off
            elif self.carry_role == 'bottom': self.rect.centery = player.rect.centery + off
            elif self.carry_role == 'none': self.rect.centery = player.rect.centery + 25 
            if self.carry_role != 'left': self.hitbox.center = self.pos = pygame.math.Vector2(player.hitbox.center)

    def pickup_item(self, item): self.held_item = item
    def drop_item(self): self.held_item = None
    def update_speed(self, ns):
        self.base_speed = ns
        mul = (1 + self.fury_percent / 100.0) if self.is_furious else 1.0
        self.speed = self.base_speed * mul
        self.move_cooldown = (BASE_COOLDOWN / self.speed) if self.speed > 0 else float('inf')
    def update_fury(self, nf): self.fury_percent = nf; self.update_speed(self.base_speed)
    def set_ai_algorithm(self, na): self.ai_algorithm, self.path = na, []
