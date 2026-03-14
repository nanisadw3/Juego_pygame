import pygame
import random
import os
from settings import *
from tile import Tile
from support import *
from player import Player
from monster import Monster
from item import Cofre, ItemIcon, DroppedItem
from spawn import Spawn

class Level:
    def __init__(self):
        self.display_surface = pygame.display.get_surface()
        self.perspective = 'Jugador'

        self.visible_sprites = YSortCameraGroup()
        self.obstacle_sprites = pygame.sprite.Group()
        self.spawn_sprites = pygame.sprite.Group()
        self.monsters = pygame.sprite.Group()

        self.blocked_tiles = set()
        self.item_tiles = set()
        self.resource_images = import_folder('../assets/Items/Resource')

        self.sfx_jingle = pygame.mixer.Sound('../assets/sounds/Jingles/Secret2.wav')
        self.sfx_stun = pygame.mixer.Sound('../assets/sounds/Jingles/GameOver4.wav')
        self.jingle_playing = False
        self.jingle_end_time = 0

        self.initial_monster_speed = MONSTER_SPEED
        self.current_monster_ai = MONSTER_AI
        self.current_monster_vision = MONSTER_VISION
        self.current_monster_fury = MONSTER_FURY
        self.player_last_seen_pos = None 
        self.player_last_stun_pos = None 

        self.create_map()

        self.map_width_tiles = self.visible_sprites.floor_surf.get_width() // TILESIZE
        self.map_height_tiles = self.visible_sprites.floor_surf.get_height() // TILESIZE
        self.player_fog_grid = [[True for _ in range(self.map_width_tiles)] for _ in range(self.map_height_tiles)]
        self.player_fog = pygame.Surface(self.visible_sprites.floor_surf.get_size(), pygame.SRCALPHA)
        
        cloud_sheet = pygame.image.load('../assets/tilesets/forge/TilesetFloorB.png').convert_alpha()
        self.cloud_tiles = {}
        cols = 11
        for id_tile in [0, 1, 2, 11, 12, 13, 22, 23, 24]:
            rect = pygame.Rect((id_tile % cols) * 16, (id_tile // cols) * 16, 16, 16)
            self.cloud_tiles[id_tile] = pygame.transform.scale(cloud_sheet.subsurface(rect), (TILESIZE, TILESIZE))
        
        self.rebuild_player_fog()

    def start_shake(self, amount=10, duration=500):
        self.visible_sprites.shake_amount = amount
        self.visible_sprites.shake_end_time = pygame.time.get_ticks() + duration

    def rebuild_player_fog(self):
        self.player_fog.fill((0, 0, 0, 0))
        for y in range(self.map_height_tiles):
            for x in range(self.map_width_tiles):
                if self.player_fog_grid[y][x]:
                    self.player_fog.blit(self.cloud_tiles[12], (x * TILESIZE, y * TILESIZE))

    def update_fog_tile(self, x, y):
        if not (0 <= x < self.map_width_tiles and 0 <= y < self.map_height_tiles): return
        rect = pygame.Rect(x * TILESIZE, y * TILESIZE, TILESIZE, TILESIZE)
        self.player_fog.fill((0, 0, 0, 0), rect)
        if self.player_fog_grid[y][x]:
            t, b, l, r = (self.player_fog_grid[y-1][x] if y > 0 else True), (self.player_fog_grid[y+1][x] if y < self.map_height_tiles - 1 else True), (self.player_fog_grid[y][x-1] if x > 0 else True), (self.player_fog_grid[y][x+1] if x < self.map_width_tiles - 1 else True)
            tid = 12
            if not t and not l: tid = 0
            elif not t and not r: tid = 2
            elif not b and not l: tid = 22
            elif not b and not r: tid = 24
            elif not t: tid = 1
            elif not b: tid = 23
            elif not l: tid = 11
            elif not r: tid = 13
            self.player_fog.blit(self.cloud_tiles[tid], (x * TILESIZE, y * TILESIZE))

    def reveal_player_tiles(self):
        tx, ty = self.player.rect.centerx // TILESIZE, self.player.rect.centery // TILESIZE
        changed, rad = set(), 4
        for yo in range(-rad, rad + 1):
            for xo in range(-rad, rad + 1):
                if xo**2 + yo**2 <= (rad + 0.5)**2:
                    rx, ry = tx + xo, ty + yo
                    if 0 <= rx < self.map_width_tiles and 0 <= ry < self.map_height_tiles and self.player_fog_grid[ry][rx]:
                        self.player_fog_grid[ry][rx] = False
                        for dx in range(-1, 2):
                            for dy in range(-1, 2):
                                nx, ny = rx + dx, ry + dy
                                if 0 <= nx < self.map_width_tiles and 0 <= ny < self.map_height_tiles: changed.add((nx, ny))
        for x, y in changed: self.update_fog_tile(x, y)

    def update_fog(self):
        if self.perspective == 'Jugador': self.reveal_player_tiles()

    def create_map(self):
        layouts = {
            'boundary': import_csv_layout("../map/Game_Muros.csv"),
            'pasto_suelo': import_csv_layout("../map/Piso_Pasto.csv"),
            'recursos': import_csv_layout('../map/ps_Rec.csv'),
            'entidades': import_csv_layout('../map/Game_Entidades.csv'),
            'puntos': import_csv_layout('../map/Game_Puntos.csv')
        }
        graphics = {'pasto_suelo': import_cut_graphics('../assets/tilesets/Tilesets/TilesetNature.png')}

        for style, layout in layouts.items():
            if style in ['pasto_suelo', 'boundary']:
                for ri, row in enumerate(layout):
                    for ci, col in enumerate(row):
                        if col != '-1':
                            x, y = ci * TILESIZE, ri * TILESIZE
                            if style == 'boundary': Tile((x, y), [self.obstacle_sprites], 'muros')
                            else: Tile((x, y), [self.visible_sprites, self.obstacle_sprites], 'decoracion', graphics['pasto_suelo'][int(col)])
        
        msize = (self.visible_sprites.floor_surf.get_width() // TILESIZE, self.visible_sprites.floor_surf.get_height() // TILESIZE)
        chests_pos = []
        for style, layout in layouts.items():
            if style not in ['pasto_suelo', 'boundary']:
                for ri, row in enumerate(layout):
                    for ci, col in enumerate(row):
                        if col != '-1':
                            x, y = ci * TILESIZE, ri * TILESIZE
                            if style == 'recursos': chests_pos.append((x, y))
                            elif style == 'puntos':
                                if col == '7': Spawn((x,y), [self.spawn_sprites], 'player')
                                elif col == '6': Spawn((x,y), [self.spawn_sprites], 'enemy')

        total = random.randint(11, 15)
        n_chests = min(15, len(chests_pos))
        sel_chests = random.sample(chests_pos, n_chests)
        c_items = [0] * n_chests
        for _ in range(total):
            val_idx = [i for i, c in enumerate(c_items) if c < 3]
            if val_idx: c_items[random.choice(val_idx)] += 1

        for i, pos in enumerate(sel_chests):
            Cofre(pos, [self.visible_sprites, self.obstacle_sprites], self.obstacle_sprites, c_items[i])

        for s in self.obstacle_sprites:
            if not isinstance(s, (Player, Monster)): self.blocked_tiles.add((s.rect.x // TILESIZE, s.rect.y // TILESIZE))

        m_pool = ['AxolotBlue', 'Bamboo', 'Cyclope', 'Eye', 'Flam', 'Flam2', 'Lizard', 'Octopus2', 'Slime', 'Snake', 'Snake2', 'Snake4', 'Spirit', 'Spirit2']
        player_done = False
        for ri, row in enumerate(layouts['entidades']):
            for ci, col in enumerate(row):
                if col != '-1':
                    x, y = ci * TILESIZE, ri * TILESIZE
                    if not player_done and col == '0':
                        self.player = Player((x,y), [self.visible_sprites], self.obstacle_sprites)
                        player_done = True
                    elif col != '-1':
                        m = Monster((x,y), [self.visible_sprites], self.obstacle_sprites, self.blocked_tiles, msize, self.initial_monster_speed, self.current_monster_ai, self.current_monster_vision, random.choice(m_pool), self.current_monster_fury)
                        m.id = len(self.monsters) + 1
                        self.monsters.add(m)

    def run(self, surface, perspective):
        self.perspective = perspective
        self.player_last_seen_pos = None
        self.player.update()
        for s in self.visible_sprites:
            if isinstance(s, Monster): s.update(self.player, self.monsters, self.spawn_sprites, self)
            elif s != self.player: s.update()
        self.player.just_recovered = False
        self.update_fog()
        
        afog = None
        if self.perspective == 'Jugador': afog = self.player_fog
        elif self.perspective == 'Monstruos':
            afog = pygame.Surface(self.get_map_size(), pygame.SRCALPHA)
            afog.fill(FOG_COLOR)
            for m in self.monsters: afog.blit(m.fog_surface, (0,0), special_flags=pygame.BLEND_RGBA_MIN)

        self.visible_sprites.custom_draw(self.player, surface, afog, self.perspective)
        self.check_jingle()
        self.check_interaction()
        self.check_monster_interaction()

    def check_jingle(self):
        if self.jingle_playing and pygame.time.get_ticks() >= self.jingle_end_time:
            pygame.mixer.music.unpause()
            self.jingle_playing = False

    def play_stun_sound(self):
        if not self.jingle_playing:
            pygame.mixer.music.pause()
            self.sfx_stun.play()
            self.jingle_playing, self.jingle_end_time = True, pygame.time.get_ticks() + int(self.sfx_stun.get_length() * 1000)
    
    def get_map_size(self): return self.visible_sprites.floor_surf.get_size()

    def check_interaction(self):
        if self.player.interacting: return
        if not pygame.key.get_pressed()[pygame.K_SPACE]: return
        self.player.start_interaction()
        if self.player.is_holding_item():
            for sp in [s for s in self.spawn_sprites if s.spawn_type == 'player']:
                if sp.hitbox.colliderect(self.player.hitbox) and sp.is_empty():
                    DroppedItem(sp.rect.topleft, self.player.held_item, [self.visible_sprites], self.obstacle_sprites)
                    sp.place_item(self.player.held_item)
                    tp = (sp.rect.x // TILESIZE, sp.rect.y // TILESIZE)
                    self.blocked_tiles.add(tp); self.item_tiles.add(tp)
                    self.player.drop_item()
                    return
        iarea = self.player.hitbox.inflate(20, 20)
        if not self.player.is_holding_item():
            for sp in self.spawn_sprites:
                if sp.spawn_type == 'enemy' and not sp.is_empty() and iarea.colliderect(sp.hitbox):
                    img = sp.item; self.player.pickup_item(img)
                    ItemIcon(self.player.rect.midtop, img, [self.visible_sprites])
                    sp.item, tp = None, (sp.rect.x // TILESIZE, sp.rect.y // TILESIZE)
                    if tp in self.blocked_tiles: self.blocked_tiles.remove(tp)
                    if tp in self.item_tiles: self.item_tiles.remove(tp)
                    for s in self.visible_sprites:
                        if isinstance(s, DroppedItem) and s.rect.topleft == sp.rect.topleft: s.kill(); break
                    return
        for s in self.obstacle_sprites:
            if isinstance(s, Cofre) and iarea.colliderect(s.hitbox):
                if not self.player.is_holding_item() and s.interactuar():
                    if not self.jingle_playing:
                        pygame.mixer.music.pause(); self.sfx_jingle.play()
                        self.jingle_playing, self.jingle_end_time = True, pygame.time.get_ticks() + (self.sfx_jingle.get_length() * 1000)
                    img = random.choice(self.resource_images); self.player.pickup_item(img)
                    ItemIcon(self.player.rect.midtop, img, [self.visible_sprites])
                    return

    def check_monster_interaction(self):
        for m in self.monsters:
            if not m.is_moving and not m.path:
                mt = (int(m.hitbox.centerx // TILESIZE), int(m.hitbox.centery // TILESIZE))
                if m.held_item:
                    for sp in self.spawn_sprites:
                        if sp.spawn_type == 'enemy' and sp.is_empty() and mt == (sp.rect.x // TILESIZE, sp.rect.y // TILESIZE):
                            DroppedItem(sp.rect.topleft, m.held_item, [self.visible_sprites], self.obstacle_sprites)
                            sp.place_item(m.held_item)
                            self.blocked_tiles.add(mt); self.item_tiles.add(mt); m.remembered_items.add(mt)
                            m.drop_item(); m.get_new_path(self.spawn_sprites); break
                else:
                    stolen = False
                    for sp in self.spawn_sprites:
                        if sp.spawn_type == 'player' and not sp.is_empty() and m.manhattan_distance(mt, (sp.rect.x // TILESIZE, sp.rect.y // TILESIZE)) <= 1:
                            m.pickup_item(sp.item); ItemIcon(m.rect.midtop, sp.item, [self.visible_sprites])
                            sp.item, tp = None, (sp.rect.x // TILESIZE, sp.rect.y // TILESIZE)
                            if tp in self.blocked_tiles: self.blocked_tiles.remove(tp)
                            if tp in self.item_tiles: self.item_tiles.remove(tp)
                            for s in self.visible_sprites:
                                if isinstance(s, DroppedItem) and s.rect.topleft == sp.rect.topleft: s.kill(); break
                            stolen = True; break
                    if stolen: continue
                    for s in self.obstacle_sprites:
                        if isinstance(s, Cofre) and m.manhattan_distance(mt, (s.rect.x // TILESIZE, s.rect.y // TILESIZE)) <= 1:
                            if s.valor > 0 and s.interactuar():
                                img = random.choice(self.resource_images); m.pickup_item(img)
                                ItemIcon(m.rect.midtop, img, [self.visible_sprites]); break

    def check_player_captured(self):
        for m in self.monsters:
            if m.state == 'carrying':
                for sp in self.spawn_sprites:
                    if sp.spawn_type == 'enemy' and m.hitbox.colliderect(sp.hitbox): return True
        return False

    def update_player_stun_duration(self, nd): self.player.update_stun_duration(nd)
    def update_zoom(self, z): self.visible_sprites.update_zoom(z)
    def update_player_speed(self, ns): self.player.update_speed(ns)
    def update_monsters_speed(self, ns):
        for m in self.monsters: m.update_speed(ns)
    def update_monsters_vision(self, nv):
        self.current_monster_vision = nv
        for m in self.monsters: m.update_vision_radius(nv)
    def update_monsters_fury(self, nf):
        self.current_monster_fury = nf
        for m in self.monsters: m.update_fury(nf)
    def update_monster_ai(self, na):
        self.current_monster_ai = na
        for m in self.monsters: m.set_ai_algorithm(na)
    def get_monster_info(self): return [{'id': m.id, 'ai': m.ai_algorithm} for m in self.monsters]
    def get_player_score(self): return len([s for s in self.spawn_sprites if s.spawn_type == 'player' and not s.is_empty()])
    def get_enemy_score(self): return len([s for s in self.spawn_sprites if s.spawn_type == 'enemy' and not s.is_empty()])
    def update_single_monster_ai(self, mid, nai):
        for m in self.monsters:
            if m.id == mid: m.set_ai_algorithm(nai); break
    def export_monster_memories(self):
        output_dir = "memorias"
        if not os.path.exists(output_dir): os.makedirs(output_dir)
        for m in self.monsters:
            filename = os.path.join(output_dir, f"moustro{m.id}_pseudomemoria.txt")
            map_text = []
            for y in range(m.map_height_tiles):
                row = ""
                for x in range(m.map_width_tiles):
                    if m.fog_grid[y][x]: row += "?"
                    elif (x, y) == self.player_last_stun_pos: row += "J"
                    elif (x, y) in self.item_tiles: row += "i"
                    elif (x, y) in self.blocked_tiles: row += "X"
                    else: row += " "
                map_text.append(row)
            with open(filename, 'w') as f: f.write("\n".join(map_text))

class YSortCameraGroup(pygame.sprite.Group):
    def __init__(self):
        super().__init__()
        self.display_surface = pygame.display.get_surface()
        self.half_width, self.half_height = int((WIDTH / ZOOM) // 2), int((HEIGHT / ZOOM) // 2)
        self.offset = pygame.math.Vector2()
        self.shake_amount, self.shake_end_time = 0, 0
        try: self.floor_surf = pygame.image.load("../map/map.png").convert()
        except:
            self.floor_surf = pygame.Surface((2000, 2000)); self.floor_surf.fill('green')
        self.floor_rect = self.floor_surf.get_rect(topleft=(0, 0))
        
    def custom_draw(self, player, surface, fog_surface, perspective):
        if perspective == 'Jugador':
            self.offset.x = player.rect.centerx - self.half_width
            self.offset.y = player.rect.centery - self.half_height
            sw, sh = surface.get_width(), surface.get_height()
            if self.floor_rect.width < sw: self.offset.x = (self.floor_rect.width - sw) / 2
            else: self.offset.x = max(0, min(self.offset.x, self.floor_rect.width - sw))
            if self.floor_rect.height < sh: self.offset.y = (self.floor_rect.height - sh) / 2
            else: self.offset.y = max(0, min(self.offset.y, self.floor_rect.height - sh))
        else: self.offset.x = self.offset.y = 0

        ctime = pygame.time.get_ticks()
        soff = pygame.math.Vector2(0, 0)
        if ctime < self.shake_end_time:
            amt = int(self.shake_amount)
            if amt > 0: soff.x, soff.y = random.randint(-amt, amt), random.randint(-amt, amt)
            self.shake_amount = max(0, self.shake_amount - 0.5)

        ox, oy = int(self.offset.x + soff.x), int(self.offset.y + soff.y)
        surface.blit(self.floor_surf, self.floor_rect.topleft - pygame.math.Vector2(ox, oy))
        for s in sorted(self.sprites(), key=lambda s: s.rect.centery):
            surface.blit(s.image, s.rect.topleft - pygame.math.Vector2(ox, oy))
        if FOG_ENABLED and perspective != 'Mapa Completo' and fog_surface:
            surface.blit(fog_surface, self.floor_rect.topleft - pygame.math.Vector2(ox, oy))

    def update_zoom(self, z):
        self.half_width, self.half_height = int((WIDTH / z) // 2), int((HEIGHT / z) // 2)
