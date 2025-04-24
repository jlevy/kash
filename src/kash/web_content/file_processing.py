from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from kash.web_content.local_file_cache import read_mtime


@dataclass(frozen=True)
class OutputType:
    """
    A type of output file, represented by the filename suffix, e.g. '.mp3', '.txt', etc.
    """

    suffix: str

    def output_path(self, src: Path) -> Path:
        """
        Resolve the output path. Will be next to the source file, e.g.
        some-dir/video.mp4 -> some-dir/video.mp3
        """
        return src.with_suffix(self.suffix)


Processor: TypeAlias = Callable[[Path, Mapping[OutputType, Path]], None]
"""
A function that takes a source file and a mapping with one or more output paths.
"""


@dataclass(frozen=True)
class FileProcess:
    """
    Process a file and produce one or more outputs.
    """

    processor: Processor
    outputs: list[OutputType]

    def is_outdated(self, src: Path) -> bool:
        """
        True when any output is missing or older (earliest mtime) than `src`.
        """
        dests = {o.output_path(src) for o in self.outputs}
        if any(not p.exists() for p in dests):
            return True
        earliest = min(read_mtime(p) for p in dests)
        return read_mtime(src) > earliest

    def run(self, src: Path) -> dict[OutputType, Path]:
        """
        Run unconditionally and return a mapping of outputs to paths.
        """
        dests = {o: o.output_path(src) for o in self.outputs}
        self.processor(src, dests)
        return dests

    def run_if_needed(self, src: Path) -> dict[OutputType, Path]:
        """
        Run only if any output is missing or outdated.
        """
        return (
            self.run(src)
            if self.is_outdated(src)
            else {o: o.output_path(src) for o in self.outputs}
        )
