# wifi-ap-win32

Programmatic WiFi Access Point (AP) on Windows.
By default, it will create a WebSocket server that mimics PhysioServer with a
timeout of 10 minutes and run an Wifi Access Point (AP).

## Run without building

Run: `uv run wifi_ap --timeout 60` (1 minute timeout)

## Connect to scanner

1. Run `wifi_ap.exe` on Windows machine (it will create a WiFi Access Point with SSID: `DIRECT-SCANNER1`)
2. From another device, open: [http://skanowanie.iniphy.pl](http://skanowanie.iniphy.pl)
3. Switch from this device to `DIRECT-SCANNER1` with passhprase `test1234`
4. In skanowanie app, setup the connection IP address: `192.168.137.1` using `ws://` protocol and port `8080`
5. The connection should work!

## Prepare *.exe

Run: `uv run pyinstaller --onefile .\wifi_ap\main.py`
