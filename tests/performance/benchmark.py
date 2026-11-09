"""B13 benchmark: recognition accuracy (NF-2 / TC-ACC-01) and latency (NF-1 / TC-PERF-01).

Run from the project root with the venv active:
    python -m tests.performance.benchmark accuracy 25       # live speech, no media key pressed
    python -m tests.performance.benchmark latency 50        # live speech, real media actions
    python -m tests.performance.benchmark synthetic 100 synthetic_test_audio
                                                            # recorded files, no mic, no media key
    python -m tests.performance.benchmark summary           # combine all CSVs in benchmarks/

Live modes read MEDIA_BACKEND from .env (default "os"), same as main.py.
Synthetic mode needs ffmpeg and measures recognition only (no latency).
"""
import csv, glob, json, os, random, re, shutil, subprocess, sys, time
from datetime import datetime

OUT_DIR = "benchmarks"
TIMEOUT_S = 8
AUDIO_EXT = (".wav", ".mp3", ".ogg", ".flac", ".m4a")

# Live-mode commands: (phrase to say after the wake word, expected intent).
# Check these phrases against src/command_parser.py and edit if its vocabulary differs.
SIMPLE = [("play", "PLAY"), ("pause", "PAUSE"),
          ("volume up", "VOLUME_UP"), ("volume down", "VOLUME_DOWN"),
          ("next", "NEXT"), ("previous", "PREVIOUS")]
MUTE_PAIR = [("quiet", "MUTE"), ("speak", "UNMUTE")]   # mute first, then unmute

# Synthetic mode: expected intent is inferred from the FILE NAME, first match wins.
# "unmute" must come before "mute" because it contains it.
KEYWORDS = [
    (r"volume[ ]?up", "VOLUME_UP"),
    (r"volume[ ]?down", "VOLUME_DOWN"),
    (r"unmute|speak", "UNMUTE"),
    (r"mute|quiet", "MUTE"),
    (r"previous|prev", "PREVIOUS"),
    (r"next", "NEXT"),
    (r"pause", "PAUSE"),
    (r"resume", "RESUME"),
    (r"play", "PLAY"),
]

FIELDS = [
    "trial", "time", "source", "speaker", "device",
    "noise_db", "backend", "mode", "file", "expected",
    "transcript", "recognized", "correct",
    "latency_s", "processing_latency_s",
    "executed", "action_success"
]

# ---------------------------------------------------------------- live modes
def make_plan(n):
    """Balanced, shuffled plan. MUTE is always followed by UNMUTE so the
    mute-state tracking in MediaController never turns a trial into a no-op."""
    items = [[c] for c in SIMPLE] + [MUTE_PAIR]
    plan = []
    while len(plan) < n:
        batch = items[:]
        random.shuffle(batch)
        for item in batch:
            plan.extend(item)
    return plan[:n]


def run_trial(capturer, engine, parser, media, execute):
    while capturer.get_audio_chunk(timeout=0.05):   # drop stale audio
        pass
    deadline = time.time() + TIMEOUT_S
    while time.time() < deadline:
        chunk = capturer.get_audio_chunk(timeout=0.5)
        if not chunk:
            continue
        t0 = time.perf_counter()      # chunk that yields the final transcript arrives
        transcript = engine.process_audio_chunk(chunk)
        if not transcript:
            continue
        phrase, wake = engine.parse_wake_word_and_intent(transcript)
        if not (wake and phrase):
            continue                  # wake word alone, or no wake word: keep listening
        intent = parser.parse_intent(phrase)
        executed = ""
        if intent and execute:
            executed = "1" if media.execute_intent(intent) else "0"
        return transcript, intent, time.perf_counter() - t0, executed
    return "", None, None, ""


def write_csv(rows, prefix, tag):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, f"{prefix}_{tag}_{datetime.now():%Y%m%d_%H%M%S}.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"\nSaved {len(rows)} trials to {path}")


def run(mode, n):
    from dotenv import load_dotenv
    from src.audio_capture import AudioCapturer
    from src.voice_engine import VoiceEngine
    from src.command_parser import CommandParser
    from src.media_controller import MediaController

    load_dotenv()
    speaker = input("Speaker name: ").strip()
    device = input("Microphone (e.g. MacBook built-in mic): ").strip()
    noise = input("Ambient noise in dB (phone dB-meter app): ").strip()

    engine = VoiceEngine(model_path="model", sample_rate=16000, wake_word="assistant")
    capturer = AudioCapturer(sample_rate=16000, blocksize=4000)
    parser = CommandParser()
    backend = os.getenv("MEDIA_BACKEND", "os").lower()
    print(f"[CONFIG] Media backend: {backend.upper()}")
    media = MediaController(backend=backend)
    if not capturer.start_stream():
        capturer.stop_stream()
        media.close()
        sys.exit(1)

    rows = []
    try:
        for i, (phrase, expected) in enumerate(make_plan(n), 1):
            input(f"\nTrial {i}/{n}: press Enter, then say 'assistant {phrase}'")
            transcript, intent, latency, executed = run_trial(
                capturer, engine, parser, media, execute=(mode == "latency"))
            correct = "1" if intent and str(intent).upper() == expected else "0"
            action = ""
            if mode == "latency":
                action = input("Did the media action actually happen? (y/n): ").strip().lower()
            lat = f"{latency:.4f}" if (mode == "latency" and intent and latency is not None) else ""
            print(f"  heard='{transcript}' intent={intent} correct={correct} "
                  f"executed={executed} latency={lat}")
            rows.append({"trial": i, "time": datetime.now().isoformat(timespec="seconds"),
                         "source": "human", "speaker": speaker, "device": device,
                         "noise_db": noise, "backend": backend, "mode": mode, "file": "",
                         "expected": expected, "transcript": transcript,
                         "recognized": intent or "", "correct": correct,
                         "latency_s": lat, "executed": executed, "action_success": action})
    finally:
        capturer.stop_stream()
        if mode == "latency" and getattr(media, "is_muted", False):
            media.execute_intent("UNMUTE")      # don't leave the machine muted
        media.close()
        write_csv(rows, mode, speaker.replace(" ", "_"))


# ------------------------------------------------------------- synthetic mode
def label_from_name(path):
    name = os.path.splitext(os.path.basename(path))[0].lower().replace("-", " ").replace("_", " ")
    for pattern, intent in KEYWORDS:
        if re.search(pattern, name):
            return intent
    return None


def decode(path):
    """Decode any audio file to 16 kHz mono 16-bit PCM bytes (same ffmpeg flags as transcribe_audio.py)."""
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-f", "s16le",
           "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1", "pipe:1"]
    out = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if out.returncode != 0:
        raise RuntimeError(out.stderr.decode(errors="replace"))
    return out.stdout


def transcribe_pcm(engine, pcm):
    """
    Transcribe PCM audio and record when the final audio chunk
    is passed to VoiceEngine.

    The timestamp is used to measure synthetic command-processing
    latency. Audio decoding is excluded.
    """
    parts = []
    step = 4000 * 2  # 4000 samples x 2 bytes

    if not pcm:
        return "", None

    last_chunk_received_at = None

    for i in range(0, len(pcm), step):
        chunk = pcm[i:i + step]

        if not chunk:
            continue

        # Record the arrival time of the final actual audio chunk.
        last_chunk_received_at = time.perf_counter()

        transcript = engine.process_audio_chunk(chunk)

        if transcript:
            parts.append(transcript)

    # Flush any remaining unfinished utterance.
    final_result = json.loads(
        engine.recognizer.FinalResult()
    )

    final_text = final_result.get("text", "").strip().lower()

    if final_text:
        parts.append(final_text)

    transcript = " ".join(parts).strip()

    return transcript, last_chunk_received_at


def run_synthetic(n, folder):
    from dotenv import load_dotenv
    from src.voice_engine import VoiceEngine
    from src.command_parser import CommandParser
    from src.media_controller import MediaController

    if shutil.which("ffmpeg") is None:
        sys.exit("ffmpeg not found. Install it using: brew install ffmpeg")

    files = sorted(
        os.path.join(d, f)
        for d, _, fs in os.walk(folder)
        for f in fs
        if f.lower().endswith(AUDIO_EXT)
    )

    if not files:
        sys.exit(f"No audio files found in {folder}")

    labelled = [(f, label_from_name(f)) for f in files]

    skipped = [f for f, label in labelled if label is None]
    labelled = [(f, label) for f, label in labelled if label]

    print("\nFile -> expected command:")

    for f, label in labelled:
        print(f"  {os.path.relpath(f, folder):<50} {label}")

    if skipped:
        print(f"\nExcluded files: {len(skipped)}")

        for f in skipped:
            print(f"  {os.path.relpath(f, folder)}")

    if input("\nAre these expected commands correct? (y/n): ").strip().lower() != "y":
        sys.exit("Stopped. Fix KEYWORDS or rename files.")

    random.shuffle(labelled)
    chosen = labelled[:n]

    if len(chosen) < n:
        print(
            f"[WARNING] Only {len(chosen)} labelled files available, "
            f"not {n}. Report the actual count."
        )

    load_dotenv()

    backend = os.getenv("MEDIA_BACKEND", "os").lower()

    print(f"\n[CONFIG] Media backend: {backend.upper()}")

    print(
        "\nWARNING: Synthetic benchmarking will execute actual "
        "media commands on your configured backend."
    )

    if input("Continue with media command execution? (y/n): ").strip().lower() != "y":
        sys.exit("Benchmark cancelled.")

    engine = VoiceEngine(
        model_path="model",
        sample_rate=16000,
        wake_word="assistant"
    )

    parser = CommandParser()
    media = MediaController(backend=backend)

    rows = []

    try:
        for i, (path, expected) in enumerate(chosen, 1):

            # Decode audio BEFORE starting the latency measurement.
            pcm = decode(path)

            # Transcribe audio and capture final chunk arrival time.
            transcript, last_chunk_received_at = transcribe_pcm(
                engine, pcm
            )

            # Wake-word detection.
            phrase, wake = (
                engine.parse_wake_word_and_intent(transcript)
                if transcript else ("", False)
            )

            # Command parsing.
            intent = (
                parser.parse_intent(phrase)
                if wake and phrase else None
            )

            correct = (
                "1"
                if intent and str(intent).upper() == expected
                else "0"
            )

            # Execute the recognized command.
            executed = ""

            if intent:
                executed = (
                    "1"
                    if media.execute_intent(intent)
                    else "0"
                )

            # Stop timing AFTER command processing/execution returns.
            processing_latency = ""

            if last_chunk_received_at is not None:
                processing_latency = (
                    time.perf_counter() - last_chunk_received_at
                )

            latency_value = (
                f"{processing_latency:.6f}"
                if processing_latency != ""
                else ""
            )

            print(
                f"  [{i}/{len(chosen)}] "
                f"{os.path.basename(path)}: "
                f"heard='{transcript}' "
                f"intent={intent} "
                f"correct={correct} "
                f"executed={executed} "
                f"processing_latency={latency_value}s"
            )

            rows.append({
                "trial": i,
                "time": datetime.now().isoformat(timespec="seconds"),
                "source": "synthetic",
                "speaker": "synthetic TTS",
                "device": "direct file input (no microphone)",
                "noise_db": "n/a",
                "backend": backend,
                "mode": "synthetic",
                "file": os.path.relpath(path),
                "expected": expected,
                "transcript": transcript,
                "recognized": intent or "",
                "correct": correct,
                "latency_s": "",
                "processing_latency_s": latency_value,
                "executed": executed,
                "action_success": ""
            })

    finally:
        # Release media backend resources.
        media.close()

        write_csv(rows, "synthetic", "files")

# -------------------------------------------------------------------- summary
def read(pattern):
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT_DIR, pattern))):
        with open(f, newline="") as fh:
            rows += list(csv.DictReader(fh))
    return rows


def pct90(values):                       # nearest-rank method
    s = sorted(values)
    return s[max(0, -(-len(s) * 9 // 10) - 1)]


def acc_line(label, rows):
    ok = sum(r["correct"] == "1" for r in rows)
    print(f"  {label}: {ok}/{len(rows)} = {100 * ok / len(rows):.1f}%")


def per_command(rows):
    for cmd in sorted({r["expected"] for r in rows}):
        sub = [r for r in rows if r["expected"] == cmd]
        ok = sum(r["correct"] == "1" for r in sub)
        print(f"    {cmd:<12} {ok}/{len(sub)}")


def summary():
    acc = read("accuracy_*.csv") + read("synthetic_*.csv")
    lat = read("latency_*.csv")
    synthetic = read("synthetic_*.csv")

    if acc:
        print("Recognition accuracy (target >= 90%):")

        for src in sorted({
            r.get("source") or "human" for r in acc
        }):
            acc_line(
                src,
                [
                    r for r in acc
                    if (r.get("source") or "human") == src
                ]
            )

        acc_line("ALL", acc)

        print(
            "  Speakers:", sorted({r["speaker"] for r in acc}),
            "| Noise (dB):", sorted({r["noise_db"] for r in acc})
        )

        print("  Per command (all sources):")
        per_command(acc)

    # Live end-to-end latency.
    if lat:
        times = [
            float(r["latency_s"])
            for r in lat
            if r["latency_s"] and r["correct"] == "1"
        ]

        if times:
            print(
                f"\nLive latency over {len(times)} correctly recognized trials:"
                f" p90 = {pct90(times):.3f}s"
                f", mean = {sum(times) / len(times):.3f}s"
                f", max = {max(times):.3f}s"
            )

        print(
            f"Latency trials: {len(lat)} total"
            f" | no command recognized: "
            f"{sum(1 for r in lat if not r['recognized'])}"
            f" | wrong command: "
            f"{sum(1 for r in lat if r['recognized'] and r['correct'] != '1')}"
        )

        print(
            f"execute_intent returned True: "
            f"{sum(r['executed'] == '1' for r in lat)}/{len(lat)}"
        )

        print(
            f"Media action actually happened (your y/n): "
            f"{sum(r['action_success'] == 'y' for r in lat)}/{len(lat)}"
        )

        print("  Backend:", sorted({r["backend"] for r in lat}))

    # Synthetic command-processing latency.
    synthetic_times = [
        float(r["processing_latency_s"])
        for r in synthetic
        if r.get("processing_latency_s")
    ]

    if synthetic_times:
        print(
            "\nSynthetic command-processing latency "
            "(final PCM chunk -> processing/execution completion):"
        )

        print(f"  Measured trials: {len(synthetic_times)}")

        print(
            f"  p90: {pct90(synthetic_times):.6f}s"
        )

        print(
            f"  Mean: "
            f"{sum(synthetic_times) / len(synthetic_times):.6f}s"
        )

        print(
            f"  Maximum: {max(synthetic_times):.6f}s"
        )

        print(
            "  Note: Audio decoding and microphone capture are excluded. "
            "This is not directly comparable to live NF-1 latency."
        )

    executed_rows = [
        r for r in synthetic
        if r.get("executed") in ("0", "1")
    ]

    if executed_rows:
        successful = sum(
            r["executed"] == "1" for r in executed_rows
        )

        print(
            f"\nSynthetic execute_intent returned True: "
            f"{successful}/{len(executed_rows)}"
        )

if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["summary"]:
        summary()
    elif len(a) == 2 and a[0] in ("accuracy", "latency"):
        run(a[0], int(a[1]))
    elif len(a) in (2, 3) and a[0] == "synthetic":
        run_synthetic(int(a[1]), a[2] if len(a) == 3 else "synthetic_test_audio")
    else:
        print(__doc__)