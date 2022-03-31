# E-Ink Solar Clock

![E-Ink Display Foto](https://secanis-public-storage.s3.nl-ams.scw.cloud/staticweb/3c75a64be78c63a6a776aea2664d07e6/rpi-eink-display_6.jpg)

## Deployment / Development

Install the dependencies
```bash
pip install -r requirements.txt
```

Start the application
```bash
/usr/bin/python3 /home/pi/clock/clock.py
```

For development enable the debug mode: 
Change the `ENABLE/DISABLE DEBUG MODE` part in `the clock.py` file or set the environment variable `PI_DEBUG` to `1`.
The debug mode will not update your screen, instead it will generate an image (like a screenshot) and will save it into the project directory.

## Configuration

- Choose and download your font, I used the [UbuntuMono-Regular](https://fonts.google.com/specimen/Ubuntu+Mono) font.
- Choose your images/icons for the display, I had...
  - a solar icon
  - a energy icon
  - a electric car icon
  - a wifi icon for the connectivity

## Start it as a daemon

```bash
# /lib/systemd/system/clock.service

[Unit]
Description=Clock Service
After=multi-user.target

[Service]
WorkingDirectory=/home/pi/clock
ExecStart=/usr/bin/python3 /home/pi/clock/clock.py
User=pi
PermissionsStartOnly=true
RuntimeDirectoryMode=755
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Reload the daemon and start the service
```bash
sudo systemctl daemon-reload
sudo systemctl enable clock.service

sudo systemctl start clock.service
sudo systemctl status clock.service
```

