import math
import random
from collections import deque


# Baseline strategy for the Type B detector.
# Run the detector, update the LostBot probability distribution, then move to the most likely cell. Break probability ties by distance, then randomly.
class TypeBBot:

    def __init__(self, ship, alpha):
        self.ship = ship
        self.alpha = alpha

        if not isinstance(alpha, (int, float)) or alpha <= 0:
            raise ValueError("alpha must be a positive number.")

        # Initially, LostBot is equally likely to occupy any open cell.
        openCells = [
            (row, col)
            for row, cells in enumerate(ship)
            for col, openCell in enumerate(cells)
            if openCell
        ]

        startingProbability = 1.0 / len(openCells)
        self.probabilities = {
            position: startingProbability for position in openCells
        }

        self.path = []
        self.shouldDetect = True

    # Return a ping with probability e^(-alpha * (distance - 1)).
    def runDetector(self, botPosition, lostBotPosition):
        if botPosition == lostBotPosition:
            return "FOUND"

        distance = math.dist(botPosition, lostBotPosition)
        pingProbability = math.exp(-self.alpha * (distance - 1))

        if random.random() < pingProbability:
            return "PING"

        return "NO_PING"

    # Update the probability of each possible location using Bayes' rule.
    def updateKnowledge(self, botPosition, detectorResult):
        updatedProbabilities = {}
        totalProbability = 0.0

        for position, priorProbability in self.probabilities.items():

            if position == botPosition:
                continue

            distance = math.dist(botPosition, position)
            exponent = -self.alpha * (distance - 1)

            # Calculate how likely the observed detector result would be if LostBot were at this particular position.
            if detectorResult == "PING":
                likelihood = math.exp(exponent)
            else:
                likelihood = -math.expm1(exponent)

            newProbability = priorProbability * likelihood

            if newProbability > 0:
                updatedProbabilities[position] = newProbability
                totalProbability += newProbability

        # If the detector result is inconsistent with all remaining possibilities, raise an error.
        if totalProbability == 0:
            raise RuntimeError("No possible LostBot locations remain after detection.")

        # Divide each updated probability by their combined total
        self.probabilities = {
            position: probability / totalProbability
            for position, probability in updatedProbabilities.items()
        }

        self.path = []

    # Find the shortest path to the highest-probability LostBot location.
    def findPath(self, botPosition):
        highestProbability = max(self.probabilities.values())

        targetCells = {
            position
            for position, probability in self.probabilities.items()
            if probability == highestProbability
        }

        queue = deque([botPosition])
        visited = {botPosition}
        previous = {}

        while queue:
            layer = [queue.popleft() for _ in range(len(queue))]

            candidates = [
                position for position in layer
                if position in targetCells
            ]

            if candidates:
                targetPosition = random.choice(candidates)
                path = []
                currentPosition = targetPosition

                # Reconstruct the path from the destination back to the bot.
                while currentPosition != botPosition:
                    path.append(currentPosition)
                    currentPosition = previous[currentPosition]

                path.reverse()
                return path

            for row, col in layer:
                for nextRow, nextCol in (
                    (row - 1, col),
                    (row + 1, col),
                    (row, col - 1),
                    (row, col + 1)
                ):
                    if not (0 <= nextRow < len(self.ship)
                            and 0 <= nextCol < len(self.ship[nextRow])
                            and self.ship[nextRow][nextCol]):
                        continue

                    neighbor = (nextRow, nextCol)
                    if neighbor in visited:
                        continue

                    visited.add(neighbor)
                    previous[neighbor] = (row, col)
                    queue.append(neighbor)

        return None

    def chooseAction(self, botPosition):
        if self.shouldDetect:
            self.shouldDetect = False
            return "DETECT", None

        # Plan a new route after every detection.
        if not self.path:
            self.path = self.findPath(botPosition)

        if not self.path:
            return None

        nextPosition = self.path.pop(0)


        if not self.path:
            self.shouldDetect = True

        return "MOVE", nextPosition
