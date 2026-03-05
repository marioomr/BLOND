import sys
import subprocess
from pathlib import Path
import shutil
import logging
from datetime import datetime

# Setup logging with immediate flush
logs_dir = Path(__file__).parent.parent / "split_logs"
logs_dir.mkdir(parents=True, exist_ok=True)

log_file = logs_dir / f"split_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"

class ImmediateFlushHandler(logging.FileHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s',
    handlers=[ImmediateFlushHandler(str(log_file), mode='w')]
)

logger = logging.getLogger(__name__)

# Also print to stdout for debugging
print(f"Starting demucs_runner.py", file=sys.stderr, flush=True)
print(f"Input: {sys.argv[1] if len(sys.argv) > 1 else 'NOT PROVIDED'}", file=sys.stderr, flush=True)
print(f"Output: {sys.argv[2] if len(sys.argv) > 2 else 'NOT PROVIDED'}", file=sys.stderr, flush=True)

try:
    if len(sys.argv) < 3:
        raise ValueError("Missing arguments: input_file output_folder")
    
    logger.info("START")
    
    input_file = Path(sys.argv[1])
    output_base = Path(sys.argv[2])
    
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")
    
    if not output_base.exists():
        raise FileNotFoundError(f"Output folder not found: {output_base}")
    
    song_name = input_file.stem
    temp_output = output_base / "temp_demucs"

    python_venv = Path(__file__).parent.parent / "python_env" / "bin" / "python3"

    logger.info(f"Input: {input_file}")
    logger.info(f"Output: {output_base}")
    logger.info(f"Song: {song_name}")

    cmd = [
        str(python_venv), "-m", "demucs.separate",
        "-n", "htdemucs",
        "--two-stems=vocals",
        "--mp3", "--mp3-bitrate", "128",
        "-o", str(temp_output),
        str(input_file)
    ]

    logger.info("PROCESSING")
    
    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, bufsize=1
    )
    
    for line in process.stdout:
        line = line.rstrip('\n')
        if line:
            logger.info(line)
    
    process.wait(timeout=180)
    
    if process.returncode != 0:
        logger.info(f"ERROR:Process returned {process.returncode}")
        sys.exit(1)
    
    logger.info("MOVING")
    
    demucs_folder = temp_output / "htdemucs" / song_name
    if not demucs_folder.exists():
        raise FileNotFoundError(f"Demucs output folder not found: {demucs_folder}")

    final_folder = output_base / song_name
    final_folder.mkdir(parents=True, exist_ok=True)

    vocals_file = demucs_folder / "vocals.mp3"
    instrumental_file = demucs_folder / "no_vocals.mp3"
    
    if not vocals_file.exists():
        raise FileNotFoundError(f"Vocals file not found: {vocals_file}")
    if not instrumental_file.exists():
        raise FileNotFoundError(f"Instrumental file not found: {instrumental_file}")

    shutil.move(str(vocals_file), str(final_folder / "vocals.mp3"))
    shutil.move(str(instrumental_file), str(final_folder / "instrumental.mp3"))

    shutil.rmtree(temp_output, ignore_errors=True)
    
    logger.info("DONE")

except Exception as e:
    logger.info(f"ERROR:{str(e)}")
    import traceback
    logger.info(traceback.format_exc())
    sys.exit(1)