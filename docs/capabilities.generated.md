# Executable Capability Baseline

Generated from registered handlers for file-uncorrupter 0.4.0.
Runtime tool availability can narrow conditional operations; run `file-uncorrupter capabilities --format json` for the current machine.

| Family | Variants | Repair | Normalize | Extract | Preview | Carve | Availability | Fidelity |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| archive | zip, tar | partial | none | validated | none | partial | available | Valid members require bounded decompression and checksum validation; ambiguous local-header entries are not reconstructed. |
| external_archive | 7z, rar | none | none | none | none | none | partial | Extraction is available only when the exact 7z-compatible tool is recorded and bounded validation succeeds. |
| image | png, gif, bmp, webp, tiff, heif, avif, jp2, raw | partial | partial | none | partial | partial | available | Native repairs are limited to structurally derivable lengths, CRCs, and trailers. Animation and multipage validation is explicit; first-frame output is preview only. |
| jpeg | jpeg | validated | baseline | none | baseline | partial | available | JPEG repair candidates are independently decoded before selection; re-encoded normalize and preview artifacts are labeled as derivatives. |
| legacy_office | doc, xls, ppt | none | none | none | none | none | partial | Detection and inert inspection only. PDF preview is explicitly unavailable because LibreOffice is not available. |
| media | mp4, mov, mkv, webm, avi, mpegts, mpegps, flv, asf, wmv, wav, mp3, flac, aac, ogg | partial | none | none | none | partial | available | Native evidence covers container boundaries and continuity. Normalize, stream extraction, and preview are explicitly unavailable because FFmpeg and ffprobe are not both available. |
| package_document | docx, docm, xlsx, xlsm, pptx, pptm, odt, ods, odp | partial | none | validated | partial | partial | available | Full-package status requires every required part and parseable package metadata; otherwise extracted parts are partial content. |
| pdf | pdf | partial | none | partial | none | partial | available | Native repair strips an unambiguous prefix, appends EOF, and rebuilds a classic xref from explicit object headers; it does not invent page content. |
| rtf | rtf | none | none | partial | partial | none | partial | RTF text is a partial inert extraction; formatting and embedded objects are not claimed as recovered. |
| text | txt, markdown, log, csv, json, xml, html | partial | validated | validated | baseline | partial | available | Recovered bytes remain unchanged; decoded text maps emitted characters and replacements to source byte ranges. |

Quality gate: **passed**. Advertised operations have registered fixture evidence; `none` means the goal is rejected rather than silently substituted.
