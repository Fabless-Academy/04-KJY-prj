import unittest
from unittest.mock import call, patch

from bev_lane_modules.control import (
    CMD_EMER_SIGNAL,
    EMER_SIGNAL_OFF,
    EMER_SIGNAL_ON,
    IpcSender,
    speed_to_bytes,
)


class SpeedCommandEncodingTests(unittest.TestCase):
    def test_speed_command_is_one_byte(self):
        self.assertEqual(speed_to_bytes(37.0), b"\x25")

    def test_speed_command_is_rounded(self):
        self.assertEqual(speed_to_bytes(37.6), b"\x26")

    def test_speed_command_is_clamped_to_supported_range(self):
        self.assertEqual(speed_to_bytes(-1.0), b"\x00")
        self.assertEqual(speed_to_bytes(100.0), b"\x64")
        self.assertEqual(speed_to_bytes(101.0), b"\x64")


class EmergencySignalCommandTests(unittest.TestCase):
    def test_sends_on_and_off_commands_only_when_state_changes(self):
        sender = IpcSender(enabled=True, ipc_path="/unused", period_ms=1)
        sender.handle = object()

        with patch("bev_lane_modules.control.time.time", side_effect=[1.0, 1.01, 1.02]):
            with patch("bev_lane_modules.control.IPC_SendPacketWithIPCHeader") as send_packet:
                sender.send(50.0, 0.0, True)
                sender.send(50.0, 0.0, True)
                sender.send(50.0, 0.0, False)

        emergency_calls = [
            packet_call
            for packet_call in send_packet.call_args_list
            if packet_call.args[3] == CMD_EMER_SIGNAL
        ]
        self.assertEqual(
            emergency_calls,
            [
                call(sender.handle, 1, 0, CMD_EMER_SIGNAL, bytes([EMER_SIGNAL_ON])),
                call(sender.handle, 1, 0, CMD_EMER_SIGNAL, bytes([EMER_SIGNAL_OFF])),
            ],
        )


if __name__ == "__main__":
    unittest.main()
