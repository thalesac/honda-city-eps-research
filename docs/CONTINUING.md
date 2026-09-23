# Continuing the investigation

## Establish the identity of each unit

Reconcile the B030 target identification with B010 returned by F181 in the bootloader logs. A useful contribution would tie together the assembly label, PCB photograph, session state, application identifiers, and bootloader identifiers for one known unit.

## Verify the MCU interpretation

The teardown notes identify `R7F701312EAFP` / RH850/P1M. Compare that interpretation with the supplied markings and authoritative part-marking information. The public record should distinguish the visible marking from the inferred orderable number. Do not inherit a debug pinout from another package without confirming it.

## Obtain a matching, verifiable image

A dump or update image needs a hash, unit identification, extraction context, and a clear description of what memory it covers. An application update container may omit bootloader or data-flash regions. Preserve address gaps and distinguish physical addresses from file offsets.

## Trace calibration candidates through code

The research identified candidate speed and assistance values in other firmware families. Follow their references and use sites before assigning functional meaning. An interpreted number in another model is not a known T14 parameter.

## Reconstruct rejected requests precisely

For any future logs, distinguish a completed RequestDownload rejection from a session-preparation failure. Compare address, length, format, and preceding state together. A negative response does not uniquely identify the failing condition. The included offline log reader can summarize JSONL events.

## Useful contributions

- A corrected hardware identification supported by photographs or part-marking documentation.
- A memory map tied to a specific matching controller.
- Annotated disassembly connecting a candidate calibration field to its use.
- A reproducible parser correction with a small example and expected interpretation.
- Evidence of a completed recovery, with exact unit and firmware identifiers.

For any result, include the setup, tool revision, inputs, observed outputs, and limits of the conclusion. Negative results are useful when the conditions are clear.
