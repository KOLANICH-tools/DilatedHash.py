#!/usr/bin/env python3
import sys
from pathlib import Path
import unittest
import itertools

sys.path.insert(0, str(Path(__file__).parent.parent))

from collections import OrderedDict

dict = OrderedDict

from DilatedHash import DilatedHash, _align


import random

try:
	from tqdm import tqdm
except ImportError:
	tqdm = lambda x: x


class Tests(unittest.TestCase):
	testArray = None
	etalonDigest = None
	hasher = None

	@classmethod
	def setUpClass(cls):
		cls.testArray = random.randbytes(32 * 1024 + 1337)
		cls.hasher = hh = DilatedHash(len(cls.testArray))

		print("blockSize:", hh.blockSize)
		print("maxOffset:", hex(hh.maxOffset), hh.maxOffset)
		print("iters:", hh.iters)
		print("sliceSize:", hh.sliceSize)

		cls.hasher.digest(cls.testArray)
		cls.etalonDigest = bytes(cls.hasher)


	def testGood(self):
		hh = DilatedHash(len(self.__class__.testArray))
		hh.load(self.__class__.etalonDigest)

		res = hh.verify(self.__class__.testArray)
		self.assertEqual(res, -1)

	def testBad(self):
		hh = DilatedHash(len(self.__class__.testArray))
		hh.load(self.__class__.etalonDigest)

		badMatrix = [
			(hh.getBlockSliceByIndex(hh.iters // 2).start, 3),
			(34080, 0)
		]
		
		for blockOffs, offsWithinBlock in badMatrix:
			with self.subTest(blockOffs=blockOffs, offsWithinBlock=offsWithinBlock):
				s = blockOffs + offsWithinBlock
				d = self.__class__.testArray
				dAltered = d[:s] + b"Z" + d[s+1:]
				res = hh.verify(dAltered)
				self.assertEqual(res, blockOffs)

	def testUgly(self):
		iters = 1000
		d = self.__class__.testArray
		h = self.__class__.etalonDigest
		hh = self.__class__.hasher

		tp = 0
		fn = 0

		dAltered = bytearray(d)

		for i in tqdm(range(iters)):
			s = random.randint(0, len(d))
			with self.subTest(s=s):
				backup = dAltered[s]
				dAltered[s] = ord("Z")
				res = hh.verify(dAltered)
				dAltered[s] = backup

				if res > -1:
					tp += 1
					if res != _align(s, hh.blockSize):
						print("res=", res, "s=",s, "_align(s,", hh.blockSize, ")=",_align(s, hh.blockSize))
					self.assertEqual(res, _align(s, hh.blockSize))
				else:
					fn += 1

		fnr = fn / (tp + fn)
		print("True positives: ", tp)
		print("False negatives: ", fn)
		print("Total: ", tp + fn)
		print("False negative rate: ", fnr)
		expFNR = (1. - hh.blockSize / hh.sliceSize) + hh.filterErrorRate
		print("Expected false negative rate: ", expFNR)

		with self.subTest(fnr=fnr, expFNR=expFNR):
			self.assertLessEqual(fnr, expFNR)

if __name__ == "__main__":
	unittest.main()
