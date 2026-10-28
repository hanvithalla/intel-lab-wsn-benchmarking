"""The five protocols, one file each. `make(name, config)` returns an object that
sim.core.run_simulation can run."""

from sim.protocols import ech, heed, leach, pegasis, rleach
from sim.protocols.common import ProtocolRunner, State

MODULES = {"leach": leach, "heed": heed, "pegasis": pegasis, "rleach": rleach, "ech": ech}


def make(name, config=None):
    return ProtocolRunner(MODULES[name], config)
