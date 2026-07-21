# -*- coding: utf-8 -*-
"""
piece.py
--------
テトリミノ(I,O,T,S,Z,J,L)の形状・回転定義と、7種一巡(7-bag)方式の
ランダム生成を扱うモジュール。
"""

import random
from config import PIECE_COLORS

# 各ミノの回転状態(0,1,2,3)ごとの、4x4グリッド内でのブロック座標(x, y)
# y は下方向が正。
SHAPES = {
    "I": [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(1, 0), (1, 1), (1, 2), (1, 3)],
    ],
    "O": [
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (2, 1)],
    ],
    "T": [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "S": [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(1, 1), (2, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    "Z": [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 0), (0, 1), (1, 1), (0, 2)],
    ],
    "J": [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    "L": [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
}

# 回転時に壁蹴り(ウォールキック)として試すオフセット候補(簡易版)
KICK_OFFSETS = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]

PIECE_TYPES = list(SHAPES.keys())


class Piece:
    """盤面上を落下する1つのテトリミノを表すクラス。"""

    def __init__(self, piece_type, spawn_x=3, spawn_y=0):
        self.type = piece_type
        self.rotation = 0
        self.x = spawn_x  # 4x4グリッド左上の盤面上での列
        self.y = spawn_y  # 4x4グリッド左上の盤面上での行
        self.color = PIECE_COLORS[piece_type]

    def cells(self, rotation=None, x=None, y=None):
        """現在(または指定)の回転・位置における、盤面座標のブロックリストを返す。"""
        rot = self.rotation if rotation is None else rotation
        ox = self.x if x is None else x
        oy = self.y if y is None else y
        shape = SHAPES[self.type][rot % 4]
        return [(ox + cx, oy + cy) for cx, cy in shape]

    def clone(self):
        p = Piece(self.type, self.x, self.y)
        p.rotation = self.rotation
        return p


class SevenBagRandomizer:
    """7種類のミノを1袋に入れ、シャッフルして順番に払い出す標準的な方式。"""

    def __init__(self):
        self._bag = []

    def _refill(self):
        self._bag = PIECE_TYPES.copy()
        random.shuffle(self._bag)

    def next(self):
        if not self._bag:
            self._refill()
        return self._bag.pop()
