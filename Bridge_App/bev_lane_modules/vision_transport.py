from __future__ import annotations
"""Telechips Vision Protocol transport helpers for zonal_app."""

import argparse
import ctypes
import json
import os
import threading
import time
from typing import Any, Dict, Optional


BLOCKING = -1
VISION_SUCCESS = 0
VISION_MSG_EVENT_RESULT_DATA_JSON = 44
VISION_PROTOCOL_CTRL_DATA_SIZE = 1024 * 320
VISION_PROTOCOL_STREAM_QUEUE_COUNT = 4
VISION_PROTOCOL_CTRL_QUEUE_COUNT = 6
SYS_DEFAULT_BUFSIZE = 0

MESSAGE_MODE = 0
STREAM_MODE = 1
INTERFACE_ETHERNET = 0
SERVER = 0
OFF = 0
ON = 1


class VisionProtocolImportError(RuntimeError):
    pass


class QueueInfo(ctypes.Structure):
    _fields_ = [("maxDataSize", ctypes.c_uint32), ("numQ", ctypes.c_uint8)]


class NetworkBufSize(ctypes.Structure):
    _fields_ = [("sendBufSize", ctypes.c_uint32), ("recvBufSize", ctypes.c_uint32)]


class VisionUserConfig(ctypes.Structure):
    _fields_ = [
        ("netInterface", ctypes.c_int),
        ("netRole", ctypes.c_int),
        ("netBuf", NetworkBufSize),
        ("ip", ctypes.c_char * 16),
        ("port", ctypes.c_uint16),
        ("opMode", ctypes.c_int),
        ("reconnection", ctypes.c_int),
        ("streamZeroCopy", ctypes.c_int),
        ("sendQ", QueueInfo),
        ("recvQ", QueueInfo),
    ]


class VisionStreamInfo(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_uint32),
        ("pBuffer", ctypes.POINTER(ctypes.c_uint8)),
        ("length", ctypes.c_uint32),
        ("seqNum", ctypes.c_uint64),
        ("timestamp", ctypes.c_uint64),
    ]


class VisionMessageHeader(ctypes.Structure):
    _fields_ = [
        ("id", ctypes.c_uint32),
        ("length", ctypes.c_uint32),
        ("seqNum", ctypes.c_uint64),
        ("timestamp", ctypes.c_uint64),
    ]


def _candidate_lib_dirs(rtpm_root: str):
    module_dir = os.path.join(os.path.dirname(__file__), "visionprotocol")
    yield module_dir
    yield os.path.join(module_dir, "cython_visionprotocol")
    yield os.path.join(rtpm_root, "model", "visionprotocol", "cython_visionprotocol")
    yield os.path.join(rtpm_root, "model", "visionprotocol")


def _load_library(rtpm_root: str) -> ctypes.CDLL:
    last_error: Optional[BaseException] = None
    for directory in _candidate_lib_dirs(rtpm_root):
        for name in ("libvisionprotocol.so.2.1.0", "libvisionprotocol.so.2.0.0", "libvisionprotocol.so", "libvisionprotocol.dll"):
            path = os.path.join(directory, name)
            if not os.path.exists(path):
                continue
            try:
                return ctypes.CDLL(path)
            except OSError as exc:
                last_error = exc
    raise VisionProtocolImportError(f"cannot load libvisionprotocol from {rtpm_root}: {last_error}")


def _configure_api(lib: ctypes.CDLL) -> ctypes.CDLL:
    lib.Vision_API_Initialization.argtypes = [ctypes.POINTER(VisionUserConfig), ctypes.POINTER(ctypes.c_void_p)]
    lib.Vision_API_Initialization.restype = ctypes.c_int
    lib.Vision_API_Deinitialization.argtypes = [ctypes.POINTER(ctypes.c_void_p)]
    lib.Vision_API_Deinitialization.restype = ctypes.c_int
    lib.Vision_API_Connection.argtypes = [ctypes.c_void_p]
    lib.Vision_API_Connection.restype = ctypes.c_int
    lib.Vision_API_Disconnection.argtypes = [ctypes.c_void_p]
    lib.Vision_API_Disconnection.restype = ctypes.c_int
    lib.Vision_API_SendMessage.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int16]
    lib.Vision_API_SendMessage.restype = ctypes.c_int
    lib.Vision_API_RecvMessage.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int16]
    lib.Vision_API_RecvMessage.restype = ctypes.c_int
    lib.Vision_API_PeekMessage.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
    lib.Vision_API_PeekMessage.restype = ctypes.c_int
    lib.Vision_API_RegisterStreamSendBuffer.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_uint32]
    lib.Vision_API_RegisterStreamSendBuffer.restype = ctypes.c_int
    lib.Vision_API_GetStreamSendBuffer.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.POINTER(VisionStreamInfo)),
        ctypes.POINTER(ctypes.c_uint8),
        ctypes.c_int16,
    ]
    lib.Vision_API_GetStreamSendBuffer.restype = ctypes.c_int
    lib.Vision_API_SendStream.argtypes = [ctypes.c_void_p, ctypes.POINTER(VisionStreamInfo), ctypes.c_uint8]
    lib.Vision_API_SendStream.restype = ctypes.c_int
    return lib


def _make_config(port: int, op_mode: int, send_size: int, send_count: int, recv_size: int, recv_count: int,
                 zero_copy: bool = False) -> VisionUserConfig:
    config = VisionUserConfig()
    config.netInterface = INTERFACE_ETHERNET
    config.netRole = SERVER
    config.netBuf.sendBufSize = SYS_DEFAULT_BUFSIZE
    config.netBuf.recvBufSize = SYS_DEFAULT_BUFSIZE
    config.ip = b"0.0.0.0"
    config.port = port
    config.opMode = op_mode
    config.reconnection = OFF
    config.streamZeroCopy = ON if zero_copy else OFF
    config.sendQ.maxDataSize = send_size
    config.sendQ.numQ = send_count
    config.recvQ.maxDataSize = recv_size
    config.recvQ.numQ = recv_count
    return config


class _VisionChannel:
    def __init__(self, lib: ctypes.CDLL, config: VisionUserConfig):
        self.lib = lib
        self.handle = ctypes.c_void_p()
        ret = self.lib.Vision_API_Initialization(ctypes.byref(config), ctypes.byref(self.handle))
        if ret != VISION_SUCCESS:
            raise RuntimeError(f"Vision_API_Initialization failed: {ret}")
        self.buffers = []
        if config.opMode == STREAM_MODE:
            for _ in range(config.sendQ.numQ):
                buf = (ctypes.c_uint8 * config.sendQ.maxDataSize)()
                ret = self.lib.Vision_API_RegisterStreamSendBuffer(self.handle, buf, config.sendQ.maxDataSize)
                if ret != VISION_SUCCESS:
                    raise RuntimeError(f"Vision_API_RegisterStreamSendBuffer failed: {ret}")
                self.buffers.append(buf)
        ret = self.lib.Vision_API_Connection(self.handle)
        if ret != VISION_SUCCESS:
            raise RuntimeError(f"Vision_API_Connection failed: {ret}")

    def close(self) -> None:
        if self.handle.value:
            try:
                self.lib.Vision_API_Disconnection(self.handle)
                self.lib.Vision_API_Deinitialization(ctypes.byref(self.handle))
            finally:
                self.handle = ctypes.c_void_p()


class VisionBridge:
    """PC-side Vision Protocol server: stream frames out, receive result messages."""

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.lib = _configure_api(_load_library(getattr(args, "rtpm_root", "/mnt/c/ai_work/rtpm")))
        self.frame_bytes = args.width * args.height * 3
        self.seq = 0
        self.msg: Optional[_VisionChannel] = None
        self.stream: Optional[_VisionChannel] = None

    def open(self) -> None:
        msg_config = _make_config(
            self.args.message_port,
            MESSAGE_MODE,
            VISION_PROTOCOL_CTRL_DATA_SIZE,
            VISION_PROTOCOL_CTRL_QUEUE_COUNT,
            VISION_PROTOCOL_CTRL_DATA_SIZE,
            VISION_PROTOCOL_CTRL_QUEUE_COUNT,
            False,
        )
        stream_config = _make_config(
            self.args.stream_port,
            STREAM_MODE,
            self.frame_bytes,
            VISION_PROTOCOL_STREAM_QUEUE_COUNT,
            0,
            0,
            True,
        )
        self.msg = _VisionChannel(self.lib, msg_config)
        self.stream = _VisionChannel(self.lib, stream_config)
        print(
            f"[zonal-app] Vision Protocol server stream=0.0.0.0:{self.args.stream_port} "
            f"message=0.0.0.0:{self.args.message_port}"
        )

    def close(self) -> None:
        for channel in (self.stream, self.msg):
            if channel is not None:
                channel.close()
        self.stream = None
        self.msg = None

    def send_frame(self, frame_bytes: bytes) -> bool:
        if self.stream is None or len(frame_bytes) != self.frame_bytes:
            return False
        info = ctypes.POINTER(VisionStreamInfo)()
        index = ctypes.c_uint8()
        ret = self.lib.Vision_API_GetStreamSendBuffer(self.stream.handle, ctypes.byref(info), ctypes.byref(index), BLOCKING)
        if ret != VISION_SUCCESS or not info:
            return False

        info.contents.id = 0x11
        info.contents.length = self.frame_bytes
        info.contents.seqNum = self.seq
        info.contents.timestamp = 0
        ctypes.memmove(info.contents.pBuffer, frame_bytes, self.frame_bytes)

        ret = self.lib.Vision_API_SendStream(self.stream.handle, info, index)
        if ret == VISION_SUCCESS:
            self.seq += 1
            return True
        return False

    def recv_result(self) -> Optional[Dict[str, Any]]:
        if self.msg is None:
            return None

        header = VisionMessageHeader()
        ret = self.lib.Vision_API_PeekMessage(self.msg.handle, ctypes.byref(header), ctypes.sizeof(header))
        if ret != VISION_SUCCESS:
            return None
        ret = self.lib.Vision_API_RecvMessage(self.msg.handle, ctypes.byref(header), ctypes.sizeof(header), BLOCKING)
        if ret != VISION_SUCCESS:
            return None

        payload = (ctypes.c_uint8 * header.length)()
        ret = self.lib.Vision_API_RecvMessage(self.msg.handle, payload, header.length, BLOCKING)
        if ret != VISION_SUCCESS or header.id != VISION_MSG_EVENT_RESULT_DATA_JSON:
            return None

        text = bytes(payload).rstrip(b"\0\r\n").decode("utf-8", errors="replace")
        return json.loads(text)


def vision_result_loop(
    bridge: VisionBridge,
    process_result,
    stop_event: threading.Event,
) -> None:
    """Read Vision Protocol JSON results and hand them to zonal_app's payload path."""
    while not stop_event.is_set():
        try:
            result = bridge.recv_result()
            if result is None:
                time.sleep(0.001)
                continue
            process_result(result)
        except Exception as exc:
            print(f"[zonal-app] Vision result error: {exc}")
            time.sleep(0.1)
