"""Real, server-side code formatting for the languages where a genuine
formatter exists — Python (black), C/C++ (clang-format), and Java
(google-java-format). JavaScript/TypeScript are formatted client-side via
Prettier instead (see frontend CodeEditor.tsx) since that has no server
round-trip. Every other language in the editor's picker has no formatter
wired up and the frontend hides the Format button for them accordingly.

black and clang-format ship as plain pip packages (clang-format bundles a
real prebuilt binary in the wheel) — no extra setup. Java needs an actual
JDK, which is too large to vendor in the repo (~200MB); it's downloaded once
from Amazon Corretto (a legitimate, stable OpenJDK distribution) and cached
on disk, the same shape as a lazy asset download. The google-java-format jar
itself is small (~4MB) and is vendored directly in vendor/.
"""
import asyncio
import platform
import subprocess
import tarfile
import urllib.request
from pathlib import Path

import black
from clang_format import get_executable as _clang_format_executable

_JDK_VERSION = "21"  # must match (or exceed) the class file version google-java-format was built with
_JDK_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / ".jdk-cache"
_GJF_JAR = Path(__file__).resolve().parent / "vendor" / "google-java-format-1.36.1-all-deps.jar"

# google-java-format reaches into javac's internals, which the module system
# hides by default on JDK 16+ — these flags are the documented way to expose
# them. See https://github.com/google/google-java-format#jdk-16
_GJF_JVM_ARGS = [
    "--add-exports", "jdk.compiler/com.sun.tools.javac.api=ALL-UNNAMED",
    "--add-exports", "jdk.compiler/com.sun.tools.javac.file=ALL-UNNAMED",
    "--add-exports", "jdk.compiler/com.sun.tools.javac.parser=ALL-UNNAMED",
    "--add-exports", "jdk.compiler/com.sun.tools.javac.tree=ALL-UNNAMED",
    "--add-exports", "jdk.compiler/com.sun.tools.javac.util=ALL-UNNAMED",
    "--add-opens", "jdk.compiler/com.sun.tools.javac.code=ALL-UNNAMED",
    "--add-opens", "jdk.compiler/com.sun.tools.javac.comp=ALL-UNNAMED",
]


class FormatError(Exception):
    """The formatter ran but rejected the code (e.g. a syntax error)."""


def _corretto_platform_tag() -> tuple[str, str]:
    os_name = {"linux": "linux", "darwin": "macos"}.get(platform.system().lower())
    arch = {"x86_64": "x64", "amd64": "x64", "arm64": "aarch64", "aarch64": "aarch64"}.get(
        platform.machine().lower()
    )
    if os_name is None or arch is None:
        raise RuntimeError(f"Unsupported platform for Java formatting: {platform.system()}/{platform.machine()}")
    return os_name, arch


def _java_binary_path() -> Path:
    """Returns the cached Corretto `java` binary, downloading and extracting
    it first if this is the first call since the cache was last cleared
    (e.g. after a fresh deploy on ephemeral disk)."""
    os_name, arch = _corretto_platform_tag()
    jdk_dir = _JDK_CACHE_DIR / f"corretto-{_JDK_VERSION}-{os_name}-{arch}"
    java_bin = jdk_dir / "Contents" / "Home" / "bin" / "java" if os_name == "macos" else jdk_dir / "bin" / "java"
    if java_bin.exists():
        return java_bin

    _JDK_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    url = f"https://corretto.aws/downloads/latest/amazon-corretto-{_JDK_VERSION}-{arch}-{os_name}-jdk.tar.gz"
    archive_path = _JDK_CACHE_DIR / "corretto.tar.gz"
    urllib.request.urlretrieve(url, archive_path)
    with tarfile.open(archive_path) as tar:
        tar.extractall(_JDK_CACHE_DIR)
    archive_path.unlink()

    extracted = next(p for p in _JDK_CACHE_DIR.iterdir() if p.name.startswith("amazon-corretto") and p.is_dir())
    extracted.rename(jdk_dir)

    if not java_bin.exists():
        raise RuntimeError("Corretto download succeeded but the java binary wasn't found where expected")
    return java_bin


def _format_python_sync(code: str) -> str:
    try:
        return black.format_str(code, mode=black.Mode())
    except Exception as e:
        raise FormatError(str(e)) from e


def _format_clang_sync(code: str) -> str:
    result = subprocess.run(
        [_clang_format_executable("clang-format"), "--style=Google"],
        input=code, capture_output=True, text=True, timeout=10, check=False,
    )
    if result.returncode != 0:
        raise FormatError(result.stderr or "clang-format failed")
    return result.stdout


def _format_java_sync(code: str) -> str:
    java_bin = _java_binary_path()
    result = subprocess.run(
        [str(java_bin), *_GJF_JVM_ARGS, "-jar", str(_GJF_JAR), "-a", "-"],
        input=code, capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode != 0:
        raise FormatError(result.stderr or "google-java-format failed")
    return result.stdout


# clang-format handles C for free (same binary, same call) — included
# alongside the C++ support that was actually asked for.
_FORMATTERS = {
    "python": _format_python_sync,
    "c": _format_clang_sync,
    "cpp": _format_clang_sync,
    "java": _format_java_sync,
}

SUPPORTED_LANGUAGES = frozenset(_FORMATTERS.keys())


async def format_code(language: str, code: str) -> str:
    fn = _FORMATTERS.get(language)
    if fn is None:
        raise ValueError(f"No server-side formatter for language: {language}")
    return await asyncio.to_thread(fn, code)
