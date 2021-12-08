DilatedHash.py [![Unlicensed work](https://raw.githubusercontent.com/unlicense/unlicense.org/master/static/favicon.png)](https://unlicense.org/)
==============
~~[wheel (GitLab)](https://gitlab.com/KOLANICH-tools/DilatedHash.py/-/jobs/artifacts/master/raw/dist/DilatedHash-0.CI-py3-none-any.whl?job=build)~~
[wheel (GHA via `nightly.link`)](https://nightly.link/KOLANICH-tools/DilatedHash.py/workflows/CI/master/DilatedHash-0.CI-py3-none-any.whl)
~~![GitLab Build Status](https://gitlab.com/KOLANICH-tools/DilatedHash.py/badges/master/pipeline.svg)~~
~~![GitLab Coverage](https://gitlab.com/KOLANICH-tools/DilatedHash.py/badges/master/coverage.svg)~~
[![GitHub Actions](https://github.com/KOLANICH-tools/DilatedHash.py/workflows/CI/badge.svg)](https://github.com/KOLANICH-tools/DilatedHash.py/actions/)
[![Libraries.io Status](https://img.shields.io/librariesio/github/KOLANICH-tools/DilatedHash.py.svg)](https://libraries.io/github/KOLANICH-tools/DilatedHash.py)

This is a library doing kinda *fast* **probabilistic** test of **big changes** in *big files*.


Rationale
---------

Goals:

* `fast`, but `in big files` - the task is IO-bounded, and so we **avoid reading whole files**. We read only a negligible subsample of it.
* `probabilistic` - no false positives, but there **ARE** false negatives. We cannot exclude false negatives in the bytes of file we don't read. In fact **most of the changes will go undetected**.
* `big changes` - only changes affecting 
* `parallel` - we can utilize OS IO reordering mechanisms by doing the stuff in multiple threads.
* `succinct` - the fingerprint must not be much larger than a usual hashsum and must consume much less space than the blocks hashed.
* it should be possible to get an approximate location of the detected corruption.

Non-goals:

* Detection of intentional tampering. It is **TRIVIAL** to introduce changes, while avoiding detection: just run the algorithm, collect the offsets of blocks touched by it and don't introduce any changes into them and don't change the length of file.
* Reliably detecting changes.

The main purpose of this library is to detect that certain files within a bundle is incompatible to each other. I. e. it can be a binary file and an index for that file. If a single byte is appended into the binary, all the offsets within the index must be shifted. Also an operator can make a mistake and attach an index from one version of the file to another one, and then get weird behavior. The purpose of this lib is to detect such kind of operator mistakes.

Implementation
--------------

Instead of hashing whole file it just hashes it in evenly-spaced blocks. By controlling the percentage of file affected you can control the probability to detect the corruptions.

The hashes of blocks fill a data structure called [Bloom filter](https://en.wikipedia.org/wiki/Bloom_filter), and this Bloom filter is used instead of a hash. Bloom filters have false-positive rate, its false-positives (reporting blobs being present in the filter, while they don't) become false-negatives in our case (fhen the filter reports a block being present, it is considered a negative).

I have tried [cuckoo filters](https://en.wikipedia.org/wiki/Cuckoo_filter) instead, they have given a smaller fingerprint, but the impl I have tried has a defect causing exception to be thrown on some inputs and its author doesn't know how to address it, and increasing the capacity causes everything be very slow.

In order to verify the "hash" we iterate the file from end to beginning, hash its blocks alongside with their offsets and search for them in the filter.

This **can** be done in parallel, but the first block that is to be checked is the last one because it is likely that the changes resulting in insertion anywhere in the file will affect it.

The resulting Bloom/cuckoo filter bitmap is sparse is compressed using `zlib` to make it succinct. `zlib` surbrisingly has worked better than `lzma`, `brotli` worked even better, but is not in the standard lib of `python`.

API
---
Read the [`tutorial.ipynb`](./tutorial.ipynb) ([NBViewer](https://nbviewer.jupyter.org/github/KOLANICH-tools/DilatedHash.py/blob/master/tutorial.ipynb)).
