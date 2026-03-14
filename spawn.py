import pygame
from settings import TILESIZE

class Spawn(pygame.sprite.Sprite):
    def __init__(self, pos, groups, spawn_type):
        super().__init__(groups)
        
        self.spawn_type = spawn_type
        
        # Create a transparent surface for the spawn point
        self.image = pygame.Surface((TILESIZE, TILESIZE), pygame.SRCALPHA)
        
        self.rect = self.image.get_rect(topleft=pos)
        self.hitbox = self.rect
        self.item = None # To hold the item dropped on this spawn

    def is_empty(self):
        return self.item is None

    def place_item(self, item_sprite):
        self.item = item_sprite
