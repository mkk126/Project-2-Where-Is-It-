import csv
import json
import time
from itertools import zip_longest
from pathlib import Path

from shipGeneration import generateShip
from simulation import placeEntities, runSimulation, runsDirectory
from bots.typeABot import TypeABot
from bots.typeABotImproved import TypeABotImproved
from bots.typeAFree import TypeAFree
from bots.typeBBot import TypeBBot
from bots.typeBBotImproved import TypeBBotImproved
from bots.typeBFree import TypeBFree


# Experiment settings. Switch between "standard" and "free" to select
experimentMode = "free"

dimension = 50
numberOfTrials = 100
kValues = [20, 22, 24, 26]
alphaValues = [0.10, 0.125, 0.15, 0.175, 0.20]
detectorCost = 0.5

dataDirectory = Path(__file__).resolve().parent / "data"

# Build the list of bots and detector settings to test.
def buildConfig():
    if experimentMode not in ("standard", "free"):
        raise ValueError('experimentMode must be "standard" or "free".')

    #if its free, the movement cost is 0, otherwise its 1
    freeMovement = experimentMode == "free"
    movementCost = 0.0 if freeMovement else 1.0
    movementMode = "Free Movement" if freeMovement else "Standard"
    configurations = []

    # Alternate Type A and Type B settings so they are tested in a consistent order.
    for k, alpha in zip_longest(kValues, alphaValues):
        if k is not None:
            configurations.append(("A", "k", k, movementMode, movementCost, "Baseline", TypeABot))
            configurations.append(("A", "k", k, movementMode, movementCost, "Improved", TypeABotImproved))

            if freeMovement:
                configurations.append(("A", "k", k, movementMode, movementCost, "Free Movement", TypeAFree))

        if alpha is not None:
            configurations.append(("B", "alpha", alpha, movementMode, movementCost, "Baseline", TypeBBot))
            configurations.append(("B", "alpha", alpha, movementMode, movementCost, "Improved", TypeBBotImproved))

            if freeMovement:
                configurations.append(("B", "alpha", alpha, movementMode, movementCost, "Free Movement", TypeBFree))

    return configurations


# Number experiments by checking the JSON files already saved in runs/.
def nextExperimentId():
    existingIds = []
    for path in runsDirectory.glob("experiment*.json"):
        number = path.stem.removeprefix("experiment")
        if number.isdigit():
            existingIds.append(int(number))
    return max(existingIds, default=0) + 1


#Run every bot on the same ship and starting positions, then save the results in a JSON file.
def runExperiments(dimension, numberOfTrials):
    configurations = buildConfig()
    # Initialize the totals for each configuration.
    totals = [
        {"successes": 0, "cost": 0, "moves": 0, "detections": 0}
        for _ in configurations
    ]
    trialResults = []
    runCounter = 0

    # An 'experiment' gets one sequential number, and its runs start at 1.
    runsDirectory.mkdir(exist_ok=True)
    experimentId = nextExperimentId()
    recordingPath = runsDirectory / f"experiment{experimentId}.json"

    # Stream the JSON as trials finish
    with open(recordingPath, "x", encoding="utf-8") as recordingFile:
        header = {
            #the first format was inefficient so i added a version number to the json so that i can change the format in the future if needed
            "formatVersion": 2,
            "experimentId": experimentId,
            "experimentMode": experimentMode,
            "dimension": dimension,
            "numberOfTrials": numberOfTrials,
            "kValues": kValues,
            "alphaValues": alphaValues
        }

        # Write the header and start the trials array.
        recordingFile.write('{"settings":')
        json.dump(header, recordingFile)
        recordingFile.write(',"trials":[\n')

        #run each trial with a new ship and starting positions, then run each bot on the same ship.
        for trial in range(1, numberOfTrials + 1):

            #print the trial number to the console so that the user can see progress.
            print(f"Running trial {trial}/{numberOfTrials}")
            #generate a new ship and randomly place the LocatorBot and LostBot.
            ship = generateShip(dimension)
            botPosition, lostBotPosition = placeEntities(ship)

            #Store/Write the only once, and then store each run
            if trial > 1:
                recordingFile.write(",\n")
            recordingFile.write("{\n")
            recordingFile.write(f'"trial":{trial},"ship":')
            json.dump(ship, recordingFile, separators=(",", ":"))
            recordingFile.write(',"botStart":')
            json.dump(botPosition, recordingFile)
            recordingFile.write(',"lostBotPosition":')
            json.dump(lostBotPosition, recordingFile)
            recordingFile.write(',"runs":[\n')

            #Limiter in case a bot has a forever bug. Scale the limiter based on how big the ship is
            openCells = sum(sum(row) for row in ship)
            maxActions = max(500, 30 * openCells)

            # Run each bot on the same ship and starting positions, then record the results.
            for index, (configuration, total) in enumerate(zip(configurations, totals)):
                detectorType, settingName, setting, mode, movementCost, botName, botClass = configuration
                bot = botClass(ship, setting)
                runCounter += 1
                success, cost, status, moves, detections = runSimulation(
                    ship, bot, botPosition, lostBotPosition,
                    movementCost, detectorCost, maxActions,
                    compact=True, recordingPath=recordingPath, runId=runCounter
                )

                # Append this run to the shared JSON,
                if index > 0:
                    recordingFile.write(",\n")
                    
                json.dump(bot._runRecording, recordingFile, separators=(",", ":"))
                trialResults.append({
                    "trial": trial, "detectorType": detectorType, "bot": botName,
                    "movementMode": mode, "settingName": settingName, "setting": setting,
                    "status": status, "cost": cost, "moves": moves, "detections": detections,
                    "runId": bot.lastRecordingId,
                    "recordingFile": "runs/" + recordingPath.name
                })

                # The average discovery cost only includes successful runs.
                # The summary also includes the success rate to expose failures.
                if success:
                    total["successes"] += 1
                    total["cost"] += cost
                    total["moves"] += moves
                    total["detections"] += detections

            recordingFile.write("]}")
            recordingFile.flush()  # A completed trial is already on disk.

        recordingFile.write("]}\n")

    #let the user know where the experiment recordings are saved
    print("Saved experiment recordings:", recordingPath)
    results = []

    # Calculate the overall averages for each configuration and return them along with the individual trial results.
    for configuration, total in zip(configurations, totals):
        detectorType, settingName, setting, mode, movementCost, botName, botClass = configuration
        successes = total["successes"]
        results.append({
            "detectorType": detectorType, "bot": botName, "movementMode": mode,
            "dimension": dimension, "settingName": settingName, "setting": setting,
            "trials": numberOfTrials, "successes": successes,
            "successRate": successes / numberOfTrials,
            "averageCost": total["cost"] / successes if successes else None,
            "averageMoves": total["moves"] / successes if successes else None,
            "averageDetections": total["detections"] / successes if successes else None
        })

    return results, trialResults, experimentId


# Save overall averages and individual trial details in the data folder.

#"Results" saves specifically the averages for each configuration.
#"Trials" saves the individual results for each trial and bot run.
#A trial is one ship and starting positions, and a run is one bot on that trial.
def saveResults(results, trialResults, experimentId):
    dataDirectory.mkdir(exist_ok=True)
    for fileName, rows in ((f"experiment{experimentId}Results.csv", results),
                           (f"experiment{experimentId}Trials.csv", trialResults)):
        if not rows:
            continue
        with open(dataDirectory / fileName, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

# Run the experiments and save the results.
if __name__ == "__main__":
    start = time.time()
    results, trialResults, experimentId = runExperiments(dimension, numberOfTrials)
    saveResults(results, trialResults, experimentId)

    for result in results:
        print(f"{result['detectorType']} {result['bot']} | {result['movementMode']} | "
              f"{result['settingName']}={result['setting']} | "
              f"Success: {result['successes']}/{numberOfTrials} | "
              f"Average cost: {result['averageCost']}")
    print(f"Total simulations: {len(trialResults)} | Runtime: {time.time()-start:.1f}s")
