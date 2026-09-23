# Diagnostic and recovery research tools

The original research used a comma 3X and Panda to communicate with the City EPS. These compact scripts keep the parts that help another researcher inspect a controller and interpret recovery results.

## Read an identifier or memory range

`eps_dump.py` connects through Panda and opendbc to the EPS address observed in the research. It can read one DID or attempt a requested memory range:

```bash
python3 experimental/eps_dump.py info 0xF181
python3 experimental/eps_dump.py --access l7 read 0x4000 0x100 output.bin
```

The `read` command saves data only if every requested chunk succeeds. L1 and L7 authentication are optional; neither unlocked memory reading in the documented T14 experiments. The program reports errors directly and does not fill unreadable regions with substitute bytes. It does not erase or write flash.

The hardware path requires compatible Panda and opendbc installations. It has not been rerun on the vehicle since this refactor. Confirm the bus and connection on your setup.

## Summarize recovery logs offline

`eps_recovery.py` takes JSONL logs from the original investigation format and distinguishes RequestDownload responses from failures that occurred before the request:

```bash
python3 experimental/eps_recovery.py /path/to/eps_recovery.log --show-probes
python3 experimental/eps_recovery.py --state /path/to/eps_recovery_state.json
```

The script does not communicate with a vehicle. The [article](../ARTICLE.md) records the original programming sequence and the observed failures.
