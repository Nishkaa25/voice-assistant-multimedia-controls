import sys
import queue
import sounddevice as sd

class AudioCapturer:
    def __init__(self, sample_rate=16000, blocksize=4000, channels=1):
        """
        FR-01: Continuous Microphone Audio Capturer with Device-Disconnect Auto-Recovery.
        - sample_rate: 16000 Hz (Standard input rate for Vosk)
        - blocksize: 4000 samples (~0.25 seconds per buffer chunk)
        - channels: 1 (Mono input)
        """
        self.sample_rate = sample_rate
        self.blocksize = blocksize
        self.channels = channels
        self.audio_queue = queue.Queue()
        self.stream = None
        self.is_running = False

    def _audio_callback(self, indata, frames, time_info, status):
        """Internal callback invoked by sounddevice when new mic audio arrives."""
        # Suppress transient buffer overflow warnings gracefully without crashing
        if status.input_overflow:
            pass
        elif status:
            print(f"[AUDIO WARN] Stream status: {status}", file=sys.stderr)
        
        # Non-blocking push into memory queue
        try:
            self.audio_queue.put_nowait(bytes(indata))
        except queue.Full:
            pass

    def start_stream(self):
        """Starts the background non-blocking microphone stream."""
        self.stop_stream()
        try:
            self.stream = sd.RawInputStream(
                samplerate=self.sample_rate,
                blocksize=self.blocksize,
                dtype='int16',
                channels=self.channels,
                callback=self._audio_callback
            )
            self.stream.start()
            self.is_running = True
            print("[AUDIO] Live microphone stream started successfully.")
            return True
        except Exception as e:
            print(f"[AUDIO ERROR] Failed to start microphone stream: {e}", file=sys.stderr)
            self.is_running = False
            return False

    def get_audio_chunk(self, timeout=0.5):
        """
        Retrieves the next captured audio chunk from the queue.
        If stream freezes due to earphone/headset disconnect, attempts auto-recovery.
        """
        try:
            return self.audio_queue.get(block=True, timeout=timeout)
        except queue.Empty:
            if self.is_running:
                # Timeout reached — stream stalled (e.g., earphone unplugged)
                print("[AUDIO WARN] Audio stream stalled (Device change detected). Recovering...")
                self.restart_stream()
            return None

    def restart_stream(self):
        """Re-binds audio capture to default active system microphone."""
        print("[AUDIO] Resetting microphone binding...")
        self.start_stream()

    def stop_stream(self):
        """Cleanly releases the hardware microphone lock."""
        self.is_running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
            
        # Clear stale audio queue
        with self.audio_queue.mutex:
            self.audio_queue.queue.clear()


# ==========================================
# Module Self-Test
# ==========================================
if __name__ == "__main__":
    import time

    capturer = AudioCapturer()
    if capturer.start_stream():
        print("\n[TEST] Listening continuously. Try unplugging your earphones to test auto-recovery...")
        start_time = time.time()
        
        try:
            while time.time() - start_time < 10:
                chunk = capturer.get_audio_chunk(timeout=0.5)
                if chunk:
                    print(f" -> Captured live block: {len(chunk)} bytes")
        finally:
            capturer.stop_stream()