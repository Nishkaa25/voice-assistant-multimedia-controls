import sys
import queue
import sounddevice as sd

class AudioCapturer:
    def __init__(self, sample_rate=16000, blocksize=8000, channels=1):
        """
        Initializes the continuous microphone audio capturer.
        - sample_rate: 16000 Hz (Standard input rate for Vosk/Whisper)
        - blocksize: 8000 samples (0.5 seconds of audio per buffer chunk)
        - channels: 1 (Mono input)
        """
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.stream = None

    def _audio_callback(self, indata, frames, time_info, status):
        """Internal callback invoked by sounddevice whenever new mic audio arrives."""
        if status:
            print(f"[AUDIO WARN] Stream status: {status}", file=sys.stderr)
        
        # Push raw byte buffer into thread-safe FIFO queue
        self.audio_queue.put(bytes(indata))

    def start_stream(self):
        """Starts the background non-blocking microphone stream."""
        try:
            self.stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.blocksize,
                dtype='int16',
                channels=self.channels,
                callback=self._audio_callback
            )
            self.stream.start()
            print("[AUDIO] Live microphone stream started successfully.")
            return True
        except Exception as e:
            print(f"[AUDIO ERROR] Failed to start microphone stream: {e}", file=sys.stderr)
            return False

    def get_audio_chunk(self, block=True, timeout=None):
        """
        Retrieves the next captured audio chunk from the queue.
        Passes raw PCM bytes directly to your voice recognition engine.
        """
        try:
            return self.audio_queue.get(block=block, timeout=timeout)
        except queue.Empty:
            return None

    def stop_stream(self):
        """Cleanly releases the hardware microphone lock."""
        if self.stream:
            self.stream.stop()
            self.stream.close()
            print("[AUDIO] Microphone stream stopped and hardware lock released.")

# ==========================================
# Self-Test Execution
# ==========================================
if __name__ == "__main__":
    import time

    capturer = AudioCapturer()
    if capturer.start_stream():
        print("\nListening continuously for 5 seconds... Speak into your mic!")
        start_time = time.time()
        
        try:
            while time.time() - start_time < 5:
                chunk = capturer.get_audio_chunk(timeout=1.0)
                if chunk:
                    print(f" -> Captured continuous stream block: {len(chunk)} bytes")
        finally:
            capturer.stop_stream()