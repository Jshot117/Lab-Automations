import json
from datetime import timedelta
from pathlib import Path
import random

# Constants
EVENTS_PATH = Path("simulation_events.json")

SHIFTS = ["morning", "afternoon", "night"]
SHIFT_DURATION = timedelta(hours=7)

DOCTOR_WELLS_PER_SHIFT = 6
NURSE_WELLS_PER_SHIFT = 12

TOTAL_P20_TIPS = 96 * 5  # Tips per rack * racks
TOTAL_P300_TIPS = 96 * 1  # Tips per rack * racks
PATIENT_WELL_COUNT = 20
DOCTOR_WELL_COUNT = DOCTOR_WELLS_PER_SHIFT * len(SHIFTS)
NURSE_WELL_COUNT = NURSE_WELLS_PER_SHIFT * len(SHIFTS)
EQUIPMENT_WELL_COUNT = 20
SURFACE_WELL_COUNT = 60

END_OF_SHIFT_CLEAN_COUNT = DOCTOR_WELLS_PER_SHIFT + NURSE_WELLS_PER_SHIFT
END_OF_DAY_CLEAN_COUNT = EQUIPMENT_WELL_COUNT + SURFACE_WELL_COUNT
TOTAL_CLEAN_COUNT = END_OF_SHIFT_CLEAN_COUNT * len(SHIFTS) + END_OF_DAY_CLEAN_COUNT

MAX_INTERACTION_COUNT = TOTAL_P20_TIPS
END_OF_SHIFT_CLEAN_COUNT = DOCTOR_WELLS_PER_SHIFT + NURSE_WELLS_PER_SHIFT
END_OF_DAY_MAX_CLEAN_COUNT = TOTAL_P300_TIPS - END_OF_SHIFT_CLEAN_COUNT * 3
INTERACTIONS_PER_SHIFT = TOTAL_P20_TIPS // 3

# Adjustable variables
INITIAL_BACTERIA_UL = 100
INITIAL_MEDIA_UL = 50
BACTERIA_TRANSFER_UL = 10
CLEANING_MEDIA_BASE_UL = 50
# CLEANING_MEDIA_GAUSS_MU = 0.0
# CLEANING_MEDIA_GAUSS_SIGMA = 1.0
BACTERIA_TRANSFER_SETTLE_WAIT_SECS = 30

INTERACTION_PROBABILITIES = {
    "nurse_patient": 0.50,
    "nurse_surface": 0.10,
    "nurse_equipment": 0.20,
    "nurse_doctor": 0.20,
    "doctor_patient": 0.30,
    "doctor_equipment": 0.15,
    "doctor_surface": 0.05,
    "doctor_nurse": 0.35,
    "patient_equipment": 0.05,
    "patient_surface": 0.10,
    "patient_nurse": 0.25,
    "patient_doctor": 0.60,
    "equipment_surface": 0.05,
    "equipment_nurse": 0.10,
    "equipment_doctor": 0.15,
    "equipment_patient": 0.20,
    "surface_nurse": 0.10,
    "surface_doctor": 0.15,
    "surface_patient": 0.20,
    "surface_equipment": 0.05,
}

CLEANING_PROBABILITIES = {
    "nurse": 0.25,
    "doctor": 0.30,
    "patient": 0.10,
    "equipment": 0.15,
    "surface": 0.05,
}


# This does not correspond to the positions in well plates. This gives 0 indexed
# exclusive ranges for which well plates can be used during a shift. For example,
# all the doctor well plates are numbered [0, 18], but for the morning shift, only
# the well plates for doctors [0, 5] can be used. For equipment, all 20 equipment
# well plates [0, 19] can be used at any point.The well plate number has to be
# translated into a well plate position when generating the Opentron steps code.
WELLS_NUMBERS_RANGE_OF_TYPE_PER_SHIFT = {
    "patient": {shift: (0, PATIENT_WELL_COUNT) for shift in SHIFTS},
    "doctor": {
        shift: (
            DOCTOR_WELLS_PER_SHIFT * shift_number,
            DOCTOR_WELLS_PER_SHIFT * (shift_number + 1),
        )
        for shift_number, shift in enumerate(SHIFTS)
    },
    "nurse": {
        shift: (
            NURSE_WELLS_PER_SHIFT * shift_number,
            NURSE_WELLS_PER_SHIFT * (shift_number + 1),
        )
        for shift_number, shift in enumerate(SHIFTS)
    },
    "equipment": {shift: (0, EQUIPMENT_WELL_COUNT) for shift in SHIFTS},
    "surface": {shift: (0, SURFACE_WELL_COUNT) for shift in SHIFTS},
}


if __name__ == "__main__":
    p20_tips_used = 0
    p300_tips_used = 0

    time_since_start = timedelta(seconds=0)

    simulation_events = []

    def add_interaction_event(
        time_since_start: timedelta,
        source_category,
        source_well_number,
        target_category,
        target_well_number,
        bacteria_transfer_ul,
        shift,
    ):
        simulation_events.append(
            {
                "type": "interaction",
                "seconds_after_start": time_since_start.total_seconds(),
                "interaction_info": {
                    "source_category": source_category,
                    "source_well_number": source_well_number,
                    "target_category": target_category,
                    "target_well_number": target_well_number,
                    "bacteria_transfer_ul": bacteria_transfer_ul,
                    "shift": shift,
                },
            }
        )

    def add_comment_event(time_since_start: timedelta, comment: str):
        simulation_events.append(
            {
                "type": "comment",
                "seconds_after_start": time_since_start.total_seconds(),
                "comment": comment,
            }
        )

    for shift_number, shift in enumerate(SHIFTS):
        shift_start_time = SHIFT_DURATION * shift_number
        time_between_interactions = SHIFT_DURATION / INTERACTIONS_PER_SHIFT

        # Create lists of interactions and their corresponding probabilities
        interactions = list(INTERACTION_PROBABILITIES.keys())
        probabilities = list(INTERACTION_PROBABILITIES.values())

        # Use random.choices to select interactions based on their probabilities
        selected_interactions = random.choices(
            interactions, weights=probabilities, k=INTERACTIONS_PER_SHIFT
        )

        for interaction_number, interaction in enumerate(selected_interactions):
            # TODO: Set aside time for cleaning
            interaction_time = (
                shift_start_time + time_between_interactions * interaction_number
            )
            source_category, target_category = interaction.split("_")
            add_comment_event(interaction_time, f"Interaction: {interaction}")
            shift_source_range = WELLS_NUMBERS_RANGE_OF_TYPE_PER_SHIFT[source_category][
                shift
            ]
            shift_target_range = WELLS_NUMBERS_RANGE_OF_TYPE_PER_SHIFT[target_category][
                shift
            ]
            source_well_number = random.randrange(
                shift_source_range[0], shift_source_range[1]
            )
            target_well_number = random.randrange(
                shift_target_range[0], shift_target_range[1]
            )
            add_interaction_event(
                interaction_time,
                source_category,
                source_well_number,
                target_category,
                target_well_number,
                BACTERIA_TRANSFER_UL,  # TODO: Add random spread
                shift,
            )
            p20_tips_used += 1

            # TODO: Add end of shift cleaning

        # TODO: Add end of day cleaning

    assert p20_tips_used <= TOTAL_P20_TIPS
    assert all(
        (
            simulation_events[i - 1]["seconds_after_start"]
            <= simulation_events[i]["seconds_after_start"]
            for i in range(1, len(simulation_events))
        )
    )
    EVENTS_PATH.write_text(json.dumps(simulation_events, indent="    "))
