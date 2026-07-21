# -*- coding: utf-8 -*-
"""
game.py
-------
ホーム画面 → プレイ画面 → ゲームオーバー画面 の状態遷移と描画、
メインループを担当するモジュール。
"""

import time
import pygame

import config as cfg
from board import Board
from piece import Piece, SevenBagRandomizer
from scoring import ScoreManager
from input_handler import InputHandler

STATE_HOME = "HOME"
STATE_PLAYING = "PLAYING"
STATE_GAMEOVER = "GAMEOVER"


def load_japanese_font(size):
    """日本語が表示できるフォントを可能な限り探して読み込む。"""
    import os
    if os.path.exists(cfg.CUSTOM_FONT_PATH):
        try:
            return pygame.font.Font(cfg.CUSTOM_FONT_PATH, size)
        except Exception:
            pass
    for name in cfg.FALLBACK_SYSTEM_FONTS:
        try:
            f = pygame.font.SysFont(name, size)
            if f is not None:
                return f
        except Exception:
            continue
    # 最終手段: デフォルトフォント(日本語は表示できない可能性あり)
    return pygame.font.Font(None, size)


class Menu:
    """ホーム画面・ゲームオーバー画面で使う、左右キーで選択するボタン群。"""

    def __init__(self, options):
        self.options = options  # [(label, action_id), ...]
        self.index = 0

    def move_left(self):
        self.index = (self.index - 1) % len(self.options)

    def move_right(self):
        self.index = (self.index + 1) % len(self.options)

    def selected_action(self):
        return self.options[self.index][1]


class TetrisGame:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("テトリス風パズルゲーム")
        self.screen = pygame.display.set_mode((cfg.SCREEN_W, cfg.SCREEN_H))
        self.clock = pygame.time.Clock()

        self.font_large = load_japanese_font(40)
        self.font_medium = load_japanese_font(26)
        self.font_small = load_japanese_font(18)

        self.input_handler = InputHandler()

        self.state = STATE_HOME
        self.home_menu = Menu([("ゲーム開始", "START")])
        self.gameover_menu = Menu([("タイトルへ戻る", "TO_TITLE")])

        # 速度レベルはホーム/ゲームオーバーをまたいで保持する
        # (実機では可変抵抗の現在値をそのまま読み続けるイメージ)
        self.speed_level = cfg.SPEED_LEVEL_DEFAULT

        self._reset_game_state()

        self.running = True

    # ------------------------------------------------------------------
    # ゲーム状態初期化
    # ------------------------------------------------------------------
    def _reset_game_state(self):
        self.board = Board()
        self.randomizer = SevenBagRandomizer()
        self.score_manager = ScoreManager(speed_level=self.speed_level)

        self.current_piece = self._spawn_piece()
        self.next_type = self.randomizer.next()

        self._drop_timer = 0.0
        self._last_time = time.perf_counter()

    def _spawn_piece(self):
        piece_type = self.randomizer.next()
        return Piece(piece_type)

    # ------------------------------------------------------------------
    # メインループ
    # ------------------------------------------------------------------
    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            actions = self.input_handler.poll()

            if self.state == STATE_HOME:
                self._update_home(actions)
            elif self.state == STATE_PLAYING:
                self._update_playing(actions)
            elif self.state == STATE_GAMEOVER:
                self._update_gameover(actions)

            self._draw()
            self.clock.tick(cfg.FPS)

        pygame.quit()

    # ------------------------------------------------------------------
    # HOME
    # ------------------------------------------------------------------
    def _update_home(self, actions):
        if actions["menu_left"]:
            self.home_menu.move_left()
        if actions["menu_right"]:
            self.home_menu.move_right()
        if actions["confirm"]:
            action = self.home_menu.selected_action()
            if action == "START":
                self._reset_game_state()
                self.state = STATE_PLAYING

    # ------------------------------------------------------------------
    # PLAYING
    # ------------------------------------------------------------------
    def _update_playing(self, actions):
        now = time.perf_counter()
        dt = now - self._last_time
        self._last_time = now

        # 速度調整(暫定: +/- キー。将来的には可変抵抗のADC値を毎フレーム読む)
        if actions["speed_up"]:
            self.score_manager.change_speed_level(1)
        if actions["speed_down"]:
            self.score_manager.change_speed_level(-1)

        moved = False
        if actions["move_left"]:
            if self.board.is_valid_position(self.current_piece, dx=-1):
                self.current_piece.x -= 1
                moved = True
        if actions["move_right"]:
            if self.board.is_valid_position(self.current_piece, dx=1):
                self.current_piece.x += 1
                moved = True

        if actions["rotate"]:
            self.board.try_rotate(self.current_piece, direction=1)

        # ソフトドロップ(下ボタン長押しで加速して落下+得点)
        if actions["soft_drop"]:
            if self.board.is_valid_position(self.current_piece, dy=1):
                self.current_piece.y += 1
                self.score_manager.add_soft_drop_score(1)
                self._drop_timer = 0.0

        # 確定ボタン: ハードドロップ(一番下まで即座に落下させて固定)
        if actions["confirm"]:
            distance = self.board.hard_drop_distance(self.current_piece)
            self.current_piece.y += distance
            self.score_manager.add_hard_drop_score(distance)
            self._lock_and_spawn_next()
            return

        # 自然落下(時間経過)
        self._drop_timer += dt
        interval = self.score_manager.current_drop_interval()
        if self._drop_timer >= interval:
            self._drop_timer = 0.0
            if self.board.is_valid_position(self.current_piece, dy=1):
                self.current_piece.y += 1
            else:
                self._lock_and_spawn_next()

    def _lock_and_spawn_next(self):
        self.board.lock_piece(self.current_piece)
        cleared = self.board.clear_lines()
        if cleared > 0:
            self.score_manager.add_line_clear_score(cleared)

        self.current_piece = Piece(self.next_type)
        self.next_type = self.randomizer.next()

        if self.board.is_game_over(self.current_piece):
            self.state = STATE_GAMEOVER
            self.gameover_menu.index = 0

    # ------------------------------------------------------------------
    # GAME OVER
    # ------------------------------------------------------------------
    def _update_gameover(self, actions):
        if actions["menu_left"]:
            self.gameover_menu.move_left()
        if actions["menu_right"]:
            self.gameover_menu.move_right()
        if actions["confirm"]:
            action = self.gameover_menu.selected_action()
            if action == "TO_TITLE":
                self.state = STATE_HOME

    # ------------------------------------------------------------------
    # 描画
    # ------------------------------------------------------------------
    def _draw(self):
        self.screen.fill(cfg.COLOR_BG)

        if self.state == STATE_HOME:
            self._draw_home()
        elif self.state == STATE_PLAYING:
            self._draw_playing()
        elif self.state == STATE_GAMEOVER:
            self._draw_playing(dim=True)
            self._draw_gameover_overlay()

        pygame.display.flip()

    def _draw_menu_buttons(self, menu, center_y):
        spacing = 260
        total_w = spacing * (len(menu.options) - 1)
        start_x = cfg.SCREEN_W // 2 - total_w // 2
        for i, (label, _action) in enumerate(menu.options):
            x = start_x + i * spacing
            is_selected = (i == menu.index)
            color = cfg.COLOR_SELECT if is_selected else cfg.COLOR_TEXT
            rect_w, rect_h = 220, 60
            rect = pygame.Rect(0, 0, rect_w, rect_h)
            rect.center = (x, center_y)
            border_color = cfg.COLOR_SELECT if is_selected else cfg.COLOR_TEXT_SUB
            pygame.draw.rect(self.screen, (40, 40, 50), rect, border_radius=8)
            pygame.draw.rect(self.screen, border_color, rect, width=3, border_radius=8)
            text_surf = self.font_medium.render(label, True, color)
            text_rect = text_surf.get_rect(center=rect.center)
            self.screen.blit(text_surf, text_rect)

    def _draw_home(self):
        title_surf = self.font_large.render("テトリス風パズルゲーム", True, cfg.COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H // 2 - 100))
        self.screen.blit(title_surf, title_rect)

        self._draw_menu_buttons(self.home_menu, cfg.SCREEN_H // 2 + 40)

        hint = "← → で選択 / Enterキー(確定ボタン)で決定"
        hint_surf = self.font_small.render(hint, True, cfg.COLOR_TEXT_SUB)
        hint_rect = hint_surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H - 60))
        self.screen.blit(hint_surf, hint_rect)

    def _draw_board_grid(self):
        board_rect = pygame.Rect(
            cfg.BOARD_ORIGIN_X, cfg.BOARD_ORIGIN_Y, cfg.BOARD_PIXEL_W, cfg.BOARD_PIXEL_H
        )
        pygame.draw.rect(self.screen, cfg.COLOR_BOARD_BG, board_rect)

        for x in range(cfg.BOARD_COLS + 1):
            px = cfg.BOARD_ORIGIN_X + x * cfg.CELL_SIZE
            pygame.draw.line(
                self.screen, cfg.COLOR_GRID,
                (px, cfg.BOARD_ORIGIN_Y), (px, cfg.BOARD_ORIGIN_Y + cfg.BOARD_PIXEL_H)
            )
        for y in range(cfg.BOARD_ROWS + 1):
            py = cfg.BOARD_ORIGIN_Y + y * cfg.CELL_SIZE
            pygame.draw.line(
                self.screen, cfg.COLOR_GRID,
                (cfg.BOARD_ORIGIN_X, py), (cfg.BOARD_ORIGIN_X + cfg.BOARD_PIXEL_W, py)
            )

        # 固定済みブロック
        for y in range(cfg.BOARD_ROWS):
            for x in range(cfg.BOARD_COLS):
                color = self.board.grid[y][x]
                if color is not None:
                    self._draw_cell(x, y, color)

    def _draw_cell(self, x, y, color, alpha_outline_only=False):
        px = cfg.BOARD_ORIGIN_X + x * cfg.CELL_SIZE
        py = cfg.BOARD_ORIGIN_Y + y * cfg.CELL_SIZE
        rect = pygame.Rect(px + 1, py + 1, cfg.CELL_SIZE - 2, cfg.CELL_SIZE - 2)
        if alpha_outline_only:
            pygame.draw.rect(self.screen, color, rect, width=2, border_radius=3)
        else:
            pygame.draw.rect(self.screen, color, rect, border_radius=3)

    def _draw_ghost_piece(self):
        distance = self.board.hard_drop_distance(self.current_piece)
        for x, y in self.current_piece.cells(y=self.current_piece.y + distance):
            if y >= 0:
                self._draw_cell(x, y, cfg.COLOR_GHOST, alpha_outline_only=True)

    def _draw_current_piece(self):
        for x, y in self.current_piece.cells():
            if y >= 0:
                self._draw_cell(x, y, self.current_piece.color)

    def _draw_side_panel(self):
        panel_x = cfg.BOARD_ORIGIN_X * 2 + cfg.BOARD_PIXEL_W
        y = cfg.BOARD_ORIGIN_Y

        def label(text, yy, font=None, color=None):
            f = font or self.font_medium
            c = color or cfg.COLOR_TEXT
            surf = f.render(text, True, c)
            self.screen.blit(surf, (panel_x, yy))

        # スコア表示 (画面端 / サイドパネル)
        label("SCORE", y, self.font_small, cfg.COLOR_TEXT_SUB)
        label(str(self.score_manager.score), y + 24)

        y += 70
        label("LEVEL", y, self.font_small, cfg.COLOR_TEXT_SUB)
        label(str(self.score_manager.level), y + 24)

        y += 70
        label("LINES", y, self.font_small, cfg.COLOR_TEXT_SUB)
        label(str(self.score_manager.lines_cleared_total), y + 24)

        y += 70
        label("SPEED Lv", y, self.font_small, cfg.COLOR_TEXT_SUB)
        mult = self.score_manager.score_multiplier
        label(f"{self.score_manager.speed_level}  (x{mult:.1f})", y + 24)

        y += 70
        label("NEXT", y, self.font_small, cfg.COLOR_TEXT_SUB)
        self._draw_next_preview(panel_x, y + 30)

        y += 160
        hint_lines = [
            "← → : 移動",
            "↑ : 回転",
            "↓ : ソフトドロップ",
            "Enter : 確定(ハードドロップ)",
            "+ / - : 速度レベル調整(暫定)",
        ]
        for i, line in enumerate(hint_lines):
            surf = self.font_small.render(line, True, cfg.COLOR_TEXT_SUB)
            self.screen.blit(surf, (panel_x, y + i * 22))

    def _draw_next_preview(self, panel_x, top_y):
        from piece import SHAPES
        from config import PIECE_COLORS
        shape = SHAPES[self.next_type][0]
        color = PIECE_COLORS[self.next_type]
        cell = 18
        for cx, cy in shape:
            rect = pygame.Rect(panel_x + cx * cell, top_y + cy * cell, cell - 2, cell - 2)
            pygame.draw.rect(self.screen, color, rect, border_radius=2)

    def _draw_playing(self, dim=False):
        self._draw_board_grid()
        self._draw_ghost_piece()
        self._draw_current_piece()
        self._draw_side_panel()

        if dim:
            overlay = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H))
            overlay.set_alpha(160)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

    def _draw_gameover_overlay(self):
        title_surf = self.font_large.render("GAME OVER", True, cfg.COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H // 2 - 100))
        self.screen.blit(title_surf, title_rect)

        score_text = f"SCORE: {self.score_manager.score}"
        score_surf = self.font_medium.render(score_text, True, cfg.COLOR_TEXT)
        score_rect = score_surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H // 2 - 40))
        self.screen.blit(score_surf, score_rect)

        self._draw_menu_buttons(self.gameover_menu, cfg.SCREEN_H // 2 + 40)

        hint = "← → で選択 / Enterキー(確定ボタン)で決定"
        hint_surf = self.font_small.render(hint, True, cfg.COLOR_TEXT_SUB)
        hint_rect = hint_surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H - 60))
        self.screen.blit(hint_surf, hint_rect)
