#!/usr/bin/env python3
"""Read Honda City EPS identifiers or a requested memory range through a Panda.

Requires the compatible Panda and opendbc versions used by the operator.
The recorded T14 experiments did not obtain a complete firmware dump.
Memory reads may be denied even after authentication. This tool never fills gaps.
"""

import argparse
import hashlib
import struct
import sys
from pathlib import Path

EPS_ADDRESS = 0x18DA30F1
DEFAULT_BUS = 1


def level1_key(seed):
    """Calculate the recorded two-byte Honda EPS Level 1 response."""
    if len(seed) != 2:
        raise ValueError(f"Expected a two-byte Level 1 seed, got {len(seed)}")
    value = int.from_bytes(seed, 'big')
    key = ((value + 0x0111) ^ ((value * 0x0112) % 0x1120)) & 0xFFFF
    return struct.pack('>H', key)


def open_client(bus):
    try:
        from panda import Panda
        from opendbc.car.uds import UdsClient
    except ImportError as exc:
        raise RuntimeError('Panda and opendbc must be available on the diagnostic host') from exc
    panda = Panda()
    try:
        panda.set_safety_mode(3)
        client = UdsClient(panda, EPS_ADDRESS, bus=bus, timeout=10)
        return panda, client
    except Exception:
        panda.close()
        raise


def authenticate(client, level):
    if level == 'none':
        return
    from opendbc.car.uds import SESSION_TYPE
    client.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)
    if level == 'l1':
        seed = client.security_access(0x01)
        client.security_access(0x02, level1_key(seed))
    elif level == 'l7':
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
        from honda_level7_keygen import compute_key
        seed = client.security_access(0x07)
        key = compute_key(seed)
        if key is None:
            raise ValueError(f'No L7 table entry for seed suffix {seed[-2:].hex()}')
        client.security_access(0x08, key)


def read_range(client, address, size, chunk_size):
    """Return only a complete, contiguous read. Propagate the first failure."""
    result = bytearray()
    while len(result) < size:
        count = min(chunk_size, size - len(result))
        data = client.read_memory_by_address(
            address + len(result), count, memory_address_bytes=4, memory_size_bytes=2
        )
        if len(data) != count:
            raise IOError(f'Short read at 0x{address + len(result):08X}: {len(data)} of {count} bytes')
        result.extend(data)
    return bytes(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bus', type=int, default=DEFAULT_BUS)
    parser.add_argument('--access', choices=['none', 'l1', 'l7'], default='none')
    actions = parser.add_subparsers(dest='action', required=True)
    info = actions.add_parser('info', help='Read a specified DID without changing flash')
    info.add_argument('did', type=lambda value: int(value, 0), help='DID, for example 0xF181')
    read = actions.add_parser('read', help='Attempt a contiguous memory read')
    read.add_argument('address', type=lambda value: int(value, 0))
    read.add_argument('size', type=lambda value: int(value, 0))
    read.add_argument('output', type=Path)
    read.add_argument('--chunk', type=int, default=128)
    args = parser.parse_args()
    if args.action == 'read':
        if not 0 <= args.address <= 0xFFFFFFFF or args.size <= 0:
            parser.error('address must fit in 32 bits and size must be positive')
        if args.address + args.size > 0x100000000:
            parser.error('requested range exceeds 32-bit address space')
        if not 1 <= args.chunk <= 0xFFFF:
            parser.error('chunk must be between 1 and 65535 bytes')
    elif not 0 <= args.did <= 0xFFFF:
        parser.error('DID must fit in 16 bits')
    panda, client = open_client(args.bus)
    try:
        authenticate(client, args.access)
        if args.action == 'info':
            data = client.read_data_by_identifier(args.did)
            print(f'0x{args.did:04X}: {data.hex()}')
        else:
            data = read_range(client, args.address, args.size, args.chunk)
            args.output.write_bytes(data)
            print(f'{len(data)} bytes saved to {args.output}; SHA-256 {hashlib.sha256(data).hexdigest()}')
    finally:
        panda.close()


if __name__ == '__main__':
    main()
