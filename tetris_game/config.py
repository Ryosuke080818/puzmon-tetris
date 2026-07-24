# -*- coding: utf-8 -*-
"""
config.py
---------
ゲーム全体の設定値をまとめたモジュール。

将来 Raspberry Pi + Raspberry Pi Pico + LCD + タクトスイッチ + 可変抵抗 構成へ
移行する際に変更が必要になりそうな値(画面サイズ、キー割り当て、速度パラメータ)は
できるだけこのファイルに集約している。
"""

import os

# ============================================================
# 画面・盤面サイズ
# ============================================================
CELL_SIZE = 30                # 1マスのピクセルサイズ
BOARD_COLS = 10                # 盤面の横マス数(標準テトリスは10)
BOARD_ROWS = 20                # 盤面の縦マス数(標準テトリスは20)

BOARD_PIXEL_W = CELL_SIZE * BOARD_COLS
BOARD_PIXEL_H = CELL_SIZE * BOARD_ROWS

# 盤面の左上を画面上のどこに描画するか
BOARD_ORIGIN_X = 40
BOARD_ORIGIN_Y = 40

# サイドパネル(スコア・NEXT・HOLD表示など)の幅
SIDE_PANEL_W = 220

SCREEN_W = BOARD_ORIGIN_X * 2 + BOARD_PIXEL_W + SIDE_PANEL_W
SCREEN_H = BOARD_ORIGIN_Y * 2 + BOARD_PIXEL_H

FPS = 60

# ============================================================
# 色定義 (R, G, B)
# ============================================================
COLOR_BG = (18, 18, 24)
COLOR_GRID = (60, 60, 70)
COLOR_BOARD_BG = (28, 28, 36)
COLOR_TEXT = (240, 240, 240)
COLOR_TEXT_SUB = (170, 170, 180)
COLOR_SELECT = (255, 210, 60)
COLOR_GHOST = (90, 90, 100)
COLOR_WHITE = (255, 255, 255)

# パズルフィールドの外枠(白色・太め)
FIELD_BORDER_COLOR = COLOR_WHITE
FIELD_BORDER_WIDTH = 4

# NEXT / HOLD ミノ表示の境界線(白色・細め)
PREVIEW_BORDER_COLOR = COLOR_WHITE
PREVIEW_BORDER_WIDTH = 2
PREVIEW_BOX_W = 140
PREVIEW_BOX_H = 80
# ミノ1マスあたりの表示サイズ。通常の18pxから150%に拡大(枠の大きさは変えない)
PREVIEW_CELL_SIZE = 27

# ポーズ/ゲームオーバー時の黒色フィルターの不透明度(0-255)。
# 文字の視認性を上げるため、当初の160から約20%上げて濃くしている。
OVERLAY_ALPHA = 192

# ミノごとの色(標準的な配色)
PIECE_COLORS = {
    "I": (0, 240, 240),
    "O": (240, 240, 0),
    "T": (160, 0, 240),
    "S": (0, 240, 0),
    "Z": (240, 0, 0),
    "J": (0, 0, 240),
    "L": (240, 160, 0),
}

# ============================================================
# キー割り当て (Windows PC 開発時 = 矢印キー / Enter)
# 将来、GPIO タクトスイッチに置き換える際は input_handler.py 側の
# 実装だけを差し替えれば良いように、ゲームロジック側は
# 「論理アクション名」(MOVE_LEFT 等)でしか判定しないようにしている。
# ============================================================
import pygame

KEY_MOVE_LEFT = pygame.K_LEFT
KEY_MOVE_RIGHT = pygame.K_RIGHT
KEY_SOFT_DROP = pygame.K_DOWN
KEY_ROTATE = pygame.K_UP
KEY_HARD_DROP = pygame.K_RETURN          # 確定ボタン(Enter)
KEY_PAUSE = pygame.K_SPACE               # ポーズボタン(Space)
KEY_HOLD_L = pygame.K_LSHIFT             # ホールドボタン(左Shift)
KEY_HOLD_R = pygame.K_RSHIFT             # ホールドボタン(右Shift)

# 速度調整用(可変抵抗の実機がまだ無いための暫定キー)
KEY_SPEED_UP = pygame.K_EQUALS           # "+" キー(調整用・暫定)
KEY_SPEED_DOWN = pygame.K_MINUS          # "-" キー(調整用・暫定)

# ============================================================
# 落下速度・スコア関連
# ============================================================
# レベルごとの基本落下間隔(秒)。10ラインごとにレベルアップする。
# 数値は公式テトリスガイドラインの体感に近づけた簡易カーブ。
LEVEL_INTERVALS = [
    1.000, 0.793, 0.618, 0.473, 0.355,
    0.262, 0.190, 0.135, 0.094, 0.064,
    0.043, 0.028, 0.018, 0.012, 0.007,
]
MIN_INTERVAL = 0.05
LINES_PER_LEVEL = 10

# 可変抵抗(現段階ではキーで代用)による速度レベル 0〜9
SPEED_LEVEL_MIN = 0
SPEED_LEVEL_MAX = 9
SPEED_LEVEL_DEFAULT = 0
# 速度レベル1段階につき、落下間隔を何%短縮するか
SPEED_INTERVAL_STEP = 0.07
# 速度レベル1段階につき、ライン消去スコアを何倍にするか(例: ×1.1)
SPEED_SCORE_STEP = 0.1

# ラインクリア基本スコア(公式テトリスガイドライン準拠、レベル倍率あり)
SCORE_SINGLE = 100
SCORE_DOUBLE = 300
SCORE_TRIPLE = 500
SCORE_TETRIS = 800

# ソフトドロップ・ハードドロップの1マスあたりの得点
SCORE_SOFT_DROP_PER_CELL = 1
SCORE_HARD_DROP_PER_CELL = 2

# ============================================================
# 入力のリピート(左右移動・ソフトドロップ長押し)
# ============================================================
DAS_DELAY = 0.18   # キーを押してから連続移動が始まるまでの時間(秒)
DAS_INTERVAL = 0.04  # 連続移動の間隔(秒)

# ============================================================
# フォント
# ============================================================
# 日本語表示のため、まずは assets/フォントファイルを探し、
# 無ければ OS 標準の日本語フォント名を順に試す。
ASSET_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
CUSTOM_FONT_PATH = os.path.join(ASSET_DIR, "NotoSansJP-Regular.otf")

FALLBACK_SYSTEM_FONTS = [
    "yugothic", "meiryo", "msgothic", "notosanscjkjp",
    "hiraginosans", "takaoexgothic",
]
