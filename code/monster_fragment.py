    def get_new_path(self, spawn_sprites=None):
        """
        Selecciona y ejecuta el algoritmo de IA para obtener una nueva ruta.
        Prioriza:
        1. Volver a un spawn vacío si tiene un objeto.
        2. Ir a un cofre si ve uno.
        3. Explorar.
        """
        current_tile = (int(self.hitbox.centerx // TILESIZE), int(self.hitbox.centery // TILESIZE))

        # 1. Si tiene un objeto, buscar el spawn enemigo vacío más cercano
        if self.held_item and spawn_sprites:
            best_spawn = None
            min_dist = float('inf')
            for s in spawn_sprites:
                if s.spawn_type == 'enemy' and s.is_empty():
                    dist = self.manhattan_distance(current_tile, (s.rect.x // TILESIZE, s.rect.y // TILESIZE))
                    if dist < min_dist:
                        min_dist = dist
                        best_spawn = s
            
            if best_spawn:
                target_tile = (best_spawn.rect.x // TILESIZE, best_spawn.rect.y // TILESIZE)
                
                # Si ya estamos en el spawn, no buscamos ruta, esperamos interacción
                if current_tile == target_tile:
                    return

                # Intentar por ruta conocida
                self.path = self.astar_to_target(target_tile, respect_fog=True)
                if self.path: return
                
                # SI SE TRABA (no hay ruta conocida), usa "instinto" (ignora niebla para volver)
                self.path = self.astar_to_target(target_tile, respect_fog=False)
                if self.path: return

        # 2. Si ve un cofre cercano no vacío, ir a por él
        chest = self.find_closest_chest()
        if chest:
            chest_tile = (chest.rect.x // TILESIZE, chest.rect.y // TILESIZE)
            # Buscar una casilla adyacente libre y conocida
            target_tile = self.find_reachable_adjacent(chest_tile)

            # SI NO HAY ADYACENTE LIBRE (pasillo estrecho), intentamos ir al cofre directamente
            if not target_tile:
                target_tile = chest_tile

            if target_tile:
                # Si ya estamos al lado del cofre (distancia 1 o menos), esperar interacción
                if self.manhattan_distance(current_tile, chest_tile) <= 1:
                    return

                # Permitimos ignorar la solidez del cofre SOLO si es nuestro objetivo final
                self.path = self.astar_to_target(target_tile, respect_fog=True, allow_target_solid=True)
                if self.path: return

        # 3. Exploración estándar
        if self.ai_algorithm == 'dfs':
            self.path = self.dfs_path()
        elif self.ai_algorithm == 'bfs':
            self.path = self.bfs_path()
        elif self.ai_algorithm == 'astar':
            self.path = self.astar_path()

    def find_closest_chest(self):
        """Busca el cofre más cercano que el monstruo haya 'descubierto' (niebla quitada) y que no esté vacío."""
        closest_chest = None
        min_dist = float('inf')
        
        from item import Cofre
        for sprite in self.obstacle_sprites:
            if isinstance(sprite, Cofre) and sprite.valor > 0:
                tx, ty = sprite.rect.x // TILESIZE, sprite.rect.y // TILESIZE
                if 0 <= tx < self.map_width_tiles and 0 <= ty < self.map_height_tiles:
                    if not self.fog_grid[ty][tx]: # Solo si ya lo ha visto
                        dist = self.manhattan_distance((self.hitbox.centerx // TILESIZE, self.hitbox.centery // TILESIZE), (tx, ty))
                        if dist < min_dist:
                            min_dist = dist
                            closest_chest = sprite
        return closest_chest

    def find_reachable_adjacent(self, tile):
        """Busca la casilla adyacente más cercana que sea caminable y conocida."""
        neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        random.shuffle(neighbors)
        for dx, dy in neighbors:
            adj = (tile[0] + dx, tile[1] + dy)
            if 0 <= adj[0] < self.map_width_tiles and 0 <= adj[1] < self.map_height_tiles:
                if adj not in self.blocked_tiles and not self.fog_grid[adj[1]][adj[0]]:
                    return adj
        return None

    def astar_to_target(self, target_tile, respect_fog=False, allow_target_solid=False):
        """Generalización de A* para ir a una casilla específica."""
        start_tile = (int(self.hitbox.centerx // TILESIZE), int(self.hitbox.centery // TILESIZE))
        if start_tile == target_tile: return []

        open_set = []
        heapq.heappush(open_set, (0, self.manhattan_distance(start_tile, target_tile), [start_tile]))
        visited = {start_tile}

        while open_set:
            f, h, path = heapq.heappop(open_set)
            current = path[-1]
            if current == target_tile: return path[1:]

            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                next_tile = (current[0] + dx, current[1] + dy)
                if next_tile not in visited:
                    if 0 <= next_tile[0] < self.map_width_tiles and 0 <= next_tile[1] < self.map_height_tiles:
                        # Si respect_fog es True, solo caminamos por donde ya hemos visto
                        if respect_fog and self.fog_grid[next_tile[1]][next_tile[0]] and next_tile != target_tile:
                            continue
                            
                        # SOLO casillas NO bloqueadas, a menos que sea el target y esté permitido
                        if next_tile not in self.blocked_tiles or (allow_target_solid and next_tile == target_tile):
                            visited.add(next_tile)
                            new_path = path + [next_tile]
                            heapq.heappush(open_set, (len(new_path) + self.manhattan_distance(next_tile, target_tile), self.manhattan_distance(next_tile, target_tile), new_path))
        return []
