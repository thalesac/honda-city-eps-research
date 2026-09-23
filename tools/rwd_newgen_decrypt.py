#!/usr/bin/env python3
"""
Honda New-Gen 0x5A RWD Decryptor
For 2021-2023 Bosch EPS firmwares (Renesas RH850)

DISCOVERED CIPHER:
  plaintext = ((ciphertext XOR 0xAF) + 0x9E) & 0xFF

  Where 0xAF = key[0] XOR key[1] = 0xBF XOR 0x10
  And   0x9E = key[2]

  Using the rwd-xray formula: (((e XOR k0) XOR k1) ADD k2) & 0xFF
  With keys from header: k0=0xBF, k1=0x10, k2=0x9E

FILE FORMAT (0x5A multi-block):
  Signature: 5A 0D 0A
  Headers: 6 header groups (versions, security keys, encryption key)
  Firmware blocks: MULTIPLE blocks, each with:
    - Start address (4 bytes, big-endian)
    - Data length (4 bytes, big-endian)
    - Encrypted data (length bytes)
  File checksum: 4 bytes (little-endian, sum of all preceding bytes)

MEMORY MAP (all three files identical structure):
  Block 1: 0xA0058000, 0x8000 bytes (32KB)  - Exception/vector table
  Block 2: 0xA0080000, 0x180000 bytes (1.5MB) - Main firmware + calibration
"""

import os
import sys
import struct
import string
from collections import Counter

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(BASE_DIR, "eps-rwd-samples")
OUTPUT_DIR = os.path.join(BASE_DIR, "analysis", "rwd_decoded")


def build_decrypt_table(k0, k1, k2):
    """Build the 256-byte decryption lookup table."""
    table = bytearray(256)
    for e in range(256):
        table[e] = ((e ^ k0 ^ k1) + k2) & 0xFF
    return bytes(table)


def build_encrypt_table(decrypt_table):
    """Build the inverse (encryption) lookup table."""
    table = bytearray(256)
    for e in range(256):
        table[decrypt_table[e]] = e
    return bytes(table)


def parse_5a_header(data):
    """Parse 0x5A format header, return headers dict and end offset."""
    assert data[0] == 0x5A, f"Not 0x5A format: {data[0]:#x}"
    assert data[1:3] == b'\x0d\x0a', "Missing CRLF"

    idx = 3
    headers = []
    for _ in range(6):
        count = data[idx]; idx += 1
        values = []
        for _ in range(count):
            length = data[idx]; idx += 1
            value = data[idx:idx+length]
            idx += length
            values.append(value)
        headers.append(values)
    return headers, idx


def parse_firmware_blocks(data, header_end):
    """Parse multiple firmware blocks from the data section."""
    blocks = []
    idx = header_end
    file_end = len(data) - 4  # exclude checksum

    while idx + 8 <= file_end:
        start_addr = struct.unpack('!I', data[idx:idx+4])[0]
        block_len = struct.unpack('!I', data[idx+4:idx+8])[0]

        if block_len == 0 or block_len > file_end - idx - 8:
            break

        block_data = data[idx+8:idx+8+block_len]
        blocks.append({
            'address': start_addr,
            'length': block_len,
            'data': block_data,
            'file_offset': idx + 8,
        })
        idx += 8 + block_len

    return blocks


def decrypt_rwd(filepath, output_dir=None):
    """Decrypt a new-gen 0x5A RWD file."""
    if output_dir is None:
        output_dir = OUTPUT_DIR

    fname = os.path.basename(filepath)
    base = fname.replace('.rwd', '')

    print(f"\n{'='*60}")
    print(f"Decrypting: {fname}")
    print(f"{'='*60}")

    with open(filepath, 'rb') as f:
        data = f.read()

    # Parse header
    headers, header_end = parse_5a_header(data)

    # Extract key info
    enc_key = headers[5][0]
    k0, k1, k2 = enc_key[0], enc_key[1], enc_key[2]
    print(f"  Encryption key: {enc_key.hex()} ({k0:#04x}, {k1:#04x}, {k2:#04x})")

    # Extract firmware version strings
    print(f"  Supported versions:")
    for v in headers[3]:
        ver_str = v.rstrip(b'\x00').decode('ascii', errors='replace')
        print(f"    {ver_str}")

    # Verify checksum
    file_checksum = struct.unpack('<I', data[-4:])[0]
    calc_checksum = sum(data[:-4]) & 0xFFFFFFFF
    assert file_checksum == calc_checksum, f"Checksum mismatch: {file_checksum:#x} vs {calc_checksum:#x}"
    print(f"  File checksum: OK ({file_checksum:#010x})")

    # Parse firmware blocks
    blocks = parse_firmware_blocks(data, header_end)
    print(f"  Firmware blocks: {len(blocks)}")

    # Build decryption table
    decrypt_table = build_decrypt_table(k0, k1, k2)

    # Decrypt each block
    total_size = 0
    decrypted_blocks = []

    for i, block in enumerate(blocks):
        addr = block['address']
        length = block['length']
        encrypted = block['data']

        decrypted = encrypted.translate(decrypt_table)
        decrypted_blocks.append({
            'address': addr,
            'length': length,
            'data': decrypted,
        })

        total_size += length

        # Count printable ASCII
        printable = sum(1 for b in decrypted if 32 <= b < 127)
        pct = printable / length * 100

        # Count 0xFF (erased flash)
        ff_count = decrypted.count(0xFF)
        ff_pct = ff_count / length * 100

        print(f"  Block {i+1}: {addr:#010x} - {addr+length:#010x} ({length:,} bytes)")
        print(f"    Printable ASCII: {pct:.1f}%, Erased (0xFF): {ff_pct:.1f}%")

    # Save outputs
    os.makedirs(output_dir, exist_ok=True)

    # 1. Raw concatenated decrypted data
    raw_path = os.path.join(output_dir, f"{base}_decrypted.bin")
    with open(raw_path, 'wb') as f:
        for block in decrypted_blocks:
            f.write(block['data'])
    print(f"\n  Saved concatenated: {raw_path} ({total_size:,} bytes)")

    # 2. Memory-mapped binary (with gaps filled by 0xFF)
    base_addr = decrypted_blocks[0]['address']
    end_addr = decrypted_blocks[-1]['address'] + decrypted_blocks[-1]['length']
    mem_size = end_addr - base_addr

    mem_data = bytearray(b'\xFF' * mem_size)
    for block in decrypted_blocks:
        offset = block['address'] - base_addr
        mem_data[offset:offset+block['length']] = block['data']

    mem_path = os.path.join(output_dir, f"{base}_memory.bin")
    with open(mem_path, 'wb') as f:
        f.write(mem_data)
    print(f"  Saved memory-mapped: {mem_path} ({mem_size:,} bytes, base={base_addr:#010x})")

    # 3. Search for strings to validate decryption
    full_dec = bytes(mem_data)
    print(f"\n  Validation:")

    # Look for part number
    for v in headers[3]:
        ver_str = v.rstrip(b'\x00').decode('ascii', errors='replace')
        short = ver_str[:9]  # e.g., "39990-T38"
        if short.encode() in full_dec:
            idx = full_dec.find(short.encode())
            ctx = full_dec[idx:idx+20]
            print(f"    Found '{short}' at memory offset {idx:#x} (addr {base_addr+idx:#010x})")

    # Look for common firmware strings
    for needle in [b'Bosch', b'BOSCH', b'Honda', b'HONDA', b'EPS', b'Copyright', b'Error', b'Version']:
        if needle in full_dec:
            idx = full_dec.find(needle)
            # Get surrounding context
            start = max(0, idx - 4)
            end = min(len(full_dec), idx + 40)
            ctx = full_dec[start:end]
            printable_ctx = ''.join(chr(b) if 32 <= b < 127 else '.' for b in ctx)
            print(f"    Found '{needle.decode()}' at offset {idx:#x}: '{printable_ctx}'")

    # Find all readable strings >= 10 chars
    long_strings = []
    current = []
    for j, b in enumerate(full_dec):
        if 32 <= b < 127:
            current.append(chr(b))
        else:
            if len(current) >= 10:
                long_strings.append((j - len(current), ''.join(current)))
            current = []
    if len(current) >= 10:
        long_strings.append((len(full_dec) - len(current), ''.join(current)))

    print(f"\n  Readable strings (>= 10 chars): {len(long_strings)} found")
    for off, s in long_strings[:30]:
        addr = base_addr + off
        print(f"    {addr:#010x}: '{s[:80]}'")

    return decrypted_blocks, decrypt_table


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Decode the studied 0x5A XOR/ADD RWD variant offline.")
    parser.add_argument("files", nargs="+", help="Uncompressed .rwd inputs")
    parser.add_argument("-o", "--output-dir", required=True)
    args = parser.parse_args()
    for filepath in args.files:
        decrypt_rwd(filepath, args.output_dir)


if __name__ == "__main__":
    main()
