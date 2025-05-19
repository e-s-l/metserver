# TODO

- adapt serial ports to open by path
    Don't use hardcoded /dev/ttyUSBX in config file.

    Check current serial ports cmd line w 
    ```
    python -m serial.tools.list_ports -v
    ```
    or go to dir (which exists when serial ports do) `/dev/serial/by-path`.
- need to have vaisala or met4 metserver types as options.
- maybe before entering the mainloop: 
    - check the units, &c
    ...?
 - consider adding database uploader, may as well set up one on godzilla
 mariadb with table for a site, just need to timestamp the uploads
 oh no hang on, this should be a seperate script running on godzilla
 - test
- update the requirements.txt & things accordingly
