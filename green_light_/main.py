import os
import csv
import time
import random
import pygame

# --- 1. IMPORTATION DES NOUVELLES FONCTIONS DE L'IA ---
from traffic_ai import (
    _ai_instance,
    report_emergency_to_ai,
    report_bus_to_ai,
    train_model
)

# Initialisation
pygame.init()
WIDTH, HEIGHT = 800, 800
WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Simulation de Trafic Avancée (Guidée par IA)")
FONT = pygame.font.SysFont("Arial", 18)
FONT_BOLD = pygame.font.SysFont("Arial", 22, bold=True)

# Couleurs
WHITE, GREY, RED, GREEN = (255, 255, 255), (50, 50, 50), (255, 0, 0), (0, 255, 0)
BLACK, BLUE, YELLOW, ORANGE = (0, 0, 0), (0, 120, 255), (255, 255, 0), (255, 165, 0)

# Constantes
ROAD_WIDTH, CAR_WIDTH, CAR_HEIGHT = 200, 30, 50
SPEED, SPAWN_RATE = 1.5, 77
DIRECTIONS = ["N", "S", "E", "W"]
STOP_LINES = { "N": HEIGHT // 2 - 100, "S": HEIGHT // 2 + 100, "E": WIDTH // 2 + 100, "W": WIDTH // 2 - 100 }

# --- 2. ZONES DE DÉTECTION POUR LES VÉHICULES PRIORITAIRES ---
DETECTION_ZONES = {
    "N": HEIGHT // 2 - 250, "S": HEIGHT // 2 + 250,
    "E": WIDTH // 2 + 250, "W": WIDTH // 2 - 250
}


class TrafficLight:
    def __init__(self, position, direction):
        self.position = position
        self.direction = direction
        self.green = False

    def draw(self):
        color = GREEN if self.green else RED
        pygame.draw.circle(WIN, color, self.position, 15)


# --- 3. CLASSE CARPOUR GERER LES TYPES DE VÉHICULES ---
class Car:
    def __init__(self, direction):
        self.direction = direction
        self.type = self._get_random_type()  # 'normal', 'bus', 'emergency'

        # Attributs visuels et de vitesse basés sur le type
        if self.type == 'emergency':
            self.color = ORANGE
            self.speed = SPEED * 1.5
        elif self.type == 'bus':
            self.color = YELLOW
            self.speed = SPEED * 0.9
        else:
            self.color = BLUE
            self.speed = SPEED

        dx, dy = 0, 0
        if direction == "N":
            self.x, self.y, dy = WIDTH // 2 - ROAD_WIDTH // 4, -CAR_HEIGHT, self.speed
        elif direction == "S":
            self.x, self.y, dy = WIDTH // 2 + ROAD_WIDTH // 4 - CAR_WIDTH, HEIGHT, -self.speed
        elif direction == "E":
            self.x, self.y, dx = WIDTH, HEIGHT // 2 - ROAD_WIDTH // 4 - CAR_WIDTH, -self.speed
        else:
            self.x, self.y, dx = -CAR_HEIGHT, HEIGHT // 2 + ROAD_WIDTH // 4, self.speed

        width, height = (CAR_WIDTH, CAR_HEIGHT) if direction in ['N', 'S'] else (CAR_HEIGHT, CAR_WIDTH)
        self.rect = pygame.Rect(self.x, self.y, width, height)
        self.dx, self.dy = dx, dy
        self.stopped = False
        self.passed_line = False
        self.priority_reported = False

    def _get_random_type(self):
        rand_val = random.randint(1, 150)
        if rand_val == 1: return 'emergency'
        if rand_val <= 4: return 'bus'
        return 'normal'

    def move(self, lights):
        line = STOP_LINES[self.direction]
        light = lights[self.direction]

        if self.type == 'emergency':
            self.stopped = False
        else:
            pos_check = {"N": self.rect.bottom >= line, "S": self.rect.top <= line, "E": self.rect.left <= line,
                         "W": self.rect.right >= line}
            block_check = {"N": self.rect.bottom + self.speed >= line, "S": self.rect.top - self.speed <= line,
                           "E": self.rect.left - self.speed <= line, "W": self.rect.right + self.speed >= line}
            if pos_check[self.direction]: self.passed_line = True
            if not self.passed_line and block_check[self.direction] and not light.green:
                self.stopped = True
            elif light.green or self.passed_line:
                self.stopped = False

        if not self.stopped:
            self.rect.x += self.dx
            self.rect.y += self.dy

    def draw(self):
        pygame.draw.rect(WIN, self.color, self.rect)
        if self.type == 'emergency':  # Ajoute un petit "U" pour urgence
            text = FONT.render("U", True, BLACK)
            WIN.blit(text, (self.rect.centerx - 5, self.rect.centery - 10))


def draw_roads():
    WIN.fill(GREEN)
    pygame.draw.rect(WIN, GREY, (WIDTH // 2 - ROAD_WIDTH // 2, 0, ROAD_WIDTH, HEIGHT))
    pygame.draw.rect(WIN, GREY, (0, HEIGHT // 2 - ROAD_WIDTH // 2, WIDTH, ROAD_WIDTH))


def draw_info_panel(counts, ai_decision):
    ns_count = counts.get('N', 0) + counts.get('S', 0)
    ew_count = counts.get('E', 0) + counts.get('W', 0)

    ns_text = FONT_BOLD.render(f"NS: {ns_count}", True, BLACK)
    ew_text = FONT_BOLD.render(f"EW: {ew_count}", True, BLACK)
    WIN.blit(ns_text, (10, 10))
    WIN.blit(ew_text, (10, 40))

    if ai_decision:
        dir_text = FONT.render(f"Decision: {ai_decision['direction']}", True, BLACK)
        dur_text = FONT.render(f"Duration: {ai_decision['duration']}s", True, BLACK)
        rea_text = FONT.render(f"Reason: {ai_decision['reason']}", True, BLACK)
        WIN.blit(dir_text, (10, 80))
        WIN.blit(dur_text, (10, 100))
        WIN.blit(rea_text, (10, 120))


def main():
    clock = pygame.time.Clock()
    run = True
    frame_count = 0


    lights = {d: TrafficLight((0, 0), d) for d in DIRECTIONS}  # Positions mises à jour après
    lights['N'].position, lights['S'].position = (WIDTH // 2 - 60, HEIGHT // 2 - 100), (WIDTH // 2 + 60,
                                                                                        HEIGHT // 2 + 100)
    lights['E'].position, lights['W'].position = (WIDTH // 2 + 100, HEIGHT // 2 - 60), (WIDTH // 2 - 100,
                                                                                        HEIGHT // 2 + 60)

    cars = []

    # --- 4. GESTION DU CYCLE DE L'IA ---
    # L'IA prend le contrôle du temps
    ai_decision = None
    green_direction = "NS"  # Direction par défaut
    green_duration = 10  # Durée par défaut
    last_decision_time = time.time()

    while run:
        clock.tick(60)
        frame_count += 1

        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                run = False

        if frame_count % SPAWN_RATE == 0:
            cars.append(Car(random.choice(DIRECTIONS)))

        # --- 5. DÉTECTION ET RAPPORT DES VÉHICULES PRIORITAIRES ---
        for car in cars:
            if car.priority_reported or car.passed_line:
                continue

            # Vérifie si la voiture est dans une zone de détection
            det_line = DETECTION_ZONES[car.direction]
            in_zone = False
            if car.direction == 'N' and car.rect.bottom >= det_line:
                in_zone = True
            elif car.direction == 'S' and car.rect.top <= det_line:
                in_zone = True
            elif car.direction == 'E' and car.rect.left <= det_line:
                in_zone = True
            elif car.direction == 'W' and car.rect.right >= det_line:
                in_zone = True

            if in_zone:
                if car.type == 'emergency':
                    report_emergency_to_ai('NS' if car.direction in ['N', 'S'] else 'EW')
                    car.priority_reported = True
                elif car.type == 'bus':
                    report_bus_to_ai('NS' if car.direction in ['N', 'S'] else 'EW')
                    car.priority_reported = True

        # Logique de collision et mouvement des voitures
        for direction in DIRECTIONS:
            group = [c for c in cars if c.direction == direction]
            group.sort(key=lambda c: (c.rect.y if direction in ['N', 'S'] else c.rect.x),
                       reverse=(direction in ['N', 'W']))
            for i, car in enumerate(group):
                car_ahead = group[i - 1] if i > 0 else None
                if car_ahead:
                    min_gap = 10
                    if direction == 'N' and car.rect.bottom + car.speed > car_ahead.rect.top - min_gap:
                        car.stopped = True; continue
                    elif direction == 'S' and car.rect.top - car.speed < car_ahead.rect.bottom + min_gap:
                        car.stopped = True; continue
                    elif direction == 'E' and car.rect.left - car.speed < car_ahead.rect.right + min_gap:
                        car.stopped = True; continue
                    elif direction == 'W' and car.rect.right + car.speed > car_ahead.rect.left - min_gap:
                        car.stopped = True; continue
                car.move(lights)

        # --- 6. PRISE DE DÉCISION BASÉE SUR LE TEMPS DE L'IA ---
        now = time.time()
        if now - last_decision_time > green_duration:
            # Le temps est écoulé, on demande une nouvelle décision à l'IA
            waiting = {d: sum(1 for c in cars if c.direction == d and c.stopped) for d in DIRECTIONS}
            ns_waiting = waiting.get('N', 0) + waiting.get('S', 0)
            ew_waiting = waiting.get('E', 0) + waiting.get('W', 0)

            # Appel à la méthode de décision de l'instance de l'IA
            ai_decision = _ai_instance.decide(ns_waiting, ew_waiting)

            green_direction = ai_decision['direction']
            # durée MINIMALE de 5s
            green_duration = max(5, ai_decision.get('duration', 10))
            last_decision_time = now

            if ai_decision['reason'] == 'EMERGENCY VEHICLE PRIORITY':
                last_decision_time = now - green_duration + 2

        # Mise à jour des feux
        for d in DIRECTIONS:
            lights[d].green = d in green_direction

        # Nettoyage des voitures hors de l'écran
        cars = [c for c in cars if -100 < c.rect.x < WIDTH + 100 and -100 < c.rect.y < HEIGHT + 100]

        # Dessin
        draw_roads()
        [light.draw() for light in lights.values()]
        [car.draw() for car in cars]
        waiting_counts = {d: sum(1 for c in cars if c.direction == d and c.stopped) for d in DIRECTIONS}
        draw_info_panel(waiting_counts, ai_decision)
        pygame.display.update()

    pygame.quit()
    print("Training model on latest data...")
    train_model()


if __name__ == "__main__":
    main()