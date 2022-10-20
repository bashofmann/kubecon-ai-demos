import asyncio
import argparse
from tkinter import E
import nats
from nats.errors import NoServersError, TimeoutError
from time import sleep
import os
import serial

rps_move = {
    b'rock'     : b'1', 
    b'paper'    : b'2', 
    b'scissors' : b'3', 
    b'win'      : b'4', 
    b'lose'     : b'5'
}
servo = {"pinky": 0x18, "ring": 0x18, "middle": 0x18, "pointer": 0x18, "thumb": 0x18, "wrist": 0x18, }
agent = None
device = None
PORT = os.environ['UDEV_DEVNODE']
BAUDRATE = 115200
TIMEOUT = 0 # serial.read timeout value 0 makes reads non blocking

async def main(nats_server_url, loop):
    async def disconnected_cb():
        print("Got disconnected!")

    async def reconnected_cb():
        print("Got reconnected to NATS...")

    async def error_cb(e):
        print(f"There was an error: {e}")

    async def closed_cb():
        print("Connection is closed")

    nc = await nats.connect(
        nats_server_url,
        error_cb=error_cb,
        reconnected_cb=reconnected_cb,
        disconnected_cb=disconnected_cb,
        closed_cb=closed_cb,
    )

    def connect():
        global device
        try:
            device = serial.Serial(PORT, BAUDRATE, TIMEOUT)
        except Exception as e:
            print("Serial device connection failed. ", e)
            device = None
    
    def disconnect():
        global device
        try:
            device.close()
            device = None
        except Exception as e:
            print("There was a problem disconnecting. ", e)

    async def move_robot(msg):
        global device
        print("Computer move registered: ", msg.data)
        if(device == None):
            try:
                connect()
            except Exception as e:
                print("Gesture changed but device not connected", e)
                if msg.reply:
                    await msg.respond(msg.reply, "disconnected")
                return # bail out 

        try:
            # Move the robot hand
            device.write(rps_move[msg.data])
        except Exception as e:
            print("Could not process gesture:", e)

        disconnect()

        if msg.reply:
            await msg.respond(msg.reply, msg.data)
                        

    if nc.is_connected:
        sub = await nc.subscribe("computer_move", cb=move_robot)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("nats_server_url")
    args = vars(parser.parse_args())

    loop = asyncio.get_event_loop()
    loop.run_until_complete(main(args["nats_server_url"], loop))
    loop.run_forever()
    loop.close()
