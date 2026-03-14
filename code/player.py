import pygame
from settings import *

class Player(pygame.sprite.Sprite):
    def __init__(self, pos, groups, sprites_obstacle):
        super().__init__(groups)
        self.image = None 
        self.frame_index = 0
        self.animation_speed = 0.15
        self.status = 'down'
        
        # 1. Cargar Assets
        self.import_player_assets()
        
        # 2. Configuración inicial
        # Usamos la primera imagen de "idle_down" para empezar
        self.image = self.animations[self.status][self.frame_index]
        self.rect = self.image.get_rect(topleft=pos)
        
        # Hitbox ajustada (más pequeña que el sprite para dar profundidad)
        self.hitbox = self.rect.inflate(-2, -5) 

        # 3. Datos de movimiento
        self.direction = pygame.math.Vector2()
        self.speed = 5
        self.sprites_obstacle = sprites_obstacle

        # Interaction
        self.interacting = False
        self.interaction_cooldown = 400
        self.interaction_time = 0
        self.previous_status = 'idle_down'

        # Item Inventory
        self.held_item = None

        # Stun Logic
        self.is_stunned = False
        self.stun_duration = STUN_TIME * 1000 # Convertir a ms
        self.stun_time = 0
        self.is_being_carried = False
        self.just_recovered = False
        self.grace_period = 3000 # 3 segundos de inmunidad tras recuperarse
        self.grace_start_time = 0

    def is_holding_item(self):
        return self.held_item is not None

    def pickup_item(self, item):
        if not self.is_holding_item():
            self.held_item = item

    def drop_item(self):
        self.held_item = None

    def import_player_assets(self):
        import settings
        path = f'../assets/sprites/Characters/{settings.PLAYER_SPRITE}/SpriteSheet.png'
        sheet = pygame.image.load(path).convert_alpha()
        
        
        # --- PASO 1: Recortar TODO en una lista plana (0, 1, 2, ... N) ---
        frames = []
        original_size = 16   # Tamaño del cuadrito en el PNG
        scale_size = TILESIZE # Tamaño en el juego (64)
        
        cols = int(sheet.get_width() / original_size)
        rows = int(sheet.get_height() / original_size)
        
        for row in range(rows):
            for col in range(cols):
                x = col * original_size
                y = row * original_size
                
                # Recortar frame individual
                cut_rect = pygame.Rect(x, y, original_size, original_size)
                cut_surf = sheet.subsurface(cut_rect)
                
                # Escalar
                scaled_surf = pygame.transform.scale(cut_surf, (scale_size, scale_size))
                frames.append(scaled_surf)

        # --- PASO 2: Construir Animaciones con TUS ÍNDICES ---
        # Estructura del ciclo: [Paso 1, Pies Juntos, Paso 2, Pies Juntos]
        self.animations = {
            # IDLE (Quieto)
            'idle_down':  [frames[0]],
            'idle_up':    [frames[1]],
            'idle_left':  [frames[2]],
            'idle_right': [frames[3]],

            # ABAJO (Columna 0)
            # Paso1(4) -> Junto(8) -> Paso2(12) -> Junto(8)
            'down': [frames[4], frames[8], frames[12], frames[8]], 
            
            # ARRIBA (Columna 1)
            # Paso1(5) -> Junto(9) -> Paso2(13) -> Junto(9)
            'up':   [frames[5], frames[9], frames[13], frames[9]], 
            
            # IZQUIERDA (Columna 2)
            # Paso1(6) -> Junto(10) -> Paso2(14) -> Junto(10)
            'left': [frames[6], frames[10], frames[14], frames[10]],
            
            # DERECHA (Columna 3)
            # Paso1(7) -> Junto(11) -> Paso2(15) -> Junto(11)
            'right': [frames[7], frames[11], frames[15], frames[11]],
            
            # ITEM
            'item': [frames[25]],
            # STUNNED
            'stunned': [frames[24]]
        }

    def input(self):
        if self.interacting or self.is_stunned or self.is_being_carried:
            self.direction = pygame.math.Vector2()
            return
            
        keys = pygame.key.get_pressed()
        
        if keys[pygame.K_UP]:
            self.direction.y = -1
            self.status = 'up'
        elif keys[pygame.K_DOWN]:
            self.direction.y = 1
            self.status = 'down'
        else:
            self.direction.y = 0

        if keys[pygame.K_RIGHT]:
            self.direction.x = 1
            self.status = 'right'
        elif keys[pygame.K_LEFT]:
            self.direction.x = -1
            self.status = 'left'
        else:
            self.direction.x = 0

    def get_status(self):
        if self.interacting or self.is_stunned or self.is_being_carried or self.status == 'stunned':
            return

        # Si estamos quietos, cambiamos a estado 'idle'
        if self.direction.magnitude() == 0:
            if not 'idle' in self.status:
                self.status = self.status.replace(self.status, 'idle_' + self.status)

    def animate(self):
        if self.is_stunned or self.is_being_carried:
            self.status = 'stunned'
            
        if self.status not in self.animations:
            self.status = 'idle_down'
            
        animation = self.animations[self.status]
        
        # Avanzar frame
        self.frame_index += self.animation_speed
        if self.frame_index >= len(animation):
            self.frame_index = 0
        
        # Actualizar imagen
        self.image = animation[int(self.frame_index)]
        if self.is_stunned or self.is_being_carried:
            self.image.set_alpha(200)
        else:
            self.image.set_alpha(255)
        self.rect = self.image.get_rect(center=self.hitbox.center)

    def collision(self, direction):
        if direction == 'horizontal':
            for sprite in self.sprites_obstacle:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.x > 0: self.hitbox.right = sprite.hitbox.left
                    if self.direction.x < 0: self.hitbox.left = sprite.hitbox.right

        if direction == 'vertical':
            for sprite in self.sprites_obstacle:
                if sprite.hitbox.colliderect(self.hitbox):
                    if self.direction.y > 0: self.hitbox.bottom = sprite.hitbox.top
                    if self.direction.y < 0: self.hitbox.top = sprite.hitbox.bottom

    def move(self, speed):
        if self.is_stunned or self.is_being_carried: return
        # Normalizar vector
        if self.direction.magnitude() != 0:
            self.direction = self.direction.normalize()
        
        # Mover y comprobar colisiones por ejes separados
        self.hitbox.x += self.direction.x * speed
        self.collision('horizontal')
        self.hitbox.y += self.direction.y * speed
        self.collision('vertical')
        
        # Mover el sprite real a la posición de la hitbox
        self.rect.center = self.hitbox.center

    def start_interaction(self):
        if not self.interacting:
            self.interacting = True
            self.interaction_time = pygame.time.get_ticks()
            self.previous_status = self.status
            self.status = 'item'
            self.frame_index = 0

    def cooldowns(self):
        current_time = pygame.time.get_ticks()
        if self.interacting:
            if current_time - self.interaction_time >= self.interaction_cooldown:
                self.interacting = False
                self.status = self.previous_status
        
        if self.is_stunned and not self.is_being_carried:
            if current_time - self.stun_time >= self.stun_duration:
                self.is_stunned = False
                self.just_recovered = True
                self.status = 'idle_down'
                self.is_being_carried = False
                self.direction = pygame.math.Vector2()
                self.grace_start_time = current_time # Empezar inmunidad

    def get_stunned(self):
        current_time = pygame.time.get_ticks()
        # Solo se estunea si no está ya estuneado Y no está en periodo de gracia
        if not self.is_stunned and current_time - self.grace_start_time >= self.grace_period:
            self.is_stunned = True
            self.stun_time = current_time
            self.direction = pygame.math.Vector2()
            return True
        return False

    def update_speed(self, new_speed):
        self.speed = new_speed

    def update_stun_duration(self, new_duration):
        self.stun_duration = new_duration * 1000

    def update(self):
        self.input()
        self.cooldowns()
        self.get_status()
        self.animate()
        self.move(self.speed)
