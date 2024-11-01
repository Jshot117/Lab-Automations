import json
from pathlib import Path
import matplotlib.pyplot as plt


events = json.loads(Path("simulation_events.json").read_text())

interactions = [e for e in events if e["type"] == "interaction"]
interaction_times_per_category: dict[str, list[float]] = {
    "doctor": [],
    "nurse": [],
    "patient": [],
    "equipment": [],
    "surface": [],
}
for e in interactions:
    t = e["seconds_after_start"]
    info = e["interaction_info"]
    interaction_times_per_category[info["source_category"]].append(t)
    interaction_times_per_category[info["target_category"]].append(t)

for category, interaction_times in interaction_times_per_category.items():
    interaction_hours = [t / 60 / 60 for t in interaction_times]
    plt.plot(interaction_hours, range(1, len(interaction_hours) + 1), label=category)

plt.title("Cumulative Interactions per Category Over Time")
plt.ylabel("Cumulative Interactions")
plt.xlabel("Hours")
plt.legend(loc="upper left")
plt.show()
