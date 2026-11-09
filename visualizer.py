import tkinter as tk
from unittest import result
from simulation import startRecording, saveRecording, runTimeStep


# Draw the ship and its knowledge.
def drawShip(canvas, ship, bot, botPosition, lostBotPosition, cellSize, lastDetectorPosition=None):

    # Erase the previous frame so moving bots do not leave colored cells
    canvas.delete("all")

    path = set(getattr(bot, "path", None) or [])
    possible = getattr(bot, "possibleLocations", None)
    probabilities = getattr(bot, "probabilities", None)
    maxProbability = max(probabilities.values(), default=0) if probabilities is not None else 0

    # Draw the entire grid using the saved map
    for row, cells in enumerate(ship):
        for col, openCell in enumerate(cells):
            position = (row, col)
            color = "gray" if not openCell else "lightblue"

            if openCell:
                # Type A: show all cells that could contain the LostBot.
                if possible is not None and position in possible:
                    color = "#91D4B5"

                # Type B: color cells in a gradient by their estimated probability.
                if probabilities is not None and maxProbability:
                    intensity = (probabilities.get(position, 0) / maxProbability) ** 0.5
                    color = f"#{int(210+25*intensity):02x}{int(231-140*intensity):02x}{int(239-170*intensity):02x}"

                #Draw both bots and the path on topmost layer of the grid.
                if position in path:
                    color = "yellow"
                if position == lostBotPosition:
                    color = "limegreen"
                #blue means the LocatorBot is on the LostBot cell, but it hasnt detected it yet.
                if position == botPosition:
                    color = "mediumpurple" if position == lostBotPosition else "blue"

            # Convert the grid row/column into pixel coordinates for Tkinter
            x, y = col * cellSize, row * cellSize
            canvas.create_rectangle(x, y, x + cellSize, y + cellSize, fill=color, outline="black")

    # For Type A, outline the square covered by the last detection.
    if lastDetectorPosition is not None and hasattr(bot, "k"):
        row, col = lastDetectorPosition
        k = bot.k
        canvas.create_rectangle(
            max(0, col-k)*cellSize, max(0, row-k)*cellSize,
            min(len(ship[0]), col+k+1)*cellSize, min(len(ship), row+k+1)*cellSize,
            outline="orange", width=2, dash=(4, 2)
        )


# Run the simulation via button clicks, and show all needed info
def visualizeShip(ship, bot, botPosition, lostBotPosition, movementCost=1.0, detectorCost=0.5):
    # Create a new Tkinter window for this one live simulation.
    window = tk.Tk()
    botName = type(bot).__name__
    window.title("LocatorBot Visualizer: " + botName)

    # Scale cells based on ship size and screen height
    cellSize = max(1, min(750, int(window.winfo_screenheight() * 0.7)) // len(ship))
    canvas = tk.Canvas(window, width=len(ship[0])*cellSize, height=len(ship)*cellSize)
    canvas.pack()

    # Display which strategy is running and its detector setting.
    setting = f"k = {bot.k}" if hasattr(bot, "k") else f"alpha = {bot.alpha}"
    tk.Label(window, text=f"Bot: {botName} | {setting}").pack()
    actionLabel = tk.Label(window)
    actionLabel.pack()
    statusLabel = tk.Label(window)
    statusLabel.pack()

    # Start saving the simulation events to a recording file for later replay.
    startRecording(ship, bot, botPosition, lostBotPosition, movementCost, detectorCost)
    saveRecording(bot)

    state = {"position": botPosition, "lastDetection": None}

    # Refresh the labels and grid using the latest saved simulation event.
    def redraw():
        result = bot._runRecording["result"]
        latest = bot._runRecording["events"][-1]
        actionLabel.config(text=f"Actions: {result['actionCount']} | Moves: {result['moveActions']} | "
                                f"Detections: {result['detectorActions']} | Cost: {result['totalCost']:.2f}")
        statusLabel.config(text=f"{result['status']} | Last action: {latest['action']} "
                                f"{latest.get('detectorResult', '')}")
        drawShip(canvas, ship, bot, state["position"], lostBotPosition, cellSize, state["lastDetection"])

    # Run a single action.
    def nextStep():
        # If the bot has already finished, do not run another step.
        if bot._runRecording["result"]["status"] != "RUNNING":
            return

        state["position"], action, status = runTimeStep(
            ship, bot, state["position"], lostBotPosition, movementCost, detectorCost
        )

        if action == "DETECT":
            state["lastDetection"] = state["position"]

        if status != "CONTINUE":
            nextButton.config(state="disabled")
        redraw()

    nextButton = tk.Button(window, text="Next Step", command=nextStep)
    nextButton.pack(pady=5)
    tk.Label(window, text="Blue: LocatorBot | Yellow: path | Green: possible cells | "
                          "Lime: LostBot | Orange: detector range").pack()

    redraw()
    window.mainloop()
