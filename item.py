import pygame
import random
from settings import *

class Cofre(pygame.sprite.Sprite):
    def __init__(self, pos, groups, obstacle_sprites, valor):
        super().__init__(groups)
        
        # 1. Cargar y Recortar Imagen
        path = '../assets/Items/Treasure/BigTreasureChest.png'
        full_image = pygame.image.load(path).convert_alpha()
        
        # Recorte Cerrado (0, 0)
        self.image_cerrado = full_image.subsurface(pygame.Rect(0, 0, 16, 14))
        self.image_cerrado = pygame.transform.scale(self.image_cerrado, (TILESIZE, TILESIZE))
        
        # Recorte Abierto (16, 0) - Asumiendo que están lado a lado
        self.image_abierto = full_image.subsurface(pygame.Rect(16, 0, 16, 14))
        self.image_abierto = pygame.transform.scale(self.image_abierto, (TILESIZE, TILESIZE))
        
        # 2. Configuración Inicial
        self.image = self.image_cerrado
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10)
        
        # Añadir a colisiones
        obstacle_sprites.add(self)

        # 3. Lógica del Item
        self.valor = valor
        if self.valor == 0:
            self.image = self.image_abierto

    def interactuar(self):
        if self.valor > 0:
            self.valor -= 1
            print(f"¡Has recogido un objeto! Quedan {self.valor}.")
            if self.valor == 0:
                self.image = self.image_abierto
                print("El cofre ahora está vacío.")
            return True # Signal successful interaction
        else:
            print("El cofre está vacío.")
            return False # Signal empty chest

class ItemIcon(pygame.sprite.Sprite):
    def __init__(self, pos, image, groups):
        super().__init__(groups)
        self.image = image
        self.rect = self.image.get_rect(midbottom=pos)
        self.spawn_time = pygame.time.get_ticks()
        self.lifetime = 400  # ms (Reducido para una respuesta más rápida)

    def update(self):
        # The icon should not move upwards
        
        # Kill after lifetime
        current_time = pygame.time.get_ticks()
        if current_time - self.spawn_time > self.lifetime:
            self.kill()

class DroppedItem(pygame.sprite.Sprite):
    def __init__(self, pos, image, groups, obstacle_sprites):
        super().__init__(groups)
        self.image = image
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect.inflate(0, -10)
        obstacle_sprites.add(self)
