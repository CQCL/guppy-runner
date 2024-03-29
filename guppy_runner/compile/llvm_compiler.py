"""Utilities to link and run the final LLVM artifact."""


import os
import subprocess
from pathlib import Path
from subprocess import CalledProcessError

from guppy_runner.compile import (
    CompilerError,
    StageCompiler,
    UnsupportedEncodingError,
)
from guppy_runner.stage import EncodingMode, Stage
from guppy_runner.util import LOGGER

LLC = "llc"
LLC_ENV = "LLC"

# TODO: Find the way to use a temporary file that gets deleted afterwards.
DEFAULT_OBJ = Path("a.o")


class LlvmCompiler(StageCompiler):
    """A processor for running an LLVMIR artifact."""

    INPUT_STAGE: Stage = Stage.LLVM
    OUTPUT_STAGE: Stage = Stage.OBJECT

    def process_stage(  # noqa: PLR0913
        self,
        *,
        input_path: Path,
        input_encoding: EncodingMode,
        output_path: Path | None,
        output_encoding: EncodingMode,
        temp_file: bool = False,
        module_name: str | None = None,
    ) -> str | bytes | Path:
        """Compile the LLVMIR artifact into an object file."""
        _ = input_path, input_encoding, output_encoding, temp_file, module_name

        if output_encoding == EncodingMode.TEXTUAL:
            raise UnsupportedEncodingError(self.OUTPUT_STAGE, output_encoding)

        if not output_path:
            output_path = DEFAULT_OBJ

        output_as_text = output_encoding == EncodingMode.TEXTUAL
        cmd = [self._get_compiler()[0], input_path, "--filetype=obj"]
        if output_path:
            cmd += ["-o", output_path]

        cmd_str = " ".join(str(c) for c in cmd)
        msg = f"Executing command: '{cmd_str}'"
        LOGGER.info(msg)
        try:
            subprocess.run(
                cmd,  # noqa: S603
                capture_output=True,
                check=True,
                text=output_as_text,
            )
        except FileNotFoundError as err:
            raise LlcNotFoundError from err
        except CalledProcessError as err:
            raise LlcError(err) from err

        return output_path

    def _get_compiler(self) -> tuple[Path, bool]:
        """Returns the path to the `llc` binary.

        The returned boolean indicates whether the path was overridden via the
        environment variable.
        """
        if LLC_ENV in os.environ:
            return (Path(os.environ[LLC_ENV]), True)
        return (Path(LLC), False)


class LlvmError(CompilerError):
    """Base class for Hugr compiler errors."""


class LlcNotFoundError(LlvmError):
    """Raised when the translation program cannot be found."""

    def __init__(self) -> None:
        """Initialize the error."""
        super().__init__(f"Could not find '{LLC}' binary in your $PATH.")


class LlcError(LlvmError):
    """Raised when the translation program cannot be found."""

    def __init__(self, perror: CalledProcessError) -> None:
        """Initialize the error."""
        err_line = next(iter(perror.stderr.splitlines()), "")
        super().__init__(
            f"An error occurred while calling '{LLC}':\n{err_line}",
        )
