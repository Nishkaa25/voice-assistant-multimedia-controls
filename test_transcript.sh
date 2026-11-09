
#!/usr/bin/env bash

set -uo pipefail

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

declare -A RESULTS

correct=0
failed=0

echo "===== TRANSCRIPTION RESULTS ====="

# Transcribe every generated WAV.
for command in "${COMMANDS[@]}"; do
    file="$OUTPUT_DIR/test_$command.wav"
    expected="assistant ${command//_/ }"

    echo
    echo "----- $file -----"

    if [[ ! -f "$file" ]]; then
        echo "Audio file not found"
        RESULTS["$command"]="FILE NOT FOUND"
        ((failed+=1))
        continue
    fi

    output=$(python "$TRANSCRIBE_SCRIPT" "$file" 2>&1)
    exit_code=$?

    if [[ $exit_code -ne 0 ]]; then
        echo "Transcription failed"
        RESULTS["$command"]="SCRIPT ERROR"
        ((failed+=1))
        continue
    fi

    # Extract the final transcript from transcribe_audio.py output.
    transcript=$(
        printf '%s\n' "$output" |
        sed -n '/FINAL TRANSCRIPT/,$p' |
        tail -n +2 |
        tr '[:upper:]' '[:lower:]' |
        xargs
    )

    transcript="${transcript:-NO SPEECH RECOGNIZED}"
    RESULTS["$command"]="$transcript"

    echo "Expected    : $expected"
    echo "Transcribed : $transcript"

    if [[ "$transcript" == "$expected" ]]; then
        ((correct+=1))
        echo "Result      : PASS"
    else
        ((failed+=1))
        echo "Result      : FAIL"
    fi
done

# Final summary.
total=${#COMMANDS[@]}

echo
echo "=============================================="
echo "              FINAL SUMMARY"
echo "=============================================="

printf "%-15s | %-25s | %s\n" \
    "EXPECTED" "TRANSCRIBED" "RESULT"

echo "------------------------------------------------"

for command in "${COMMANDS[@]}"; do
    expected="assistant ${command//_/ }"
    transcript="${RESULTS[$command]:-NOT TESTED}"

    if [[ "$transcript" == "$expected" ]]; then
        status="PASS"
    else
        status="FAIL"
    fi

    printf "%-15s | %-25s | %s\n" \
        "$expected" "$transcript" "$status"
done

echo "------------------------------------------------"
echo "Total commands : $total"
echo "Correct        : $correct"
echo "Incorrect      : $failed"

accuracy=$(awk -v c="$correct" -v t="$total" \
    'BEGIN { printf "%.2f", (c/t)*100 }')

echo "Accuracy       : ${accuracy}%"
echo "=============================================="
