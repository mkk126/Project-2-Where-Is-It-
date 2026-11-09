import random
from collections import deque


# Baseline strategy for the Type A detector.
# Run the detector, update the possible LostBot locations, then move to
# the nearest remaining possible location. Break distance ties randomly.
class TypeABot:
    def __init__(self, ship, k):
        self.ship = ship
        self.k = k

        if type(k) is not int or k < 0:
            raise ValueError("k must be a nonnegative integer.")
        
        # The LostBot could initially be in any open cell, so we start with all open cells as possible locations.
        self.possibleLocations = {
            (row, col)
            for row, cells in enumerate(ship)
            for col, openCell in enumerate(cells)
            if openCell
        }

        self.path = []
        self.shouldDetect = True

    # Return whether the LostBot is within the detector's square radius.
    def runDetector(self, botPosition, lostBotPosition):
        if botPosition == lostBotPosition:
            return "FOUND"

        botRow, botCol = botPosition
        lostRow, lostCol = lostBotPosition

        if abs(botRow - lostRow) <= self.k and abs(botCol - lostCol) <= self.k:
            return "PING"

        return "NO_PING"

    # Eliminate locations inconsistent with the latest detector result.
    def updateKnowledge(self, botPosition, detectorResult):
        botRow, botCol = botPosition
        remainingLocations = set()

        for row, col in self.possibleLocations:
            inRange = (
                abs(row - botRow) <= self.k
                and abs(col - botCol) <= self.k
            )

            # A ping means the LostBot must be inside the square.
            if detectorResult == "PING" and inRange:
                remainingLocations.add((row, col))

            # No ping means the LostBot must be outside the square.
            elif detectorResult == "NO_PING" and not inRange:
                remainingLocations.add((row, col))

        # Detecting here without finding LostBot rules out our current cell.
        remainingLocations.discard(botPosition)
        self.possibleLocations = remainingLocations

        # Choose a fresh destination after each detector reading.
        self.path = []

    # Use BFS to reach the nearest possible LostBot location.
    def findPath(self, botPosition):
        queue = deque([botPosition])
        visited = {botPosition}
        previous = {}

        while queue:
            # Every cell currently in the queue belongs to this BFS layer.
            # 'Layer' is the set of cells that are all the same walking distance from the LocatorBot, like an onion.
            layer = [queue.popleft() for _ in range(len(queue))]

            candidates = [
                position for position in layer
                if position in self.possibleLocations
            ]

            if candidates:
                targetPosition = random.choice(candidates)
                path = []
                currentPosition = targetPosition

                while currentPosition != botPosition:
                    path.append(currentPosition)
                    currentPosition = previous[currentPosition]

                path.reverse()
                return path

            # None of the cells at this distance could contain the LostBot. Expand their open neighbors to search farther away.
            for row, col in layer:
                for nextRow, nextCol in (
                    (row - 1, col),
                    (row + 1, col),
                    (row, col - 1),
                    (row, col + 1)
                ):
                    if not (0 <= nextRow < len(self.ship)):
                        continue
                    if not (0 <= nextCol < len(self.ship[nextRow])):
                        continue
                    if not self.ship[nextRow][nextCol]:
                        continue
                    neighbor = (nextRow, nextCol)
                    if neighbor in visited:
                        continue

                    visited.add(neighbor)
                    previous[neighbor] = (row, col)
                    queue.append(neighbor)

        # No remaining possible LostBot location is reachable.
        # Should never happen but return None because im a java coder and thats what we do
        return None

    # Called by simulation.py to determine the next action.
    def chooseAction(self, botPosition):
        # The baseline detects once at the start and after reaching each target.
        if self.shouldDetect:
            self.shouldDetect = False
            return "DETECT", None

        # Find a new route if there is no existing one. 
        if not self.path:
            self.path = self.findPath(botPosition)

        # Stop if BFS could not find a valid destination.
        if not self.path:
            return None

        # Move one cell, then schedule a detection
        nextPosition = self.path.pop(0)

        # After the last step, run the detector at the new position.
        if not self.path:
            self.shouldDetect = True

        return "MOVE", nextPosition
