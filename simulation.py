import json
import random
from pathlib import Path


# Save all standalone runs in the runs folder. 
runsDirectory = Path(__file__).resolve().parent / "runs"


# Find a filename that will not overwrite an existing standalone run.
def nextStandaloneRunId():
    existingIds = []

    for path in runsDirectory.glob("run*.json"):
        number = path.stem.removeprefix("run")

        if number.isdigit():
            existingIds.append(int(number))

    return max(existingIds, default=0) + 1


# Randomly choose different open cells for the two bots.
def placeEntities(ship):
    openCells = [
        (r, c)
        for r, row in enumerate(ship)
        for c, cell in enumerate(row)
        if cell
    ]

    return random.sample(openCells, 2)


# Convert the bot's knowledge into lists that JSON can store.
def captureKnowledge(bot):
    if hasattr(bot, "possibleLocations"):
        return {
            "type": "possibleLocations",
            "cells": [list(p) for p in sorted(bot.possibleLocations)]
        }
    if hasattr(bot, "probabilities"):
        return {
            "type": "probabilities",
            "cells": [
                [*p, value]
                for p, value in sorted(bot.probabilities.items())
            ]
        }
    return None


# Save the bot's BFS route for replay.
def capturePath(bot):
    path = getattr(bot, "path", None)
    return [list(p) for p in path] if path is not None else None


# Set up the recording before the first action. A standalone run saves # its own ship and detailed events. 
# An experiment stores the ship once per trial and gives each bot a short action history.
def startRecording(ship, bot, botPosition, lostBotPosition, movementCost=1.0,
                   detectorCost=0.5, maxActions=None, compact=False,
                   recordingPath=None, runId=None):

    # experiments.py provides numbered IDs. A standalone run needs to find its own unused number.
    if runId is None:
        runsDirectory.mkdir(exist_ok=True)
        runId = nextStandaloneRunId()

    #Record only the setting that the selected bot possesses.
    settings = {}
    if hasattr(bot, "k"):
        settings["k"] = bot.k

    if hasattr(bot, "alpha"):
        settings["alpha"] = bot.alpha

    # experiments.py reads these attributes when writing trialResults.csv.
    bot.lastRecordingId = runId
    bot.lastRecordingPath = str(
        recordingPath or runsDirectory / f"run{runId}.json"
    )

    # These counters are updated after every action.
    result = {
        "success": False,
        "status": "RUNNING",
        "totalCost": 0.0,
        "moveActions": 0,
        "detectorActions": 0,
        "actionCount": 0,
        "lastPosition": list(botPosition)
    }

    # Compact recordings store only the action history.
    # My early JSON format was incredibly large so i made a compact version to reduce the size of the file
    # However i kept it an option because the larger format is useful for debugging and replaying a standalone run
    if compact:
        bot._runRecording = {
            "runId": runId,
            "botType": type(bot).__name__,
            "detectorSettings": settings,
            "movementCost": movementCost,
            "detectorCost": detectorCost,
            "actions": [],
            "result": result
        }

    else:
        #Standalone runs store the ship, starting positions, and detailed events.
        bot._runRecording = {
            "runId": runId,
            "botType": type(bot).__name__,
            "detectorSettings": settings,
            "dimension": len(ship),
            "ship": ship,
            "botStart": list(botPosition),
            "lostBotPosition": list(lostBotPosition),
            "movementCost": movementCost,
            "detectorCost": detectorCost,
            "maxActions": maxActions,
            "events": [{
                "step": 0,
                "action": "START",
                "position": list(botPosition),
                "fromPosition": list(botPosition),
                "status": "RUNNING",
                "moveActions": 0,
                "detectorActions": 0,
                "totalCost": 0.0,
                "plannedPath": capturePath(bot),
                "knowledge": captureKnowledge(bot)
            }],
            "result": result
        }

    return bot._runRecording


# Write a standalone recording to disk.
def saveRecording(bot):
    runsDirectory.mkdir(exist_ok=True)
    with open(bot.lastRecordingPath, "w", encoding="utf-8") as file:
        json.dump(bot._runRecording, file, indent=2)


# Perform one bot action and update its internal recording.
def performStep(ship, bot, botPosition, lostBotPosition):
    recording = bot._runRecording
    oldPosition = botPosition

    decision = bot.chooseAction(botPosition)
    action, destination = decision if decision is not None else (None, None)
    detectorResult = None
    status = "CONTINUE"

    if action == "DETECT":
        # Finding LostBot requires detecting on its cell.
        if botPosition == lostBotPosition:
            detectorResult = "FOUND"
            status = "SUCCESS"

        else:
            detectorResult = bot.runDetector(botPosition, lostBotPosition)
            bot.updateKnowledge(botPosition, detectorResult)

    # The bot moves to the destination, pylance complains if i don't check for None even though the bot should never return a MOVE with no destination.
    elif action == "MOVE" and destination is not None:
        botPosition = destination

    else:
        status = "NO_VALID_PATH"

    # Update the counters used to calculate discovery cost and report
    result = recording["result"]
    result["actionCount"] += 1

    # Update the action counters based on the action taken.
    if action == "MOVE":
        result["moveActions"] += 1
    elif action == "DETECT":
        result["detectorActions"] += 1

    # Update the total cost based on the number of moves and detections.
    result["totalCost"] = (
        result["moveActions"] * recording["movementCost"]
        + result["detectorActions"] * recording["detectorCost"]
    )

    result["lastPosition"] = list(botPosition)
    result["status"] = "RUNNING" if status == "CONTINUE" else status
    result["success"] = status == "SUCCESS"


    if "actions" in recording:
        # Compact events record just M (move), D (detect), or X (no path).
        # reconstructs the knowledge from these entries when requested.
        if action == "MOVE":
            recording["actions"].append(["M", *botPosition])
        elif action == "DETECT":
            recording["actions"].append(["D", *botPosition, detectorResult])
        else:
            recording["actions"].append(["X", *botPosition])
        return botPosition, action, status

    # Standalone recordings preserve the route and running statistics
    event = {
        "step": result["actionCount"],
        "action": action or "NONE",
        "fromPosition": list(oldPosition),
        "position": list(botPosition),
        "status": status,
        "moveActions": result["moveActions"],
        "detectorActions": result["detectorActions"],
        "totalCost": result["totalCost"],
        "plannedPath": capturePath(bot)
    }

    #save the knowledge after a detection
    if action == "DETECT":
        event["detectorResult"] = detectorResult
        event["knowledge"] = captureKnowledge(bot)
    if action == "MOVE":
        event["targetPosition"] = (
            event["plannedPath"][-1]
            if event["plannedPath"]
            else list(botPosition)
        )

    recording["events"].append(event)

    return botPosition, action, status


# The visualizer calls this on each click and saves the updated replay.
def runTimeStep(ship, bot, botPosition, lostBotPosition,
                movementCost=1.0, detectorCost=0.5):

    botPosition, action, status = performStep(
        ship, bot, botPosition, lostBotPosition
    )

    saveRecording(bot)

    return botPosition, action, status


# Execute a complete run
def runSimulation(ship, bot, botPosition, lostBotPosition, movementCost=1.0,
                  detectorCost=0.5, maxActions=None, compact=False,
                  recordingPath=None, runId=None):

    recording = startRecording(
        ship, bot, botPosition, lostBotPosition,
        movementCost, detectorCost, maxActions,
        compact, recordingPath, runId
    )

    try:
        while True:
            result = recording["result"]

            #if unusually long search happens, end the simulation and count it as a failure
            if maxActions is not None and result["actionCount"] >= maxActions:
                result["status"] = "ACTION_LIMIT"

                # Save the last action in the standalone recording
                if not compact:
                    recording["events"].append({
                        "step": result["actionCount"],
                        "action": "ACTION_LIMIT",
                        "position": list(botPosition),
                        "status": "ACTION_LIMIT",
                        "moveActions": result["moveActions"],
                        "detectorActions": result["detectorActions"],
                        "totalCost": result["totalCost"],
                        "plannedPath": capturePath(bot)
                    })

                break

            botPosition, action, status = performStep(
                ship, bot, botPosition, lostBotPosition
            )

            if status != "CONTINUE":
                break

    finally:
        # Save the recording after the run.
        if not compact:
            saveRecording(bot)

    # Preserve the five values expected by main.py and experiments.py.
    result = recording["result"]

    return (
        result["success"],
        result["totalCost"],
        result["status"],
        result["moveActions"],
        result["detectorActions"]
    )