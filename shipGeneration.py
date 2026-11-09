import random

#RULES FOR GENERATION
# - Start with a square grid of "Blocked" cells, and define orthognal cells as neighbours
# - Randomly choose a cell (excluding the border of the grid) and declare it an "open" cell
# - Iteratively, do the following
    # identify all currently blocked cells with open neighbours
    # of the cells with just one neighbour, pick one at random and open it
    # repeat until the conditions are impossible to satisfy
# identify all open cells with one open neighbour as "Dead Ends"
# Pick a random dead end, open one of its blocked neighbours and repeat until half or less remain.


def generateShip(dimension):

    #if the dimension is not an integer, raise an error
    if isinstance(dimension, int) == False:
        raise TypeError("Dimension must be an integer.")

    #If the dimension is less than 3 x 3, no "interior cells" exist, so we cannot generate a ship.
    if(dimension < 3):
        raise ValueError("Dimension must be at least 3.")


    # Start with every cell blocked.
    # False = blocked
    # True = open
    ship = [[False for col in range(dimension)] for row in range(dimension)]

    # Pick a random cell and open it.
    # -2 ensures that we don't pick a border cell.
    row = random.randint(1, dimension - 2)
    col = random.randint(1, dimension - 2)
    ship[row][col] = True

    # Grow the ship.
    # OG code scanned every cell in the entire ship after each
    # new cell was opened to rebuild the candidates list.
    # new implementation just updates the neighbours

    # The candidates set contains all blocked cells with exactly one open neighbor.
    candidates = set()

    # The four neighbors of the first open cell are the only possible
    # candidates at the beginning.
    for neighborRow, neighborCol in getNeighbors(ship, row, col):
        if ship[neighborRow][neighborCol] == False:
            if countOpenNeighbors(ship, neighborRow, neighborCol) == 1:
                candidates.add((neighborRow, neighborCol))

    # Keep opening candidates until there are no more.
    while len(candidates) > 0:

        # Randomly choose one candidate and open it.
        # OG code was a list using random.choice()
        # A set lets us quickly add and remove affected candidates. 
        # but random.choice() doesn't work on sets, so we convert to a tuple first.
        row, col = random.choice(tuple(candidates))
        candidates.remove((row, col))
        ship[row][col] = True

        # Only neighboring blocked cells can have had their number of open
        # neighbors changed by opening this cell.
        for neighborRow, neighborCol in getNeighbors(ship, row, col):

            if ship[neighborRow][neighborCol] == False:

                # If the blocked cell now has exactly one open neighbor,
                # it is a candidate.
                if countOpenNeighbors(ship, neighborRow, neighborCol) == 1:
                    candidates.add((neighborRow, neighborCol))

                # If it now has more than one open neighbor, it is no longer
                # a valid candidate.
                else:
                    candidates.discard((neighborRow, neighborCol))

    # Find all dead ends.
    deadEnds = set()

    #former implementation of checking every neighbour
    #now is just used for the dead end check.
    for row in range(dimension):
        for col in range(dimension):
            if ship[row][col]:
                if countOpenNeighbors(ship, row, col) == 1:
                    deadEnds.add((row, col))

    # Set target number of dead ends at beginning to half the current number of dead ends.
    # Loop until target is met
    targetDeadEnds = len(deadEnds) // 2

    while len(deadEnds) > targetDeadEnds:

        # Pick a random dead end.
        # Originally  was a list. 
        #turned into set for same reason as candidates
        #tupling for the same reason
        row, col = random.choice(tuple(deadEnds))

        #create list of blocked neighbors of the dead end
        blockedNeighbors = []

        #extract the blocked neighbors of the dead end
        for neighborRow, neighborCol in getNeighbors(ship, row, col):
            if ship[neighborRow][neighborCol] == False:
                blockedNeighbors.append((neighborRow, neighborCol))

        # Pick one blocked neighbor and open it.
        newRow, newCol = random.choice(blockedNeighbors)
        ship[newRow][newCol] = True

        # Recalculate the current dead ends.
        affectedCells = {(newRow, newCol)}

        for neighborRow, neighborCol in getNeighbors(ship, newRow, newCol):
            if ship[neighborRow][neighborCol]:
                affectedCells.add((neighborRow, neighborCol))

        for affectedRow, affectedCol in affectedCells:

            if countOpenNeighbors(ship, affectedRow, affectedCol) == 1:
                deadEnds.add((affectedRow, affectedCol))
            else:
                deadEnds.discard((affectedRow, affectedCol))

    return ship


# Returns the orthogonal neighbors of a cell that are inside the ship.
def getNeighbors(ship, row, col):

    neighbors = []
    dimension = len(ship)

    # Up
    if row > 0:
        neighbors.append((row - 1, col))

    # Down
    if row < dimension - 1:
        neighbors.append((row + 1, col))

    # Left
    if col > 0:
        neighbors.append((row, col - 1))

    # Right
    if col < dimension - 1:
        neighbors.append((row, col + 1))

    return neighbors

# Returns the number of open neighbors of a cell.
def countOpenNeighbors(ship, row, col):
    count = 0
    dimension = len(ship)

    # Up
    if row > 0 and ship[row - 1][col]:
        count += 1

    # Down
    if row < dimension - 1 and ship[row + 1][col]:
        count += 1

    # Left
    if col > 0 and ship[row][col - 1]:
        count += 1  

    # Right
    if col < dimension - 1 and ship[row][col + 1]:
        count += 1

    return count
