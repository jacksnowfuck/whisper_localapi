import sounddevice as sd
import numpy as np
import requests
import queue
import threading
from scipy.io.wavfile import write
import io
import webrtcvad

# 初始化VAD
vad = webrtcvad.Vad()
vad.set_mode(1)  # 敏感度等级，范围从0到3，其中3最为敏感

fs = 16000  # 采样率
frame_duration_ms = 30  # VAD帧的持续时间，单位毫秒
silence_duration = 0.3  # 确定结束的静默时间，单位秒
frame_size = int(fs * frame_duration_ms / 1000)  # 每个VAD帧的大小
num_silent_frames_to_finish = int(silence_duration / (frame_duration_ms / 1000))  # 静默时间内的帧数

q = queue.Queue()  # 音频数据队列
audio_buffer = np.array([], dtype=np.int16)  # 累计音频缓冲区
silent_frames = 0  # 当前连续静默帧计数器

api_url = "http://127.0.0.1:8000/v1/audio/transcriptions"  # API地址

def callback(indata, frames, time, status):
    """声音流回调函数，将捕获的音频放入队列。"""
    if status:
        print(status)
    q.put(indata.copy())  # 将音频块放入队列

def send_audio():
    global audio_buffer
    global silent_frames
    while True:
        frame = q.get()
        is_speech = vad.is_speech(frame.tobytes(), fs)

        if is_speech:
            audio_buffer = np.append(audio_buffer, frame)
            silent_frames = 0
        else:
            silent_frames += 1
            
            if silent_frames >= num_silent_frames_to_finish and len(audio_buffer) > 0:
                # 发送累积的音频缓冲区
                send_buffer(audio_buffer)
                audio_buffer = np.array([], dtype=np.int16)  # 重置缓冲区
                silent_frames = 0

def send_buffer(buffer):
    """不断从队列中读取音频数据，并通过POST请求发送到服务器。"""
    # 使用io.BytesIO对象来构建WAV文件
    wav_io = io.BytesIO()
    write(wav_io, fs, buffer)
    
    # 准备请求参数
    files = {
        'model': (None, 'large-v3'),
        'file': ("audio_chunk.wav", wav_io.getvalue(), "audio/wav"),
        'response_format': (None, 'srt'),
        'language': (None, 'cn')
    }

    try:
        # 发送 POST 请求到服务器
        response = requests.post(api_url, files=files)

        result = response.json()
        print(result)

    except requests.RequestException as e:
        print("Request failed:", e)


# 启动一个新线程来发送音频，这样它就不会阻塞主线程（即音频捕获）
send_thread = threading.Thread(target=send_audio)
send_thread.start()

# 配置并启动音频流
with sd.InputStream(callback=callback, channels=1, samplerate=fs, blocksize=frame_size, dtype=np.int16):
    print("Recording started. Press Ctrl+C to stop.")
    try:
        # 使用 Event 对象等待，以便我们可以优雅地处理Ctrl+C (KeyboardInterrupt)
        threading.Event().wait()
    except KeyboardInterrupt:
        print("Recording stopped.")

# 确保所有音频块都被发送完毕
send_thread.join()
