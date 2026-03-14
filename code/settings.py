import os

# Valores por defecto
WIDTH = 1280
HEIGHT = 720
FPS = 60
TILESIZE = 16

ZOOM = 2.5
RAP = 4
VOLUME = 0.5
PERSPECTIVE = 'Jugador'

# Fog of War settings
FOG_ENABLED = True
FOG_COLOR = 'black'

# Configuración de los monstruos
MONSTER_SPEED = 1.0
MONSTER_VISION = 4
STUN_TIME = 5
MONSTER_AI = 'territorial'
MONSTER_FURY = 20
PLAYER_SPRITE = 'Inspector' # Opciones: 'Inspector', 'NinjaDark', 'Noble', 'Spirit'

def load_config():
    global ZOOM, FPS, RAP, VOLUME, PERSPECTIVE, MONSTER_SPEED, MONSTER_VISION, MONSTER_FURY, STUN_TIME, MONSTER_AI, PLAYER_SPRITE
    config_path = os.path.join(os.path.dirname(__file__), 'configuracion', 'config.txt')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if '=' in line:
                        key, val = line.strip().split('=')
                        if key == 'ZOOM': ZOOM = float(val)
                        elif key == 'FPS': FPS = int(val)
                        elif key == 'RAP': RAP = int(val)
                        elif key == 'VOLUME': VOLUME = float(val)
                        elif key == 'PERSPECTIVE': PERSPECTIVE = val
                        elif key == 'MONSTER_SPEED': MONSTER_SPEED = float(val)
                        elif key == 'MONSTER_VISION': MONSTER_VISION = int(val)
                        elif key == 'MONSTER_FURY': MONSTER_FURY = int(val)
                        elif key == 'STUN_TIME': STUN_TIME = int(val)
                        elif key == 'MONSTER_AI': MONSTER_AI = val
                        elif key == 'PLAYER_SPRITE': PLAYER_SPRITE = val
            print(f"Configuración completa cargada desde {config_path}")
        except Exception as e:
            print(f"Error cargando configuración: {e}")

# Cargar configuración al inicio
load_config()
