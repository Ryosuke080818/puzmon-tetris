# -*- coding: utf-8 -*-
"""
scoring.py
----------
公式テトリスガイドラインに準じたスコア計算、レベル管理、
可変抵抗(速度調整)によるスコア倍率・落下速度の計算を行う。
"""

from config import (
    LEVEL_INTERVALS, MIN_INTERVAL, LINES_PER_LEVEL,
    SCORE_SINGLE, SCORE_DOUBLE, SCORE_TRIPLE, SCORE_TETRIS,
    SCORE_SOFT_DROP_PER_CELL, SCORE_HARD_DROP_PER_CELL,
    SPEED_LEVEL_MIN, SPEED_LEVEL_MAX, SPEED_INTERVAL_STEP, SPEED_SCORE_STEP,
)

LINE_CLEAR_BASE_SCORE = {
    1: SCORE_SINGLE,
    2: SCORE_DOUBLE,
    3: SCORE_TRIPLE,
    4: SCORE_TETRIS,
}


class ScoreManager:
    """スコア・レベル・ライン数・速度レベルをまとめて管理するクラス。"""

    def __init__(self, speed_level=0):
        self.score = 0
        self.lines_cleared_total = 0
        self.level = 1
        # 可変抵抗(現状はキー入力で代用)による速度レベル 0〜9
        self.speed_level = max(SPEED_LEVEL_MIN, min(SPEED_LEVEL_MAX, speed_level))

    # ------------------------------------------------------------------
    # 速度レベル(可変抵抗)関連
    # ------------------------------------------------------------------
    def set_speed_level(self, value):
        self.speed_level = max(SPEED_LEVEL_MIN, min(SPEED_LEVEL_MAX, value))

    def change_speed_level(self, delta):
        self.set_speed_level(self.speed_level + delta)

    @property
    def score_multiplier(self):
        """速度レベルに応じたスコア倍率。例: レベル1で ×1.1。"""
        return 1.0 + self.speed_level * SPEED_SCORE_STEP

    def current_drop_interval(self):
        """現在のレベル・速度レベルから、実際の落下間隔(秒)を計算する。"""
        idx = min(self.level - 1, len(LEVEL_INTERVALS) - 1)
        base_interval = LEVEL_INTERVALS[idx]
        # 速度レベル1段階につき SPEED_INTERVAL_STEP の割合だけ短縮する
        factor = max(0.1, 1.0 - self.speed_level * SPEED_INTERVAL_STEP)
        interval = base_interval * factor
        return max(MIN_INTERVAL, interval)

    # ------------------------------------------------------------------
    # スコア加算
    # ------------------------------------------------------------------
    def add_line_clear_score(self, num_lines):
        """ライン消去時のスコアを加算する。速度レベルによる倍率を適用。"""
        if num_lines <= 0:
            return 0
        base = LINE_CLEAR_BASE_SCORE.get(num_lines, SCORE_TETRIS)
        gained = int(round(base * self.level * self.score_multiplier))
        self.score += gained

        self.lines_cleared_total += num_lines
        new_level = 1 + self.lines_cleared_total // LINES_PER_LEVEL
        if new_level != self.level:
            self.level = new_level
        return gained

    def add_soft_drop_score(self, cells):
        gained = cells * SCORE_SOFT_DROP_PER_CELL
        self.score += gained
        return gained

    def add_hard_drop_score(self, cells):
        gained = cells * SCORE_HARD_DROP_PER_CELL
        self.score += gained
        return gained
