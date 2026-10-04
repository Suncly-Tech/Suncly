"""The Runner (schema §2): the only component that holds credentials and calls the agent.

It runs in its own process (``python -m suncly.runner.process``), receives
exactly what one run needs on stdin, speaks A2A to the one target host, redacts
secrets before anything leaves it, and writes the result to stdout.
"""
