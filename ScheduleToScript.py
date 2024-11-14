import json
import sys
from pathlib import Path

from typing import Literal


events_json_log_path = Path("simulation_events.json")
script_output_path = Path("GeneratedScript.py")

if len(sys.argv) == 1:
    pass
elif len(sys.argv) == 2:
    events_json_log_path = Path(sys.argv[1])
elif len(sys.argv) == 3:
    events_json_log_path = Path(sys.argv[1])
    script_output_path = Path(sys.argv[2])
else:
    print(
        "usage: python ScheduleToScript.py [EVENTS_JSON_PATH] [GENERATED_SCRIPT_PATH]"
    )
    exit(1)


events = json.loads(events_json_log_path.read_text())
generated_lines = []


PlateTypes = (
    Literal["patient"] | Literal["staff"] | Literal["equipment"] | Literal["surface"]
)


def get_well_plate(category: str) -> PlateTypes:
    if category == "patient":
        return "patient"
    elif category == "doctor":
        return "staff"
    elif category == "nurse":
        return "staff"
    elif category == "equipment":
        return "equipment"
    elif category == "surface":
        return "surface"
    raise ValueError(f"unexpected category {category}")


for event in events:
    if "seconds_after_start" in event:
        generated_lines.append(
            f"""    simulation.sleep_seconds_after_start({event['seconds_after_start']})"""
        )

    if event["type"] == "comment":
        generated_lines.append(f"""    simulation.comment("{event['comment']}")""")
    elif event["type"] == "interaction":
        # TODO: Count tips used
        interaction = event["interaction_info"]
        source_well_plate = get_well_plate(interaction["source_category"])
        target_well_plate = get_well_plate(interaction["target_category"])
        source_well_number = interaction["source_well_number"]
        target_well_number = interaction["target_well_number"]
        transfer_ul = interaction["bacteria_transfer_ul"]
        generated_lines.append(
            f"""    simulation.transfer("{source_well_plate}", "{target_well_plate}", {source_well_number}, {target_well_number}, {transfer_ul})"""
        )
    elif event["type"] == "clean_well":
        clean_info = event["clean_target_info"]
        well_plate = get_well_plate(clean_info["well_category"])
        well_number = clean_info["well_number"]
        clean_ul = clean_info["clean_ul"]
        generated_lines.append(
            f"""    simulation.clean("{well_plate}", {well_number}, {clean_ul})"""
        )
    elif event["type"] == "wait_for_continue":
        generated_lines.append(f"    simulation.wait_for_continue({event['resume_at']})")
    elif event["type"] == "reset_tiprack":
        generated_lines.append("    simulation.reset_tip_racks()")
    else:
        raise ValueError(f"unexpected event type {event['type']}")

template = Path("ScheduleToScriptTemplate.py").read_text()

script_output_path.write_text(
    """
################################################################
### THIS SCRIPT WAS MACHINE GENERATED. DO NOT EDIT IT BY HAND. #
################################################################

"""
    + template
    + "\n"
    + "\n".join(generated_lines)
)
