import json
import tkinter as tk
from pathlib import Path
from types import SimpleNamespace
from visualizer import drawShip
from simulation import captureKnowledge
from bots.typeABot import TypeABot
from bots.typeBBot import TypeBBot


# Choose a JSON file and, for experiments, a run ID from the Trials CSV.
# An empty filename opens the newest recording. Run ID 0 selects the last run.
replayFilePath = ""
selectedRunId = 0
runsDirectory = Path(__file__).resolve().parent / "runs"


# Locate the recording to replay.
def findReplay():
    if replayFilePath:
        path = Path(replayFilePath)
        return path if path.is_absolute() else runsDirectory.parent / path

    if selectedRunId:
        raise ValueError("Set replayFilePath to an experiment JSON to select a run number.")

    files = list(runsDirectory.glob("*.json"))
    if not files:
        raise FileNotFoundError("No JSON recordings found in " + str(runsDirectory))
    
    return max(files, key=lambda path: path.stat().st_mtime)


# Read either an single-run JSON or a new file containing all trials.
def loadRecording(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if "trials" not in data:
        return data

    # Search backward so run ID 0 chooses the last run in the experiment.
    for trial in reversed(data["trials"]):
        for run in reversed(trial["runs"]):
            if selectedRunId and str(run["runId"]) != str(selectedRunId):
                continue

            recording = dict(run)
            recording["ship"] = trial["ship"]
            recording["botStart"] = trial["botStart"]
            recording["lostBotPosition"] = trial["lostBotPosition"]
            recording["trial"] = trial["trial"]
            return recording

    raise ValueError("Run ID was not found inside " + path.name)


# Reconstruct the knowledge shown after each detector reading.
def expandCompactEvents(recording):
    settings = recording["detectorSettings"]
    # Different bot types have different knowledge representations, so create a temporary bot to update its knowledge.
    if "k" in settings:
        knowledgeBot = TypeABot(recording["ship"], settings["k"])
    else:
        knowledgeBot = TypeBBot(recording["ship"], settings["alpha"])

    position = tuple(recording["botStart"])
    moves = detections = 0

    # Begin with the knowledge the bot had before its first action.
    events = [{
        "action": "START", "position": list(position), "step": 0,
        "moveActions": 0, "detectorActions": 0, "totalCost": 0.0,
        "status": "RUNNING", "knowledge": captureKnowledge(knowledgeBot)
    }]

     # Convert each recorded action into a frame for the replay.

    for index, entry in enumerate(recording["actions"], 1):
        code, row, col = entry[:3]
        position = (row, col)
        action = {"M": "MOVE", "D": "DETECT", "X": "NONE"}[code]

        moves += action == "MOVE"
        detections += action == "DETECT"

        event = {
            "step": index, "action": action, "position": [row, col],
            "moveActions": moves, "detectorActions": detections,
            "totalCost": moves * recording["movementCost"]
                         + detections * recording["detectorCost"],
            "status": "CONTINUE"
        }

        if action == "DETECT":
            detectorResult = entry[3]
            event["detectorResult"] = detectorResult

            # Recreate the knowledge the bot would have after this detection.
            if detectorResult != "FOUND":
                knowledgeBot.updateKnowledge(position, detectorResult)
            event["knowledge"] = captureKnowledge(knowledgeBot)
            if detectorResult == "FOUND":
                event["status"] = "SUCCESS"
        elif action == "NONE":
            event["status"] = "NO_VALID_PATH"

        events.append(event)

    # If the bot reached the action limit, add a final event to indicate that.
    if recording["result"]["status"] == "ACTION_LIMIT":
        events.append({
            **events[-1],
            "action": "ACTION_LIMIT",
            "status": "ACTION_LIMIT"
        })

    return events


# Reconstruct each frame using recorded actions.
def replaySimulation():
    path = findReplay()
    recording = loadRecording(path)

    #Expand the compact events into a full list of events for the replay.
    if "actions" in recording:
        recording["events"] = expandCompactEvents(recording)

    ship = recording["ship"]
    events = recording["events"]
    lostBotPosition = tuple(recording["lostBotPosition"])
    settings = recording.get("detectorSettings", {})

    # Create a window and canvas to display the ship, bot, and LostBot, similar to the visualizer.
    window = tk.Tk()
    window.title(f"Replay: {path.name} | Run {recording['runId']}")


    cellSize = max(1, min(750, int(window.winfo_screenheight() * 0.7)) // len(ship))
    canvas = tk.Canvas(window, width=len(ship[0]) * cellSize,
                       height=len(ship) * cellSize)
    canvas.pack()

    step = tk.IntVar(value=0)
    infoLabel = tk.Label(window, justify="left")
    infoLabel.pack()

    # Keep the last knowledge and detector location with each frame, allowing for a slider to move backward and forward through the replay.
    frames = []
    knowledge = None
    lastDetector = None

    for event in events:
        if event.get("knowledge") is not None:
            knowledge = event["knowledge"]

        if event["action"] == "DETECT":
            lastDetector = tuple(event["position"])

        frames.append((event, knowledge, lastDetector))

    # Draw the ship, bot, and LostBot for the current step in the replay.
    def draw():
        index = step.get()
        event, knowledge, lastDetector = frames[index]
        botPosition = tuple(event["position"])

        # Detailed recordings contain the planned BFS path. Compact runs show consecutive recorded moves until the next detector action.
        if "actions" in recording:
            plannedPath = []

            for nextIndex in range(index + 1, len(events)):
                future = events[nextIndex]

                if future["action"] != "MOVE":
                    break

                plannedPath.append(tuple(future["position"]))

        else:
            plannedPath = [
                tuple(p) for p in event.get("plannedPath") or []
            ]

        # Create a temporary bot to display its knowledge
        bot = SimpleNamespace(path=plannedPath)
        if "k" in settings:
            bot.k = settings["k"]
        if knowledge and knowledge["type"] == "possibleLocations":
            bot.possibleLocations = {tuple(p) for p in knowledge["cells"]}
        if knowledge and knowledge["type"] == "probabilities":
            bot.probabilities = {(r, c): p for r, c, p in knowledge["cells"]}

        drawShip(canvas, ship, bot, botPosition, lostBotPosition, cellSize, lastDetector)

        # Display the number of possible locations and the three most likely cells for Type B.
        knowledgeCount = len(knowledge["cells"]) if knowledge else 0
        topCells = ""

        if knowledge and knowledge["type"] == "probabilities":
            top = sorted(knowledge["cells"], key=lambda cell: cell[2], reverse=True)[:3]
            topCells = "\nTop cells: " + ", ".join(f"({r},{c}) {p:.1%}" for r, c, p in top)

        # Show the action, current position, detector result, and cost in the replay window
        infoLabel.config(text=(
            f"Step {index}/{len(events)-1} | {recording['botType']} | {settings}\n"
            f"Action: {event['action']} {event.get('detectorResult', '')} | Status: {event['status']}\n"
            f"Moves: {event.get('moveActions', 0)} | Detections: {event.get('detectorActions', 0)} | "
            f"Cost: {event.get('totalCost', 0):.2f} | Known cells: {knowledgeCount}\n"
            f"Position: {event['position']} | Target: {event.get('targetPosition', plannedPath[-1] if plannedPath else '-')}{topCells}"
        ))

    #Prevent dragging the bar to either extreme from closing the window and allow the user to continue replaying.
    def changeStep(amount):
        step.set(max(0, min(len(events) - 1, step.get() + amount)))
        draw()

    controls = tk.Frame(window)
    controls.pack()
    
    tk.Button(
        controls, text="Previous",
        command=lambda: changeStep(-1)
    ).pack(side="left", padx=5)

    tk.Button(
        controls, text="Next",
        command=lambda: changeStep(1)
    ).pack(side="left", padx=5)

    tk.Scale(
        window,
        from_=0,
        to=len(events)-1,
        variable=step,
        orient="horizontal",
        command=lambda value: draw()
    ).pack(fill="x")

    draw()
    window.mainloop()

if __name__ == "__main__":
    replaySimulation()
