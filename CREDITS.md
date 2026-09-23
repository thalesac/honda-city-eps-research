# Credits and provenance

Research and photographs: Thales.

This work builds on the Honda EPS research community and tools including openpilot/Panda, opendbc, rwd-xray, and AutoECU. Their complete repositories are not vendored here, and their licenses continue to apply to their own code.

- openpilot and Panda provided the diagnostic hardware/software context used in the vehicle experiments.
- opendbc supplied the UDS client used by the experimental scripts.
- rwd-xray provided prior work on Honda update containers and payload transformations. The decoder's original comments acknowledge its formula.
- AutoECU served as a programming-sequence reference during the research.
- Analysis of Honda diagnostic software informed the reconstructed security algorithm and update sequence. Decompiled vendor applications and installers are not included.

The MIT license covers the contributor-authored material in this publication, including the article, tooling, and photographs, to the extent the contributors hold those rights. The original HR-V firmware in `examples/hrv-brazil/` is third-party material and is excluded from the MIT grant. See the notice alongside that file.

The article names the original research tools and the HR-V example includes its SHA-256 hash. The published code is a focused rewrite for readers who want to continue the investigation.
