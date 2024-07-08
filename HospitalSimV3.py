import time
import random
from opentrons import protocol_api


metadata = {
    "protocolName": "Hospital Simulation V2",
    "authorName": "Jonnathan Saavedra",
    "description": "Simulates hospital environment using wells as subjects from a hospital incorporates shifts",
    "apiLevel": "2.14",
}

# Labware definitions
P20_TIPRACK_SLOT = "9"
P20_TIPRACK_LOADNAME = "opentrons_96_filtertiprack_20ul"

P300_TIPRACK_SLOT = "6"
P300_TIPRACK_LOADNAME = "opentrons_96_filtertiprack_200ul"

well_plate_patient_SLOT = "4"
well_plate_patient_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"  # need to update loadname value to correct value

well_plate_shift_SLOT = "5"
well_plate_shift_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"  # need to update loadname value to correct value

well_plate_second_patient_SLOT = "6"
well_plate_second_patient_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"  # need to update loadname value to correct value

well_plate_surfaces_SLOT = "8"
well_plate_surfaces_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"  # need to update loadname value to correct value

well_plate_equipment_SLOT = "2"
well_plate_equipment_LOADNAME = "opentronsappliedbiosystems_96_aluminumblock_200ul"  # need to update loadname value to correct value


LEFT_PIPETTE_MOUNT = "left"
LEFT_PIPETTE_NAME = "p20_single_gen2"

RIGHT_PIPETTE_MOUNT = "right"
RIGHT_PIPETTE_NAME = "P300_single_gen2"

TUBERACK_SLOT = "3"
TUBERACK_LOADNAME = "opentrons_6_tuberack_falcon_50ml_conical"

# adjustable variables
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


def run(protocol: protocol_api.ProtocolContext):
    # initalize labware
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
    # initizlize instruments
    left_pipette = protocol.load_instrument(
        LEFT_PIPETTE_NAME, LEFT_PIPETTE_MOUNT, tip_racks=[p20tiprack]
    )
    right_pipette = protocol.load_instrument(
        RIGHT_PIPETTE_NAME, RIGHT_PIPETTE_MOUNT, tip_racks=[p300tiprack]
    )

    # label wells to categories
    categories = {
        "patients": well_plate_patient.wells()[:20],
        "doctors": {
            "shift_one": well_plate_shift.wells()[:6],
            "shift_two": well_plate_shift.wells()[18:24],
            "shift_three": well_plate_shift.wells()[36:42],
        },
        "nurses": {
            "shift_one": well_plate_shift.wells()[6:18],
            "shift_two": well_plate_shift.wells()[24:36],
            "shift_three": well_plate_shift.wells()[42:54],
        },
        "equipment": well_plate_equipment.wells()[:20],
        "surfaces": well_plate_surfaces.wells()[:60],
    }
    well_plate_volumes = {
        "shift": {
            well: initial_media_amount
            for shift in ["shift_one", "shift_two", "shift_three"]
            for category in ["doctors", "nurses"]
            for well in categories[category][shift]
        },
        "patient": {well: initial_media_amount for well in categories["patients"]},
        "equipment": {well: initial_media_amount for well in categories["equipment"]},
        "surface": {well: initial_media_amount for well in categories["surfaces"]},
    }

    # name common variables
    source_well = tuberack.wells()[0]
    source_well_volume = tuberack.wells()[0].max_volume
    source_well_bacteria = tuberack.wells()[1]
    source_well_bacteria_volume = tuberack.wells()[1].max_volume # or actual amount of bacteria in tube
    patient_zero_well = categories["patients"][0]  # location for patient zero
    patient_zero_well_volume = initial_bacteria_amount + initial_media_amount

    right_pipette.transfer(
        initial_bacteria_amount, source_well.top(zone_five), patient_zero_well
    )
    source_well_volume = source_well_volume - initial_bacteria_amount

    def fill_wells_with_media(target_wells, amount_of_media):
        global source_well_volume  # Make source_well_volume global to update it within this function
        aspiration_zone = determine_aspiration_zone(source_well_volume)
        source_well_aspiration_zone = (
            source_well
            if aspiration_zone == "bottom"
            else source_well.top(aspiration_zone)
        )
        right_pipette.pick_up_tip()
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
                return
        right_pipette.drop_tip()
    
    





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
