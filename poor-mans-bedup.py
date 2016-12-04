#!/usr/bin/env python


# Inspired by rich man's bedup:
#   https://github.com/g2p/bedup

import hashlib
import os
import re
import subprocess
import sys
import collections

kilo = 2**10

size_thresh = 2 * kilo

ignores = tuple(map(re.compile, [
    '.*/\.git']))

def walk(pathname):
    if os.path.islink(pathname):
        return
    if any(x.match(pathname) for x in ignores):
        return
    if os.path.isdir(pathname):
        for x in os.listdir(pathname):
            yield from walk(os.path.join(pathname, x))
    if not os.path.isfile(pathname):
        return
    stat = os.stat(pathname)
    if stat.st_size < size_thresh:
        return
    yield (stat.st_mtime, pathname)

blocksize = 64 * kilo
def hash_file(pathname):
    size = 0
    hasher = hashlib.md5()
    with open(pathname, 'rb') as f:
        buf = f.read(blocksize)
        while len(buf):
            size += len(buf)
            hasher.update(buf)
            buf = f.read(blocksize)
    return size, hasher.hexdigest()

hashes = collections.defaultdict(list)

paths = sys.argv[1:] if len(sys.argv) > 1 else ['.']
for path in paths:
    for mtime, filename in walk(os.path.abspath(path)):
        hashes[hash_file(filename)].append((mtime, filename))

speculative_savings = sum(k[0] * (len(v) - 1) for k, v in hashes.items())

duplists = filter(lambda v: len(v) > 1, hashes.values())
for dups in duplists:
    dupnames = [d[1] for d in sorted(dups)]
    keep = dupnames[0]
    for dup in dupnames[1:]:
        # python can't do reflinks far as I can tell, have to shell out
        subprocess.call([
                '/usr/bin/cp',
                '--reflink=auto',
                '--no-preserve=all',
                keep,
                dup])
    print("reflinked {} dups of {}".format(len(dups) - 1, keep))
print("possibly freed {} Mb".format(speculative_savings / kilo**2))
