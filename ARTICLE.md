# A marathon inside the Honda City's power steering firmware

I started with a practical question: how much of the Honda City's steering behavior could be understood by looking inside its electric power steering controller?

The car was a Brazilian seventh-generation Honda City Touring, model year 2023, used with openpilot on a comma 3X. The research notes identified a steering intervention threshold around 23 km/h and conservative torque limits. I wanted to understand where those restrictions came from and whether the firmware contained parameters that could explain them.

That question turned into a research marathon across CAN diagnostics, security algorithms, firmware containers, binary comparisons, and finally the circuit board itself. Along the way, I reproduced an access algorithm, learned why authentication was not enough to read memory, analyzed firmware from other Honda models, and erased the EPS application during an unsuccessful reprogramming attempt.

This is the record of that work. The last state documented in the experiments is a responsive bootloader without a recovered application. There is no working T14 firmware modification at the end of this story. There is, however, a collection of code, observations, photographs, and failed approaches that someone else can build on.

## Finding the right controller

The target was recorded as EPS part `39990-T14-B030`. Before the reprogramming incident, the notes recorded calibration ID `53200T00B030M1` and ECU name `PG2C150109D`.

Those identifiers became the starting point for almost everything: comparing firmware, looking for related controllers, and deciding whether observations from another Honda model might apply to this one. They also created a trap. A similar name, vehicle generation, or calibration pattern can suggest a relationship without proving compatible hardware or memory layout.

The physical assembly was another useful correction. The City has assistance integrated into the steering column. Early comparisons with other vehicles had led the investigation toward assumptions about rack-mounted hardware. Looking at the actual assembly brought the target back into focus.

![Steering column assembly, with the EPS housing circled in the supplied photograph](photos/20260326_112510.jpg)

*The column assembly photographed during the research. The red annotation was already present in the supplied image.*

## Getting a conversation over CAN

The successful diagnostic path used the comma 3X connection at the camera harness. The recorded setup used bus 1 at 500 kbit/s, with request ID `0x18DA30F1` and response ID `0x18DAF130`.

CAN carries the frames. UDS supplies the diagnostic services, such as reading an identifier, changing a session, or requesting access. ISO-TP handles messages that do not fit inside a single CAN frame. A DID is a data identifier that the diagnostic client can ask the ECU to read.

The distinction matters because a failed request has several possible explanations. The tool may be on the wrong bus. Its transport code may be handling frames incorrectly. The service may require another session. Or the ECU may reject the operation even though communication is working.

The research encountered all of those kinds of ambiguity. Changes in the Panda receive API and assumptions about message layout had to be checked before interpreting a timeout as a property of the EPS. The OBD connection tested with a GODIAG adapter also did not reach the EPS in that setup, while the camera-harness path did.

Once communication was established, the ECU's responses became more useful than a simple supported/unsupported checklist. A service's behavior could change with the session and with whether the application or bootloader was handling the request.

## Reproducing security access

One of the early advances was reproducing the Level 7 seed/key calculation from the diagnostic software's security DLL.

In this mechanism, the ECU sends a challenge, usually called a seed. The client calculates a response, called a key. If the response is accepted, the ECU grants the corresponding access level.

For the T14 case studied here, the four-byte seed was handled as two 16-bit words. The first varied between observations. The second, `0x48A0`, selected the relevant entry in the extracted lookup table. The calculation combined additions, rotations, and XOR operations; the final two bytes of the key preserved the identifier from the seed.

The [published implementation](tools/honda_level7_keygen.py) includes the lookup table and calculation. One example recorded in the research is:

```text
Seed: 5B FE 48 A0
Key:  22 66 48 A0
```

Reproducing this calculation felt like an important step toward a firmware dump. The subsequent result was more specific: authentication succeeded, but ReadMemoryByAddress remained denied with NRC `0x33`.

NRC means negative response code. Here, `0x33` was reported as `securityAccessDenied`. The useful finding was that successful L7 access did not grant the memory access I wanted. It was an advance in understanding one mechanism, without solving firmware extraction.

There was also a separate Level 1 path that later proved sufficient to enter programming. A third access level, `0x41`, remained unresolved. The saved progress file records 104 tested candidate indices and no successful match. That closes out the candidate set used in that experiment; it does not establish that every possible implementation or source of constants was exhausted.

## The firmware collection

I assembled a collection of Honda firmware files to compare generations and look for patterns. One [HR-V EPS image](examples/hrv-brazil/README.md) is included as a binary example: `39990T7T_M020M1__A0099993.rwd`. It is 475,213 bytes and contains one block at `0x0000C000`. This gives readers a concrete file to inspect.

The local collection contained 87 distinct nonempty EPS payloads across 38 filename families when compressed and uncompressed copies were matched by their decompressed bytes. The examples that mattered most to this investigation were:

Some of the most relevant examples were:

| Family | Examples present in the snapshot | Role in the research |
|---|---|---|
| T38 | `39990T38_A050M1__A2303876.rwd` | Newer firmware container and calibration comparisons. |
| T39 | `39990T39_A140M1__A2303858.rwd.gz` | Comparison with a substantially different candidate speed value. |
| T43 | `39990T43_J030M1__A2303874.rwd` | Comparison with T38 and T60. |
| T60 | `39990T60_J040M1__A2303869.rwd` | Candidate speed threshold and assistance tables. |
| T9A | `39990T9A_P050M1__A0099993.rwd` | Previous-generation City comparison. |
| T9L | `39990T9L_M040M1__A0099993.rwd` | Another previous-generation City reference. |
| T5N | `39990-T5N-M020-M1.rwd.gz` | Fit/Jazz family comparison. |
| T7T | `39990T7T_M020M1__A0099993.rwd` | HR-V family comparison. |
| T7W | `39990-T7W-A020-M1.rwd.gz` | Additional comparison across payload transformations. |

The target EPS firmware, T14, was absent from the collection I analyzed. Having many other files was useful for forming hypotheses, but it did not substitute for the correct image.

Earlier notes mention larger collection totals. The numbers here describe the files available in the publication snapshot, rather than treating every historical count as independently verified.

## Opening the RWD container

A firmware update file is not necessarily a flat dump of the ECU's memory. In the studied RWD examples, the container carries metadata and blocks associated with destination addresses.

For the newer examples analyzed here, the signature was `5A 0D 0A`. The parser walked six header groups, then block descriptors containing a four-byte address, a four-byte length, and the block's data. The decoder also checked the stored additive checksum.

For the studied T38/T43/T60 payloads, the transformation reduced to:

```python
plaintext_byte = ((ciphertext_byte ^ 0xAF) + 0x9E) & 0xFF
```

The constants came from three bytes in the header: the first two combined through XOR, and the third supplied the addition. Other files in the research used different transformations. This formula belongs to the particular variant studied here.

The [decoder source](tools/rwd_newgen_decrypt.py) exposes the parsing and transformation directly. It produces both concatenated block data and a memory-layout output that preserves gaps between block addresses. That distinction matters when comparing offsets: an offset in a concatenated file is not automatically an address in the ECU.

The newer comparison files contained blocks at `0xA0058000` and `0xA0080000`. Those addresses were useful observations about those files. Treating them as the City's memory map would require separate evidence.

## Looking for calibration patterns

Once the payloads were readable, I compared numeric values, table shapes, and strings across firmware revisions.

The notes identified a candidate speed-related value at offset `0x0C8948` in the analyzed newer comparison binaries. Interpreted with eight fractional bits, `0x1700` corresponds to 23.0 and `0x1340` to 19.25. A T39 example was recorded with `0x0002`, a value close to zero on the same scale.

There were also groups interpreted as assistance curves and speed breakpoints. Those patterns were promising because they connected differences between firmware files to behavior worth investigating.

There are still three separate questions, though: what bytes are present, what the surrounding code does with them, and what effect a change has on the real controller. A plausible numeric interpretation answers only part of that chain.

The original notes sometimes called the T39 value proof of a disabled speed lockout. A more defensible conclusion is that the difference is a useful candidate for tracing through code. The research published here does not contain a controlled demonstration of that behavior, and the corresponding T14 field has not been located in a verified T14 image.

## Entering programming, then losing the application

The major turning point came on March 22.

Earlier attempts had suggested that the unresolved access level might be necessary to enter programming. Correcting the order of operations changed that result: extended session, Level 1 access, and then programming session succeeded.

The ECU accepted the initial configuration and the erase routine. The subsequent RequestDownload operation was rejected.

That left the EPS with an erased application and a bootloader that still answered diagnostic requests. The recorded consequence was loss of electrical steering assistance. The central mistake was reaching the erase step before establishing a complete recovery path with an image and parameters accepted by this controller.

The success of the preceding commands did not mean that firmware transfer would succeed. They were separate decisions made by the ECU.

The original recovery experiments taught a naming lesson: a command called `probe` or `scan` could include an erase operation. The streamlined recovery script in this repository reads JSONL records offline and never contacts a controller.

## What the recovery attempts actually established

The next sessions tried different address and size combinations, revisited configuration values, and compared the sequence against other implementations.

The preserved logs show a recurring pattern:

```text
Extended session: accepted
Level 1 access: accepted
Programming session: accepted
Initial configuration: accepted
Erase routine: accepted
Programming information: accepted
RequestDownload: rejected, NRC 0x31
```

The rejection was reported as `requestOutOfRange`. Address incompatibility was an important hypothesis, especially given that the comparison firmware belonged to other models. But the response alone did not prove that address was the only remaining issue. The request also carried a size and format, and its interpretation depended on the ECU's state and expectations.

The March 24 log contains 25 recorded download probes, all rejected with `0x31`. The final March 25 log contains 55, also all rejected. These are counts of logged probe events, not distinct addresses or a complete count of every experiment.

The saved scan state tells another part of the story: 16 entries were marked out of range, while 14 failed during preparation. Those 14 do not establish that the proposed address was tested and rejected.

There is also an identification discrepancy worth keeping visible. The general notes call the target `39990-T14-B030`, but F181 reads in the recovery logs return `39990-T14-B010`. That could reflect a difference between application and bootloader identification, or another distinction in the experimental record. The evidence here does not resolve it.

These are the kinds of details that disappear in a summary such as “all addresses failed.” Preserving precise outcomes makes it possible for the next person to ask a more precise question.

## Opening the housing changed the assumptions

By the end of March, the investigation had moved to the hardware.

The photographs show a board fitted around the steering assembly, with packaged ICs, exposed copper pads, and a Mitsubishi Electric logo. The board identification was recorded as `JQ331B41G05A`.

![PCB marking and Mitsubishi Electric logo](photos/20260330_145732.jpg)

*The manufacturer mark and PCB identifier are visible near the upper-left edge. The full-resolution photograph is included for inspection.*

This corrected an earlier assumption that the electronics were Bosch. Much of the software-side discussion had inherited platform labels from related vehicles. The actual board supplied a more direct piece of evidence.

The MCU close-up added another lead. The March teardown notes interpreted the markings as a Renesas `R7F701312EAFP`, in the RH850/P1M family. I have included both the close-up and the surrounding board photographs so that the identification can be checked independently. The exact orderable part number is an interpretation of the marking, rather than a complete part number printed clearly in the photograph.

![MCU marking close-up](photos/eps-honda-1.jpeg)

*The supplied close-up after the marking was exposed. See the [photo index](photos/README.md) for additional views.*

The photographs do not identify who wrote every part of the firmware, and they do not demonstrate usable debug access. They do give the next stage of research a concrete board and a candidate MCU family, instead of relying primarily on comparisons with another car.

No successful physical flash extraction is documented in this collection.

## What I am leaving for the next person

The repository includes the L7 calculation, the RWD decoder, the HR-V binary example, a streamlined diagnostic script, an offline recovery-log reader, and all eight supplied photographs. The [continuation notes](docs/CONTINUING.md) describe the main open questions.

The most useful next contribution would be a verified image from the matching T14 controller, with enough identification and provenance to establish what it belongs to. A confirmed identification of the MCU and a documented memory map would also narrow the problem substantially.

There is useful work to do without modifying a controller: reconcile B010 and B030, inspect the full-resolution markings, trace candidate calibration fields through code, and compare update containers while preserving the distinction between file offsets and destination addresses.

I also want to preserve the approaches that failed. L7 authentication did not unlock memory reading. Other Honda firmware did not provide a demonstrated T14 replacement. Entering programming did not guarantee a successful download. Opening the controller corrected assumptions that had survived a considerable amount of software analysis.

Those results define where this investigation stopped. The [continuation notes](docs/CONTINUING.md) turn them into specific questions for anyone who wants to pick it up.
