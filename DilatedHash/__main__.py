import base64
import sys
from pathlib import Path

from fsutilz import MMap
from plumbum import cli
from ProbSetAbs.core import BackendSource, getAllBackends, getBackend, getBackendByData, getBackendBySlug

from . import DilatedHash

# pylint:disable=arguments-differ


class MainCLI(cli.Application):
	"""A CLI tool to deal with "dilated hashes"."""


@MainCLI.subcommand("compute")
class ComputeCLI(cli.Application):
	"""Computes a "dilated hash" and prints it as base64."""

	backend = cli.SwitchAttr("--backend", str, default=None, help="Specify probabilistic data structure backend")  # in fact we need to insert in each class an own copy

	def getBackendCtor(self):
		if self.backend is not None:
			return getBackendBySlug(self.backend)
		else:
			return None

	def main(self, path: cli.ExistingFile):
		path = Path(path)

		backendCtor = self.getBackendCtor()

		with MMap(path) as d:
			h = DilatedHash(len(d), backendCtor=backendCtor)
			h.digest(d)
			r = bytes(h)
			print(base64.b64encode(r).decode("ascii"))


@MainCLI.subcommand("verify")
class VerifyCLI(cli.Application):
	"""Verifies that a "dilated hash" matches a file."""

	def main(self, path: cli.ExistingFile, digest: str):
		path = Path(path)
		digest = base64.b64decode(digest.encode("ascii"))

		with MMap(path) as d:
			h = DilatedHash(len(d), backendCtor=None)
			h.load(digest)
			print("Using backend:", h.f.__class__.prettyName, file=sys.stderr)

			res = h.verify(d)
			if res < 0:
				print("OK✅", file=sys.stderr)
				return 0

			print(res)
			return 1


@MainCLI.subcommand("list-backends")
class ShowBackendsCLI(cli.Application):
	"""Shows implemented backends."""

	def main(self):
		for el in getAllBackends():
			print(el.prettyName)


if __name__ == "__main__":
	MainCLI.run()
