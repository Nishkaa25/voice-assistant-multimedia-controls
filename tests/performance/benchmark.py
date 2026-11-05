"""B13 benchmark: recognition accuracy (NF-2 / TC-ACC-01) and latency (NF-1 / TC-PERF-01).

Run from the project root with the venv active:
    python -m tests.performance.benchmark accuracy 25   # no media key pressed
    python -m tests.performance.benchmark latency 50    # real media actions executed
    python -m tests.performance.benchmark summary       # combine all CSVs in benchmarks/

Media backend comes from MEDIA_BACKEND in .env (default "os"), same as main.py.
"""
import csv, glob, os, random, sys, time
from datetime import datetime

OUT_DIR = "benchmarks"
TIMEOUT_S = 8

# (phrase to say after the wake word, expected intent).
# Check these phrases against src/command_parser.py and edit if its vocabulary differs.
SIMPLE = [("play", "PLAY"), ("pause", "PAUSE"),
          ("volume up", "VOLUME_UP"), ("volume down", "VOLUME_DOWN"),
          ("next", "NEXT"), ("previous", "PREVIOUS")]
MUTE_PAIR = [("quiet", "MUTE"), ("speak", "UNMUTE")]   # always run in this order

FIELDS = ["trial", "time", "speaker", "device", "noise_db", "backend", "mode",
          "expected", "transcript", "recognized", "correct", "latency_s",
          "executed", "action_success"]


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
                         "speaker": speaker, "device": device, "noise_db": noise,
                         "backend": backend, "mode": mode, "expected": expected,
                         "transcript": transcript, "recognized": intent or "",
                         "correct": correct, "latency_s": lat, "executed": executed,
                         "action_success": action})
    finally:
        capturer.stop_stream()
        if mode == "latency" and getattr(media, "is_muted", False):
            media.execute_intent("UNMUTE")      # don't leave the machine muted
        media.close()
        os.makedirs(OUT_DIR, exist_ok=True)
        path = os.path.join(OUT_DIR, f"{mode}_{speaker.replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M%S}.csv")
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=FIELDS)
            w.writeheader()
            w.writerows(rows)
        print(f"\nSaved {len(rows)} trials to {path}")


def read(pattern):
    rows = []
    for f in sorted(glob.glob(os.path.join(OUT_DIR, pattern))):
        with open(f, newline="") as fh:
            rows += list(csv.DictReader(fh))
    return rows


def pct90(values):                       # nearest-rank method
    s = sorted(values)
    return s[max(0, -(-len(s) * 9 // 10) - 1)]


def per_command(rows):
    for cmd in sorted({r["expected"] for r in rows}):
        sub = [r for r in rows if r["expected"] == cmd]
        ok = sum(r["correct"] == "1" for r in sub)
        print(f"    {cmd:<12} {ok}/{len(sub)}")


def summary():
    acc, lat = read("accuracy_*.csv"), read("latency_*.csv")
    if acc:
        ok = sum(r["correct"] == "1" for r in acc)
        print(f"Recognition accuracy: {ok}/{len(acc)} = {100 * ok / len(acc):.1f}%  (target >= 90%)")
        print("  Speakers:", sorted({r['speaker'] for r in acc}),
              "| Noise (dB):", sorted({r['noise_db'] for r in acc}),
              "| Backend:", sorted({r['backend'] for r in acc}))
        per_command(acc)
    if lat:
        times = [float(r["latency_s"]) for r in lat if r["latency_s"] and r["correct"] == "1"]
        if times:
            print(f"Latency over {len(times)} correctly recognized trials: "
                  f"p90 = {pct90(times):.3f}s (target <= 1.5s), "
                  f"mean = {sum(times) / len(times):.3f}s, max = {max(times):.3f}s")
        print(f"Trials: {len(lat)} total | no command recognized: "
              f"{sum(1 for r in lat if not r['recognized'])} | "
              f"wrong command: {sum(1 for r in lat if r['recognized'] and r['correct'] != '1')}")
        print(f"execute_intent returned True: {sum(r['executed'] == '1' for r in lat)}/{len(lat)}")
        print(f"Media action actually happened (your y/n): "
              f"{sum(r['action_success'] == 'y' for r in lat)}/{len(lat)}")
        print("  Backend:", sorted({r['backend'] for r in lat}))


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "summary":
        summary()
    elif len(sys.argv) == 3 and sys.argv[1] in ("accuracy", "latency"):
        run(sys.argv[1], int(sys.argv[2]))
    else:
        print(__doc__)