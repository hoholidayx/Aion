#!/usr/bin/env python3
"""Manage the local Aion Web and Image MCP services."""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ACTIONS = ("start", "stop", "restart", "status")
SERVICES = {
    "image-mcp": [str(ROOT / "aion-openai-image-mcp/scripts/service.sh")],
    "web": [sys.executable, str(ROOT / "AionUi/packages/web-cli/manageWebService.py")],
}
TARGETS = ("all", *SERVICES)


def manage(action, target):
    targets = tuple(SERVICES) if target == "all" else (target,)
    if action == "stop":
        targets = targets[::-1]

    failed = False
    for name in targets:
        print(f"== {name} ==", flush=True)
        try:
            result = subprocess.run([*SERVICES[name], action], cwd=ROOT, check=False)
        except OSError as error:
            print(f"{name}: {error}", file=sys.stderr)
            failed = True
        else:
            failed = failed or result.returncode != 0
    return int(failed)


def interactive():
    print(f"操作：{' / '.join(ACTIONS)}    服务：{' / '.join(TARGETS)}")
    print("输入操作和服务，省略服务时选择 all。回车查看状态，输入 exit 退出。")
    while True:
        try:
            words = input("aion> ").split() or ["status"]
        except EOFError:
            print()
            return 0
        if words == ["exit"]:
            return 0

        action = words[0]
        target = words[1] if len(words) > 1 else "all"
        if len(words) > 2 or action not in ACTIONS or target not in TARGETS:
            print("请输入有效的操作和服务。", file=sys.stderr)
            continue
        manage(action, target)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=ACTIONS, help="defaults to status")
    parser.add_argument("target", nargs="?", choices=TARGETS, help="defaults to all")
    parser.add_argument("-i", "--interactive", action="store_true", help="open the service console")
    args = parser.parse_args()
    if args.interactive:
        if args.action is not None:
            parser.error("--interactive cannot be combined with a command")
        return interactive()
    return manage(args.action or "status", args.target or "all")


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(130)
