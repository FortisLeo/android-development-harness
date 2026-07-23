#!/usr/bin/env python3
import argparse
import xml.etree.ElementTree as ET

parser = argparse.ArgumentParser(description="Assert required Android accessibility nodes exist.")
parser.add_argument("xml")
parser.add_argument("--text", action="append", default=[])
parser.add_argument("--content-desc", action="append", default=[])
parser.add_argument("--resource-id", action="append", default=[])
args = parser.parse_args()

root = ET.parse(args.xml).getroot()
nodes = list(root.iter())

def values(key):
    return [node.attrib.get(key, "") for node in nodes]

missing = []
for value in args.text:
    if value not in values("text"):
        missing.append(f"text={value!r}")
for value in args.content_desc:
    if value not in values("content-desc"):
        missing.append(f"content-desc={value!r}")
for value in args.resource_id:
    if value not in values("resource-id"):
        missing.append(f"resource-id={value!r}")

if missing:
    print("FAIL: missing accessibility nodes:")
    print("\n".join(f" - {item}" for item in missing))
    raise SystemExit(1)

print(f"PASS: accessibility assertions ({len(nodes)} nodes)")
