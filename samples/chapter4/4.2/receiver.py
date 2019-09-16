import threading
import tkinter as tk
from enum import Enum

import numpy as np
import pyaudio

import common


# 状態のEnumの定義
class Status(Enum):
    WAIT = 1  # SYNコードの受付状態
    READY = 2  # 入力受付状態


# 定数
CHUNK = int(common.SR * common.PERIOD)  # バッファ
FREQ_THRESHOLD = 50

global root
global status_text
global button


# 8ビットずつ読み込んで復号化する
def decode(data):
    if len(data) % 8 != 0:  # or len(data) < 8:
        raise Exception("invalid length")
    if len(data) > 8:
        return data + decode(data[8:])
    bin_str = np.array2string(data, separator="")[1:-1]
    code = int(bin_str, 2)
    return chr(code)


# ハミング符号から誤り訂正してデータを取り取り出す
def correct_hamming_code(data):
    if len(data) % 8 != 0:
        raise Exception("invalid length")
    if len(data) > 8:
        return np.r_[
            common.hamming_coder.correct(data[:8]),
            correct_hamming_code(data[8:])
        ]
    return common.hamming_coder.correct(data)


# 波形データから0か1の信号を判定する
def demodulation(data):
    n = len(data)

    fft_data = np.fft.fft(data) / (n / 2)
    fft_data = np.abs(fft_data)

    fft_axis = np.fft.fftfreq(n, d=1.0 / common.SR)

    max_amp_freq = np.abs(fft_axis[np.argmax(fft_data)])
    print(max_amp_freq)

    # 周波数が外れすぎている場合は -1にする
    if np.abs(max_amp_freq - common.ONE_FREQ) < FREQ_THRESHOLD:
        return 1
    elif np.abs(max_amp_freq - common.ZERO_FREQ) < FREQ_THRESHOLD:
        return 0
    return -1


# マイクから音の入力を受け付ける
def listen():
    # 変数
    status = Status.WAIT
    # SYN判定用のハミング符号分を含めた直近16ビットのバッファ
    recent_bin_data = np.zeros(16, dtype=np.int8)

    # # 検波したバイナリデータ
    # bin_data = np.empty(0).astype(np.int8)

    # メッセージ本文の2進数データ
    input_bin_data = np.empty(0).astype(np.int8)

    # PyAudioの初期化処理
    p = pyaudio.PyAudio()
    stream = p.open(format=pyaudio.paInt16,
                    channels=1,
                    rate=common.SR,
                    frames_per_buffer=CHUNK,
                    input=True)

    # マイクから入力値を受け付ける
    while stream.is_active():
        raw_data = stream.read(CHUNK)
        data = np.frombuffer(raw_data, dtype=np.int16) / np.iinfo(np.int16).max

        signal = demodulation(data)

        recent_bin_data = np.roll(recent_bin_data, -1)
        recent_bin_data[-1] = signal
        print("chunk", recent_bin_data)

        # 待ち状態の場合
        if status == Status.WAIT:
            status_text.set("wait")
            # 直近のデータがSYNコードと一致するか判定
            if check_syn(recent_bin_data):
                # SYNコードの場合入力受付状態に変更
                status = Status.READY

        # 入力受付状態の場合
        elif status == Status.READY:
            status_text.set("ready")
            input_bin_data = np.r_[input_bin_data, signal]

            if np.all(recent_bin_data == -1):
                status_text.set("error")
                break

            # SYNコードか判定
            if check_syn(recent_bin_data):
                # 直近8ビットがsynコードなので入力データから除外
                # input_bin_data = input_bin_data[:-8]
                input_bin_data = input_bin_data[:-16]
                break

    # PyAudioの終了処理
    stream.stop_stream()
    stream.close()
    p.terminate()

    correct_data = correct_hamming_code(input_bin_data)
    message = decode(correct_data)
    end(message)


# 受信データを元にウィンドウの背景色を変える
def update_bgcolor(code):
    if code in common.objects:
        root.configure(bg=common.objects[code]["color"])
    else:
        root.configure(bg="#ffffff")


# 直近のデータがSYNのデータか判定する
def check_syn(data):
    # 信号を検知できないデータがある場合は確認しない
    if -1 in data:
        return False

    try:
        correct_data = np.r_[
            common.hamming_coder.correct(data[0:8]),
            common.hamming_coder.correct(data[8:16])
        ]
    except Exception:
        print("error")
        return False
    print("correct chunk", correct_data)
    return True if np.array_equal(correct_data, common.SYN_CODE) else False


# クリックされたらマイクをONにする
def click_event():
    button.configure(state=tk.DISABLED)
    threading.Thread(target=listen).start()


# メッセージを受け取って終了処理をする
def end(message):
    update_bgcolor(message)
    button.configure(state=tk.NORMAL)
    status_text.set("done")


# GUIの初期化
root = tk.Tk()
root.title("音波リモコン(受信側)")
root.geometry("400x300")
status_text = tk.StringVar()
# status_text.set("done")
status_label = tk.Label(root, textvariable=status_text)
status_label.pack()
button = tk.Button(root, text="start", command=click_event)
button.pack(fill=tk.X)

# GUIアプリの実行
root.mainloop()
