import time
import random
from opentrons import protocol_api

metadata = {
    "protocolName": "Hospital Simulation V3",
    "authorName": "Jonnathan Saavedra",
    "description": "Simulates hospital environment using wells as subjects from a hospital incorporates shifts",
    "apiLevel": "2.14",
}

# Labware definitions
P20_TIPRACK_SLOT = "9"
P20_TIPRACK_LOADNAME = "opentrons_96_filtertiprack_20ul"

P300_TIPRACK_SLOT = "6"
P300_TIPRACK_LOADNAME = "opentrons_96_filtertiprack_200ul"

well_plate_patient_SLOT = "10"
well_plate_patient_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"

well_plate_shift_SLOT = "7"
well_plate_shift_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"

well_plate_second_patient_SLOT = "4"
well_plate_second_patient_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"

well_plate_surfaces_SLOT = "8"
well_plate_surfaces_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"

well_plate_equipment_SLOT = "11"
well_plate_equipment_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"

LEFT_PIPETTE_MOUNT = "left"
LEFT_PIPETTE_NAME = "p20_single_gen2"

RIGHT_PIPETTE_MOUNT = "right"
RIGHT_PIPETTE_NAME = "P300_single_gen2"

TUBERACK_SLOT = "3"
TUBERACK_LOADNAME = "opentrons_6_tuberack_falcon_50ml_conical"

# Adjustable variables
initial_bacteria_amount = 100  # can not go over 200
initial_media_amount = 50
time_amount = 1  # time in seconds until pipette dispenses next "liquid" into wells
bacteria_transfer_amount = 50  # can not go over initial_bacteria_amount and initial_bacteria_amount mod bacteria_transfer_amount = zero

interaction_probabilities = {
    "nurse_patient": 0.50,
    "doctor_patient": 0.30,
    "nurse_equipment": 0.20,
    "doctor_equipment": 0.15,
    "nurse_surface": 0.10,
    "doctor_surface": 0.05,
}

shifts = ["shift_one", "shift_two", "shift_three"]

zone_five = -40
zone_four = -59
zone_three = -76
zone_two = -97

# Helper function to calculate distance from the top of tube pipette should aspirate
def determine_aspiration_zone(volume):
    if volume <= 10000:
        return "bottom"
    elif volume <= 20000:
        return zone_two
    elif volume <= 30000:
        return zone_three
    elif volume <= 40000:
        return zone_four
    else:
        return zone_five

def fill_wells_with_media(protocol, right_pipette, target_wells, amount_of_media, source_well, source_well_volume):
    aspiration_zone = determine_aspiration_zone(source_well_volume)
    source_well_aspiration_zone = (
        source_well if aspiration_zone == "bottom" else source_well.top(aspiration_zone)
    )
    for well in target_wells:
        right_pipette.transfer(
            amount_of_media, source_well_aspiration_zone, well, new_tip="never"
        )
        right_pipette.blow_out()
        source_well_volume -= amount_of_media
        protocol.comment(f"Remaining source volume: {source_well_volume}")
        protocol.comment(f"Aspiration zone: {aspiration_zone}")

        if source_well_volume <= 0:
            right_pipette.drop_tip()
            protocol.pause("No liquid in tube rack, well 0")
            return source_well_volume
    return source_well_volume

def simulate_interaction(protocol, left_pipette, source_well, target_well, interaction_type, source_category, well_plate_volumes):
    if random.random() < interaction_probabilities[interaction_type]:
        transfer_amount = min(
            bacteria_transfer_amount,
            well_plate_volumes[source_category][source_well]
        )
        if transfer_amount > 0:
            left_pipette.transfer(
                transfer_amount, source_well, target_well, new_tip="always"
            )
            protocol.delay(seconds=time_amount)
            # Update volumes in the source and target wells
            well_plate_volumes[source_category][source_well] -= transfer_amount
            
            # Determine the category of the target_well
            for category in well_plate_volumes:
                if target_well in well_plate_volumes[category]:
                    well_plate_volumes[category][target_well] += transfer_amount
                    break

def simulate_shift(protocol, left_pipette, categories, well_plate_volumes, shift):
    for doctor_well in categories["doctor"][shift]:
        if random.choices(
            [True, False],
            [
                interaction_probabilities["doctor_patient"],
                1 - interaction_probabilities["doctor_patient"],
            ],
        )[0]:
            simulate_interaction(
                protocol, left_pipette, categories["patient"][0], doctor_well, "doctor_patient", "patient", well_plate_volumes
            )
        for equipment_well in categories["equipment"]:
            if random.choices(
                [True, False],
                [
                    interaction_probabilities["doctor_equipment"],
                    1 - interaction_probabilities["doctor_equipment"],
                ],
            )[0]:
                simulate_interaction(
                    protocol, left_pipette, doctor_well, equipment_well, "doctor_equipment", "shift", well_plate_volumes
                )
        for surface_well in categories["surface"]:
            if random.choices(
                [True, False],
                [
                    interaction_probabilities["doctor_surface"],
                    1 - interaction_probabilities["doctor_surface"],
                ],
            )[0]:
                simulate_interaction(
                    protocol, left_pipette, doctor_well, surface_well, "doctor_surface", "shift", well_plate_volumes
                )

    for nurse_well in categories["nurse"][shift]:
        if random.choices(
            [True, False],
            [
                interaction_probabilities["nurse_patient"],
                1 - interaction_probabilities["nurse_patient"],
            ],
        )[0]:
            simulate_interaction(
                protocol, left_pipette, categories["patient"][0], nurse_well, "nurse_patient", "patient", well_plate_volumes
            )
        for equipment_well in categories["equipment"]:
            if random.choices(
                [True, False],
                [
                    interaction_probabilities["nurse_equipment"],
                    1 - interaction_probabilities["nurse_equipment"],
                ],
            )[0]:
                simulate_interaction(
                    protocol, left_pipette, nurse_well, equipment_well, "nurse_equipment", "shift", well_plate_volumes
                )
        for surface_well in categories["surface"]:
            if random.choices(
                [True, False],
                [
                    interaction_probabilities["nurse_surface"],
                    1 - interaction_probabilities["nurse_surface"],
                ],
            )[0]:
                simulate_interaction(
                    protocol, left_pipette, nurse_well, surface_well, "nurse_surface", "shift", well_plate_volumes
                )

def run(protocol: protocol_api.ProtocolContext):
    # Initialize labware
    well_plate_patient = protocol.load_labware(
        well_plate_patient_LOADNAME, well_plate_patient_SLOT
    )
    well_plate_shift = protocol.load_labware(
        well_plate_shift_LOADNAME, well_plate_shift_SLOT
    )
    well_plate_second_patient = protocol.load_labware(
        well_plate_second_patient_LOADNAME, well_plate_second_patient_SLOT
    )
    well_plate_surfaces = protocol.load_labware(
        well_plate_surfaces_LOADNAME, well_plate_surfaces_SLOT
    )
    well_plate_equipment = protocol.load_labware(
        well_plate_equipment_LOADNAME, well_plate_equipment_SLOT
    )
    p20tiprack = protocol.load_labware(P20_TIPRACK_LOADNAME, P20_TIPRACK_SLOT)
    p300tiprack = protocol.load_labware(P300_TIPRACK_LOADNAME, P300_TIPRACK_SLOT)
    tuberack = protocol.load_labware(TUBERACK_LOADNAME, TUBERACK_SLOT)
    # Initialize instruments
    left_pipette = protocol.load_instrument(
        LEFT_PIPETTE_NAME, LEFT_PIPETTE_MOUNT, tip_racks=[p20tiprack]
    )
    right_pipette = protocol.load_instrument(
        RIGHT_PIPETTE_NAME, RIGHT_PIPETTE_MOUNT, tip_racks=[p300tiprack]
    )

    # Label wells to categories
    categories = {
        "patient": well_plate_patient.wells()[:20],
        "doctor": {
            "shift_one": well_plate_shift.wells()[:6],
            "shift_two": well_plate_shift.wells()[18:24],
            "shift_three": well_plate_shift.wells()[36:42],
        },
        "nurse": {
            "shift_one": well_plate_shift.wells()[6:18],
            "shift_two": well_plate_shift.wells()[24:36],
            "shift_three": well_plate_shift.wells()[42:54],
        },
        "equipment": well_plate_equipment.wells()[:20],
        "surface": well_plate_surfaces.wells()[:60],
    }

    # Create well_plate_volumes dictionary
    well_plate_volumes = {
        "shift": {
            well: initial_media_amount
            for shift in ["shift_one", "shift_two", "shift_three"]
            for category in ["doctor", "nurse"]
            for well in categories[category][shift]
        },
        "patient": {well: initial_media_amount for well in categories["patient"]},
        "equipment": {well: initial_media_amount for well in categories["equipment"]},
        "surface": {well: initial_media_amount for well in categories["surface"]},
    }

    # Initialize common variables
    source_well = tuberack.wells()[0]
    source_well_volume = tuberack.wells()[0].max_volume
    source_well_bacteria = tuberack.wells()[1]
    source_well_bacteria_volume = tuberack.wells()[
        1
    ].max_volume  # or actual amount of bacteria in tube
    patient_zero_well = categories["patient"][0]  # location for patient zero

    right_pipette.transfer(
        initial_bacteria_amount, source_well.top(zone_five), patient_zero_well
    )
    source_well_volume -= initial_bacteria_amount
    
    right_pipette.pick_up_tip()
    source_well_volume = fill_wells_with_media(
        protocol, right_pipette, categories["patient"], initial_media_amount, source_well, source_well_volume
    )
    source_well_volume = fill_wells_with_media(
        protocol, right_pipette, categories["doctor"]["shift_one"], initial_media_amount, source_well, source_well_volume
    )
    source_well_volume = fill_wells_with_media(
        protocol, right_pipette, categories["nurse"]["shift_one"], initial_media_amount, source_well, source_well_volume
    )
    source_well_volume = fill_wells_with_media(
        protocol, right_pipette, categories["surface"], initial_media_amount, source_well, source_well_volume
    )
    source_well_volume = fill_wells_with_media(
        protocol, right_pipette, categories["equipment"], initial_media_amount, source_well, source_well_volume
    )
    right_pipette.drop_tip()
    # Infect patient zero
    left_pipette.transfer(
        bacteria_transfer_amount, source_well_bacteria, patient_zero_well
    )
    # Update volumes of in source well and patient zero well
    source_well_bacteria_volume -= bacteria_transfer_amount
    well_plate_volumes["patient"][patient_zero_well] += bacteria_transfer_amount

    for shift in shifts:
        protocol.comment(f"Starting {shift} simulation")
        simulate_shift(protocol, left_pipette, categories, well_plate_volumes, shift)
        protocol.comment(f"Completed {shift} simulation")

    protocol.comment("Simulation complete")

    # for i in range(4):
    #     random_target = random.choices(
    #         well_plate_patient.wells(), weights=well_probabilites, k=1
    #     )[0]
    #     while well_plate_morning_volume[random_target] >= 50:
    #         random_target_index = well_plate_patient.wells().index(random_target)
    #         well_probabilites[random_target_index] = 0
    #         # Check if there's no valid well left
    #         if sum(well_probabilites) == 0:
    #             protocol.comment("All wells are full. Stopping transfer.")
    #             return
    #         random_target = random.choices(
    #             well_plate_patient.wells(), weights=well_probabilites, k=1
    #         )[0]
    #     left_pipette.transfer(
    #         bacteria_transfer_amount,
    #         patient_zero_well,
    #         random_target,
    #         pick_up_tip="once",
    #     )
    #     well_plate_morning_volume[random_target] += bacteria_transfer_amount
    #     patient_zero_well_volume = patient_zero_well_volume - bacteria_transfer_amount
    #     aspiration_zone = determine_aspiration_zone(source_well_volume)
    #     if aspiration_zone == "bottom":
    #         source_well_aspiration_zone = source_well
    #     else:
    #         source_well_aspiration_zone = source_well.top(aspiration_zone)
    #     if patient_zero_well_volume <= 0:
    #         right_pipette.transfer(
    #             initial_bacteria_amount,
    #             source_well_aspiration_zone,
    #             patient_zero_well,
    #             pick_up_tip="once",
    #         )
    #         patient_zero_well_volume = initial_bacteria_amount
    #         source_well_volume = source_well_volume - initial_bacteria_amount
    #     time.sleep(time_amount)
