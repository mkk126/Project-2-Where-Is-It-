import random
from collections import deque
from bots.typeBBot import TypeBBot

# Note: I am realizing that I could have made a much simpler type B improvement bot
# where I just have it run the detector twice in a row
# which would give it a better idea of where the lost bot is,
# Remember to think smarter not harder next time

# Improved Type B: retain exact Bayesian updates but weigh the chance of finding LostBot against the cost of walking to a candidate cell.
class TypeBBotImproved(TypeBBot):

    def findReachable(self, botPosition):
        queue = deque([botPosition])
        distance = {botPosition: 0}
        previous = {}

        while queue:
            row, col = queue.popleft()

            for nextRow, nextCol in (
                (row - 1, col),
                (row + 1, col),
                (row, col - 1),
                (row, col + 1)
            ):
                neighbor = (nextRow, nextCol)

                if (0 <= nextRow < len(self.ship)
                        and 0 <= nextCol < len(self.ship[nextRow])
                        and self.ship[nextRow][nextCol]
                        and neighbor not in distance):
                    distance[neighbor] = distance[(row, col)] + 1
                    previous[neighbor] = (row, col)
                    queue.append(neighbor)

        return distance, previous

    # Trace backward from the destination, then reverse the path
    def buildPath(self, botPosition, destination, previous):
        path = []

        while destination != botPosition:
            path.append(destination)
            destination = previous[destination]

        return path[::-1]

    # Select the candidate with the best probability-to-cost ratio.
    def findPath(self, botPosition):
        distance, previous = self.findReachable(botPosition)
        bestScore = -1.0
        bestPositions = []

        for position, probability in self.probabilities.items():
            moves = distance[position]
            score = probability / (moves + 0.5)

            if score > bestScore + 1e-12:
                bestScore = score
                bestPositions = [position]

            elif abs(score - bestScore) <= 1e-12:
                bestPositions.append(position)

        # Choose randomly among equally scored cells and follow its BFS path.
        destination = random.choice(bestPositions)
        return self.buildPath(botPosition, destination, previous)
