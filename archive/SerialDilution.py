from opentrons import protocol_api 


metadata = {
    'protocolName': 'SerialDilution Protocol',
    'authorName' : 'Jonnathan Saavedra',
    'description' : 'Transfers 900 micro liters into 1.5ml snapcaps then proceeds to do serial dilution', 
    'apiLevel' : '2.14'
            }

#Labware definitions
P20_TIPRACK_SLOT = '7'
P20_TIPRACK_LOADNAME = 'opentrons_96_filtertiprack_20ul'

P300_TIPRACK_SLOT = '11'
P300_TIPRACK_LOADNAME = 'opentrons_96_filtertiprack_200ul'

WELLPLATE_SLOT = '5'
WELLPLATE_LOADNAME = 'opentronsappliedbiosystems_96_aluminumblock_200ul'

ALUMINUMBLOCK_SLOT =  '1'
ALUMINUMBLOCK_LOADNAME = 'opentrons_24_aluminumblock_nest_1.5ml_snapcap'

LEFT_PIPETTE_MOUNT = 'left'
LEFT_PIPETTE_NAME = 'p20_single_gen2'

RIGHT_PIPETTE_MOUNT = 'right'
RIGHT_PIPETTE_NAME = 'P300_single_gen2'

TUBERACK_SLOT = '3'
TUBERACK_LOADNAME = 'opentrons_6_tuberack_falcon_50ml_conical'



dilution_transfer_amount = 900
media_transfer_amount = 100
iterations = 3
#Zone Data for falcon 50 ml tube
zone_five = -40 ; zone_four = -59 ; zone_three = -76 ; zone_two = -97
# Helper function to calculate distance from the top of tube pipette should aspirate
def determine_aspiration_zone(volume):
    if volume<= 10000:
        return 'bottom'
    elif volume<= 20000:
        return zone_two
    elif volume<= 30000:
        return zone_three
    elif volume<= 40000:
        return zone_four
    else:
        return zone_five 
def run(protocol: protocol_api.ProtocolContext):
    #initalize labware
    wellplate = protocol.load_labware(WELLPLATE_LOADNAME,WELLPLATE_SLOT)
    p20tiprack = protocol.load_labware(P20_TIPRACK_LOADNAME,P20_TIPRACK_SLOT)
    p300tiprack = protocol.load_labware(P300_TIPRACK_LOADNAME,P300_TIPRACK_SLOT)
    tuberack = protocol.load_labware(TUBERACK_LOADNAME,TUBERACK_SLOT)
    aluminumblock = protocol.load_labware(ALUMINUMBLOCK_LOADNAME,ALUMINUMBLOCK_SLOT)
    #initizlize instruments
    left_pipette = protocol.load_instrument(LEFT_PIPETTE_NAME,LEFT_PIPETTE_MOUNT,tip_racks = [p20tiprack])
    right_pipette = protocol.load_instrument(RIGHT_PIPETTE_NAME,RIGHT_PIPETTE_MOUNT,tip_racks = [p300tiprack])
    #name common variables
    source_well = tuberack.wells()[0]
    source_well_volume = tuberack.wells()[0].max_volume
    media_source_well = tuberack.wells()[1]
    
    #volume for media set as 10,000 as default should not be greater than 10,000
    media_source_well_volume = 10000
    #start of commands
    target_wells = aluminumblock.wells()
    excluded_wells = aluminumblock.rows_by_name()['B'] 
    target_wells = [well for well in target_wells if well not in excluded_wells]
    for i in range(iterations):
        right_pipette.pick_up_tip()
        for well in target_wells: 
            aspiration_zone = determine_aspiration_zone(source_well_volume)
            if aspiration_zone == 'bottom':
                source_well_aspiration_zone = source_well
            else:
                source_well_aspiration_zone = source_well.top(aspiration_zone)
            right_pipette.transfer(dilution_transfer_amount, source_well_aspiration_zone,well, new_tip = 'never')
            right_pipette.blow_out()
            source_well_volume = source_well_volume - dilution_transfer_amount
            protocol.comment(source_well_volume)
            protocol.comment(aspiration_zone)
            if source_well_volume <= 0:
                right_pipette.home()
                protocol.pause("No liquid in tube rack, well 0")
        right_pipette.drop_tip()
        for index in range(3):
            if index == 2:
                index+=1
            head_of_row = aluminumblock.rows()[index][0]
            media_source_well_volume = media_source_well_volume-media_transfer_amount
            if media_source_well_volume <= 0:
                right_pipette.home()
                protocol.pause("No media in tube rack, well 1")
            right_pipette.transfer(media_transfer_amount,media_source_well,head_of_row, mix_after = (3,100), new_tip = 'once')
            previous_well = head_of_row
            for well in aluminumblock.rows()[index][1:]:
                right_pipette.transfer(media_transfer_amount,previous_well,well, mix_after = (3,100), new_tip = 'once')
                previous_well = well
        right_pipette.home()
        if i != iterations-1: protocol.pause()