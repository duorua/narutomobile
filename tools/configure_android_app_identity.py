#!/usr/bin/env python3

import argparse
import re
from pathlib import Path
from typing import Optional

PUBLIC_ID = "man"
PUBLIC_LABEL = "MAN"
INTERNAL_ID = "man.ci"
INTERNAL_LABEL = "MAN 内测版"
AGENT_ABI_PATTERN = re.compile(r"^  abi: \[[^\]\n]*\]")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Configure the Android app identity")
    parser.add_argument(
        "--distribution",
        choices=("public", "internal"),
        required=True,
        help="artifact distribution",
    )
    parser.add_argument(
        "--profile",
        type=Path,
        default=Path("Android/profile.yaml"),
        help="Android profile path",
    )
    parser.add_argument(
        "--agent-abi",
        choices=("arm64-v8a", "x86_64"),
        help="replace the profile's agent ABI list with a single ABI",
    )
    return parser.parse_args()


def has_identity(text: str, app_id: str, label: str) -> bool:
    return text.count(f"  id: {app_id}\n") == 1 and text.count(f"  label: {label}\n") == 1


def replace_agent_abi(text: str, agent_abi: str) -> str:
    lines = text.splitlines(keepends=True)
    in_agent_section = False
    matches = []
    for index, line in enumerate(lines):
        content = line.rstrip("\r\n")
        if content == "agent:":
            in_agent_section = True
            continue
        if in_agent_section and content and not content[0].isspace():
            break
        if in_agent_section and AGENT_ABI_PATTERN.fullmatch(content):
            matches.append(index)
    if len(matches) != 1:
        raise SystemExit(
            f"expected exactly one agent.abi list in the profile, found {len(matches)}",
        )

    index = matches[0]
    newline = lines[index][len(lines[index].rstrip("\r\n")) :]
    lines[index] = f"  abi: [{agent_abi}]{newline}"
    return "".join(lines)


def configure(profile: Path, distribution: str, agent_abi: Optional[str] = None) -> None:
    text = profile.read_text(encoding="utf-8")
    original_text = text
    has_public_identity = has_identity(text, PUBLIC_ID, PUBLIC_LABEL)
    has_internal_identity = has_identity(text, INTERNAL_ID, INTERNAL_LABEL)
    if distribution == "internal":
        if has_public_identity and has_internal_identity:
            raise SystemExit(f"found both public and internal app identities in {profile}")
        if has_public_identity:
            text = text.replace(f"  id: {PUBLIC_ID}\n", f"  id: {INTERNAL_ID}\n")
            text = text.replace(
                f"  label: {PUBLIC_LABEL}\n",
                f"  label: {INTERNAL_LABEL}\n",
            )
        elif not has_internal_identity:
            raise SystemExit(
                f"could not identify public or internal app identity in {profile}",
            )
    else:
        if not has_public_identity or has_internal_identity:
            raise SystemExit(f"could not identify public app identity in {profile}")
    if agent_abi is not None:
        text = replace_agent_abi(text, agent_abi)
    if text != original_text:
        profile.write_text(text, encoding="utf-8")


def main() -> None:
    args = parse_args()
    configure(args.profile, args.distribution, args.agent_abi)


if __name__ == "__main__":
    main()
