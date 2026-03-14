import pygame
from settings import *

class SettingsMenu:
    def __init__(self, screen):
        self.screen = screen
        self.font = pygame.font.Font(None, 36)
        self.is_active = False
        self.selected_option = 0
        self.base_options = ['Zoom', 'FPS', 'Rapidez', 'Volume', 'Next Song', 'Perspectiva', 'Velocidad Monstruos', 'Visión Monstruos', 'Furia', 'Tiempo Estuneo', 'IA Monstruos', 'Personaje']
        self.action_options = ['Guardar Config', 'Exportar Memorias', 'Reiniciar Juego', 'Salir']
        
        self.perspective_modes = ['Jugador', 'Monstruos', 'Mapa Completo']
        self.ai_modes = ['territorial', 'repulsion', 'noise', 'boids']
        self.player_sprites = ['Inspector', 'NinjaDark', 'Noble', 'Spirit']
        # monster_sprites se usará internamente en el nivel, no en el menú

    def display(self, surface, current_settings, events, monster_info=None):
        new_settings = current_settings.copy()
        new_settings['next_song'] = False
        new_settings['single_monster_ai'] = None # format: (id, new_ai)
        action = None

        # Build dynamic options list
        options = self.base_options.copy()
        options.extend(self.action_options)
        
        # Ensure selection is within bounds
        self.selected_option = self.selected_option % len(options)

        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    self.selected_option = (self.selected_option - 1) % len(options)
                elif event.key == pygame.K_DOWN:
                    self.selected_option = (self.selected_option + 1) % len(options)
                
                elif event.key == pygame.K_RETURN:
                    option_text = options[self.selected_option]
                    if option_text == 'Reiniciar Juego': action = 'restart'
                    elif option_text == 'Salir': action = 'exit'
                    elif option_text == 'Exportar Memorias': action = 'export'
                    elif option_text == 'Guardar Config': action = 'save'

                elif event.key == pygame.K_LEFT:
                    option_text = options[self.selected_option]
                    if option_text == 'Zoom': new_settings['zoom'] = max(1.0, round(new_settings['zoom'] - 0.1, 1))
                    elif option_text == 'FPS': new_settings['fps'] = max(30, new_settings['fps'] - 5)
                    elif option_text == 'Rapidez': new_settings['rap'] = max(1, new_settings['rap'] - 1)
                    elif option_text == 'Volume': new_settings['volume'] = max(0.0, round(new_settings['volume'] - 0.1, 1))
                    elif option_text == 'Perspectiva':
                        idx = (self.perspective_modes.index(new_settings['perspective']) - 1) % len(self.perspective_modes)
                        new_settings['perspective'] = self.perspective_modes[idx]
                    elif option_text == 'Velocidad Monstruos': new_settings['monster_speed'] = max(0.5, round(new_settings['monster_speed'] - 0.1, 1))
                    elif option_text == 'Visión Monstruos': new_settings['monster_vision'] = max(1, new_settings['monster_vision'] - 1)
                    elif option_text == 'Furia': new_settings['monster_fury'] = max(0, new_settings['monster_fury'] - 5)
                    elif option_text == 'Tiempo Estuneo': new_settings['stun_time'] = max(1, new_settings['stun_time'] - 1)
                    elif option_text == 'IA Monstruos':
                        idx = (self.ai_modes.index(new_settings['monster_ai']) - 1) % len(self.ai_modes)
                        new_settings['monster_ai'] = self.ai_modes[idx]
                    elif option_text == 'Personaje':
                        idx = (self.player_sprites.index(new_settings['player_sprite']) - 1) % len(self.player_sprites)
                        new_settings['player_sprite'] = self.player_sprites[idx]

                elif event.key == pygame.K_RIGHT:
                    option_text = options[self.selected_option]
                    if option_text == 'Zoom': new_settings['zoom'] = min(5.0, round(new_settings['zoom'] + 0.1, 1))
                    elif option_text == 'FPS': new_settings['fps'] = min(120, new_settings['fps'] + 5)
                    elif option_text == 'Rapidez': new_settings['rap'] = min(10, new_settings['rap'] + 1)
                    elif option_text == 'Volume': new_settings['volume'] = min(1.0, round(new_settings['volume'] + 0.1, 1))
                    elif option_text == 'Next Song': new_settings['next_song'] = True
                    elif option_text == 'Perspectiva':
                        idx = (self.perspective_modes.index(new_settings['perspective']) + 1) % len(self.perspective_modes)
                        new_settings['perspective'] = self.perspective_modes[idx]
                    elif option_text == 'Velocidad Monstruos': new_settings['monster_speed'] = min(4.0, round(new_settings['monster_speed'] + 0.1, 1))
                    elif option_text == 'Visión Monstruos': new_settings['monster_vision'] = min(10, new_settings['monster_vision'] + 1)
                    elif option_text == 'Furia': new_settings['monster_fury'] = min(200, new_settings['monster_fury'] + 5)
                    elif option_text == 'Tiempo Estuneo': new_settings['stun_time'] = min(20, new_settings['stun_time'] + 1)
                    elif option_text == 'IA Monstruos':
                        idx = (self.ai_modes.index(new_settings['monster_ai']) + 1) % len(self.ai_modes)
                        new_settings['monster_ai'] = self.ai_modes[idx]
                    elif option_text == 'Personaje':
                        idx = (self.player_sprites.index(new_settings['player_sprite']) + 1) % len(self.player_sprites)
                        new_settings['player_sprite'] = self.player_sprites[idx]

        self.screen.fill((0, 0, 0))
        title_text = self.font.render("Configuración Individual", True, (255, 255, 255))
        self.screen.blit(title_text, title_text.get_rect(center=(WIDTH / 2, 40)))

        for i, option in enumerate(options):
            color = (255, 255, 0) if i == self.selected_option else (255, 255, 255)
            text = option
            if option == 'Zoom': text = f"Zoom: {new_settings['zoom']:.1f}"
            elif option == 'FPS': text = f"FPS: {new_settings['fps']}"
            elif option == 'Rapidez': text = f"Rapidez: {new_settings['rap']}"
            elif option == 'Volume': text = f"Volume: {new_settings['volume']:.1f}"
            elif option == 'Perspectiva': text = f"Perspectiva: < {new_settings['perspective']} >"
            elif option == 'Velocidad Monstruos': text = f"Velocidad Monstruos: {new_settings['monster_speed']:.1f}"
            elif option == 'Visión Monstruos': text = f"Visión Monstruos: {new_settings['monster_vision']} (área {new_settings['monster_vision']*2+1}x{new_settings['monster_vision']*2+1})"
            elif option == 'Furia': text = f"Furia: +{new_settings['monster_fury']}% (si ve al jugador)"
            elif option == 'Tiempo Estuneo': text = f"Tiempo Estuneo: {new_settings['stun_time']}s"
            elif option == 'IA Monstruos': text = f"IA Monstruos: < {new_settings['monster_ai']} >"
            elif option == 'Personaje': text = f"Personaje: < {new_settings['player_sprite']} >"
            elif option == 'Guardar Config': text = ">>> GUARDAR CONFIGURACIÓN <<<"
            
            opt_surf = self.font.render(text, True, color)
            self.screen.blit(opt_surf, opt_surf.get_rect(center=(WIDTH / 2, 90 + i * 32)))

        pygame.display.update()
        return new_settings, action
