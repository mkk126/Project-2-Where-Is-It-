from bots.typeABotImproved import TypeABotImproved
class TypeAFree(TypeABotImproved):

    #Remove the movement penalty from the score calculation, so the bot always maximizes the number of candidates eliminated.
    def scorePosition(self, expectedEliminated, moves):
        return expectedEliminated
