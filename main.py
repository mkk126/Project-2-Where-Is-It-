from shipGeneration import generateShip
from simulation import placeEntities
from visualizer import visualizeShip
from bots.typeABot import TypeABot
from bots.typeABotImproved import TypeABotImproved
from bots.typeAFree import TypeAFree
from bots.typeBBot import TypeBBot
from bots.typeBBotImproved import TypeBBotImproved
from bots.typeBFree import TypeBFree


# Choose a strategy: A/B for baseline, AI/BI for improved, AF/BF for free movement.
dimension = 20
botType = "AF"
k = 10
alpha = 0.5

detectorCost = 0.5


def main():
    # Generate a ship and randomly place the LocatorBot and LostBot.
    ship = generateShip(dimension)
    botPosition, lostBotPosition = placeEntities(ship)

    # Match each bot type to its class and detector setting.
    botClasses = {
        "A": (TypeABot, k),
        "AI": (TypeABotImproved, k),
        "AF": (TypeAFree, k),
        "B": (TypeBBot, alpha),
        "BI": (TypeBBotImproved, alpha),
        "BF": (TypeBFree, alpha)
    }

    if botType not in botClasses:
        raise ValueError("Unknown botType: " + botType)

    # Create the selected bot. Free variants do not pay for movement.
    botClass, setting = botClasses[botType]
    bot = botClass(ship, setting)
    movementCost = 0.0 if botType in ("AF", "BF") else 1.0

    # The visualizer runs and records the simulation one action per click.
    # Closing the window returns control to main without restarting the bot.
    visualizeShip(
        ship, bot, botPosition, lostBotPosition,
        movementCost, detectorCost
    )

    # Read the existing recording instead of running the bot a second time.
    result = bot._runRecording["result"]

    print(
        f"Status: {result['status']} | "
        f"Moves: {result['moveActions']} | "
        f"Detections: {result['detectorActions']} | "
        f"Cost: {result['totalCost']:.2f}"
    )
    print("Saved recording:", bot.lastRecordingPath)


if __name__ == "__main__":
    main()