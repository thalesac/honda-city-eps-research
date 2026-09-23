# Research tools

These tools operate on local data. Python 3 and the standard library are sufficient.

## Level 7 seed/key calculation

```bash
python3 tools/honda_level7_keygen.py 5bfe48a0
```

The recorded example produces `226648a0`. The implementation includes the lookup table and computation reconstructed during the research. It calculates a response locally; it does not contact an ECU. Successful L7 access did not unlock memory reading on the T14 in the recorded experiments.

## Decode the studied newer RWD variant

```bash
python3 tools/rwd_newgen_decrypt.py /path/to/example.rwd -o /tmp/eps-decoded
```

Use an uncompressed RWD file from the studied XOR/ADD variant. The output contains concatenated decrypted blocks and a memory-layout file. The output offsets differ when the source blocks have gaps. This is the research decoder, not a general validator for arbitrary RWD files. Its checksum check uses Python assertions, so do not run it with `python -O`.

Publication edits replace the original machine-specific paths and fixed sample list with a command-line input and output directory. The parsing and byte-transformation functions are retained.
