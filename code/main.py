#!/usr/bin/env python3
import pygame
import sys
import random
import os
from settings import *
from level import Level
from menu import SettingsMenu


class Game:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Captura")

        # Load and play random music
        script_dir = os.path.dirname(__file__)
        music_folder = os.path.abspath(os.path.join(script_dir, '../assets/sounds/Musics'))
        self.music_files = [os.path.join(music_folder, f) for f in os.listdir(music_folder) if f.endswith('.ogg')]
        if self.music_files:
            random_music = random.choice(self.music_files)
            pygame.mixer.music.load(random_music)
            pygame.mixer.music.play(-1)
        
        self.settings = {
            'zoom': ZOOM,
            'fps': FPS,
            'rap': RAP,
            'volume': VOLUME,
            'perspective': PERSPECTIVE,
            'monster_speed': MONSTER_SPEED,
            'monster_vision': MONSTER_VISION,
            'monster_fury': MONSTER_FURY,
            'stun_time': STUN_TIME,
            'monster_ai': MONSTER_AI,
            'player_sprite': PLAYER_SPRITE
        }
        pygame.mixer.music.set_volume(self.settings['volume'])

        self.internal_surf = pygame.Surface(
            (int(WIDTH / self.settings['zoom']), int(HEIGHT / self.settings['zoom']))
        )

        self.clock = pygame.time.Clock()
        self.level = Level()
        
        # Aplicar configuración cargada al nivel inicial
        if self.settings['perspective'] != 'Jugador':
            map_size = self.level.get_map_size()
            self.internal_surf = pygame.Surface(map_size)
        
        self.level.update_player_speed(self.settings['rap'])
        self.level.update_monsters_speed(self.settings['monster_speed'])
        self.level.update_zoom(self.settings['zoom'])
        self.level.update_monster_ai(self.settings['monster_ai'])
        self.level.update_monsters_vision(self.settings['monster_vision'])
        self.level.update_monsters_fury(self.settings['monster_fury'])
        self.level.update_player_stun_duration(self.settings['stun_time'])

        self.settings_menu = SettingsMenu(self.screen)
        self.state = 'running'
        self.paused_surface = None

        # Audio de fin de juego
        self.sfx_defeat = pygame.mixer.Sound('../assets/sounds/Jingles/GameOver3.wav')
        self.sfx_victory = pygame.mixer.Sound('../assets/sounds/Jingles/Success3.wav')
        self.end_sound_played = False

    def update_zoom(self, new_zoom):
        # Solo actualiza el zoom si estamos en perspectiva de jugador
        if self.settings['perspective'] == 'Jugador':
            self.settings['zoom'] = new_zoom
            self.internal_surf = pygame.Surface(
                (int(WIDTH / self.settings['zoom']), int(HEIGHT / self.settings['zoom']))
            )
        self.level.update_zoom(new_zoom)


    def update_rap(self, new_rap):
        self.settings['rap'] = new_rap
        self.level.update_player_speed(new_rap)

    def update_volume(self, new_volume):
        self.settings['volume'] = new_volume
        pygame.mixer.music.set_volume(self.settings['volume'])

    def change_music(self):
        if self.music_files:
            random_music = random.choice(self.music_files)
            pygame.mixer.music.load(random_music)
            pygame.mixer.music.play(-1)
    
    def update_perspective(self, new_perspective):
        self.settings['perspective'] = new_perspective
        if new_perspective == 'Jugador':
            self.internal_surf = pygame.Surface((int(WIDTH / self.settings['zoom']), int(HEIGHT / self.settings['zoom'])))
        else: # Monstruos o Mapa Completo
            map_size = self.level.get_map_size()
            self.internal_surf = pygame.Surface(map_size)
    
    def update_monster_speed(self, new_speed):
        self.settings['monster_speed'] = new_speed
        self.level.update_monsters_speed(new_speed)

    def update_monster_ai(self, new_ai):
        self.settings['monster_ai'] = new_ai
        self.level.update_monster_ai(new_ai)

    def update_monster_vision(self, new_vision):
        self.settings['monster_vision'] = new_vision
        self.level.update_monsters_vision(new_vision)

    def update_monster_fury(self, new_fury):
        self.settings['monster_fury'] = new_fury
        self.level.update_monsters_fury(new_fury)

    def update_stun_time(self, new_time):
        self.settings['stun_time'] = new_time
        self.level.update_player_stun_duration(new_time)

    def update_player_sprite(self, new_sprite):
        self.settings['player_sprite'] = new_sprite
        import settings
        settings.PLAYER_SPRITE = new_sprite
        self.save_configuration() # Guardar automáticamente al cambiar personaje
        self.restart_game()

    def save_configuration(self):
        config_dir = os.path.join(os.path.dirname(__file__), 'configuracion')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
        
        config_path = os.path.join(config_dir, 'config.txt')
        try:
            with open(config_path, 'w') as f:
                f.write(f"ZOOM={self.settings['zoom']}\n")
                f.write(f"FPS={self.settings['fps']}\n")
                f.write(f"RAP={self.settings['rap']}\n")
                f.write(f"VOLUME={self.settings['volume']}\n")
                f.write(f"PERSPECTIVE={self.settings['perspective']}\n")
                f.write(f"MONSTER_SPEED={self.settings['monster_speed']}\n")
                f.write(f"MONSTER_VISION={self.settings['monster_vision']}\n")
                f.write(f"MONSTER_FURY={self.settings['monster_fury']}\n")
                f.write(f"STUN_TIME={self.settings['stun_time']}\n")
                f.write(f"MONSTER_AI={self.settings['monster_ai']}\n")
                f.write(f"PLAYER_SPRITE={self.settings['player_sprite']}\n")
            print("Configuración completa guardada exitosamente.")
        except Exception as e:
            print(f"Error al guardar configuración: {e}")

    def restart_game(self):
        # Crea una nueva instancia del nivel, reseteando todo
        self.level = Level()
        # Vuelve a aplicar las configuraciones actuales al nuevo nivel
        self.level.update_player_speed(self.settings['rap'])
        self.level.update_monsters_speed(self.settings['monster_speed'])
        self.level.update_zoom(self.settings['zoom'])
        self.level.update_monster_ai(self.settings['monster_ai'])
        self.level.update_monsters_vision(self.settings['monster_vision'])
        self.level.update_monsters_fury(self.settings['monster_fury'])
        self.level.update_player_stun_duration(self.settings['stun_time'])
        
        self.end_sound_played = False

    def run(self):
        while True:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == 'running':
                            self.state = 'paused'
                            self.paused_surface = self.screen.copy()
                        elif self.state == 'paused':
                            self.state = 'running'
                    if (self.state == 'game_over' or self.state == 'victory') and event.key == pygame.K_RETURN:
                        self.restart_game()
                        self.state = 'running'
            
            if self.state == 'running':
                self.internal_surf.fill('black')
                self.level.run(self.internal_surf, self.settings['perspective'])

                # Comprobar si el jugador fue capturado por los monstruos
                if self.level.check_player_captured():
                    self.state = 'game_over'
                    pygame.mixer.music.stop()
                    if not self.end_sound_played:
                        self.sfx_defeat.play()
                        self.end_sound_played = True

                # Comprobar condición de victoria del jugador (5 items)
                elif self.level.get_player_score() >= 5:
                    self.state = 'victory'
                    pygame.mixer.music.stop()
                    if not self.end_sound_played:
                        self.sfx_victory.play()
                        self.end_sound_played = True

                # Comprobar condición de victoria de la computadora (10 items)
                elif self.level.get_enemy_score() >= 10:
                    self.state = 'game_over'
                    pygame.mixer.music.stop()
                    if not self.end_sound_played:
                        self.sfx_defeat.play()
                        self.end_sound_played = True

                scaled_surf = pygame.transform.scale(
                    self.internal_surf, (WIDTH, HEIGHT)
                )
                self.screen.blit(scaled_surf, (0, 0))
                pygame.display.update()
            elif self.state == 'paused':
                mutable_settings = {
                    'zoom': self.settings['zoom'],
                    'fps': self.settings['fps'],
                    'rap': self.settings['rap'],
                    'volume': self.settings['volume'],
                    'perspective': self.settings['perspective'],
                    'monster_speed': self.settings['monster_speed'],
                    'monster_vision': self.settings['monster_vision'],
                    'monster_fury': self.settings['monster_fury'],
                    'stun_time': self.settings['stun_time'],
                    'monster_ai': self.settings['monster_ai'],
                    'player_sprite': self.settings['player_sprite']
                }
                monster_info = self.level.get_monster_info()
                new_settings, action = self.settings_menu.display(self.paused_surface, mutable_settings, events, monster_info)
                
                # Procesa la acción primero
                if action == 'exit':
                    pygame.quit()
                    sys.exit()
                elif action == 'restart':
                    self.restart_game()
                    continue
                elif action == 'export':
                    self.level.export_monster_memories()
                elif action == 'save':
                    self.save_configuration()

                # Aplicar cambios individuales de IA
                if new_settings.get('single_monster_ai'):
                    m_id, m_ai = new_settings['single_monster_ai']
                    self.level.update_single_monster_ai(m_id, m_ai)

                # Aplicar cambios en los ajustes generales
                if new_settings['zoom'] != self.settings['zoom']:
                    self.update_zoom(new_settings['zoom'])
                if new_settings['rap'] != self.settings['rap']:
                    self.update_rap(new_settings['rap'])
                if new_settings['volume'] != self.settings['volume']:
                    self.update_volume(new_settings['volume'])
                if new_settings.get('next_song'):
                    self.change_music()
                if new_settings['perspective'] != self.settings['perspective']:
                    self.update_perspective(new_settings['perspective'])
                if new_settings['monster_speed'] != self.settings['monster_speed']:
                    self.update_monster_speed(new_settings['monster_speed'])
                if new_settings['monster_vision'] != self.settings['monster_vision']:
                    self.update_monster_vision(new_settings['monster_vision'])
                if new_settings['monster_fury'] != self.settings['monster_fury']:
                    self.update_monster_fury(new_settings['monster_fury'])
                if new_settings['stun_time'] != self.settings['stun_time']:
                    self.update_stun_time(new_settings['stun_time'])
                if new_settings['monster_ai'] != self.settings['monster_ai']:
                    self.update_monster_ai(new_settings['monster_ai'])
                if new_settings['player_sprite'] != self.settings['player_sprite']:
                    self.update_player_sprite(new_settings['player_sprite'])

            elif self.state == 'game_over' or self.state == 'victory':
                self.screen.fill('black')
                font = pygame.font.Font(None, 100)
                
                if self.state == 'victory':
                    text = "¡Victoria!"
                    color = (0, 255, 0)
                else:
                    text = "Derrota"
                    color = (255, 0, 0)
                
                msg_surf = font.render(text, True, color)
                msg_rect = msg_surf.get_rect(center=(WIDTH/2, HEIGHT/2))
                self.screen.blit(msg_surf, msg_rect)
                
                # Instrucción para reiniciar
                font_small = pygame.font.Font(None, 36)
                restart_surf = font_small.render("Presiona ENTER para reiniciar", True, (255, 255, 255))
                restart_rect = restart_surf.get_rect(center=(WIDTH/2, HEIGHT/2 + 80))
                self.screen.blit(restart_surf, restart_rect)
                
                pygame.display.update()

            self.clock.tick(self.settings['fps'])


if __name__ == '__main__':
    Game().run()
