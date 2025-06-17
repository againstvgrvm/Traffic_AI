import os
import csv
import time
import random
import pygame

from traffic_ai import train_model, load_or_train_model, predict_direction

# Initialisation
pygame.init()
WIDTH, HEIGHT = 800, 800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulation de Trafic Routier - Réaliste")
FONT = pygame.font.SysFont("Arial", 20)

# Couleurs
WHITE, GREY, RED, GREEN, BLUE, BLACK, PURPLE, ORANGE = (
    (255, 255, 255),
    (50, 50, 50),
    (255, 0, 0),
    (0, 255, 0),
    (0, 120, 255),
    (0, 0, 0),
    (255, 0, 255),
    (255, 165, 0),
)

# Constantes
ROAD_WIDTH, CAR_WIDTH, CAR_HEIGHT = 200, 30, 50
SPEED, SPAWN_RATE = 1.5, 77
DIRECTIONS = ["N", "S", "E", "W"]
STOP_LINES = {
    "N": HEIGHT // 2 - 100,
    "S": HEIGHT // 2 + 100,
    "E": WIDTH // 2 + 100,
    "W": WIDTH // 2 - 100,
}
INTERSECTION_ZONE = pygame.Rect(WIDTH // 2 - 60, HEIGHT // 2 - 60, 120, 120)

# Groupes de directions
GROUP_NS = ["N", "S"]
GROUP_EW = ["E", "W"]

class TrafficLight:
    def __init__(self, position, direction):
        self.position = position
        self.direction = direction
        self.green = False
        self.orange = False  # nouvel état orange

    def draw(self):
        if self.orange:
            color = ORANGE
        elif self.green:
            color = GREEN
        else:
            color = RED
        pygame.draw.circle(WIN, color, self.position, 15)

class Car:
    def __init__(self, direction):
        self.direction = direction
        dx, dy = 0, 0

        if direction == "N":
            self.x, self.y, dy = WIDTH // 2 - ROAD_WIDTH // 4, -CAR_HEIGHT, SPEED
        elif direction == "S":
            self.x, self.y, dy = WIDTH // 2 + ROAD_WIDTH // 4 - CAR_WIDTH, HEIGHT, -SPEED
        elif direction == "E":
            self.x, self.y, dx = WIDTH, HEIGHT // 2 - ROAD_WIDTH // 4 - CAR_WIDTH, -SPEED
        else:  # W
            self.x, self.y, dx = -CAR_HEIGHT, HEIGHT // 2 + ROAD_WIDTH // 4, SPEED

        width, height = (CAR_WIDTH, CAR_HEIGHT) if direction in ['N', 'S'] else (CAR_HEIGHT, CAR_WIDTH)
        self.rect = pygame.Rect(self.x, self.y, width, height)
        self.dx, self.dy = dx, dy
        self.stopped = False
        self.passed_line = False

    def move(self, lights, cars, light_phase):
        line = STOP_LINES[self.direction]
        light = lights[self.direction]

        pos_check = {
            "N": self.rect.bottom >= line,
            "S": self.rect.top <= line,
            "E": self.rect.left <= line,
            "W": self.rect.right >= line,
        }
        block_check = {
            "N": self.rect.bottom + SPEED >= line,
            "S": self.rect.top - SPEED <= line,
            "E": self.rect.left - SPEED <= line,
            "W": self.rect.right + SPEED >= line,
        }

        if pos_check[self.direction]:
            self.passed_line = True

        self.stopped = False

        # Empêcher de rentrer dans l'intersection si une autre voiture y est
        if not self.passed_line and self.rect.colliderect(INTERSECTION_ZONE):
            for other in cars:
                if other != self and other.rect.colliderect(INTERSECTION_ZONE):
                    self.stopped = True
                    return

        # Vision pour éviter collision
        vision = self.rect.copy()
        vision.move_ip(self.dx * 20, self.dy * 20)
        for other in cars:
            if other != self and vision.colliderect(other.rect):
                self.stopped = True
                return

        # Logique d'arrêt selon état feu + position
        # Important : le feu orange est considéré comme arrêt (rouge)
        if (
            not self.passed_line
            and (not light.green or light_phase != "green")
            and block_check[self.direction]
        ):
            self.stopped = True
        else:
            self.stopped = False

        if not self.stopped:
            self.rect.x += self.dx
            self.rect.y += self.dy

    def draw(self):
        pygame.draw.rect(WIN, PURPLE if self.stopped else BLUE, self.rect)

def draw_roads():
    WIN.fill(GREEN)
    pygame.draw.rect(WIN, GREY, (WIDTH // 2 - ROAD_WIDTH // 2, 0, ROAD_WIDTH, HEIGHT))
    pygame.draw.rect(WIN, GREY, (0, HEIGHT // 2 - ROAD_WIDTH // 2, WIDTH, ROAD_WIDTH))
    pygame.draw.rect(WIN, (255, 255, 0), INTERSECTION_ZONE, 2)

def draw_waiting_counts(counts):
    positions = {
        "N": (WIDTH // 2 - 80, HEIGHT // 2 - 140),
        "S": (WIDTH // 2 + 60, HEIGHT // 2 + 120),
        "E": (WIDTH // 2 + 120, HEIGHT // 2 - 80),
        "W": (WIDTH // 2 - 140, HEIGHT // 2 + 60),
    }
    for dir, pos in positions.items():
        WIN.blit(FONT.render(f"{counts[dir]}", True, BLACK), pos)

def simulate_african_conditions(lights):
    if random.random() < 0.001:
        print("Coupure de courant!")
        for light in lights.values():
            light.green = False
            light.orange = False

def main():
    clock = pygame.time.Clock()
    run = True
    frame_count = 0
    last_log_time = time.time()

    if not os.path.exists("data.csv"):
        with open("data.csv", mode='w', newline='') as f:
            csv.writer(f).writerow(["waiting_NS", "waiting_EW", "label"])

    lights = {
        "N": TrafficLight((WIDTH // 2 - 60, HEIGHT // 2 - 100), "N"),
        "S": TrafficLight((WIDTH // 2 + 60, HEIGHT // 2 + 100), "S"),
        "E": TrafficLight((WIDTH // 2 + 100, HEIGHT // 2 - 60), "E"),
        "W": TrafficLight((WIDTH // 2 - 100, HEIGHT // 2 + 60), "W"),
    }

    green_direction = "NS"
    phase_start = time.time()
    light_phase = "green"

    cars = []
    model = load_or_train_model()

    while run:
        clock.tick(60)
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE
            ):
                run = False

        # Spawn des voitures
        if frame_count % SPAWN_RATE == 0:
            cars.append(Car(random.choice(DIRECTIONS)))

        # Comptage voitures arrêtées par direction
        waiting = {d: sum(1 for c in cars if c.direction == d and c.stopped) for d in DIRECTIONS}
        ns, ew = waiting["N"] + waiting["S"], waiting["E"] + waiting["W"]

        now = time.time()
        duration = now - phase_start
        min_switch_interval = max(3, min(10, 3 + (ns if green_direction == "NS" else ew) // 3))

        # Gestion des phases du feu (green, orange, red_all)
        if light_phase == "green" and duration >= min_switch_interval:
            light_phase = "orange"
            phase_start = now
        elif light_phase == "orange" and duration >= 2:
            light_phase = "red_all"
            phase_start = now
        elif light_phase == "red_all" and duration >= 1:
            new_direction = predict_direction(model, ns, ew)
            if new_direction != green_direction:
                green_direction = new_direction
            light_phase = "green"
            phase_start = now

        # Mise à jour des feux avec gestion orange
        for d in DIRECTIONS:
            if light_phase == "green":
                if green_direction == "NS" and d in GROUP_NS:
                    lights[d].green = True
                    lights[d].orange = False
                elif green_direction == "EW" and d in GROUP_EW:
                    lights[d].green = True
                    lights[d].orange = False
                else:
                    lights[d].green = False
                    lights[d].orange = False
            elif light_phase == "orange":
                if green_direction == "NS" and d in GROUP_NS:
                    lights[d].green = False
                    lights[d].orange = True
                elif green_direction == "EW" and d in GROUP_EW:
                    lights[d].green = False
                    lights[d].orange = True
                else:
                    lights[d].green = False
                    lights[d].orange = False
            else:  # red_all
                lights[d].green = False
                lights[d].orange = False

        simulate_african_conditions(lights)

        # Déplacement des voitures par groupe et gestion espacement entre elles
        for direction in DIRECTIONS:
            group = [c for c in cars if c.direction == direction]
            # Tri selon direction pour gérer la voiture devant
            reverse_order = direction in ["N", "W"]
            group.sort(key=lambda c: (c.rect.y if direction in ["N", "S"] else c.rect.x), reverse=reverse_order)
            for i, car in enumerate(group):
                car_ahead = group[i - 1] if i > 0 else None
                if car_ahead:
                    min_gap = 20
                    if direction == "N" and car.rect.bottom + SPEED > car_ahead.rect.top - min_gap:
                        car.stopped = True
                        continue
                    elif direction == "S" and car.rect.top - SPEED < car_ahead.rect.bottom + min_gap:
                        car.stopped = True
                        continue
                    elif direction == "E" and car.rect.left - SPEED < car_ahead.rect.right + min_gap:
                        car.stopped = True
                        continue
                    elif direction == "W" and car.rect.right + SPEED > car_ahead.rect.left - min_gap:
                        car.stopped = True
                        continue
                car.move(lights, cars, light_phase)

        # Sauvegarde données tous les 5s
        if now - last_log_time >= 5:
            with open("data.csv", mode="a", newline="") as f:
                csv.writer(f).writerow([ns, ew, green_direction])
            last_log_time = now

        # Affichage
        draw_roads()
        [light.draw() for light in lights.values()]
        [car.draw() for car in cars]
        draw_waiting_counts(waiting)
        WIN.blit(
            FONT.render(f"Feu Vert: {green_direction} | Phase: {light_phase}", True, BLACK),
            (10, 10),
        )
        pygame.display.update()

    pygame.quit()
    train_model()

if __name__ == "__main__":
    main()
