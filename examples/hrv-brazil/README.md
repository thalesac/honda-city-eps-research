# Honda HR-V EPS binary example

[Download the original RWD file](39990T7T_M020M1__A0099993.rwd).

This is the T7T HR-V EPS image used as a comparison during the City investigation. The file is included unchanged as a concrete binary example for offline analysis.

| Property | Value |
|---|---|
| Filename | `39990T7T_M020M1__A0099993.rwd` |
| File size | 475,213 bytes |
| SHA-256 | `ebb0afe90afec24e9c966e1e08788a7c1f3f021b885a3060d5b6e05a067828cc` |
| Signature | `5A 0D 0A` |
| Version strings | `39990-T7T-M010`, `39990-T7T-M020` |
| Block address | `0x0000C000` |
| Block length | `0x74000` / 475,136 bytes |
| Block data offset in this file | `0x49` |

The stored additive checksum matches the sum of the preceding file bytes modulo 2^32.

This T7T file is an HR-V comparison example. Its compatibility with a particular vehicle or with the City T14 has not been established here.

## Inspect the container

From the repository root:

```bash
sha256sum examples/hrv-brazil/39990T7T_M020M1__A0099993.rwd
```

The existing parser can inspect the headers and block descriptors without applying a payload transformation:

```python
import sys
from pathlib import Path

sys.path.insert(0, 'tools')
from rwd_newgen_decrypt import parse_5a_header, parse_firmware_blocks

data = Path('examples/hrv-brazil/39990T7T_M020M1__A0099993.rwd').read_bytes()
headers, offset = parse_5a_header(data)
print([value.decode('ascii').rstrip('\x00') for value in headers[3]])
for block in parse_firmware_blocks(data, offset):
    print(hex(block['address']), block['length'], hex(block['file_offset']))
```

The newer T38/T43/T60 payload transformation is not established as the correct HR-V decoder merely because the header parser accepts this file. Historical HR-V notes disagree about the transformation. This example preserves the original bytes and makes no claim that a decoded HR-V image has been validated here.

## Third-party notice

This original vendor firmware is third-party material. It is not licensed under the repository's MIT license, and its inclusion does not assert ownership or grant additional rights to the firmware. The accompanying research explanations and tools are covered by the repository license.
