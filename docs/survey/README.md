# How many Linux wheels link extensions to libpython?

On Linux, an extension module should not link to libpython: the interpreter
that loads it already provides the symbols. If an extension lists a
libpython such as `libpython3.12.so.1.0` among its dependencies, the dynamic
loader must find and load that file whenever the extension is imported. A
statically linked interpreter has no such file of its own, so the import
either fails because the file is missing, or loads it as a second, separate
copy of the Python runtime next to the one already running. In the discussion
on [no longer assuming libpython is dynamically
linked](https://discuss.python.org/t/deprecating-the-assumption-that-libpython-is-dynamically-linked/107434/3),
the question came up of how common such extensions are. This survey looked
inside public wheels to find out.

**Answer: rare.** Of the 22,069 PyPI projects whose latest stable release
has a Linux wheel containing a Python extension, **117 (0.53%)** ship one
that directly links to libpython. **74 (0.34%)** do so in wheels for a
Python that still receives updates (3.11 or newer), 31 of them for 3.14 or
3.15; the other 43 only in wheels for end-of-life Pythons.

| Sample | Projects with an affected extension | Affected extensions |
| --- | ---: | ---: |
| 15,000 most-downloaded projects, PyPI and piwheels | 8 / 1,842 (0.43%) | 14 / 11,597 (0.12%) |
| Latest stable release of every PyPI project with a Linux wheel | 117 / 22,069 (0.53%) | 611 / 75,789 (0.81%) |

Each project counts once however many extensions it ships; the denominators
are the projects (and extensions) where the survey found a Python extension
at all. Across both samples, 122 distinct projects out of 22,363 had an
affected wheel.

- [Method](method.md): how projects and wheels were chosen, the BigQuery
  query, what counts as an extension, and where every candidate went.
- [Affected projects](projects.md): all 122, each linked to the wheel
  inspected.

## How it was measured

Two samples, inspecting Linux wheels without running any of their code:

1. **Popularity:** the 15,000 most-downloaded PyPI projects in October 2026,
   per [Hugo van Kemenade's list](https://hugovk.dev/top-pypi-packages/),
   with a wheel from each of PyPI and piwheels, falling back to older
   releases when the newest had no Linux wheel.
2. **Latest releases:** every project for which BigQuery's public PyPI
   datasets list a Linux wheel in the latest stable release (28,704
   candidates), checked against PyPI's live JSON API on November 21–24,
   2026, and inspected from its highest non-yanked stable release.

Each project is judged by the Linux wheel for the newest Python in that
release, preferring manylinux x86-64: the build a user on a current Python
installs. A file counts as a Python extension if it is an ELF shared object
exporting the `PyInit_*` or `PyModExport_*` function for its module name.
It is *affected* if its own `DT_NEEDED` entries name a libpython: exactly
what `libpython-linkcheck` checks at import time.

## Findings

- **Current, not just legacy.** By the libpython version the inspected
  wheel needs:

  | libpython | 2.7 | 3.6 | 3.7 | 3.8 | 3.9 | 3.10 | 3.11 | 3.12 | 3.13 | 3.14 | 3.15 |
  | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
  | Projects | 1 | 10 | 10 | 8 | 5 | 9 | 6 | 25 | 12 | 14 | 17 |

  The 43 for 3.10 and older matter only on end-of-life Pythons. The 74 for
  3.11 and newer include actively released projects: all 15
  `devart-*-connector` packages already ship affected `cp315` wheels.
- **Concentrated.** Five wheels hold 322 of the 611 affected extensions:
  `isaacsim-ros2` (98), `scipy-mpmkp` (88), `mdw` (52), `kwiver` (43) and
  `pandas-mpmkp` (41). Families of related packages repeat one build setup:
  15 `devart-*-connector` packages, 7 `isaacsim-*` packages.
- **The build matters, not just the project.** `pybigwig` and `jpype1` link
  to libpython in their piwheels ARM builds but not in their PyPI x86-64
  wheels. Within one release, wheels for older Pythons are affected more
  often: in 33 other latest releases, only wheels for Pythons older than the
  release's newest (all 3.10 or older) link libpython, so those projects are
  not counted.
- **The Stable ABI is nearly immune.** No `abi3` or `abi3t` wheel inspected
  in the latest-release sample (6,385 wheels, 11,113 extensions) was
  affected, and no extension in either sample needed `libpython3.so`. The
  one exception seen: `eegvizlib 0.2.0` also ships a `cp310-abi3` wheel
  whose extension needs `libpython3.10.so.1.0`.
- **Names vary.** Besides the usual `libpython3.X.so.1.0`, affected
  extensions need unversioned files (`libpython3.13.so`), ABI-flagged ones
  (`libpython3.7m.so.1.0`), and names rewritten by auditwheel when it copied
  a libpython *into* the wheel (`libpython3-72114d11.11.so.1.0`, in `brion`,
  `kya-validator` and `cohere`).
- **Embedding is common and legitimate.** Another 607 ELF files that are
  not Python extensions (programs and helper libraries embedding Python)
  link to libpython in 77 projects of the latest-release sample; they are
  excluded from the numbers above.

## Limitations

- Mostly one wheel per project (per index), and mostly manylinux x86-64;
  other platforms and Python versions of the same release can differ. The
  counts are lower bounds (see [method](method.md#choosing-the-wheel)).
- Only direct `DT_NEEDED` entries: an extension that reaches libpython
  through another library, or opens it at run time, is not counted.
- These are project counts, not users: they do not say how many
  installations would see a warning, and say nothing about private or
  non-PyPI extensions (conda, distribution packages).
- PyPI's metadata and releases change; the numbers are a snapshot of
  November 2026.
