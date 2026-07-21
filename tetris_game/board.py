# -*- coding: utf-8 -*-
"""
board.py
--------
テトリスの盤面(グリッド)を管理するモジュール。
衝突判定、ミノの固定、ライン消去判定を行う。
"""

from config import BOARD_COLS, BOARD_ROWS
from piece import KICK_OFFSETS


class Board:
    def __init__(self):
        self.cols = BOARD_COLS
        self.rows = BOARD_ROWS
        # grid[y][x] = None(空) または 色タプル
        self.grid = [[None for _ in range(self.cols)] for _ in range(self.rows)]

    def is_valid_position(self, piece, rotation=None, dx=0, dy=0):
        """指定の回転・移動量でミノが盤面に収まり、他ブロックと衝突しないか判定する。"""
        for x, y in piece.cells(rotation=rotation, x=piece.x + dx, y=piece.y + dy):
            if x < 0 or x >= self.cols:
                return False
            if y >= self.rows:
                return False
            if y >= 0 and self.grid[y][x] is not None:
                return False
            # y < 0 (盤面より上)は、回転時のウォールキックでごく僅かに
            # 押し出された場合のみ一時的に許容する(ミノは spawn_y=0 で
            # フィールド最上部から出現するため、通常はここを通らない)。
        return True

    def try_rotate(self, piece, direction=1):
        """
        回転を試みる。成功したら piece の rotation/x を更新して True を返す。
        簡易ウォールキック: KICK_OFFSETS の候補位置を順に試す。
        """
        new_rotation = (piece.rotation + direction) % 4
        for kx, ky in KICK_OFFSETS:
            if self.is_valid_position(piece, rotation=new_rotation, dx=kx, dy=ky):
                piece.rotation = new_rotation
                piece.x += kx
                piece.y += ky
                return True
        return False

    def hard_drop_distance(self, piece):
        """ハードドロップ(確定ボタン)で何マス落下するかを計算する。"""
        distance = 0
        while self.is_valid_position(piece, dy=distance + 1):
            distance += 1
        return distance

    def lock_piece(self, piece):
        """ミノを盤面に固定する。"""
        for x, y in piece.cells():
            if 0 <= y < self.rows and 0 <= x < self.cols:
                self.grid[y][x] = piece.color

    def clear_lines(self):
        """揃った行を消去し、消えたライン数を返す。"""
        remaining_rows = [row for row in self.grid if any(cell is None for cell in row)]
        cleared = self.rows - len(remaining_rows)
        if cleared > 0:
            new_rows = [[None for _ in range(self.cols)] for _ in range(cleared)]
            self.grid = new_rows + remaining_rows
        return cleared

    def is_game_over(self, piece):
        """
        新しいミノの出現位置(フィールド最上部, y=0付近)が既に
        積みあがったブロックと衝突している場合、ゲームオーバーと判定する。

        これは「積みあがったブロックの上端がパズルフィールドの上端を
        越えて、新しいミノが入りきらなくなった」状態を意味する。
        """
        return not self.is_valid_position(piece)
