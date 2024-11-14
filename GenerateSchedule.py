import json
from datetime import timedelta
from pathlib import Path
import random

# Constants
EVENTS_PATH = Path("simulation_events.json")

SHIFTS = ["morning", "afternoon", "night"]
SHIFT_DURATION = timedelta(hours=6, minutes=50)
END_OF_SHIFT_CLEAN_DURATION = timedelta(minutes=10)
END_OF_DAY_CLEAN_DURATION = timedelta(minutes=10)
DAY_DURATION = timedelta(days=1)
MANUAL_SERVICE_DURATION = (
    DAY_DURATION
    - END_OF_DAY_CLEAN_DURATION
    - (len(SHIFTS) * (SHIFT_DURATION + END_OF_SHIFT_CLEAN_DURATION))
)
DAYS = 1

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

# 2 pipette tips are needed to clean a well
MAX_INTERACTION_COUNT = TOTAL_P20_TIPS - 2 * TOTAL_CLEAN_COUNT
END_OF_SHIFT_CLEAN_COUNT = DOCTOR_WELLS_PER_SHIFT + NURSE_WELLS_PER_SHIFT
END_OF_DAY_MAX_CLEAN_COUNT = TOTAL_P300_TIPS - END_OF_SHIFT_CLEAN_COUNT * 3
INTERACTIONS_PER_SHIFT = MAX_INTERACTION_COUNT // 3

# Adjustable variables
_INITIAL_BACTERIA_UL = 100  # TODO: Pass to generated script
_INITIAL_MEDIA_UL = 50  # TODO: Pass to generated script
# TODO: Use an interaction matrix for different classes
BACTERIA_TRANSFER_BASE_UL = 5
BACTERIA_TRANSFER_GAUSS_MUL = 5
CLEANING_AMOUNT_BASE_UL = 35
CLEANING_AMOUNT_GAUSS_MUL = 10
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


# This should correspond to positions in well plates
WELLS_NUMBERS_RANGE_OF_TYPE_PER_SHIFT = {
    "patient": {shift: (0, PATIENT_WELL_COUNT) for shift in SHIFTS},
    "doctor": {
        shift: (
            (DOCTOR_WELLS_PER_SHIFT + NURSE_WELLS_PER_SHIFT) * shift_number,
            (DOCTOR_WELLS_PER_SHIFT + NURSE_WELLS_PER_SHIFT) * shift_number
            + DOCTOR_WELLS_PER_SHIFT,
        )
        for shift_number, shift in enumerate(SHIFTS)
    },
    "nurse": {
        shift: (
            (DOCTOR_WELLS_PER_SHIFT + NURSE_WELLS_PER_SHIFT) * shift_number
            + DOCTOR_WELLS_PER_SHIFT,
            (DOCTOR_WELLS_PER_SHIFT + NURSE_WELLS_PER_SHIFT) * shift_number
            + DOCTOR_WELLS_PER_SHIFT
            + NURSE_WELLS_PER_SHIFT,
        )
        for shift_number, shift in enumerate(SHIFTS)
    },
    "equipment": {shift: (0, EQUIPMENT_WELL_COUNT) for shift in SHIFTS},
    "surface": {shift: (0, SURFACE_WELL_COUNT) for shift in SHIFTS},
}


def clamped_gaussian(mu: float, sigma: float, minval: float, maxval: float) -> float:
    val = random.gauss(mu, sigma)
    val = min(val, maxval)
    val = max(val, minval)
    return val


def random_transfer_ul() -> float:
    gauss = clamped_gaussian(0, 0.4, -1, 1)
    return BACTERIA_TRANSFER_BASE_UL + gauss * BACTERIA_TRANSFER_GAUSS_MUL


def random_clean_ul() -> float:
    gauss = clamped_gaussian(0, 0.4, -1, 1)
    return CLEANING_AMOUNT_BASE_UL + gauss * CLEANING_AMOUNT_GAUSS_MUL


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

    def add_clean_well_event(
        well_category: str,
        well_number: int,
        clean_ul: int | float,
    ):
        simulation_events.append(
            {
                "type": "clean_well",
                "clean_target_info": {
                    "well_category": well_category,
                    "well_number": well_number,
                    "clean_ul": clean_ul,
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

    def add_wait_for_continue_event(time_since_start: timedelta):
        simulation_events.append(
            {
                "type": "wait_for_continue",
                "resume_at": time_since_start.total_seconds(),
            }
        )

    def add_reset_tiprack_event(time_since_start: timedelta):
        simulation_events.append(
            {
                "type": "reset_tiprack",
                "seconds_after_start": time_since_start.total_seconds(),
            }
        )

    for day in range(DAYS):
        if day != 0:
            maintenance_end_time = DAY_DURATION * day
            add_wait_for_continue_event(maintenance_end_time)

        daily_p20_tips_used = 0
        for shift_number, shift in enumerate(SHIFTS):
            shift_start_time = (
                SHIFT_DURATION + END_OF_SHIFT_CLEAN_DURATION
            ) * shift_number
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
                    DAY_DURATION * day
                    + shift_start_time
                    + time_between_interactions * interaction_number
                )
                source_category, target_category = interaction.split("_")
                add_comment_event(interaction_time, f"Interaction: {interaction}")
                shift_source_range = WELLS_NUMBERS_RANGE_OF_TYPE_PER_SHIFT[
                    source_category
                ][shift]
                shift_target_range = WELLS_NUMBERS_RANGE_OF_TYPE_PER_SHIFT[
                    target_category
                ][shift]
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
                    random_transfer_ul(),
                    shift,
                )
                p20_tips_used += 1
                daily_p20_tips_used += 1

            # End of shift cleaning
            for category in ["doctor", "nurse"]:
                shift_well_range = WELLS_NUMBERS_RANGE_OF_TYPE_PER_SHIFT[category][
                    shift
                ]
                for well in range(shift_well_range[0], shift_well_range[1]):
                    add_clean_well_event(category, well, random_clean_ul())

        # End of day cleaning
        for category in ["equipment", "surface"]:
            for well in range(shift_well_range[0], shift_well_range[1]):
                add_clean_well_event(category, well, random_clean_ul())

        end_of_day_time = (
            DAY_DURATION * day
            + (SHIFT_DURATION + END_OF_SHIFT_CLEAN_DURATION) * len(SHIFTS)
            + END_OF_DAY_CLEAN_DURATION
        )
        add_comment_event(end_of_day_time, f"Finished day {day + 1}/{DAYS}")
        add_reset_tiprack_event(end_of_day_time)
        assert daily_p20_tips_used <= TOTAL_P20_TIPS

    assert all(
        (
            "seconds_after_start" not in simulation_events[i - 1]
            or "seconds_after_start" not in simulation_events[i]
            or simulation_events[i - 1]["seconds_after_start"]
            <= simulation_events[i]["seconds_after_start"]
            for i in range(1, len(simulation_events))
        )
    )
    EVENTS_PATH.write_text(json.dumps(simulation_events, indent="    "))

    print(
        f"{SHIFT_DURATION} long shifts ({SHIFT_DURATION + END_OF_SHIFT_CLEAN_DURATION} including end of shift cleaning)"
    )
    print(f"{MAX_INTERACTION_COUNT} interactions per day")
    print(f"{MANUAL_SERVICE_DURATION} to restock pipette tips and take well samples")
