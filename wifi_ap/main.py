import asyncio
import logging
from argparse import ArgumentParser
from datetime import datetime

import msgpack
import winrt.windows.devices.wifidirect as wifi
from websockets.asyncio.server import serve

wifi_error = {
    wifi.WiFiDirectError.SUCCESS: "SUCCESS",
    wifi.WiFiDirectError.RADIO_NOT_AVAILABLE: "RADIO_NOT_AVAILABLE",
    wifi.WiFiDirectError.RESOURCE_IN_USE: "RESOURCE_IN_USE",
}

publisher_status = {
    wifi.WiFiDirectAdvertisementPublisherStatus.CREATED: "CREATED",
    wifi.WiFiDirectAdvertisementPublisherStatus.STARTED: "STARTED",
    wifi.WiFiDirectAdvertisementPublisherStatus.STOPPED: "STOPPED",
    wifi.WiFiDirectAdvertisementPublisherStatus.ABORTED: "ABORTED",
}

discoverability_state = {
    wifi.WiFiDirectAdvertisementListenStateDiscoverability.NONE: "NONE",
    wifi.WiFiDirectAdvertisementListenStateDiscoverability.NORMAL: "NORMAL",
    wifi.WiFiDirectAdvertisementListenStateDiscoverability.INTENSIVE: "INTENSIVE",
}


def main():
    # Setup logging to file and terminal
    log = logging.getLogger()
    log.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        fmt="%(asctime)s:%(name)s:[%(levelname)s]: %(message)s",
        datefmt="%Y/%m/%d %H:%M:%S",
    )
    file_log = logging.FileHandler(
        filename="wifi_ap_{:%Y-%m-%d}.log".format(datetime.now()), encoding="utf-8"
    )
    file_log.setFormatter(formatter)
    log.addHandler(file_log)
    stream_log = logging.StreamHandler()
    stream_log.setFormatter(formatter)
    log.addHandler(stream_log)

    log.info("================ Starting the wifi_ap program ================")
    parser = ArgumentParser()
    parser.add_argument("--ssid", default="DIRECT-SCANNER1", help="Wifi AP SSID")
    parser.add_argument("--passphrase", default="test1234", help="Wifi AP passphrase")
    parser.add_argument(
        "--websocket-url",
        default="0.0.0.0",
        help="Websocket IP address hosted by the Wifi AP (0.0.0.0 will make it available for other machines)",
    )
    parser.add_argument(
        "--websocket-port",
        default=8080,
        type=int,
        help="Websocket port hosted by the Wifi AP",
    )
    parser.add_argument(
        "--timeout",
        default=60 * 10,
        type=int,
        help="Time in seconds after the Wifi AP exists",
    )
    args = parser.parse_args()

    # Start Wifi AP Advertisment
    publisher = wifi.WiFiDirectAdvertisementPublisher()
    log.debug(f"Setup publisher (initial status={publisher_status[publisher.status]})")

    # Pass a function
    def on_status_change(sender, args):
        """
        sender: WiFiDirectAdvertisementPublisher
        """
        log.info(
            f"Publisher status changed to: {publisher_status[args.status]} / {wifi_error[args.error]}"
        )

    token = publisher.add_status_changed(on_status_change)

    log.debug("Setup Wifi AP settings")
    # Must set the autonomous group owner (GO) enabled flag
    # Legacy Wi-Fi Direct advertisement uses a Wi-Fi Direct GO to act as an access point to legacy settings
    publisher.advertisement.is_autonomous_group_owner_enabled = True
    log.info(
        f"Listen state discoverability: {discoverability_state[publisher.advertisement.listen_state_discoverability]} -> INTENSIVE"
    )
    publisher.advertisement.listen_state_discoverability = (
        wifi.WiFiDirectAdvertisementListenStateDiscoverability.INTENSIVE
    )
    publisher.advertisement.legacy_settings.is_enabled = True
    publisher.advertisement.legacy_settings.ssid = args.ssid
    publisher.advertisement.legacy_settings.passphrase.password = args.passphrase
    log.info(f"SSID: {publisher.advertisement.legacy_settings.ssid}")
    log.info(
        f"Passphrase: {publisher.advertisement.legacy_settings.passphrase.password}"
    )
    for method in publisher.advertisement.supported_configuration_methods:
        log.debug(f"Configuration method: {method}")

    def on_connection_change(sender, args):
        """
        sender: WiFiDirectConnectionListener
        """
        device = args.get_connection_request().device_information
        log.info(f"New connected device (name={device.name}, id={device.id}, kind={device.kind})")

    log.debug("Setup connection listener")
    listener = wifi.WiFiDirectConnectionListener()
    token_connection = listener.add_connection_requested(on_connection_change)

    log.debug("Start publisher")
    publisher.start()

    async def select_handle_request(websocket):
        async for message in websocket:
            unpacked = msgpack.unpackb(message)
            if "command" not in unpacked:
                log.warning(
                    "Not a properly formatted command. Missing the 'command' field."
                )
                return
            command = unpacked["command"]
            log.debug(f"--> Received request: {command}")
            if command == "check_connection":
                response = {
                    "command": "check_connection",
                    "success": True,
                    "errors": [],
                }
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
            log.debug("<-- Sending response")
            await websocket.send(packed_response)

    async def run_websocket_server():
        try:
            log.debug(f"Running WebSocket server for {args.timeout} seconds")
            async with asyncio.timeout(args.timeout):
                async with serve(
                    select_handle_request, args.websocket_url, args.websocket_port
                ) as server:
                    await server.serve_forever()  # run forever
        except TimeoutError:
            log.warning("WebSocket server is turning off because of the timeout.")

    asyncio.run(run_websocket_server())

    log.debug("Stop publisher")
    publisher.stop()
    log.debug("Remove callbacks")
    listener.remove_connection_requested(token_connection)
    publisher.remove_status_changed(token)


if __name__ == "__main__":
    main()
