#!/usr/bin/env python3
"""
Demucs Runner for BLOND Stem Splitter
Calls demucs.separate.main() directly - no subprocess needed.
Usage: demucs_runner <input_file> <output_folder> <log_file>
"""
import sys
import os
from pathlib import Path
import shutil

# Save original stderr BEFORE any redirection
_stderr = sys.stderr


def log(msg, log_path=None):
    print(msg, file=_stderr, flush=True)
    if log_path:
        try:
            with open(log_path, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')
                f.flush()
        except Exception:
            pass


def main():
    if len(sys.argv) < 4:
        log("ERROR:Usage: demucs_runner <input> <output> <log_file>")
        sys.exit(1)

    input_file = Path(sys.argv[1])
    output_base = Path(sys.argv[2])
    log_file = sys.argv[3]

    log("START", log_file)
    log(f"Input: {input_file}", log_file)
    log(f"Output: {output_base}", log_file)

    if not input_file.exists():
        log(f"ERROR:Input file not found: {input_file}", log_file)
        sys.exit(1)

    output_base.mkdir(parents=True, exist_ok=True)

    song_name = input_file.stem
    temp_output = output_base / "temp_demucs"
    temp_output.mkdir(parents=True, exist_ok=True)

    log("PROCESSING", log_file)

    try:
        import demucs.separate
        import io
        import contextlib

        class LogWriter(io.RawIOBase):
            """Captures demucs stdout/stderr and writes to our log file."""
            def __init__(self, log_path):
                self.log_path = log_path
                self._buf = ''

            def write(self, b):
                if isinstance(b, (bytes, bytearray)):
                    text = b.decode('utf-8', errors='replace')
                else:
                    text = str(b)
                self._buf += text
                while '\n' in self._buf:
                    line, self._buf = self._buf.split('\n', 1)
                    line = line.strip()
                    if line:
                        log(line, self.log_path)
                return len(b)

            def flush(self):
                if self._buf.strip():
                    log(self._buf.strip(), self.log_path)
                    self._buf = ''

            # TextIOWrapper compatibility
            def readable(self): return False
            def writable(self): return True
            def seekable(self): return False

        import io
        writer_stdout = io.TextIOWrapper(LogWriter(log_file), encoding='utf-8')
        writer_stderr = io.TextIOWrapper(LogWriter(log_file), encoding='utf-8')

        opts = [
            "-n", "htdemucs",
            "--two-stems=vocals",
            "--mp3", "--mp3-bitrate", "128",
            "-o", str(temp_output),
            str(input_file)
        ]

        with contextlib.redirect_stdout(writer_stdout), contextlib.redirect_stderr(writer_stderr):
            demucs.separate.main(opts)

    except SystemExit as e:
        if e.code != 0:
            log(f"ERROR:Demucs exited with code {e.code}", log_file)
            sys.exit(1)
    except Exception as e:
        import traceback
        log(f"ERROR:{str(e)}", log_file)
        log(traceback.format_exc(), log_file)
        sys.exit(1)

    log("MOVING", log_file)

    demucs_folder = temp_output / "htdemucs" / song_name
    if not demucs_folder.exists():
        log(f"ERROR:Demucs output not found at: {demucs_folder}", log_file)
        sys.exit(1)

    final_folder = output_base / song_name
    final_folder.mkdir(parents=True, exist_ok=True)

    vocals_src = demucs_folder / "vocals.mp3"
    instrumental_src = demucs_folder / "no_vocals.mp3"

    if not vocals_src.exists():
        log(f"ERROR:vocals.mp3 not found in {demucs_folder}", log_file)
        sys.exit(1)
    if not instrumental_src.exists():
        log(f"ERROR:no_vocals.mp3 not found in {demucs_folder}", log_file)
        sys.exit(1)

    shutil.move(str(vocals_src), str(final_folder / "vocals.mp3"))
    shutil.move(str(instrumental_src), str(final_folder / "instrumental.mp3"))
    shutil.rmtree(temp_output, ignore_errors=True)

    log("DONE", log_file)


if __name__ == "__main__":
    main()
