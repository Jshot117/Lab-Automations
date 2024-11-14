import json
from pathlib import Path
import matplotlib.pyplot as plt


events = json.loads(Path("simulation_events.json").read_text())

interactions = [e for e in events if e["type"] == "interaction"]
interactions_ul = [i["interaction_info"]["bacteria_transfer_ul"] for i in interactions]

plt.title("Interactions histogram")
plt.hist(interactions_ul, bins=20)
plt.show()
