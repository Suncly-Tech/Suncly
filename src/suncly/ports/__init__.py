"""Ports: the interfaces between the core and the outside world.

Every form of I/O (storage, transcripts, HTTP, keys, clock, ids, subprocesses,
progress output) is reached through one of these Protocols, so each core
component is tested without network or disk, with a deterministic clock and ids.
"""
