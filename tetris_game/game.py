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
STATE_PAUSED = "PAUSED"
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
        # ゲームオーバー画面の「GAME OVER」文字・スコア文字は通常の1.5倍で表示する
        self.font_gameover_title = load_japanese_font(60)
        self.font_gameover_score = load_japanese_font(39)
        # プレイ中のサイドパネル(SCORE/SPEED/LINES/NEXT/HOLD)の文字は
        # 通常の1.5倍で表示する
        self.font_panel_label = load_japanese_font(27)   # 見出し(18→27)
        self.font_panel_value = load_japanese_font(39)   # 数値(26→39)

        self.input_handler = InputHandler()

        self.state = STATE_HOME
        self.home_menu = Menu([("プレイ", "START")])
        self.gameover_menu = Menu([
            ("タイトルへ", "TO_TITLE"),
            ("リトライ", "RETRY"),
        ])
        self.pause_menu = Menu([
            ("タイトルへ", "TO_TITLE"),
            ("リトライ", "RETRY"),
            ("閉じる", "CLOSE"),
        ])

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

        # ホールド機能の状態(ホールド中のミノ種類 / 今回ホールド可能か)
        self.held_type = None
        self.can_hold = True

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
            elif self.state == STATE_PAUSED:
                self._update_paused(actions)
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
        # ポーズボタン: プレイ中の一時停止 → ポーズパネル表示
        if actions["pause"]:
            # 開いた時点では「閉じる」ボタンをデフォルトで選択しておく
            self.pause_menu.index = len(self.pause_menu.options) - 1
            self.state = STATE_PAUSED
            return

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

        # ホールドボタン: 現在落下中のミノをホールドする(1回のミノにつき1回まで)
        if actions["hold"] and self.can_hold:
            self._do_hold()
            return

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

        # 新しいミノに切り替わったので、ホールドボタンを再び使用可能にする
        self.can_hold = True

        if self.board.is_game_over(self.current_piece):
            self.state = STATE_GAMEOVER
            self.gameover_menu.index = 0

    def _do_hold(self):
        """
        落下中のミノをホールドする。
        - ホールド中のミノが無ければ、現在のミノをホールドし、NEXTのミノへ進む。
        - ホールド中のミノがあれば、現在のミノとホールド中のミノを入れ替える。
        1つのミノにつき、次にロックされるまで1回のみ使用可能。
        """
        if self.held_type is None:
            self.held_type = self.current_piece.type
            self.current_piece = Piece(self.next_type)
            self.next_type = self.randomizer.next()
        else:
            swapped_type = self.held_type
            self.held_type = self.current_piece.type
            self.current_piece = Piece(swapped_type)

        self.can_hold = False
        self._drop_timer = 0.0

        # 入れ替え後のミノが出現できない(積み上がりで入りきらない)場合はゲームオーバー
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
            elif action == "RETRY":
                # タイトル画面を介さず、ゲーム画面に戻って再スタートする
                self._reset_game_state()
                self.state = STATE_PLAYING

    # ------------------------------------------------------------------
    # PAUSE
    # ------------------------------------------------------------------
    def _update_paused(self, actions):
        if actions["menu_left"]:
            self.pause_menu.move_left()
        if actions["menu_right"]:
            self.pause_menu.move_right()
        if actions["confirm"]:
            action = self.pause_menu.selected_action()
            if action == "TO_TITLE":
                self.state = STATE_HOME
            elif action == "RETRY":
                # タイトル画面を介さず、ゲーム画面に戻って再スタートする
                self._reset_game_state()
                self.state = STATE_PLAYING
            elif action == "CLOSE":
                # ポーズパネルを閉じてプレイを再開する
                self._last_time = time.perf_counter()
                self.state = STATE_PLAYING

    # ------------------------------------------------------------------
    # 描画
    # ------------------------------------------------------------------
    def _draw(self):
        self.screen.fill(cfg.COLOR_BG)

        if self.state == STATE_HOME:
            self._draw_home()
        elif self.state == STATE_PLAYING:
            self._draw_playing()
        elif self.state == STATE_PAUSED:
            self._draw_playing(dim=True)
            self._draw_pause_panel()
        elif self.state == STATE_GAMEOVER:
            self._draw_playing(dim=True)
            self._draw_gameover_overlay()

        pygame.display.flip()

    def _draw_menu_buttons(self, menu, center_y):
        n = len(menu.options)
        if n <= 1:
            button_w, gap = 220, 0
        else:
            button_w, gap = 150, 20
        total_w = n * button_w + (n - 1) * gap
        start_x = cfg.SCREEN_W // 2 - total_w // 2 + button_w // 2

        for i, (label, _action) in enumerate(menu.options):
            x = start_x + i * (button_w + gap)
            is_selected = (i == menu.index)
            color = cfg.COLOR_SELECT if is_selected else cfg.COLOR_TEXT
            rect_w, rect_h = button_w, 60
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

        hint = "Enterキー(確定ボタン)で開始"
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

        # パズルフィールドの外枠(白色・太め)を最後に描画して目立たせる。
        # board_rect ちょうどの位置に太い線を描くと内側(ブロック側)に
        # めり込んでしまうため、枠の分だけ外側に広げた矩形に描画する。
        border_w = cfg.FIELD_BORDER_WIDTH
        outer_rect = pygame.Rect(
            board_rect.x - border_w, board_rect.y - border_w,
            board_rect.w + border_w * 2, board_rect.h + border_w * 2,
        )
        pygame.draw.rect(
            self.screen, cfg.FIELD_BORDER_COLOR, outer_rect,
            width=border_w
        )

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
            f = font or self.font_panel_value
            c = color or cfg.COLOR_TEXT
            surf = f.render(text, True, c)
            self.screen.blit(surf, (panel_x, yy))

        section_gap = 90
        value_offset = 34

        # スコア表示 (画面端 / サイドパネル)
        label("SCORE", y, self.font_panel_label, cfg.COLOR_TEXT_SUB)
        label(str(self.score_manager.score), y + value_offset)

        y += section_gap
        label("SPEED", y, self.font_panel_label, cfg.COLOR_TEXT_SUB)
        label(str(self.score_manager.level), y + value_offset)

        y += section_gap
        label("LINES", y, self.font_panel_label, cfg.COLOR_TEXT_SUB)
        label(str(self.score_manager.lines_cleared_total), y + value_offset)

        # NEXT表示(白枠つきボックス、文字は中央揃え)
        y += section_gap
        self._draw_preview_box("NEXT", self.next_type, panel_x, y)

        # HOLD表示。NEXTのすぐ下隣に配置する
        y += value_offset + cfg.PREVIEW_BOX_H + 20
        self._draw_preview_box("HOLD", self.held_type, panel_x, y)

    def _draw_preview_box(self, label_text, piece_type, panel_x, top_y):
        """NEXT / HOLD 共通の、白い細枠つきミノ表示ボックスを描画する。"""
        label_surf = self.font_panel_label.render(label_text, True, cfg.COLOR_TEXT_SUB)
        label_rect = label_surf.get_rect(midtop=(panel_x + cfg.PREVIEW_BOX_W // 2, top_y))
        self.screen.blit(label_surf, label_rect)

        box_top = top_y + 34
        box_rect = pygame.Rect(panel_x, box_top, cfg.PREVIEW_BOX_W, cfg.PREVIEW_BOX_H)
        pygame.draw.rect(
            self.screen, cfg.PREVIEW_BORDER_COLOR, box_rect,
            width=cfg.PREVIEW_BORDER_WIDTH, border_radius=4
        )

        if piece_type is not None:
            self._draw_mini_piece(piece_type, box_rect)

    def _draw_mini_piece(self, piece_type, box_rect):
        """
        NEXT / HOLD ボックス内にミノを、枠からはみ出さないサイズで
        ちょうど中央に描画する。
        """
        from piece import SHAPES
        from config import PIECE_COLORS
        shape = SHAPES[piece_type][0]
        color = PIECE_COLORS[piece_type]
        cell = cfg.PREVIEW_CELL_SIZE

        xs = [cx for cx, _ in shape]
        ys = [cy for _, cy in shape]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        piece_w = (max_x - min_x + 1) * cell
        piece_h = (max_y - min_y + 1) * cell

        origin_x = box_rect.x + (box_rect.w - piece_w) // 2 - min_x * cell
        origin_y = box_rect.y + (box_rect.h - piece_h) // 2 - min_y * cell

        for cx, cy in shape:
            rect = pygame.Rect(
                origin_x + cx * cell, origin_y + cy * cell, cell - 2, cell - 2
            )
            pygame.draw.rect(self.screen, color, rect, border_radius=2)

    def _draw_playing(self, dim=False):
        self._draw_board_grid()
        self._draw_ghost_piece()
        self._draw_current_piece()
        self._draw_side_panel()

        if dim:
            overlay = pygame.Surface((cfg.SCREEN_W, cfg.SCREEN_H))
            overlay.set_alpha(cfg.OVERLAY_ALPHA)
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

    def _draw_gameover_overlay(self):
        title_surf = self.font_gameover_title.render("GAME OVER", True, cfg.COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H // 2 - 110))
        self.screen.blit(title_surf, title_rect)

        score_text = f"SCORE: {self.score_manager.score}"
        score_surf = self.font_gameover_score.render(score_text, True, cfg.COLOR_TEXT)
        score_rect = score_surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H // 2 - 30))
        self.screen.blit(score_surf, score_rect)

        self._draw_menu_buttons(self.gameover_menu, cfg.SCREEN_H // 2 + 50)

        hint = "← → で選択 / Enterキー(確定ボタン)で決定"
        hint_surf = self.font_small.render(hint, True, cfg.COLOR_TEXT_SUB)
        hint_rect = hint_surf.get_rect(center=(cfg.SCREEN_W // 2, cfg.SCREEN_H - 60))
        self.screen.blit(hint_surf, hint_rect)

    def _draw_pause_panel(self):
        """
        ポーズパネル。黒色フィルター(dim)は _draw_playing(dim=True) 側で
        既に描画済みなので、ここではパネル本体・操作方法・3ボタンを描画する。
        """
        # ボタンは(3個 × 150px + 隙間20px×2 =)490px 使うため、
        # ボタンサイズは変えずにパネル幅だけを広げて収める
        panel_w, panel_h = 560, 380
        panel_rect = pygame.Rect(0, 0, panel_w, panel_h)
        panel_rect.center = (cfg.SCREEN_W // 2, cfg.SCREEN_H // 2)
        pygame.draw.rect(self.screen, (32, 32, 42), panel_rect, border_radius=12)
        pygame.draw.rect(self.screen, cfg.COLOR_TEXT_SUB, panel_rect, width=3, border_radius=12)

        title_surf = self.font_large.render("ポーズ", True, cfg.COLOR_TEXT)
        title_rect = title_surf.get_rect(center=(cfg.SCREEN_W // 2, panel_rect.top + 55))
        self.screen.blit(title_surf, title_rect)

        # 操作方法(元々サイドパネルに表示していたものをここへ移動)
        hint_lines = [
            "← → : 移動",
            "↑ : 回転",
            "↓ : ソフトドロップ",
            "Enter : 確定(ハードドロップ)",
            "Shift : ホールド",
            "Space : ポーズ",
            "+ / - : 速度レベル調整(暫定)",
        ]
        hint_top = panel_rect.top + 100
        for i, line in enumerate(hint_lines):
            surf = self.font_small.render(line, True, cfg.COLOR_TEXT_SUB)
            rect = surf.get_rect(center=(cfg.SCREEN_W // 2, hint_top + i * 24))
            self.screen.blit(surf, rect)

        self._draw_menu_buttons(self.pause_menu, panel_rect.bottom - 60)

        select_hint = "← → で選択 / Enterキー(確定ボタン)で決定"
        select_surf = self.font_small.render(select_hint, True, cfg.COLOR_TEXT_SUB)
        select_rect = select_surf.get_rect(center=(cfg.SCREEN_W // 2, panel_rect.bottom + 24))
        self.screen.blit(select_surf, select_rect)
