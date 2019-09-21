import common
import numpy as np
import scipy.io.wavfile as siw
import pyaudio
import tkinter as tk
import threading
import wave


# 文字列を2進数のnumpy配列に変換
def encode(messages):
    # 10進数を2進数文字列に変換
    def int2bin(s):
        return str(s) if s <= 1 else int2bin(s >> 1) + str(s & 1)

    # 文字を8ビット文字列に変換
    def chr2bytestr(c):
        b = int2bin(ord(c))
        return "0" * (8 - len(b)) + b

    # 1文字ずつ8ビットの2進数に変換
    bin_data = np.empty(0, dtype=np.int8)
    for msg in messages:
        byte_str = chr2bytestr(msg)

        # 8ビット文字列をnumpyの配列に変換して、配列に追加
        bin_data = np.r_[bin_data, np.array(list(byte_str), dtype=np.int8)]
    return bin_data


# ハミング符号に変換
def gen_hamming_code(data):
    # 入力データ4ビットの倍数かバリデーション
    if len(data) % 4 != 0 or len(data) < 4:
        raise Exception("invalid length")
    if len(data) > 4:
        return np.r_[
            common.hamming_coder.calc_parity(data[:4]),
            gen_hamming_code(data[4:])
        ]
    return common.hamming_coder.calc_parity(data)


# 2進数のデータを波形データに変調する
def modulation(data):
    # 全秒数の計算
    total = common.PERIOD * len(data)

    # サンプリング時間(最後のフレームは含まない)
    t = np.linspace(0, total, common.SR * total)[:-1]

    # 各フレームにおける0, 1の判定条件
    t_on = np.vectorize(lambda x: data[int(x // common.PERIOD)] == 1)(t)
    t_off = np.invert(t_on)

    # 0, 1の時の各関数定義
    func_on = lambda x:  common.AMP * np.sin(2 * np.pi * common.ONE_FREQ * x)
    func_off = lambda x: common.AMP * np.sin(2 * np.pi * common.ZERO_FREQ * x)

    # 波の生成
    y = np.piecewise(t, [t_on, t_off], [func_on, func_off])
    print(y)

    # 量子化
    y2 = (y * np.iinfo(np.int16).max).astype(np.int16)

    # ステレオに変換
    return np.array(np.c_[y2,y2])


# 指定されたオーディオファイルを再生する
def play_audio(filename):
    chunk = 1024

    # 初期化
    wf = wave.open(filename, 'rb')
    p = pyaudio.PyAudio()
    stream = p.open(
        format=p.get_format_from_width(wf.getsampwidth()),
        channels=wf.getnchannels(),
        rate=wf.getframerate(),
        output=True)

    # read data
    data = wf.readframes(chunk)

    # play stream
    while len(data) > 0:
        stream.write(data)
        data = wf.readframes(chunk)

    # 終了処理
    stream.stop_stream()
    stream.close()
    p.terminate()


# バイナリデータの前後に同期のためのSYNコードを付加する
def add_syn(data):
    return np.r_[common.SYN_CODE, data, common.SYN_CODE]


# 送信したいデータを変調して再生する
def play(send_message):
    bin_data = encode(send_message)
    print("bin_data", bin_data)
    bin_data = add_syn(bin_data)
    print("bin data with syn", bin_data)
    hamming_codes = gen_hamming_code(bin_data)
    print(hamming_codes)
    fsk_wav = modulation(hamming_codes)
    audio_filename = "fsk_{}.wav".format(send_message)
    siw.write(audio_filename, common.SR, fsk_wav)
    play_audio(audio_filename)


# ボタンクリック時の動作
def click_event(c):
    # マルチスレッドとしてデータを変調して、再生する
    return lambda: threading.Thread(target=play, args=[c]).start()


# GUIの初期化
root = tk.Tk()
root.title("音波リモコン(送信側)")
root.geometry("400x200")

# 設定されたボタンの配置
for code, obj in common.objects.items():
    btn = tk.Button(root, text=obj["label"], command=click_event(code))
    btn.pack(fill=tk.X)

# GUIアプリの実行
root.mainloop()
