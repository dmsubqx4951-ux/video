"""Offline Mandarin dialogue and entirely synthesized street/guqin sound."""
from pathlib import Path
import json
import wave
import hashlib

import numpy as np
from scipy.signal import butter, sosfilt, resample_poly
import sherpa_onnx

ROOT = Path(__file__).resolve().parent
SR = 48000
DURATION = 36


def wav_write(path, data, rate=SR):
    pcm = (np.clip(data, -1, 1) * 32767).astype('<i2')
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(1 if pcm.ndim == 1 else pcm.shape[1])
        out.setsampwidth(2)
        out.setframerate(rate)
        out.writeframes(pcm.tobytes())


def wav_read(path):
    with wave.open(str(path), 'rb') as source:
        rate = source.getframerate()
        data = np.frombuffer(source.readframes(source.getnframes()), '<i2').astype(np.float32) / 32768
    return data, rate


def dialogue():
    destination = ROOT / 'output' / 'dialogue'
    destination.mkdir(parents=True, exist_ok=True)
    specs = [
        ('city', '此乃何方城池？', 10.95, 2.0, 49, 1.07),
        ('young', '大叔，你这诸葛亮扮得挺像！', 16.35, 3.6, 50, 1.12),
        ('object', '此物，', 23.25, .85, 49, 1.06),
        ('message', '不用烽火，亦能传讯！', 24.25, 3.0, 49, 1.10),
    ]
    engine = None
    items = []
    for name, text, start, maximum, speaker, speed in specs:
        text_key = hashlib.sha256(text.encode()).hexdigest()[:8]
        path = destination / f'{name}-kokoro-v1-s{speaker}-{speed:.2f}-{text_key}.wav'
        if not path.exists():
            if engine is None:
                model = ROOT / 'assets' / 'kokoro-multi-lang-v1_0'
                engine = sherpa_onnx.OfflineTts(sherpa_onnx.OfflineTtsConfig(
                    model=sherpa_onnx.OfflineTtsModelConfig(
                        kokoro=sherpa_onnx.OfflineTtsKokoroModelConfig(
                            model=str(model / 'model.onnx'),
                            voices=str(model / 'voices.bin'),
                            data_dir=str(model / 'espeak-ng-data'),
                            lexicon=','.join(str(model/f) for f in ('lexicon-us-en.txt', 'lexicon-zh.txt')),
                            tokens=str(model / 'tokens.txt'),
                        ), num_threads=3, provider='cpu'),
                    rule_fsts=','.join(str(model / f) for f in ('phone-zh.fst', 'date-zh.fst', 'number-zh.fst')),
                    max_num_sentences=1,
                ))
                print('Local Mandarin TTS loaded; speakers:', engine.num_speakers, flush=True)
            audio = engine.generate(text, sid=speaker, speed=speed)
            samples = np.array(audio.samples, dtype=np.float32)
            # Remove long model-generated leading/trailing silence only.
            voiced = np.flatnonzero(np.abs(samples) > .006)
            if len(voiced):
                margin = int(audio.sample_rate * .06)
                samples = samples[max(0, voiced[0] - margin):min(len(samples), voiced[-1] + margin)]
            wav_write(path, samples, audio.sample_rate)
        samples, rate = wav_read(path)
        samples = resample_poly(samples, SR, rate)
        length = len(samples) / SR
        if length > maximum + .04:
            # Only shorten an overlong take. Never stretch a short line to fill a shot.
            import subprocess
            fitted = destination / (name + '-fit.wav')
            ratio = length / maximum
            factors = []
            while ratio > 2:
                factors.append('atempo=2.0')
                ratio /= 2
            factors.append(f'atempo={ratio:.8f}')
            subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(path),
                            '-af', ','.join(factors), '-ar', str(SR), str(fitted)], check=True)
            samples, _ = wav_read(fitted)
        samples = samples[:int(maximum * SR)]
        peak = np.max(np.abs(samples))
        if peak:
            samples *= .44 / peak
        wav_write(destination / (name + '.wav'), samples)
        items.append({'name': name, 'text': text, 'speaker': speaker, 'speed': speed,
                      'model': 'kokoro-v1.0', 'start': start,
                      'end': start + len(samples) / SR, 'samples': samples})
        print(f'Dialogue {name}: {len(samples) / SR:.2f}s at {start:.2f}s', flush=True)
    return items


def make_audio():
    out = ROOT / 'output'
    out.mkdir(exist_ok=True)
    lines = dialogue()
    n = SR * DURATION
    rng = np.random.default_rng(2026)
    timeline = np.arange(n) / SR
    track = np.zeros((n, 2), dtype=np.float32)
    # Dense traffic bed: tire hiss, low engines, gentle stereo motion.
    rumble = sosfilt(butter(3, 220, fs=SR, output='sos'), rng.standard_normal(n)).astype(np.float32)
    hiss = sosfilt(butter(2, [500, 3100], btype='bandpass', fs=SR, output='sos'), rng.standard_normal(n)).astype(np.float32)
    ambience = rumble * .055 + hiss * .008
    duck = np.ones(n, dtype=np.float32)
    for line in lines:
        start, end = line['start'], line['end']
        dip = np.clip((timeline - start + .35) / .35, 0, 1) * np.clip((end + .4 - timeline) / .4, 0, 1)
        duck *= 1 - .58 * dip
    ambience *= duck
    track[:, 0] = ambience
    track[:, 1] = np.roll(ambience, 83)

    def add(signal, start, gain=1., pan=.5):
        offset = round(start * SR)
        a = max(0, offset)
        b = min(n, offset + len(signal))
        if b > a:
            segment = signal[a - offset:b - offset] * gain
            track[a:b, 0] += segment * np.sqrt(1 - pan)
            track[a:b, 1] += segment * np.sqrt(pan)

    for start in np.arange(-1., 35, 1.7):
        t = np.arange(int(2.4 * SR)) / SR
        noise = sosfilt(butter(2, 900, fs=SR, output='sos'), rng.standard_normal(len(t)))
        whoosh = noise * np.exp(-((t - 1.2) / .62) ** 2) * .026
        add(whoosh, float(start), pan=float(rng.uniform(.2, .8)))
    for start in (.45, 6.6, 14.1, 23.1):
        t = np.arange(int(.36 * SR)) / SR
        envelope = np.sin(np.pi * t / .36) ** 2
        horn = (np.sin(2 * np.pi * 370 * t) + .5 * np.sin(2 * np.pi * 465 * t)) * envelope * .035
        add(horn, start, pan=.2)
    for start in np.arange(.3, 20, .66):
        t = np.arange(int(.085 * SR)) / SR
        foot = (rng.standard_normal(len(t)) * .009 + np.sin(2 * np.pi * 150 * t) * .026) * np.exp(-t * 70)
        add(foot, float(start), pan=.8)
    for start, frequency in ((20.5, 1046.5), (21.3, 1318.5), (22.1, 1568.0)):
        t = np.arange(int(.23 * SR)) / SR
        chime = np.sin(2 * np.pi * frequency * t) * np.exp(-t * 22) * .075
        add(chime, start, pan=.64)
    for line in lines:
        add(line['samples'], line['start'], gain=1.55, pan=.52 if line['name'] == 'young' else .46)

    # Guqin-like plucked strings, built by a damped harmonic string model.
    for start, frequency in ((29.1, 146.83), (31.0, 220.0), (32.9, 293.66), (34.0, 164.81)):
        t = np.arange(int(4.7 * SR)) / SR
        string = np.zeros(len(t))
        for harmonic in range(1, 13):
            string += (np.sin(2 * np.pi * frequency * harmonic * t + .18 * harmonic)
                       * np.exp(-t * (.55 + harmonic * .24)) / harmonic ** 1.5)
        attack = np.clip(t / .007, 0, 1)
        add(string * attack * .031, start, pan=.42)
    fade_in = np.clip(timeline / .08, 0, 1)
    fade_out = np.clip((36 - timeline) / .7, 0, 1)
    track *= (fade_in * fade_out)[:, None]
    peak = float(np.max(np.abs(track)))
    if peak > .95:
        track *= .95 / peak
    wav_write(out / 'soundtrack.wav', track)
    serializable = [{k: v for k, v in line.items() if k != 'samples'} for line in lines]
    (out / 'dialogue-timing.json').write_text(json.dumps(serializable, ensure_ascii=False, indent=2))
    print('Stereo soundtrack written:', out / 'soundtrack.wav', 'peak:', peak, flush=True)
    return lines


if __name__ == '__main__':
    make_audio()

