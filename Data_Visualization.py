import json
from collections import defaultdict
import matplotlib.pyplot as plt
import numpy as np


# Sample JSON log data (replace with your actual log data)
log_data = {
    "commands": {
        "data": [
            {"commandType": "dispense", "params": {"labwareId": "c290a258-a454-4912-aeea-30bb8fde29e5", "wellName": "A1", "volume": 150}},
            {"commandType": "dispense", "params": {"labwareId": "c290a258-a454-4912-aeea-30bb8fde29e5", "wellName": "B2", "volume": 20}},
            {"commandType": "dispense", "params": {"labwareId": "c290a258-a454-4912-aeea-30bb8fde29e5", "wellName": "B2", "volume": 15}},
            # Add more log entries as needed
        ]
    }
}

# Initialize a dictionary to store well volumes
well_volumes = defaultdict(int)

# Parse the log data to update well volumes
for command in log_data["commands"]["data"]:
    if command["commandType"] == "dispense":
        well_name = command["params"]["wellName"]
        volume = command["params"]["volume"]
        well_volumes[well_name] += volume

print(well_volumes)  # Check the parsed data

# Define well plate dimensions
rows = 'ABCDEFGH'
cols = range(1, 13)

# Create a 2D array to store well volumes
heatmap_data = np.zeros((len(rows), len(cols)))

# Map the well names to the 2D array
for well, volume in well_volumes.items():
    row = rows.index(well[0])
    col = int(well[1:]) - 1
    heatmap_data[row, col] = volume

# Plot the heatmap
plt.figure(figsize=(10, 8))
plt.imshow(heatmap_data, cmap='viridis', interpolation='nearest')
plt.colorbar(label='Volume (µL)')
plt.xticks(ticks=np.arange(len(cols)), labels=cols)
plt.yticks(ticks=np.arange(len(rows)), labels=rows)
plt.xlabel('Column')
plt.ylabel('Row')
plt.title('Well Plate Volume Distribution')
plt.show()