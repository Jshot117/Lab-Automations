from datetime import datetime

from opentrons import protocol_api

metadata = {
    "protocolName": "Sleeping test",
    "author": "Patryk S.",
    "description": "Optimized simulation of hospital environment",
    "apiLevel": "2.14",
}

def run(protocol: protocol_api.ProtocolContext):
    protocol.comment("Initializing")
    current_time = datetime.now()
    sleep_until = datetime(year=2024, month=9, day=19, hour=22, minute=5) 
    sleep_duration = sleep_until - current_time
    protocol.comment(f"Time is {current_time}")
    protocol.comment(f"Sleeping until {sleep_until}")
    protocol.comment(f"Sleeping for {sleep_duration}")
    protocol.delay(sleep_duration.total_seconds())
    protocol.comment(f"Time is {datetime.now()}")
