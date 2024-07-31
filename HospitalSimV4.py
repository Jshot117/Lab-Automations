import time
import random
from opentrons import protocol_api, types

metadata = {
    "protocolName": "Hospital Simulation V4.3",
    "author": "Jonnathan Saavedra & Assistant",
    "description": "Optimized simulation of hospital environment",
    "apiLevel": "2.14",
}

# Constants
SHIFTS = ["morning", "afternoon", "night"]
SHIFT_DURATION = 8 * 60 * 60  # 8 hours in seconds
MAINTENANCE_DURATION = 30 * 60  # 30 minutes in seconds
MAINTENANCE_FREQUENCY = 2  # times per day
SIMULATION_STEP = 600  # 10 minutes in seconds

# Adjustable variables
initial_bacteria_amount = 100
initial_media_amount = 50
bacteria_transfer_amount = 50
cleaning_media_amount = 100

interaction_probabilities = {
    "nurse_patient": 0.50,
    "doctor_patient": 0.30,
    "nurse_equipment": 0.20,
    "doctor_equipment": 0.15,
    "nurse_surface": 0.10,
    "doctor_surface": 0.05,
    "patient_equipment": 0.05,
}


class HospitalSimulation:
    def __init__(self, protocol: protocol_api.ProtocolContext):
        self.protocol = protocol
        self.setup_labware()
        self.setup_pipettes()
        self.setup_reagents()
        self.setup_categories()
        self.setup_volumes()
        self.days_elapsed = 0

    def setup_labware(self):
        self.patient_plate = self.protocol.load_labware(
            "opentronsappliedbiosystems_96_aluminumblock_200ul", "1", "Patient Plate"
        )
        self.staff_plate = self.protocol.load_labware(
            "opentronsappliedbiosystems_96_aluminumblock_200ul", "2", "Staff Plate"
        )
        self.equipment_plate = self.protocol.load_labware(
            "opentronsappliedbiosystems_96_aluminumblock_200ul", "3", "Equipment Plate"
        )
        self.surface_plate = self.protocol.load_labware(
            "opentronsappliedbiosystems_96_aluminumblock_200ul", "4", "Surface Plate"
        )
        self.tiprack_20 = self.protocol.load_labware(
            "opentrons_96_filtertiprack_20ul", "6"
        )
        self.tiprack_300 = self.protocol.load_labware(
            "opentrons_96_filtertiprack_200ul", "9"
        )
        self.reservoir = self.protocol.load_labware(
            "opentrons_6_tuberack_falcon_50ml_conical", "5"
        )

        self.temp_module = self.protocol.load_module("temperature module", "10")
        self.temp_plate = self.temp_module.load_labware(
            "opentronsappliedbiosystems_96_aluminumblock_200ul"
        )

    def fill_all_wells_with_media(self, iterations=1):
        self.protocol.comment("Filling all wells with initial media...")
        source_well = self.media
        source_well_volume = 15000  # Assuming a 15mL reservoir well

        all_target_wells = []
        for category in self.categories:
            if category in ["doctor", "nurse"]:
                for shift in SHIFTS:
                    all_target_wells.extend(self.categories[category][shift])
            else:
                all_target_wells.extend(self.categories[category])

        for i in range(iterations):
            self.p300.pick_up_tip()  # Pick up a new tip at the start of each iteration
            for well in all_target_wells:
                aspiration_zone = self.determine_aspiration_zone(source_well_volume)
                if aspiration_zone == "bottom":
                    source_well_aspiration_zone = source_well
                else:
                    source_well_aspiration_zone = source_well.top(aspiration_zone)

                self.p300.transfer(
                    initial_media_amount,
                    source_well_aspiration_zone,
                    well,
                    new_tip="never",
                )
                self.p300.blow_out()
                source_well_volume -= initial_media_amount
                self.protocol.comment(f"Remaining volume: {source_well_volume}")
                self.protocol.comment(f"Aspiration zone: {aspiration_zone}")

                if source_well_volume <= 0:
                    self.p300.drop_tip()  # Drop the tip before pausing
                    self.p300.home()
                    self.protocol.pause("No liquid in media reservoir. Please refill.")
                    source_well_volume = 15000  # Reset volume after refill
                    self.p300.pick_up_tip()  # Pick up a new tip after refilling

            self.p300.drop_tip()  # Drop the tip at the end of each iteration
            self.p300.home()
            if i != iterations - 1:
                self.protocol.pause("Iteration complete. Press resume to continue.")

        self.protocol.comment("All wells filled with initial media.")
    
        # Add pause for manual bacteria addition
        self.protocol.pause("Media distribution complete. Please manually add initial bacteria to the first well of the patient plate, then resume the protocol.")

    def setup_pipettes(self):
        self.p20 = self.protocol.load_instrument(
            "p20_single_gen2", "left", tip_racks=[self.tiprack_20]
        )
        self.p300 = self.protocol.load_instrument(
            "p300_single_gen2", "right", tip_racks=[self.tiprack_300]
        )

    def setup_reagents(self):
        self.media = self.reservoir.wells()[0]
        self.bacteria = self.reservoir.wells()[1]
        self.waste = self.reservoir.wells()[2]

    def setup_categories(self):
        self.categories = {
            "patient": self.temp_plate.wells()[:20],
            "doctor": {
                shift: self.staff_plate.wells()[i : i + 6]
                for i, shift in zip([0, 18, 36], SHIFTS)
            },
            "nurse": {
                shift: self.staff_plate.wells()[i : i + 12]
                for i, shift in zip([6, 24, 42], SHIFTS)
            },
            "equipment": self.equipment_plate.wells()[:20],
            "surface": self.surface_plate.wells()[:60],
        }

    def setup_volumes(self):
        self.volumes = {
            "patient": {
                well: initial_media_amount for well in self.categories["patient"]
            },
            "doctor": {
                shift: {well: initial_media_amount for well in wells}
                for shift, wells in self.categories["doctor"].items()
            },
            "nurse": {
                shift: {well: initial_media_amount for well in wells}
                for shift, wells in self.categories["nurse"].items()
            },
            "equipment": {
                well: initial_media_amount for well in self.categories["equipment"]
            },
            "surface": {
                well: initial_media_amount for well in self.categories["surface"]
            },
        }

    def run_simulation(self, num_days):
        self.protocol.comment("Starting simulation setup...")
        self.temp_module.set_temperature(37)
        self.fill_all_wells_with_media(iterations=1)
        for day in range(num_days):
            self.days_elapsed += 1
            self.protocol.comment(f"Simulating Day {day + 1}")
            for shift in SHIFTS:
                self.run_shift(shift)
            if day % (24 // MAINTENANCE_FREQUENCY) == 0:
                self.perform_maintenance()
        self.temp_module.deactivate()
        self.protocol.comment("Simulation complete")

    def run_shift(self, shift):
        self.protocol.comment(f"Starting {shift} shift")
        steps = SHIFT_DURATION // SIMULATION_STEP
        for _ in range(steps):
            self.simulate_interactions(shift)
        self.end_shift(shift)

    def simulate_interactions(self, shift):
        for interaction, probability in interaction_probabilities.items():
            if random.random() < probability:
                source_category, target_category = interaction.split("_")
                source_well = self.get_random_well(source_category, shift)
                target_well = self.get_random_well(target_category)
                self.transfer_bacteria(
                    source_category,
                    source_well,
                    target_category,
                    target_well,
                    bacteria_transfer_amount,
                    shift,
                )

    def get_random_well(self, category, shift=None):
        if category in ["doctor", "nurse"]:
            return random.choice(self.categories[category][shift])
        return random.choice(self.categories[category])

    def transfer_bacteria(
        self, source_category, source_well, target_category, target_well, amount, shift
    ):
        source_volume = self.get_well_volume(source_category, source_well, shift)
        if source_volume >= amount:
            self.update_well_volume(source_category, source_well, -amount, shift)
            self.update_well_volume(target_category, target_well, amount, shift)
            self.p20.transfer(amount, source_well, target_well, new_tip="always")

    def get_well_volume(self, category, well, shift=None):
        if category in ["doctor", "nurse"]:
            return self.volumes[category][shift][well]
        return self.volumes[category][well]

    def update_well_volume(self, category, well, amount, shift=None):
        if category in ["doctor", "nurse"]:
            self.volumes[category][shift][well] += amount
        else:
            self.volumes[category][well] += amount

    def end_shift(self, shift):
        for category in ["doctor", "nurse"]:
            for well in self.categories[category][shift]:
                self.clean_well(category, well, shift)
        if shift == SHIFTS[-1]:  # End of day
            for well in self.categories["patient"]:
                self.clean_well("patient", well)

    def clean_well(self, category, well, shift=None):
        self.p300.pick_up_tip()
        try:
            self.p300.transfer(cleaning_media_amount, self.media, well, new_tip="never")
            self.p300.mix(3, 100, well)
            self.p300.transfer(cleaning_media_amount, well, self.waste, new_tip="never")
            self.update_well_volume(
                category,
                well,
                initial_media_amount - self.get_well_volume(category, well, shift),
                shift,
            )
        finally:
            self.p300.drop_tip()

    def transfer_bacteria(
        self, source_category, source_well, target_category, target_well, amount, shift
    ):
        source_volume = self.get_well_volume(source_category, source_well, shift)
        if source_volume >= amount:
            self.p20.pick_up_tip()
            try:
                self.p20.transfer(amount, source_well, target_well, new_tip="never")
                self.update_well_volume(source_category, source_well, -amount, shift)
                self.update_well_volume(target_category, target_well, amount, shift)
            finally:
                self.p20.drop_tip()

    def perform_maintenance(self):
        self.protocol.pause(
            f"Day {self.days_elapsed} maintenance. Please refill tips, media, and reset well plates. Resume when ready."
        )
        self.setup_volumes()
        self.p20.reset_tipracks()
        self.p300.reset_tipracks()

    def determine_aspiration_zone(self, volume):
        if volume > 1000:
            return -2  # 2mm from top
        elif volume > 500:
            return -5  # 5mm from top
        elif volume > 100:
            return -8  # 8mm from top
        else:
            return "bottom"


def run(protocol: protocol_api.ProtocolContext):
    protocol.comment("Initializing Hospital Simulation...")
    simulation = HospitalSimulation(protocol)
    simulation.run_simulation(num_days=1)  # Run for 1 day
