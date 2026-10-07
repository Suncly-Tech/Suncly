"""The judge subprocess (schema §2, Layer 2; OQ-A1, decided 2026-10-07).

It runs in its own process (``python -m suncly.judge.process``) with an
environment built from scratch that holds one variable, the customer's model
key. It receives one prompt on stdin, asks the one configured model endpoint,
redacts the key from everything, and writes the raw answer to stdout. It is
not the Runner, holds no agent credential, and never calls the agent.
"""
