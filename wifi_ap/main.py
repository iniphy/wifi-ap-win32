import asyncio
import logging as log
from argparse import ArgumentParser

import msgpack
import winrt.windows.devices.wifidirect as wifi
from websockets.asyncio.server import serve


def main():
    print("test")


parser = ArgumentParser()
parser.add_argument("--ssid", default="DIRECT-SCANNER1")
parser.add_argument("--passphrase", default="test1234")
parser.add_argument("--websocket-url", default="0.0.0.0")
parser.add_argument("--websocket-port", default=8080)
args = parser.parse_args()

# Start Wifi AP Advertisemetn
publisher = wifi.WiFiDirectAdvertisementPublisher()
advertisement = publisher.advertisement

# Pass a function
def on_status_change(sender, args):
    print("Status changed: ", sender, args)

    match args.error:
        case wifi.WiFiDirectError.SUCCESS:
            print("\tSuccess")
        case wifi.WiFiDirectError.RADIO_NOT_AVAILABLE:
            print("\tRadio is not available")
        case wifi.WiFiDirectError.RESOURCE_IN_USE:
            print("\tResource in use")

    match args.status:
        case wifi.WiFiDirectAdvertisementPublisherStatus.CREATED:
            print("\tCreated")
        case wifi.WiFiDirectAdvertisementPublisherStatus.STARTED:
            # Begin listening for connections and notify listener that the advertisement started
            print("\tStarted")
        case wifi.WiFiDirectAdvertisementPublisherStatus.STOPPED:
            # Notify listener that the advertisement is stopped
            print("\tStopped")
        case wifi.WiFiDirectAdvertisementPublisherStatus.ABORTED:
            # Check error and notify listener that the advertisement stopped
            print("\tAborted")


token = publisher.add_status_changed(on_status_change)

# Must set the autonomous group owner (GO) enabled flag
# Legacy Wi-Fi Direct advertisement uses a Wi-Fi Direct GO to act as an access point to legacy settings
advertisement.is_autonomous_group_owner_enabled = True
legacy_settings = advertisement.legacy_settings
legacy_settings.is_enabled = True
legacy_settings.ssid = args.ssid
legacy_settings.passphrase.password = args.passphrase
print("SSID: ", legacy_settings.ssid)
print("Passphrase: ", legacy_settings.passphrase.password)


def on_connection_change(sender, args):
    print("Connection change: ", sender, args)


listener = wifi.WiFiDirectConnectionListener()
token_connection = listener.add_connection_requested(on_connection_change)

publisher.start()

# TODO: start a weboscket server here


async def select_handle_request(websocket):
    async for message in websocket:
        unpacked = msgpack.unpackb(message)
        if "command" not in unpacked:
            log.warning(
                "Not a properly formatted command. Missing the 'command' field."
            )
            return
        command = unpacked["command"]
        print(f"Incoming command: {command}")
        if command == "check_connection":
            response = {"command": "check_connection", "success": True, "errors": []}
        elif command == "get_status":
            response = {
                "command": "get_status",
                "status": {},
                "success": True,
                "errors": [],
            }
        else:
            response = {}
        packed_response = msgpack.packb(response, use_bin_type=True)
        await websocket.send(packed_response)


async def run_websocket_server():
    async with serve(
        select_handle_request, args.websocket_url, args.websocket_port
    ) as server:
        await server.serve_forever()  # run forever


asyncio.run(run_websocket_server())

publisher.stop()
listener.remove_connection_requested(token_connection)
publisher.remove_status_changed(token)
