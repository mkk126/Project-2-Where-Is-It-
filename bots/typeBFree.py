
import math
import random
from bots.typeBBotImproved import TypeBBotImproved


#As a warning, this bot is fairly slow. I promise it works, but give it some time.

# Favor detector positions that are likely to behave differently (aka have a high variance to encourage travel)
class TypeBFree(TypeBBotImproved):

    def findPath(self, botPosition):

        distance, previous = self.findReachable(botPosition)
        bestScore = -1.0
        bestFound = -1.0
        bestDistance = float("inf")
        bestPositions = []

        for detectorPosition, moves in distance.items():
            foundChance = self.probabilities.get(detectorPosition, 0.0)
            remainingChance = 1.0 - foundChance

            if remainingChance <= 0:
                score = 1.0
            else:
                weightedPing = 0.0
                weightedPingSquared = 0.0

                for lostPosition, probability in self.probabilities.items():
                    if lostPosition == detectorPosition:
                        continue

                    separation = math.dist(detectorPosition, lostPosition)
                    pingChance = math.exp(-self.alpha * (separation - 1))

                    weightedPing += probability * pingChance
                    weightedPingSquared += probability * pingChance ** 2

                
                #Calculate the variance of predicted ping probabilities, conditional on LostBot not being at the detector cell.
                meanPing = weightedPing / remainingChance
                variance = weightedPingSquared / remainingChance - meanPing ** 2

                #Normaize the variance to a 0-1 scale by dividing by the maximum possible variance so that it can be compared to the chance of finding LostBot at this cell.
                score = foundChance + 4 * remainingChance * max(0.0, variance)

            if score > bestScore + 1e-12:
                bestScore = score
                bestFound = foundChance
                bestDistance = moves
                bestPositions = [detectorPosition]

            elif abs(score - bestScore) <= 1e-12:
                if foundChance > bestFound + 1e-12:
                    bestFound = foundChance
                    bestDistance = moves
                    bestPositions = [detectorPosition]

                elif abs(foundChance - bestFound) <= 1e-12:
                    if moves < bestDistance:
                        bestDistance = moves
                        bestPositions = [detectorPosition]
                    elif moves == bestDistance:
                        bestPositions.append(detectorPosition)

        destination = random.choice(bestPositions)
        return self.buildPath(botPosition, destination, previous)


    # Choose between moving and detecting. Unlike the baseline, this bot may decide to detect again at its current position if that gives the highest score, so an empty path is a valid decision
    def chooseAction(self, botPosition):
        if self.shouldDetect:
            self.shouldDetect = False
            return "DETECT", None

        if not self.path:
            self.path = self.findPath(botPosition)

            if not self.path:
                return "DETECT", None

        nextPosition = self.path.pop(0)
        
        if not self.path:
            self.shouldDetect = True

        return "MOVE", nextPosition
