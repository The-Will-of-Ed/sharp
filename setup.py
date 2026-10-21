"""Bundle the canonical agent skills; do not maintain a second instruction copy."""

from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildPy(build_py):
    def run(self):
        super().run()
        for source in (Path(__file__).parent / "skills").rglob("*.md"):
            target = Path(self.build_lib) / "sharp" / source.relative_to(Path(__file__).parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            self.copy_file(str(source), str(target))


setup(cmdclass={"build_py": BuildPy})
