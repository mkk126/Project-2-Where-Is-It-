import random
from collections import deque
from bots.typeABot import TypeABot


# Improved Type A strategy. Choose detector positions that eliminate many possible LostBot locations relative to the cost of walking there.
class TypeABotImproved(TypeABot):

    # Return a score for a detector position based on how many candidates it eliminates and how far away it is.
    def scorePosition(self, expectedEliminated, moves):
        return expectedEliminated / (moves + 0.5)

    # Use BFS to find the reachable detector position with the best score. Break ties randomly.
    def findPath(self, botPosition):
        dimension = len(self.ship)
        totalPossible = len(self.possibleLocations)

        #prefix-sum significantly speeds counting of locations.
        prefix = [[0] * (dimension + 1) for _ in range(dimension + 1)]
        for row in range(dimension):
            for col in range(dimension):
                prefix[row + 1][col + 1] = (
                    prefix[row][col + 1] + prefix[row + 1][col]
                    - prefix[row][col] + ((row, col) in self.possibleLocations)
                )

        # Run BFS once to get shortest distances and paths to all open cells.
        queue = deque([botPosition])
        distance = {botPosition: 0}
        previous = {}
        while queue:
            row, col = queue.popleft()
            for nextRow, nextCol in ((row-1, col), (row+1, col),
                                     (row, col-1), (row, col+1)):
                neighbor = (nextRow, nextCol)
                if (0 <= nextRow < dimension and 0 <= nextCol < dimension
                        and self.ship[nextRow][nextCol] and neighbor not in distance):
                    distance[neighbor] = distance[(row, col)] + 1
                    previous[neighbor] = (row, col)
                    queue.append(neighbor)

        bestScore = -1.0
        bestDistance = float("inf")
        bestPositions = []

        #Ruled out cells should still be considered for detector placement.
        for position, moves in distance.items():
            if moves == 0:
                continue

            row, col = position
            rowStart = max(0, row - self.k)
            rowEnd = min(dimension, row + self.k + 1)
            colStart = max(0, col - self.k)
            colEnd = min(dimension, col + self.k + 1)

            # Count possible LostBot positions inside this detector square.
            inside = (prefix[rowEnd][colEnd] - prefix[rowStart][colEnd]
                      - prefix[rowEnd][colStart] + prefix[rowStart][colStart])
            
            onCandidate = int(position in self.possibleLocations)
            pingCount = inside - onCandidate
            noPingCount = totalPossible - inside

            #Assume the LostBot is equally likely to be in any of the remaining possible locations.
            expectedRemaining = (pingCount ** 2 + noPingCount ** 2) / totalPossible
            expectedEliminated = totalPossible - expectedRemaining
            score = self.scorePosition(expectedEliminated, moves)

            #prefer a higher score, then a shorter path, then break ties randomly.
            #add a small epsilon to avoid floating point issues when comparing scores.
            if score > bestScore + 1e-12:
                bestScore = score
                bestDistance = moves
                bestPositions = [position]
            elif abs(score - bestScore) <= 1e-12:
                if moves < bestDistance:
                    bestDistance = moves
                    bestPositions = [position]
                elif moves == bestDistance:
                    bestPositions.append(position)


        # Reconstruct the route from the chosen detector cell back to the bot.
        destination = random.choice(bestPositions)
        path = []
        while destination != botPosition:
            path.append(destination)
            destination = previous[destination]
        return path[::-1]
