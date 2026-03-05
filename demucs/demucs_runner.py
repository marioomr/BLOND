import sys
import subprocess
from pathlib import Path
import shutil
import os
import logging
from datetime import datetime

# Create logs directory
logs_dir = Path(__file__).parent.parent / "output"
logs_dir.mkdir(parents=True, exist_ok=True)

# Setup logging
log_file = logs_dir / f"demucs_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

try:
    logger.info("=" * 60)
    logger.info("Starting demucs_runner.py")
    logger.info("=" * 60)
    
    input_file = Path(sys.argv[1])
    output_base = Path(sys.argv[2])

    song_name = input_file.stem

    temp_output = output_base / "temp_demucs"

    # Get the python executable from venv
    python_venv = Path(__file__).parent.parent / "python_env" / "bin" / "python"

    logger.info(f"Input file: {input_file}")
    logger.info(f"Input file exists: {input_file.exists()}")
    logger.info(f"Output base: {output_base}")
    logger.info(f"Song name: {song_name}")
    logger.info(f"Python venv: {python_venv}")
    logger.info(f"Python venv exists: {python_venv.exists()}")
    logger.info(f"Temp output: {temp_output}")

    # Use python -m demucs instead of demucs executable
    # Using htdemucs 
    cmd = [
        str(python_venv),
        "-m",
        "demucs.separate",
        "-n",
        "htdemucs",
        "--two-stems=vocals",
        "--mp3",
        "--mp3-bitrate",
        "128",
        "-o",
        str(temp_output),
        str(input_file)
    ]

    logger.info(f"Command: {' '.join(cmd)}")
    logger.info("Running demucs...")
    logger.info("Timeout set to 180 seconds (3 minutes)")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        
        if result.stdout:
            logger.info(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"STDERR:\n{result.stderr}")
        
        logger.info(f"Demucs exit code: {result.returncode}")
        
        if result.returncode != 0:
            raise RuntimeError(f"Demucs failed with exit code {result.returncode}")
    except subprocess.TimeoutExpired:
        logger.error("Demucs process timed out after 180 seconds")
        raise RuntimeError("Demucs process timed out. This may indicate a system issue or very large file.")
    
    logger.info("Demucs completed successfully")

    demucs_folder = temp_output / "htdemucs" / song_name
    logger.info(f"Looking for demucs output in: {demucs_folder}")

    if not demucs_folder.exists():
        logger.error(f"Demucs output folder not found: {demucs_folder}")
        # List what actually exists
        logger.info(f"Contents of {temp_output}:")
        if temp_output.exists():
            for item in temp_output.rglob("*"):
                logger.info(f"  {item}")
        raise FileNotFoundError(f"Demucs output folder not found: {demucs_folder}")

    final_folder = output_base / song_name
    final_folder.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created final folder: {final_folder}")

    # List files in demucs folder to see what we have
    files_in_demucs = list(demucs_folder.glob("*.mp3"))
    logger.info(f"Files in demucs folder: {files_in_demucs}")
    
    if not files_in_demucs:
        logger.error(f"No MP3 files found in {demucs_folder}")
        logger.info(f"All files in demucs folder:")
        for item in demucs_folder.iterdir():
            logger.info(f"  {item}")

    # Find and move vocals
    vocals_file = demucs_folder / "vocals.mp3"
    if vocals_file.exists():
        logger.info(f"Moving {vocals_file} to {final_folder / 'vocals.mp3'}")
        shutil.move(str(vocals_file), str(final_folder / "vocals.mp3"))
        logger.info("Moved vocals.mp3")
    else:
        logger.error(f"vocals.mp3 not found in {demucs_folder}")
        raise FileNotFoundError(f"vocals.mp3 not found in {demucs_folder}")

    # Find and move instrumental (could be no_vocals.mp3 or other name)
    instrumental_file = demucs_folder / "no_vocals.mp3"
    if instrumental_file.exists():
        logger.info(f"Moving {instrumental_file} to {final_folder / 'instrumental.mp3'}")
        shutil.move(str(instrumental_file), str(final_folder / "instrumental.mp3"))
        logger.info("Moved no_vocals.mp3 to instrumental.mp3")
    else:
        logger.warning("no_vocals.mp3 not found, looking for other files...")
        # List all remaining files
        remaining = list(demucs_folder.glob("*.mp3"))
        if remaining:
            logger.info(f"Moving {remaining[0].name} to instrumental.mp3")
            shutil.move(str(remaining[0]), str(final_folder / "instrumental.mp3"))
            logger.info(f"Moved {remaining[0].name} to instrumental.mp3")
        else:
            logger.error(f"No instrumental file found in {demucs_folder}")
            raise FileNotFoundError(f"No instrumental file found in {demucs_folder}")

    logger.info(f"Cleaning up {temp_output}...")
    shutil.rmtree(temp_output)
    logger.info("Cleaned up temp folder")
    
    logger.info("=" * 60)
    logger.info("DONE - Process completed successfully")
    logger.info("=" * 60)
    print("DONE")

except Exception as e:
    logger.error("=" * 60)
    logger.error(f"ERROR: {str(e)}")
    logger.error("=" * 60)
    import traceback
    logger.error(traceback.format_exc())
    print(f"ERROR: {str(e)}", flush=True)
    sys.exit(1)