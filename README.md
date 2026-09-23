# Honda City EPS firmware research

Research notes, photographs, a Honda HR-V firmware example, and source code from investigating the electric power steering controller in a Brazilian seventh-generation Honda City.

**Read the article: [A marathon inside the Honda City's power steering firmware](ARTICLE.md).**

The work covers CAN diagnostics, security access, RWD firmware analysis, an unsuccessful reprogramming attempt, and the move to physical inspection. The recorded experiments took place in February and March 2026.

The last documented state is an erased application with a responsive bootloader. This collection does not contain a verified T14 firmware dump, a completed recovery, or a working T14 steering modification.

| Material | What you can use it for |
|---|---|
| [Article](ARTICLE.md) | Follow the investigation, including failed approaches and revised conclusions. |
| [HR-V binary example](examples/hrv-brazil/README.md) | Inspect an original RWD file and its block layout. |
| [EPS photographs](photos/README.md) | Inspect the assembly, PCB marking, MCU, and surrounding circuitry. |
| [Source code](tools/README.md) | Reproduce the L7 calculation and decode the studied RWD variant. |
| [Diagnostic and recovery tools](experimental/README.md) | Read ECU data and summarize recovery logs. |
| [Continuing the work](docs/CONTINUING.md) | Find concrete unanswered questions and useful contributions. |

A [Honda HR-V EPS binary example](examples/hrv-brazil/README.md) is included with its hash and block layout.

The diagnostic script can read identifiers and attempt a memory read. No complete T14 dump was obtained during the recorded research. The recovery script summarizes JSONL logs offline.

Authored material is available under the [MIT license](LICENSE). See [credits and provenance](CREDITS.md) for the tools this work builds on and the origin of the included files.
