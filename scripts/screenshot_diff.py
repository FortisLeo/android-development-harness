#!/usr/bin/env python3
"""Dependency-free PNG identity check. For perceptual comparison install Pillow separately."""
import hashlib,sys
from pathlib import Path
if len(sys.argv)!=3: print('usage: screenshot_diff.py BASELINE ACTUAL',file=sys.stderr); raise SystemExit(2)
a,b=map(Path,sys.argv[1:]);
if not a.exists() or not b.exists(): print('MISSING'); raise SystemExit(1)
if hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest(): print('PASS: identical PNG'); raise SystemExit(0)
print('DIFFERENT: PNG bytes differ; use a perceptual comparator for tolerance-aware review'); raise SystemExit(1)
