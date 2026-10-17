"""Build a pinned GALOSH CPU reference with explicit AArch64 portability guards."""

import argparse
import hashlib
import json
import platform
import subprocess
from pathlib import Path

from demosaic.safety import writable_path

COMMIT = "11de0593cc8091933ad76d1d6d873f7dee537f15"
NOTE = (
    "/* Local AArch64 build change, 2026-10-17: guard x86 intrinsic headers and two "
    "unused archived SSE helpers. Canonical GALOSH processing code is unchanged. */\n"
)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main(root, output):
    assert platform.machine() == "aarch64"
    assert (
        subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        == COMMIT
    )
    assert not subprocess.check_output(
        ["git", "-C", str(root), "diff", "--", "standalone", "LICENSE", "NOTICE"]
    )
    output = writable_path(output)
    if output.exists():
        raise ValueError("Build output exists; inspect it or select a fresh path")
    output.mkdir(parents=True)
    source = root / "standalone"
    header = (source / "galosh_cpu.h").read_text()
    includes = (
        "#include <xmmintrin.h>  /* SSE  */\n"
        "#include <emmintrin.h>  /* SSE2 */\n"
        "#include <pmmintrin.h>  /* SSE3: _mm_hadd_ps */"
    )
    assert header.count(includes) == 1
    header = header.replace(includes, "#if defined(__SSE2__)\n" + includes + "\n#endif")
    (output / "galosh_cpu.h").write_text(NOTE + header)
    code = (source / "galosh_raw_cpu.c").read_text()
    begin = code.index("static inline void wht_decompose_8x8(")
    end = code.index(
        "/* ============================================================\n * [ARCHIVED] galosh_pass1_cfa",
        begin,
    )
    assert code.count("wht_decompose_8x8(") == code.count("wht_reconstruct_8x8(") == 1
    code = code[:begin] + "#if defined(__SSE2__)\n" + code[begin:end] + "#endif\n\n" + code[end:]
    (output / "galosh_raw_cpu.c").write_text(NOTE + code)
    for name in ["LICENSE", "NOTICE"]:
        (output / name).write_bytes((root / name).read_bytes())
    binary = output / "galosh_raw_cpu"
    command = [
        "gcc",
        "-O3",
        "-fopenmp",
        "-std=gnu11",
        "-ffp-contract=off",
        str(output / "galosh_raw_cpu.c"),
        "-o",
        str(binary),
        "-lm",
    ]
    with (output / "compiler.log").open("xb") as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    result = {
        "status": "built-local-AArch64-canonical-CPU-reference-no-quality-result",
        "official_commit": COMMIT,
        "command": command,
        "compiler": subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0],
        "official_sources": {
            str(p): sha(p)
            for p in [
                source / "galosh_raw_cpu.c",
                source / "galosh_cpu.h",
                root / "LICENSE",
                root / "NOTICE",
            ]
        },
        "local_sources": {
            str(p): sha(p) for p in [output / "galosh_raw_cpu.c", output / "galosh_cpu.h"]
        },
        "binary": {"path": str(binary), "sha256": sha(binary)},
        "changes": "Guard three x86 intrinsic includes and two unused archived static inline helpers (definitions have zero call sites). Canonical processing code is unchanged. FP contraction off, no fast-math. Cross-architecture numerical identity is unproven; this is an explicit local CPU port, not the original x86 executable.",
        "driver_sha256": sha(__file__),
    }
    (output / "build-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / Path(__file__).name).write_bytes(Path(__file__).read_bytes())
    print(json.dumps({"build": str(output / "build-receipt.json"), "binary": result["binary"]}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    main(args.root, args.output)
