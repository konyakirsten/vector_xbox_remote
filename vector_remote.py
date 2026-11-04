"""
Xbox controller remote for Anki/DDL Vector using the Wire-Pod Python SDK.

Default Xbox mapping (SDL/macOS mappings can differ):
  Left stick Y: forward/back
  Left stick X: turn
  Right stick Y: head up/down
  LT / RT: lift down/up (when exposed as axes 4/5)
  A: greet animation
  B (hold): emergency motor stop
  Back/Select: quit

Test controller axis mapping with --show-inputs before driving.
"""
import argparse
import sys
import time

import pygame
import anki_vector
from anki_vector.util import degrees

ROBOT_IP = "192.168.188.125"

# Wheel speed profiles (mm/s). Hold a shoulder button to select a slower profile.
# No shoulder button = maximum speed; LB = medium; RB = precision.
MAX_FORWARD_MMPS = 150.0
MAX_BACKWARD_MMPS = 150.0
TURN_SPEEDS_MMPS = {"max": 100.0, "medium": 50.0, "precision": 30.0}
DRIVE_SPEEDS_MMPS = {"max": 150.0, "medium": 75.0, "precision": 50.0}
WHEEL_ACCEL_FACTOR = 4.0

MAX_HEAD_RAD_S = 1.0
MAX_LIFT_RAD_S = 1.0
DEADZONE = 0.14
LOOP_HZ = 20

def deadzone(value, threshold=DEADZONE):
    if abs(value) < threshold:
        return 0.0
    # Rescale remaining range so output is continuous after the dead zone.
    return (1 if value > 0 else -1) * (abs(value) - threshold) / (1 - threshold)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default=ROBOT_IP, help="Vector's LAN IP")
    parser.add_argument("--show-inputs", action="store_true",
                        help="Print joystick axes/buttons; do not connect to Vector")
    args = parser.parse_args()

    pygame.init()
    pygame.joystick.init()
    if pygame.joystick.get_count() == 0:
        print("No controller found. Pair the Xbox controller in macOS Bluetooth settings.")
        return 2

    pad = pygame.joystick.Joystick(0)
    pad.init()
    print(f"Controller: {pad.get_name()}")
    print(f"Axes: {pad.get_numaxes()}, buttons: {pad.get_numbuttons()}")
    if args.show_inputs:
        print("Move sticks and triggers; press buttons. Ctrl+C to stop.")
        try:
            while True:
                pygame.event.pump()
                axes = [round(pad.get_axis(i), 2) for i in range(pad.get_numaxes())]
                buttons = [i for i in range(pad.get_numbuttons()) if pad.get_button(i)]
                print(f"\rAxes: {axes}  Buttons down: {buttons}      ", end="", flush=True)
                time.sleep(0.1)
        except KeyboardInterrupt:
            print()
            return 0

    print(f"Connecting to Vector at {args.ip}:443 ...")
    print("Make sure the SDK has been configured on this MacBook first.")
    robot = None
    try:
        # SDK credentials are read from ~/.anki_vector/sdk_config.ini.
        robot = anki_vector.Robot(ip=args.ip)
        robot.connect()
        print("Connected. Start with the controller sticks centered.")
        clock = pygame.time.Clock()
        last_wheels = None

        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    raise KeyboardInterrupt
                if event.type == pygame.JOYBUTTONDOWN and event.button == 0:
                    # A button: a harmless greeting animation.
                    try:
                        robot.anim.play_animation_trigger("GreetAfterLongTime")
                    except Exception as exc:
                        print(f"\nAnimation unavailable: {exc}")

            pygame.event.pump()
            if pad.get_numbuttons() > 6 and pad.get_button(6):
                break

            # B button (index 1) is a hold-to-stop override.
            if pad.get_numbuttons() > 1 and pad.get_button(1):
                robot.motors.stop_all_motors()
                last_wheels = None
                clock.tick(LOOP_HZ)
                continue

            # Common SDL layout on macOS Xbox controllers:
            # 0 = left X, 1 = left Y, 4/5 = triggers.
            # Verify with --show-inputs; some macOS/SDL versions differ.
            lx = deadzone(pad.get_axis(0)) if pad.get_numaxes() > 0 else 0.0
            ly = deadzone(pad.get_axis(1)) if pad.get_numaxes() > 1 else 0.0
            ry = deadzone(pad.get_axis(3)) if pad.get_numaxes() > 3 else 0.0

            # Stick Y is negative when pushed forward.
            drive_dir = -ly
            turn_dir = lx
            # Reverse steering is inverted so the controller remains intuitive
            # when Vector is driving backwards.
            if drive_dir < 0:
                turn_dir = -turn_dir

            # Xbox shoulder buttons select the speed profile:
            # RB (button 5) = medium, LB (button 4) = precision,
            # neither = maximum. Precision takes priority if both are held.
            lb = pad.get_numbuttons() > 4 and pad.get_button(4)
            rb = pad.get_numbuttons() > 5 and pad.get_button(5)
            if lb:
                profile = "precision"
            elif rb:
                profile = "medium"
            else:
                profile = "max"

            forward_speed = DRIVE_SPEEDS_MMPS[profile]
            backward_speed = min(MAX_BACKWARD_MMPS, forward_speed)
            turn_speed = TURN_SPEEDS_MMPS[profile]
            base_speed = drive_dir * (forward_speed if drive_dir >= 0 else backward_speed)

            left = (base_speed + turn_speed * turn_dir)
            right = (base_speed - turn_speed * turn_dir)

            # Keep both wheel commands within the selected drive-speed ceiling
            # while preserving the requested turning ratio.
            wheel_limit = forward_speed if drive_dir >= 0 else backward_speed
            peak = max(abs(left), abs(right))
            if peak > wheel_limit:
                scale = wheel_limit / peak
                left *= scale
                right *= scale

            left = round(left, 1)
            right = round(right, 1)
            wheel_params = (
                left,
                right,
                abs(left) * WHEEL_ACCEL_FACTOR,
                abs(right) * WHEEL_ACCEL_FACTOR,
            )
            if wheel_params != last_wheels:
                robot.motors.set_wheel_motors(*wheel_params)
                last_wheels = wheel_params

            # Right stick vertical controls head motor.
            robot.motors.set_head_motor(-ry * MAX_HEAD_RAD_S)

            # Triggers: SDL commonly reports released=-1, pressed=+1.
            # If the controller exposes triggers differently, inspect --show-inputs.
            if pad.get_numaxes() > 5:
                lt = max(0.0, (pad.get_axis(4) + 1.0) / 2.0)
                rt = max(0.0, (pad.get_axis(5) + 1.0) / 2.0)
                lift = (rt - lt) * MAX_LIFT_RAD_S
                robot.motors.set_lift_motor(lift)

            clock.tick(LOOP_HZ)

    except KeyboardInterrupt:
        print("\nStopping.")
    except Exception as exc:
        print(f"\nRemote-control error: {exc}", file=sys.stderr)
        return 1
    finally:
        if robot is not None:
            try:
                robot.motors.stop_all_motors()
                robot.disconnect()
            except Exception:
                pass
        pygame.quit()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
