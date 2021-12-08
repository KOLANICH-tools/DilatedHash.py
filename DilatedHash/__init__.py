import typing
import zlib
from collections.abc import ByteString
from enum import IntEnum
from math import ceil
from pathlib import Path
from struct import Struct

from fsutilz import MMap
from ProbSetAbs.backends import Bloom2Backend, PyProbablesBloomBackend, PyProbablesCuckooBackend
from ProbSetAbs.core import IBackend, getBackendByData

q = Struct("<Q")

DEFAULT_ITER_COUNT = 100
DEFAULT_DILATION = 100


def _align(n: int, pO2: int) -> int:
	return n - (n & (pO2 - 1))


class DilatedHash:
	__slots__ = ("f", "iters", "blockSize", "maxOffset", "sliceSize", "filterErrorRate", "backendCtor")

	DEFAULT_BACKEND = Bloom2Backend  # PyProbablesCuckooBackend

	def calculateItersCountFromCoefficient(self, alignedLen: int, dilationCoefficient: int) -> int:
		countOfBlocks = int(ceil(alignedLen / self.blockSize))
		countOfBlocksToVisit = int(ceil(countOfBlocks / dilationCoefficient))
		return countOfBlocksToVisit

	def __init__(self, dataLen: int, iters: typing.Optional[int] = None, dilationCoefficient: typing.Optional[int] = None, filterErrorRate: float = 0.001, blockSize: int = 16, backendCtor: typing.Type[IBackend] = None) -> None:
		self.backendCtor = backendCtor

		assert (blockSize & (blockSize - 1)) == 0, "Block size MUST be a power of 2!"

		self.blockSize = blockSize
		alignedLen = _align(dataLen, blockSize)
		self.maxOffset = alignedLen - blockSize

		# print(self.maxOffset)
		if iters is None and dilationCoefficient is not None:
			self.iters = self.calculateItersCountFromCoefficient(alignedLen, dilationCoefficient)
		elif iters is not None and dilationCoefficient is None:
			self.iters = iters
		else:
			self.iters = min(DEFAULT_ITER_COUNT, self.calculateItersCountFromCoefficient(alignedLen, DEFAULT_DILATION))

		self.sliceSize = self.maxOffset // self.iters

		if self.sliceSize <= blockSize:
			raise ValueError("Not enough size of the data to worth a diluted hash. Do the full one")

		self.f = None
		self.filterErrorRate = filterErrorRate

	def digest(self, data: ByteString) -> ByteString:
		if self.backendCtor is None:
			backendCtor = self.__class__.DEFAULT_BACKEND
		else:
			backendCtor = self.backendCtor

		self.f = backendCtor(self.iters, self.filterErrorRate)

		for i in range(self.iters):
			self.hashBlockAtIndex(data, i)

		self.hashSliced(data[: self.blockSize], 0)
		return self

	def __bytes__(self) -> ByteString:
		res = bytes(self.f)
		return zlib.compress(res)

	def load(self, d: bytes) -> None:
		d = zlib.decompress(d)
		if self.backendCtor is None:
			backendCtor = getBackendByData(d)
		else:
			backendCtor = self.backendCtor

		self.f = backendCtor(self.iters, self.filterErrorRate)
		self.f.load(d)

	def verify(self, data: ByteString) -> int:
		for i in range(self.iters):
			v = self.verifyBlockAtIndex(data, i)
			if v > 0:  # hashes itself
				return v

		if self.verifySliced(data[: self.blockSize], 0):
			return 0

		return -1

	def getBlockSliceByIndex(self, index: int) -> slice:
		offs = _align(self.maxOffset - index * self.sliceSize, self.blockSize)
		return slice(offs, offs + self.blockSize)

	@staticmethod
	def getHashMaterial(data: ByteString, offset: int) -> ByteString:
		"""Hash functions are usually padded anyway, that's why we append and not prepend"""
		return data + q.pack(offset)

	def hashSliced(self, data: ByteString, offset: int) -> None:
		self.f.add(self.getHashMaterial(data, offset))  # hashes itself

	def verifySliced(self, data: ByteString, offset: int) -> bool:
		# h = hashFunc(data[offset:offset+blockSize]).digest()
		return not self.f.check(self.getHashMaterial(data, offset))  # hashes itself

	def hashBlockAtIndex(self, data: ByteString, idx: int) -> None:
		sl = self.getBlockSliceByIndex(idx)
		self.hashSliced(data[sl], sl.start)

	def verifyBlockAtIndex(self, data: ByteString, idx: int) -> bool:
		sl = self.getBlockSliceByIndex(idx)
		# h = hashFunc(data[offset:offset+blockSize]).digest()
		# print(idx, hex(sl.start))
		if self.verifySliced(data[sl], sl.start):
			return sl.start

		return -1
