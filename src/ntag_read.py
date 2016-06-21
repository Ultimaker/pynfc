#! /usr/bin/env python3

from . import nfc
import ctypes
import binascii

MC_AUTH_A = 0x60
MC_AUTH_B = 0x61
MC_READ = 0x30
MC_WRITE = 0xA0
MC_TRANSFER = 0xB0
MC_DECREMENT = 0xC0
MC_INCREMENT = 0xC1
MC_STORE = 0xC2
card_timeout = 10

context = ctypes.pointer(nfc.nfc_context())
nfc.nfc_init(ctypes.byref(context))

conn_strings = (nfc.nfc_connstring * 10)()
devices_found = nfc.nfc_list_devices(context, conn_strings, 10)

if not devices_found:
    print("No devices found")
    exit(-1)

device = nfc.nfc_open(context, conn_strings[0])

init = nfc.nfc_initiator_init(device)

nt = nfc.nfc_target()

mods = [(nfc.NMT_ISO14443A, nfc.NBR_106)]
modulations = (nfc.nfc_modulation * len(mods))()
for i in range(len(mods)):
    modulations[i].nmt = mods[i][0]
    modulations[i].nbr = mods[i][1]

res = nfc.nfc_initiator_poll_target(device, modulations, len(modulations), 10, 2, ctypes.byref(nt))

if res < 0:
    raise IOError("NFC Error whilst polling")

uidLen = 7
uid = bytearray([nt.nti.nai.abtUid[i] for i in range(uidLen)])
print("uid = {}".format(binascii.hexlify(uid)))

# setup device
if nfc.nfc_device_set_property_bool(device, nfc.NP_ACTIVATE_CRYPTO1, True) < 0:
    raise Exception("Error setting Crypto1 enabled")
if nfc.nfc_device_set_property_bool(device, nfc.NP_INFINITE_SELECT, False) < 0:
    raise Exception("Error setting Single Select option")
if nfc.nfc_device_set_property_bool(device, nfc.NP_AUTO_ISO14443_4, False) < 0:
    raise Exception("Error setting No Auto ISO14443-A jiggery pokery")
if nfc.nfc_device_set_property_bool(device, nfc.NP_HANDLE_PARITY, True) < 0:
    raise Exception("Error setting Easy Framing property")

# Select card, but waits for tag the be removed and placed again
# nt = nfc.nfc_target()
# _ = nfc.nfc_initiator_select_passive_target(device, modulations[0], None, 0, ctypes.byref(nt))
# uid = bytearray([nt.nti.nai.abtUid[i] for i in range(nt.nti.nai.szUidLen)])
# print("uid = {}".format(binascii.hexlify(uid)))

def set_easy_framing(enable=True):
    if nfc.nfc_device_set_property_bool(device, nfc.NP_EASY_FRAMING, enable) < 0:
        raise Exception("Error setting Easy Framing property")

# _read_block
set_easy_framing(True)

def read_simple(pages):
    for block in range(pages):  # 45 pages in NTAG213
        data = tranceive_bytes(device, bytes([MC_READ, block]), 16)
        print("{:3}: {}".format(block, binascii.hexlify(data)))

def tranceive_bytes(device, transmission, receive_length):
    """
    Send the bytes in the send
    :param device: The device *via* which to transmit the bytes
    :param transmission: Data or command to send:
    :type transmission bytes
    :param receive_length: how many bytes to receive?
    :type receive_length int
    :return:
    """
    abttx = (ctypes.c_uint8 * len(transmission))()  # command length
    for index, byte in enumerate(transmission):
        abttx[index] = byte

    abtrx = (ctypes.c_uint8 * receive_length)()  # 16 is the minimum
    res = nfc.nfc_initiator_transceive_bytes(device,
                                             ctypes.pointer(abttx), len(abttx),
                                             ctypes.pointer(abtrx), len(abtrx),
                                             0)
    if res < 0:
        raise IOError("Error reading data")

    data = bytes(abtrx[:res])
    return data

read_simple(45)

nfc.nfc_close(device)

nfc.nfc_exit(context)