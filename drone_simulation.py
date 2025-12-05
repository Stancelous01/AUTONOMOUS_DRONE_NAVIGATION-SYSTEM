import pygame
import sys
import math
import random
from typing import List, Tuple
from dataclasses import dataclass

# Initialize Pygame
pygame.init()

# Display constants
WIDTH, HEIGHT = 1200, 800
GRID_SIZE = 100

# Professional color scheme
SKY_BLUE = (135, 206, 235)
BUILDING_COLORS = [(70, 70, 80), (80, 80, 90), (90, 90, 100)]
DRONE_COLOR = (255, 50, 50)
PATH_COLOR = (50, 200, 50)
CLIPPED_PATH_COLOR = (255, 255, 0)
NO_FLY_ZONE_COLOR = (255, 100, 100, 100)
GRID_COLOR = (200, 200, 200, 50)
TEXT_COLOR = (255, 255, 255)
UI_BACKGROUND = (30, 30, 40, 200)

@dataclass
class NavigationMetrics:
    paths_planned: int = 0
    obstacles_avoided: int = 0
    paths_clipped: int = 0
    total_processing_time: float = 0.0
    successful_deliveries: int = 0

class Building:
    """Represents a building obstacle"""
    def __init__(self, x: int, y: int, width: int, height: int):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = random.choice(BUILDING_COLORS)
        self.height = random.randint(5, 15)  # Visual height effect
    
    def draw(self, surface):
        # Draw building base
        pygame.draw.rect(surface, self.color, self.rect)
        
        # Draw building top (3D effect)
        top_points = [
            (self.rect.left, self.rect.top),
            (self.rect.right, self.rect.top),
            (self.rect.right - self.height, self.rect.top - self.height),
            (self.rect.left - self.height, self.rect.top - self.height)
        ]
        pygame.draw.polygon(surface, (self.color[0]-20, self.color[1]-20, self.color[2]-20), top_points)

class NoFlyZone:
    """Represents restricted airspace"""
    def __init__(self, center_x: int, center_y: int, radius: int):
        self.center = (center_x, center_y)
        self.radius = radius
        self.color = NO_FLY_ZONE_COLOR
    
    def contains_point(self, x: float, y: float) -> bool:
        distance = math.sqrt((x - self.center[0])**2 + (y - self.center[1])**2)
        return distance <= self.radius
    
    def draw(self, surface):
        # Draw semi-transparent circle
        s = pygame.Surface((self.radius * 2, self.radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, self.color, (self.radius, self.radius), self.radius)
        surface.blit(s, (self.center[0] - self.radius, self.center[1] - self.radius))
        
        # Draw warning pattern
        pygame.draw.circle(surface, (255, 255, 0), self.center, self.radius, 2)
        for angle in range(0, 360, 45):
            end_x = self.center[0] + self.radius * math.cos(math.radians(angle))
            end_y = self.center[1] + self.radius * math.sin(math.radians(angle))
            pygame.draw.line(surface, (255, 255, 0), self.center, (end_x, end_y), 2)

class Drone:
    """Autonomous drone with path planning"""
    def __init__(self, start_pos: Tuple[int, int]):
        self.x, self.y = start_pos
        self.target_x, self.target_y = start_pos
        self.speed = 3
        self.size = 8
        self.path = []
        self.clipped_path = []
        self.is_moving = False
        self.battery = 100
        self.carrying_package = True
    
    def set_target(self, target_x: int, target_y: int):
        self.target_x, self.target_y = target_x, target_y
        self.is_moving = True
    
    def update(self):
        if not self.is_moving:
            return
        
        # Calculate direction to target
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > self.speed:
            # Normalize and move
            self.x += (dx / distance) * self.speed
            self.y += (dy / distance) * self.speed
            
            # Add to path
            self.path.append((self.x, self.y))
            if len(self.path) > 100:  # Limit path length
                self.path.pop(0)
            
            # Consume battery
            self.battery -= 0.01
        else:
            # Reached target
            self.x, self.y = self.target_x, self.target_y
            self.is_moving = False
            if self.carrying_package:
                self.carrying_package = False
    
    def clip_path_to_obstacles(self, buildings: List[Building], no_fly_zones: List[NoFlyZone]):
        """Clip path to avoid obstacles using geometric clipping"""
        if len(self.path) < 2:
            return
        
        self.clipped_path = []
        safe_path = []
        
        for point in self.path:
            x, y = point
            
            # Check if point is in any obstacle
            in_obstacle = False
            for building in buildings:
                if building.rect.collidepoint(x, y):
                    in_obstacle = True
                    break
            
            for zone in no_fly_zones:
                if zone.contains_point(x, y):
                    in_obstacle = True
                    break
            
            if not in_obstacle:
                safe_path.append((x, y))
            else:
                if safe_path:
                    self.clipped_path.extend(safe_path)
                    safe_path = []
        
        # Add remaining safe path
        if safe_path:
            self.clipped_path.extend(safe_path)
    
    def draw(self, surface):
        # Draw flight path
        if len(self.path) > 1:
            pygame.draw.lines(surface, PATH_COLOR, False, self.path, 2)
        
        # Draw clipped safe path
        if len(self.clipped_path) > 1:
            pygame.draw.lines(surface, CLIPPED_PATH_COLOR, False, self.clipped_path, 3)
        
        # Draw drone
        pygame.draw.circle(surface, DRONE_COLOR, (int(self.x), int(self.y)), self.size)
        
        # Draw drone direction indicator
        if len(self.path) > 1:
            end_x = self.x + (self.path[-1][0] - self.path[-2][0]) * 2
            end_y = self.y + (self.path[-1][1] - self.path[-2][1]) * 2
            pygame.draw.line(surface, (255, 255, 255), (self.x, self.y), (end_x, end_y), 2)
        
        # Draw status indicator
        status_color = (0, 255, 0) if self.carrying_package else (255, 255, 0)
        pygame.draw.circle(surface, status_color, (int(self.x), int(self.y)), 3)

class UrbanEnvironment:
    """Main simulation environment"""
    def __init__(self):
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Autonomous Drone Path Planning with Obstacle Avoidance")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 16)
        self.title_font = pygame.font.SysFont('Arial', 24, bold=True)
        
        # Create city environment
        self.buildings = self._generate_buildings()
        self.no_fly_zones = self._generate_no_fly_zones()
        self.delivery_points = self._generate_delivery_points()
        
        # Initialize drone
        self.drone = Drone((100, 100))
        self.metrics = NavigationMetrics()
        
        # Simulation state
        self.current_delivery = 0
        self.simulation_time = 0
        self.is_paused = False
    
    def _generate_buildings(self) -> List[Building]:
        """Generate random building layout"""
        buildings = []
        for _ in range(15):
            x = random.randint(50, WIDTH - 150)
            y = random.randint(50, HEIGHT - 150)
            width = random.randint(80, 200)
            height = random.randint(80, 200)
            buildings.append(Building(x, y, width, height))
        return buildings
    
    def _generate_no_fly_zones(self) -> List[NoFlyZone]:
        """Generate restricted airspace zones"""
        return [
            NoFlyZone(400, 300, 80),
            NoFlyZone(700, 500, 60),
            NoFlyZone(900, 200, 70)
        ]
    
    def _generate_delivery_points(self) -> List[Tuple[int, int]]:
        """Generate delivery locations"""
        return [
            (100, 100),  # Start depot
            (1100, 100),  # North delivery
            (1100, 700),  # South-East delivery
            (100, 700),   # South-West delivery
            (600, 400)    # Central delivery
        ]
    
    def draw_grid(self):
        """Draw navigation grid"""
        for x in range(0, WIDTH, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, GRID_SIZE):
            pygame.draw.line(self.screen, GRID_COLOR, (0, y), (WIDTH, y), 1)
    
    def draw_ui_panel(self):
        """Draw information and control panel"""
        panel_rect = pygame.Rect(10, 10, 350, 180)
        
        # Panel background
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill(UI_BACKGROUND)
        self.screen.blit(s, panel_rect)
        
        # Title
        title = self.title_font.render("DRONE NAVIGATION SYSTEM", True, TEXT_COLOR)
        self.screen.blit(title, (20, 20))
        
        # Metrics
        metrics_text = [
            f"Paths Planned: {self.metrics.paths_planned}",
            f"Obstacles Avoided: {self.metrics.obstacles_avoided}",
            f"Paths Clipped: {self.metrics.paths_clipped}",
            f"Successful Deliveries: {self.metrics.successful_deliveries}",
            f"Battery: {self.drone.battery:.1f}%",
            f"Simulation Time: {self.simulation_time:.1f}s",
            f"Status: {'DELIVERING' if self.drone.carrying_package else 'RETURNING'}"
        ]
        
        for i, text in enumerate(metrics_text):
            rendered = self.font.render(text, True, TEXT_COLOR)
            self.screen.blit(rendered, (20, 60 + i * 20))
    
    def draw_controls_panel(self):
        """Draw control instructions"""
        panel_rect = pygame.Rect(WIDTH - 260, 10, 250, 150)
        
        # Panel background
        s = pygame.Surface((panel_rect.width, panel_rect.height), pygame.SRCALPHA)
        s.fill(UI_BACKGROUND)
        self.screen.blit(s, panel_rect)
        
        # Title
        title = self.title_font.render("CONTROLS", True, TEXT_COLOR)
        self.screen.blit(title, (WIDTH - 240, 20))
        
        controls = [
            "SPACE: Start/Stop",
            "R: Reset Simulation",
            "C: Clear Path",
            "Click: Set Target",
            "N: Next Delivery"
        ]
        
        for i, control in enumerate(controls):
            rendered = self.font.render(control, True, TEXT_COLOR)
            self.screen.blit(rendered, (WIDTH - 240, 60 + i * 20))
    
    def draw_legend(self):
        """Draw color legend"""
        legend_items = [
            (DRONE_COLOR, "Drone"),
            (PATH_COLOR, "Planned Path"),
            (CLIPPED_PATH_COLOR, "Safe Path"),
            (NO_FLY_ZONE_COLOR, "No-Fly Zone"),
            ((0, 255, 0), "Carrying Package"),
            ((255, 255, 0), "Return Trip")
        ]
        
        for i, (color, text) in enumerate(legend_items):
            y_pos = HEIGHT - 120 + i * 25
            pygame.draw.rect(self.screen, color, (20, y_pos, 20, 15))
            rendered = self.font.render(text, True, TEXT_COLOR)
            self.screen.blit(rendered, (50, y_pos))
    
    def handle_click(self, pos: Tuple[int, int]):
        """Handle mouse click for target setting"""
        x, y = pos
        
        # Check if click is in a building or no-fly zone
        for building in self.buildings:
            if building.rect.collidepoint(x, y):
                return  # Invalid target
        
        for zone in self.no_fly_zones:
            if zone.contains_point(x, y):
                return  # Invalid target
        
        # Set drone target
        self.drone.set_target(x, y)
        self.metrics.paths_planned += 1
    
    def next_delivery(self):
        """Move to next delivery point"""
        if self.current_delivery < len(self.delivery_points) - 1:
            self.current_delivery += 1
        else:
            self.current_delivery = 0  # Return to depot
        
        target = self.delivery_points[self.current_delivery]
        self.drone.set_target(*target)
        self.metrics.paths_planned += 1
        
        if self.current_delivery == 0:
            self.metrics.successful_deliveries += 1
            self.drone.carrying_package = True
    
    def update(self):
        """Update simulation state"""
        if not self.is_paused:
            self.simulation_time += 1/60
            
            # Update drone
            start_time = pygame.time.get_ticks()
            self.drone.update()
            self.drone.clip_path_to_obstacles(self.buildings, self.no_fly_zones)
            
            processing_time = pygame.time.get_ticks() - start_time
            self.metrics.total_processing_time += processing_time
            
            if len(self.drone.clipped_path) > 0:
                self.metrics.paths_clipped += 1
            
            # Count obstacles avoided
            if len(self.drone.path) != len(self.drone.clipped_path):
                self.metrics.obstacles_avoided += 1
            
            # Auto-advance to next delivery when reached target
            if not self.drone.is_moving and self.drone.carrying_package:
                current_target = self.delivery_points[self.current_delivery]
                distance = math.sqrt((self.drone.x - current_target[0])**2 + 
                                   (self.drone.y - current_target[1])**2)
                if distance < 10:
                    self.next_delivery()
    
    def draw(self):
        """Draw entire simulation"""
        # Clear screen with sky color
        self.screen.fill(SKY_BLUE)
        
        # Draw grid
        self.draw_grid()
        
        # Draw obstacles
        for zone in self.no_fly_zones:
            zone.draw(self.screen)
        
        for building in self.buildings:
            building.draw(self.screen)
        
        # Draw delivery points
        for i, (x, y) in enumerate(self.delivery_points):
            color = (0, 255, 0) if i == self.current_delivery else (255, 255, 255)
            pygame.draw.circle(self.screen, color, (x, y), 10)
            pygame.draw.circle(self.screen, (0, 0, 0), (x, y), 10, 2)
            
            # Label delivery points
            label = self.font.render(f"D{i}", True, (0, 0, 0))
            self.screen.blit(label, (x - 5, y - 5))
        
        # Draw drone and paths
        self.drone.draw(self.screen)
        
        # Draw UI elements
        self.draw_ui_panel()
        self.draw_controls_panel()
        self.draw_legend()
    
    def run(self):
        """Main simulation loop"""
        running = True
        
        print("Autonomous Drone Path Planning Simulation Started")
        print("Controls:")
        print("- SPACE: Pause/Resume")
        print("- R: Reset")
        print("- C: Clear Path")
        print("- N: Next Delivery")
        print("- Click: Set Target")
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        self.is_paused = not self.is_paused
                    elif event.key == pygame.K_r:
                        # Reset simulation
                        self.__init__()
                    elif event.key == pygame.K_c:
                        # Clear path
                        self.drone.path = []
                        self.drone.clipped_path = []
                    elif event.key == pygame.K_n:
                        self.next_delivery()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:  # Left click
                        self.handle_click(event.pos)
            
            # Update simulation
            self.update()
            
            # Draw everything
            self.draw()
            
            # Update display
            pygame.display.flip()
            self.clock.tick(60)
        
        pygame.quit()
        sys.exit()

# Run the simulation
if __name__ == "__main__":
    simulation = UrbanEnvironment()
    simulation.run()
