from opentrons import protocol_api
from datetime import datetime, timedelta

metadata = {
    "protocolName": "Generated Hospital Simulation",
    "author": "Jonnathan Saavedra",
    "description": "Optimized simulation of hospital environment",
    "apiLevel": "2.14",
}

# TODO: Get from generated schedule
INITIAL_MEDIA_UL = 50
BACTERIA_TRANSFER_SETTLE_WAIT_SECS = 30


class HospitalSimulation:
    def __init__(self, protocol: protocol_api.ProtocolContext):
        self.protocol = protocol
        self.setup_labware()
        self.setup_pipettes()
        self.setup_reagents()

    def setup_labware(self):
        temp_module = self.protocol.load_module("temperature module", "10")
        assert isinstance(temp_module, protocol_api.TemperatureModuleContext)
        self.temp_module = temp_module
        self.patient_plate = self.temp_module.load_labware(
            "corning_96_wellplate_360ul_flat"
        )
        self.staff_plate = self.protocol.load_labware(
            "corning_96_wellplate_360ul_flat", "7", "Staff Plate"
        )
        self.equipment_plate = self.protocol.load_labware(
            "corning_96_wellplate_360ul_flat", "8", "Equipment Plate"
        )
        self.surface_plate = self.protocol.load_labware(
            "corning_96_wellplate_360ul_flat", "11", "Surface Plate"
        )
        self.tiprack_20_one = self.protocol.load_labware(
            "opentrons_96_filtertiprack_20ul", "6"
        )
        self.tiprack_20_two = self.protocol.load_labware(
            "opentrons_96_filtertiprack_20ul", "5"
        )
        self.tiprack_20_three = self.protocol.load_labware(
            "opentrons_96_filtertiprack_20ul", "4"
        )
        self.tiprack_20_four = self.protocol.load_labware(
            "opentrons_96_filtertiprack_20ul", "1"
        )
        self.tiprack_20_five = self.protocol.load_labware(
            "opentrons_96_filtertiprack_20ul", "2"
        )
        self.tiprack_300 = self.protocol.load_labware(
            "opentrons_96_filtertiprack_200ul", "9"
        )
        self.reservoir = self.protocol.load_labware(
            "opentrons_6_tuberack_falcon_50ml_conical", "3"
        )
        self.plates_dict = {
            "patient": self.patient_plate,
            "staff": self.staff_plate,
            "equipment": self.equipment_plate,
            "surface": self.surface_plate,
        }

    def setup_pipettes(self):
        self.p20 = self.protocol.load_instrument(
            "p20_single_gen2",
            "left",
            tip_racks=[
                self.tiprack_20_one,
                self.tiprack_20_two,
                self.tiprack_20_three,
                self.tiprack_20_four,
                self.tiprack_20_five,
            ],
        )
        self.p300 = self.protocol.load_instrument(
            "p300_single_gen2", "right", tip_racks=[self.tiprack_300]
        )

    def setup_reagents(self):
        self.media = self.reservoir.wells()[0]
        self.bacteria = self.reservoir.wells()[1]
        self.waste = self.reservoir.wells()[2]

    def initialize(self):
        self.protocol.comment("Starting simulation setup...")
        self.temp_module.set_temperature(37)
        self.fill_all_wells_with_media(iterations=1)
        self.start_time = datetime.now()

    def fill_all_wells_with_media(self, iterations=1):
        self.protocol.comment("Filling all wells with initial media...")
        source_well = self.media
        source_well_volume = 15000  # Assuming a 15mL reservoir well

        all_target_wells = [
            *self.patient_plate.wells()[:20],
            *self.staff_plate.wells()[: (6 * 3 + 12 * 3)],
            *self.equipment_plate.wells()[:20],
            *self.surface_plate.wells()[:60],
        ]

        for i in range(iterations):
            self.p300.pick_up_tip()  # Pick up a new tip at the start of each iteration
            for well in all_target_wells:
                aspiration_zone = self.determine_aspiration_zone(source_well_volume)
                if aspiration_zone == "bottom":
                    source_well_aspiration_zone = source_well
                else:
                    source_well_aspiration_zone = source_well.top(aspiration_zone)

                self.p300.transfer(
                    INITIAL_MEDIA_UL,
                    source_well_aspiration_zone,
                    well,
                    new_tip="never",
                )
                self.p300.blow_out()
                source_well_volume -= INITIAL_MEDIA_UL
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
        self.protocol.pause(
            "Media distribution complete. Please manually add initial bacteria to the first well of the patient plate, then resume the protocol."
        )

    def determine_aspiration_zone(self, volume):
        if volume > 1000:
            return -2  # 2mm from top
        elif volume > 500:
            return -5  # 5mm from top
        elif volume > 100:
            return -8  # 8mm from top
        else:
            return "bottom"

    def sleep_seconds_after_start(self, seconds_after_start):
        sleep_until = self.start_time + timedelta(seconds=seconds_after_start)
        sleep_seconds = (sleep_until - datetime.now()).total_seconds()
        self.protocol.delay(sleep_seconds, msg=f"Sleeping until next interaction")

    def comment(self, comment):
        self.protocol.comment(comment)

    def transfer(
        self,
        source_well_plate: str,
        target_well_plate: str,
        source_well_number: int,
        target_well_number: int,
        transfer_ul: int,
    ):
        self.p20.pick_up_tip()
        source_well = self.plates_dict[source_well_plate].wells()[source_well_number]
        target_well = self.plates_dict[target_well_plate].wells()[target_well_number]
        self.p20.transfer(transfer_ul, source_well, target_well, new_tip="never")
        self.protocol.delay(
            BACTERIA_TRANSFER_SETTLE_WAIT_SECS,
            msg=f"Waiting for {target_well} bacteria to settle",
        )
        self.p20.transfer(transfer_ul, target_well, source_well, new_tip="never")
        self.p20.drop_tip()

    def reset_tip_racks(self):
        self.p20.reset_tipracks()
        self.p300.reset_tipracks()


def run(protocol: protocol_api.ProtocolContext):
    protocol.comment("Initializing Hospital Simulation...")
    simulation = HospitalSimulation(protocol)
    simulation.initialize()
