## AI Disclaimer

This project was created with the assistance of AI. The code and documentation were AI-generated and have been tested and adjusted during development, but may still contain errors or unexpected behaviour. Use at your own risk.

# Vector Xbox Remote (MacBook)

A minimal macOS Python remote for Vector firmware `2.0.1.6076ep`.
It connects directly to Vector, using the
Wire-Pod-compatible SDK configuration stored on the MacBook.

## 1. Pair the Xbox controller

Pair the Xbox Series X controller in macOS **System Settings → Bluetooth**.
Hold the controller's pairing button until the Xbox button flashes, then pair it.

## 2. Install the SDK and controller library

Open Terminal on the MacBook, `cd` into this folder, then run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The Wire-Pod SDK is a fork of the original Vector SDK with Wire-Pod support:
https://github.com/kercre123/wirepod-vector-python-sdk

## 3. Configure SDK credentials on the MacBook

With the venv activated:

```bash
python -m anki_vector.configure
```

Follow the SDK configuration prompts and use Vector's details when asked.
This should create `~/.anki_vector/sdk_config.ini` and its certificate on
the MacBook. Do not share either file; they contain authentication material.

If the wizard asks for Vector's IP, enter `192.168.188.125`.
Wire-Pod server IP is `192.168.188.250`; that is not the robot IP.

## 4. Check controller axes before connecting

```bash
python vector_remote.py --show-inputs
```

Move each stick and trigger and observe the values. The default mapping in
the script assumes SDL axes 0/1 = left stick X/Y, axis 3 = right stick Y,
axes 4/5 = triggers. If your output differs, adjust the axis indices near
the comment `Common SDL layout on macOS Xbox controllers`.

## 5. Run

```bash
python vector_remote.py
```

Or specify the robot IP explicitly:

```bash
python vector_remote.py --ip 192.168.188.125
```

## Controls

- Left stick: drive / turn
- Right stick vertical: head motor
- LT / RT: lift motor
- A: greeting animation
- Hold B: stop all motors
- Back / View: quit (button index 6; verify with `--show-inputs`)

## Safety

- Start with Vector on a clear, flat surface, away from stairs and edges.
- B is a hold-to-stop override. Ctrl+C / quitting also sends `stop_all_motors`.
- If the controller disconnects unexpectedly, stop Vector manually; this
  simple first version does not yet implement a hardware disconnect watchdog.
- Head and lift motor directions may need inversion depending on observed
  axis orientation. Test briefly and keep clear of Vector's moving parts.
