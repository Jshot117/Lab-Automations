from opentrons import protocol_api
from datetime import datetime, timedelta

metadata = {
    "protocolName": "Generated Hospital Simulation",
    "author": "Jonnathan Saavedra",
    "description": "Optimized simulation of hospital environment",
    "apiLevel": "2.14",
}

# TODO: Get from generated schedule
INITIAL_MEDIA_UL = 250
BACTERIA_TRANSFER_SETTLE_WAIT_SECS = 30
BLEACH_CONTACT_WAIT_SECS = 30
BLEACH_MIX_UL = 200
MIX_REPITITIONS = 4


class HospitalSimulation:
    def __init__(self, protocol: protocol_api.ProtocolContext):
        self.protocol = protocol
        self.setup_labware()
        self.setup_pipettes()
        self.setup_reagents()

    def setup_labware(self):
        temp_module = self.protocol.load_module("temperature module", "10")
        temp_module2 = self.protocol.load_module("temperature module", "7")
        assert isinstance(temp_module, protocol_api.TemperatureModuleContext)
        self.temp_module = temp_module
        self.temp_module2 = temp_module2
        self.patient_plate = self.temp_module.load_labware(
            "corning_96_wellplate_360ul_flat"
        )
        self.staff_plate = self.temp_module2.load_labware(
            "corning_96_wellplate_360ul_flat"
        )
        self.equipment_plate = self.protocol.load_labware(
            "corning_96_wellplate_360ul_flat", "8", "Equipment Plate"
        )
        self.surface_plate = self.protocol.load_labware(
            "corning_96_wellplate_360ul_flat", "11", "Surface Plate"
        )
        self.tiprack_300_one = self.protocol.load_labware(
            "opentrons_96_tiprack_300ul", "6"
        )
        self.tiprack_300_two = self.protocol.load_labware(
            "opentrons_96_tiprack_300ul", "5"
        )
        self.tiprack_300_three = self.protocol.load_labware(
            "opentrons_96_tiprack_300ul", "4"
        )
        self.tiprack_300_four = self.protocol.load_labware(
            "opentrons_96_tiprack_300ul", "1"
        )
        self.tiprack_300_five = self.protocol.load_labware(
            "opentrons_96_tiprack_300ul", "2"
        )
        self.tiprack_300_six = self.protocol.load_labware(
            "opentrons_96_tiprack_300ul", "9"
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
        self.p300 = self.protocol.load_instrument(
            "p300_single_gen2",
            "right",
            tip_racks=[
                self.tiprack_300_one,
                self.tiprack_300_two,
                self.tiprack_300_three,
                self.tiprack_300_four,
                self.tiprack_300_five,
                self.tiprack_300_six,
            ],
        )

    def setup_reagents(self):
        self.media = self.reservoir.wells()[0]
        self.bacteria = self.reservoir.wells()[1]
        self.waste = self.reservoir.wells()[2]
        self.bleach = self.reservoir.wells()[3]

    def initialize(self):
        self.protocol.comment("Starting simulation setup...")
        self.temp_module.set_temperature(37)
        self.temp_module2.set_temperature(37)
        self.fill_all_wells_with_media(iterations=1)
        self.start_time = datetime.now()

    def fill_all_wells_with_media(self, iterations=1):
        self.protocol.comment("Filling all wells with initial media...")
        source_well = self.media
        self.source_well_volume = 50000  # 50 ml reservoir

        all_target_wells = [
            *self.patient_plate.wells()[:20],
            *self.staff_plate.wells()[: (6 * 3 + 12 * 3)],
            *self.equipment_plate.wells()[:20],
            *self.surface_plate.wells()[:60],
        ]

        for i in range(iterations):
            self.p300.pick_up_tip()  # Pick up a new tip at the start of each iteration
            for well in all_target_wells:
                aspiration_zone = self.determine_media_aspiration_zone()
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
                self.source_well_volume -= INITIAL_MEDIA_UL
                self.protocol.comment(f"Remaining volume: {self.source_well_volume}")
                self.protocol.comment(f"Aspiration zone: {aspiration_zone}")

                if self.source_well_volume <= 0:
                    self.p300.drop_tip()  # Drop the tip before pausing
                    self.p300.home()
                    self.protocol.pause("No liquid in media reservoir. Please refill.")
                    self.source_well_volume = 50000  # Reset volume after refill
                    self.p300.pick_up_tip()  # Pick up a new tip after refilling

            self.p300.mix(MIX_REPITITIONS, BLEACH_MIX_UL, self.bleach.top(-40))
            self.p300.blow_out(self.bleach.top())
            self.protocol.delay(
                BLEACH_CONTACT_WAIT_SECS,
                msg=f"Waiting {BLEACH_CONTACT_WAIT_SECS} seconds for bleach contact",
            )
            self.p300.return_tip()  # Drop the tip at the end of each iteration
            # self.p300.drop_tip()
            self.p300.home()
            if i != iterations - 1:
                self.protocol.pause("Iteration complete. Press resume to continue.")

        self.protocol.comment("All wells filled with initial media.")

        # Add pause for manual bacteria addition
        self.protocol.pause(
            "Media distribution complete. Please manually add initial bacteria to the first well of the patient plate, then resume the protocol."
        )

    def determine_media_aspiration_zone(self):
        if self.source_well_volume <= 10000:
            return 'bottom'
        elif self.source_well_volume<= 20000:
            return -97
        elif self.source_well_volume<= 30000:
            return -76
        elif self.source_well_volume<= 40000:
            return -59
        else:
            return -40 

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
        transfer_ul: int | float,
    ):
        self.p300.pick_up_tip()
        source_well = self.plates_dict[source_well_plate].wells()[source_well_number]
        target_well = self.plates_dict[target_well_plate].wells()[target_well_number]
        self.p300.transfer(transfer_ul, source_well, target_well, new_tip="never")
        self.protocol.delay(
            BACTERIA_TRANSFER_SETTLE_WAIT_SECS,
            msg=f"Waiting for {target_well} bacteria to settle",
        )
        self.p300.transfer(transfer_ul, target_well, source_well, new_tip="never")
        self.p300.mix(MIX_REPITITIONS, BLEACH_MIX_UL, self.bleach.top(-40))
        self.p300.blow_out(self.bleach.top())
        self.protocol.delay(
                BLEACH_CONTACT_WAIT_SECS,
                msg=f"Waiting {BLEACH_CONTACT_WAIT_SECS} seconds for bleach contact",
            )
        self.p300.return_tip()
        # self.p300.drop_tip()

    def clean(
        self,
        well_plate: str,
        well_number: int,
        clean_ul: int | float,
    ):
        cleaning_well = self.plates_dict[well_plate].wells()[well_number]

        aspiration_zone = self.determine_media_aspiration_zone()
        if aspiration_zone == "bottom":
            media_well_aspiration_zone = self.media
        else:
            media_well_aspiration_zone = self.media.top(aspiration_zone)

        self.p300.pick_up_tip()
        self.p300.transfer(
            clean_ul, media_well_aspiration_zone, cleaning_well, new_tip="never"
        )
        # It's fine to reuse the pipette tip here
        self.p300.transfer(clean_ul, cleaning_well, self.waste.top(), new_tip="never")
        # TODO: Sleep during clean?
        self.p300.mix(MIX_REPITITIONS, BLEACH_MIX_UL, self.bleach.top(-40))
        self.p300.blow_out(self.bleach.top())
        self.protocol.delay(
                BLEACH_CONTACT_WAIT_SECS,
                msg=f"Waiting {BLEACH_CONTACT_WAIT_SECS} seconds for bleach contact",
            )
        self.p300.return_tip()

    def wait_for_continue(self, resume_at: int):
        self.protocol.pause("Pausing for maintenance")
        self.sleep_seconds_after_start(resume_at)

    def end_of_day_restock(self):
        self.p300.reset_tipracks()
        self.source_well_volume = 50000


def run(protocol: protocol_api.ProtocolContext):
    protocol.comment("Initializing Hospital Simulation...")
    simulation = HospitalSimulation(protocol)
    simulation.initialize()
