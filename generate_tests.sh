#!/usr/bin/env bash

set -euo pipefail

INPUT_DIR="synthetic_voice_samples"
OUTPUT_DIR="synthetic_test_audio"
TRANSCRIBE_SCRIPT="transcribe_audio.py"

COMMANDS=(
    play
    pause
    volume_up
    volume_down
    mute
    unmute
    quiet
    speak
    next
    previous
)

mkdir -p "$OUTPUT_DIR"

# Generate a WAV which combines wake word + 1s delay + command for each command.
for command in "${COMMANDS[@]}"; do
    echo "Generating: $command"

    ffmpeg -hide_banner -loglevel error -y \
        -i "$INPUT_DIR/assistant.wav" \
        -f lavfi -t 1 -i anullsrc=r=16000:cl=mono \
        -i "$INPUT_DIR/$command.wav" \
        -filter_complex \
        "[0:a]aresample=16000,aformat=sample_fmts=s16:channel_layouts=mono[a0]; \
         [1:a]aformat=sample_fmts=s16:channel_layouts=mono[a1]; \
         [2:a]aresample=16000,aformat=sample_fmts=s16:channel_layouts=mono[a2]; \
         [a0][a1][a2]concat=n=3:v=0:a=1[out]" \
        -map "[out]" -c:a pcm_s16le \
        "$OUTPUT_DIR/test_$command.wav"
done

echo

