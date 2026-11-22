"""Check one launch of an interpreter that has the autoenable companion
installed (or had it, until it was uninstalled).

Usage: python -I ci/autoenable_install_check.py MODE

MODE is one of:

* ``active``: the companion and its pinned core are installed; the hook
  was enabled at startup by the companion's startup file, with the native
  implementation, from the wheel this interpreter should get, and it blocks
  a synthetic linked extension under ``-Werror``;
* ``no-site``: run with ``-S``: nothing was imported or enabled;
* ``uninstalled``: only the core is installed: it was not imported at
  startup and no hook is active, but it still imports.

Run with ``-I`` from outside any checkout. ci/test-autoenable-install.sh
drives it.
"""

import importlib.machinery
import subprocess
import sys
import sysconfig
import tempfile
from pathlib import Path

# Before anything here imports the package: what startup did.
imported_at_startup = "libpython_linkcheck" in sys.modules
found: list = []
sys.audit("libpython_linkcheck.probe", found)
hooks = [kind for kind, _ in found]
FREE_THREADED = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))


def fail(message: str) -> None:
    sys.exit(f"autoenable_install_check: {sys.argv[1]}: FAIL: {message}")


def expected_wheel() -> str:
    """The wheel of the matrix (see AGENTS.md) that pip must pick here."""
    if sys.version_info >= (3, 15):
        return "cp315-abi3.abi3t"
    return "cp314-cp314t" if FREE_THREADED else "cp312-abi3"


def installed_wheel_tags() -> list[str]:
    from importlib.metadata import distribution  # noqa: PLC0415

    wheel = distribution("libpython-linkcheck").read_text("WHEEL") or ""
    lines = wheel.splitlines()
    return [line.split(":", 1)[1].strip() for line in lines if line.startswith("Tag:")]


def check_active() -> None:
    from importlib.metadata import distribution, version  # noqa: PLC0415

    if not imported_at_startup or hooks != ["native"]:
        fail(f"imported at startup: {imported_at_startup}, active hooks {hooks}, expected native")
    import libpython_linkcheck  # noqa: PLC0415
    from libpython_linkcheck import _elf  # noqa: PLC0415

    if _elf.IMPLEMENTATION != "native":
        fail(f"implementation {_elf.IMPLEMENTATION!r}")
    core, companion = version("libpython-linkcheck"), version("libpython-linkcheck-autoenable")
    requires = distribution("libpython-linkcheck-autoenable").requires
    if core != companion or core != libpython_linkcheck.__version__:
        fail(f"versions: core {core}, companion {companion}")
    if requires != [f"libpython-linkcheck=={core}"]:
        fail(f"companion requires {requires}")
    python_tag, abis = expected_wheel().split("-")
    tags = installed_wheel_tags()
    want = [f"{python_tag}-{abi}-" for abi in abis.split(".")]
    if len(tags) != len(want) or not all(t.startswith(w) for t, w in zip(tags, want, strict=True)):
        fail(f"installed core wheel tagged {tags}, expected {expected_wheel()}")
    if FREE_THREADED and sys._is_gil_enabled():
        fail("the GIL was re-enabled")
    if libpython_linkcheck.enable():
        fail("enable() installed a second hook")
    check_blocks()
    print(
        f"active: {companion} enabled at startup, native, core wheel {expected_wheel()}, "
        f"Python {sys.version.split()[0]}{' (free-threaded)' if FREE_THREADED else ''}"
    )


def check_blocks() -> None:
    """A fresh launch blocks a synthetic extension that links libpython."""
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))
    from elfbuild import ElfSpec, build_elf  # noqa: PLC0415

    with tempfile.TemporaryDirectory() as tmp:
        suffix = importlib.machinery.EXTENSION_SUFFIXES[0]
        elf = build_elf(ElfSpec(needed=[b"libpython3.so", b"libc.so.6"]))
        (Path(tmp) / f"fake_linked{suffix}").write_bytes(elf)
        code = (
            "import sys\n"
            f"sys.path.insert(0, {tmp!r})\n"
            "import libpython_linkcheck as m\n"
            "try:\n"
            "    import fake_linked\n"
            "except m.LibpythonLinkWarning as w:\n"
            "    print('blocked', w.module, w.needed)\n"
        )
        out = subprocess.run(
            [sys.executable, "-I", "-Werror", "-c", code],
            capture_output=True,
            text=True,
            check=False,
            cwd=tmp,
        )
    if out.returncode != 0 or out.stdout != "blocked fake_linked ('libpython3.so',)\n":
        fail(f"the hook did not block a linked extension:\n{out.stdout}{out.stderr}")


def check_no_site() -> None:
    if sys.flags.no_site != 1:
        fail("run this mode with -S")
    if imported_at_startup or hooks:
        fail(f"imported at startup: {imported_at_startup}, active hooks {hooks}")
    print("no-site: nothing enabled under -S")


def check_uninstalled() -> None:
    from importlib.metadata import PackageNotFoundError, version  # noqa: PLC0415

    if imported_at_startup or hooks:
        fail(f"imported at startup: {imported_at_startup}, active hooks {hooks}")
    try:
        companion = version("libpython-linkcheck-autoenable")
    except PackageNotFoundError:
        pass
    else:
        fail(f"companion {companion} still installed")
    import libpython_linkcheck  # noqa: PLC0415

    if libpython_linkcheck.is_enabled():
        fail("importing the core enabled the hook")
    print(f"uninstalled: core {libpython_linkcheck.__version__} installed and inactive")


MODES = {"active": check_active, "no-site": check_no_site, "uninstalled": check_uninstalled}

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in MODES:
        sys.exit(f"usage: python -I {sys.argv[0]} {{{','.join(MODES)}}}")
    MODES[sys.argv[1]]()
