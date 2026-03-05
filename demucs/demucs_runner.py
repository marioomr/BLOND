import sys
import subprocess
from pathlib import Path
import shutil
import os

input_file = Path(sys.argv[1])
output_base = Path(sys.argv[2])

song_name = input_file.stem

temp_output = output_base / "temp_demucs"

# Get the path to demucs from the virtual environment
python_env_path = Path(__file__).parent.parent / "python_env" / "bin" / "demucs"

cmd = [
    str(python_env_path),
    "-n",
    "mdx_extra_q",
    "--two-stems=vocals",
    "--mp3",
    "--mp3-bitrate",
    "320",
    "-o",
    str(temp_output),
    str(input_file)
]

subprocess.run(cmd, check=True)

demucs_folder = temp_output / "mdx_extra_q" / song_name

final_folder = output_base / song_name
final_folder.mkdir(parents=True, exist_ok=True)

shutil.move(demucs_folder / "vocals.mp3", final_folder / "vocals.mp3")
shutil.move(demucs_folder / "no_vocals.mp3", final_folder / "instrumental.mp3")

shutil.rmtree(temp_output)

print("DONE")