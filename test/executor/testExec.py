import sys

from sciflo.grid.executor import runSciflo

if len(sys.argv) == 3:
    sflString = sys.argv[1]
    pklFile = sys.argv[2]
elif len(sys.argv) == 2:
    sflString = sys.argv[1]
    pklFile = None
else:
    raise SystemExit("Invalid arguments.")

workers = 4
timeout = 86400

print((runSciflo(sflString, args={}, pklFile=pklFile, workers=workers,
                 timeout=timeout)))
