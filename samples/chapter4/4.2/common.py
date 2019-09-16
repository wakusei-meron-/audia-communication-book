import numpy as np
from py_hamming_code import py_hamming_code as phc

# 共通定数
AMP = 0.5        # 振幅
SR = 44100       # サンプリング周波数
ONE_FREQ = 440   # 1を表す周波数
ZERO_FREQ = 220  # 0を表す周波数
PERIOD = 1 / 24  # 信号周期

# SYNコード
SYN_CODE = np.array([0, 0, 0, 1, 0, 1, 1, 0])

# (8,4)の拡張ハミングエンコーダ
hamming_coder = phc.HammingCoder(3, extended=True)

# やり取りデータに関する設定
objects = {
    "f": {"label": "むらさき", "color": "#3c5a99"},
    "g": {"label": "みどり", "color": "#00b900"},
    "y": {"label": "きいろ", "color": "#fffc00"},
    "t": {"label": "みずいろ", "color": "#1da1f2"},
}
