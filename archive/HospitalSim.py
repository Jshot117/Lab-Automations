import time
import random
import math
from opentrons import protocol_api 

metadata = {
    'protocolName': 'Hospital Simulation',
    'authorName' : 'Jonnathan Saavedra',
    'description' : 'Simulates hospital environment using wells as subjects from a hospital', 
    'apiLevel' : '2.14'
            }

#Labware definitions
P20_TIPRACK_SLOT = '7'
P20_TIPRACK_LOADNAME = 'opentrons_96_filtertiprack_20ul'

P300_TIPRACK_SLOT = '11'
P300_TIPRACK_LOADNAME = 'opentrons_96_filtertiprack_200ul'

WELLPLATE_SLOT = '5'
WELLPLATE_LOADNAME = 'opentronsappliedbiosystems_96_aluminumblock_200ul'

LEFT_PIPETTE_MOUNT = 'left'
LEFT_PIPETTE_NAME = 'p20_single_gen2'

RIGHT_PIPETTE_MOUNT = 'right'
RIGHT_PIPETTE_NAME = 'P300_single_gen2'

TUBERACK_SLOT = '3'
TUBERACK_LOADNAME = 'opentrons_6_tuberack_falcon_50ml_conical'

#adjustable variables
initial_bacteria_amount = 150  #can not go over 200
time_amount = 1 #time in seconds until pipette dispenses next "liquid" into wells
bacteria_transfer_amount = 50  #can not go over initial_bacteria_amount and initial_bacteria_amount mod bacteria_transfer_amount = zero

column_probabilites = {
    "Column One" : 0,
    "Column Two" : 2.2,
    "Column Three" : 1.3,
    "Column Four" : 3.1,
    "Column Five" : 2,
    "Column Six" : 1.2,
    "Column Seven" : 1.2,
    "Column Eight" : 1.4,
    "Column Nine" : 1.5,
    "Column Ten" : 4,
    "Column Eleven" : 4.1,
    "Column Twelve" : 2,    
}


#Data for falcon 50 ml tube
zone_five = -35
zone_four = -52
zone_three = -68
zone_two = -83


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
    
    #initizlize instruments
    left_pipette = protocol.load_instrument(LEFT_PIPETTE_NAME,LEFT_PIPETTE_MOUNT,tip_racks = [p20tiprack])
    right_pipette = protocol.load_instrument(RIGHT_PIPETTE_NAME,RIGHT_PIPETTE_MOUNT,tip_racks = [p300tiprack])
    
    #name common variables
    source_well = tuberack.wells()[0]
    source_well_volume = 20300            #tuberack.wells()[0].max_volume
    patient_zero_well = wellplate.wells()[0] #location for patient zero
    patient_zero_well_volume = initial_bacteria_amount
    
    right_pipette.transfer(initial_bacteria_amount,source_well.top(zone_three),patient_zero_well)
    source_well_volume = source_well_volume - initial_bacteria_amount
    
    column_probabilites_list = list(column_probabilites.values())
    well_probabilites = []
    
    for prob in column_probabilites_list:
        well_probabilites.extend([prob] * 8)
    well_probabilites[0] = 0
    
    for i in range(10):
        random_target = random.choices(wellplate.wells(),weights = well_probabilites, k=1)[0]
        left_pipette.transfer(bacteria_transfer_amount,patient_zero_well,random_target,pick_up_tip = 'once')
        patient_zero_well_volume = patient_zero_well_volume - bacteria_transfer_amount
        
        if patient_zero_well_volume <= 0: 
            right_pipette.transfer(initial_bacteria_amount,source_well_aspiration_zone,patient_zero_well, pick_up_tip = 'once')
            patient_zero_well_volume = initial_bacteria_amount
            source_well_volume = source_well_volume - initial_bacteria_amount
        
        aspiration_zone = determine_aspiration_zone(source_well_volume)
        if aspiration_zone == 'bottom':
            source_well_aspiration_zone = source_well.bottom()
        else:
            source_well_aspiration_zone = source_well.top(aspiration_zone)
            
        time.sleep(time_amount)