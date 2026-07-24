# -*- coding: utf-8 -*-
"""
input_handler.py
-----------------
入力デバイスを抽象化するモジュール。

現在(Windows PC 開発段階)はキーボードを使うが、将来的に
Raspberry Pi Pico + タクトスイッチ + 可変抵抗 の構成に置き換える際は、
この InputHandler クラスの中身だけを GPIO / ADC 読み取りに差し替えれば、
game.py 側のロジックには一切手を入れずに済むように設計している。

論理アクション:
    move_left / move_right   : 左右移動(タクトスイッチ)
    soft_drop                 : 下方向移動(タクトスイッチ)
    rotate                    : 回転(タクトスイッチ)
    confirm                   : 確定ボタン
                                 - プレイ中: ハードドロップ(一番下まで落下)
                                 - メニュー中: 選択項目の決定
    menu_left / menu_right    : ホーム/ゲームオーバー/ポーズ画面でのボタン選択移動
    speed_up / speed_down     : 速度調整(暫定キー。将来は可変抵抗のADC値に置換)
    pause                     : ポーズボタン(プレイ中の一時停止/ポーズパネル表示)
    hold                      : ホールドボタン(落下中のミノをホールドする)
"""

import time
import pygame

from config import (
    KEY_MOVE_LEFT, KEY_MOVE_RIGHT, KEY_SOFT_DROP, KEY_ROTATE, KEY_HARD_DROP,
    KEY_SPEED_UP, KEY_SPEED_DOWN, KEY_PAUSE, KEY_HOLD_L, KEY_HOLD_R,
    DAS_DELAY, DAS_INTERVAL,
)


class RepeatingKey:
    """長押しで一定間隔ごとに True を返す(DAS/ARR相当)キーの状態管理。"""

    def __init__(self, delay=DAS_DELAY, interval=DAS_INTERVAL):
        self.delay = delay
        self.interval = interval
        self._pressed_at = None
        self._last_fire = None

    def update(self, is_down, now):
        """
        is_down: 現在このキーが押されているか
        now    : 現在時刻(time.perf_counter() 等)
        戻り値 : このフレームで「移動アクションを発火させるか」
        """
        if not is_down:
            self._pressed_at = None
            self._last_fire = None
            return False

        if self._pressed_at is None:
            # 押された瞬間は必ず1回発火
            self._pressed_at = now
            self._last_fire = now
            return True

        elapsed = now - self._pressed_at
        if elapsed < self.delay:
            return False

        if self._last_fire is None or (now - self._last_fire) >= self.interval:
            self._last_fire = now
            return True
        return False


class InputHandler:
    """1フレーム分の入力状態を集約して提供するクラス。"""

    def __init__(self):
        self.left_repeat = RepeatingKey()
        self.right_repeat = RepeatingKey()
        self.down_repeat = RepeatingKey()

        self._rotate_prev = False
        self._confirm_prev = False
        self._menu_left_prev = False
        self._menu_right_prev = False
        self._speed_up_prev = False
        self._speed_down_prev = False
        self._pause_prev = False
        self._hold_prev = False

    def poll(self):
        """
        pygame のキー状態を読み取り、論理アクションの辞書を返す。
        戻り値の各キーは「このフレームで発生したか(edge-trigger)」または
        「押され続けているか(hold)」を表す。
        """
        keys = pygame.key.get_pressed()
        now = time.perf_counter()

        left_down = keys[KEY_MOVE_LEFT]
        right_down = keys[KEY_MOVE_RIGHT]
        down_down = keys[KEY_SOFT_DROP]
        rotate_down = keys[KEY_ROTATE]
        confirm_down = keys[KEY_HARD_DROP]
        speed_up_down = keys[KEY_SPEED_UP]
        speed_down_down = keys[KEY_SPEED_DOWN]
        pause_down = keys[KEY_PAUSE]
        hold_down = keys[KEY_HOLD_L] or keys[KEY_HOLD_R]

        move_left = self.left_repeat.update(left_down, now)
        move_right = self.right_repeat.update(right_down, now)
        soft_drop = self.down_repeat.update(down_down, now)

        rotate = rotate_down and not self._rotate_prev
        confirm = confirm_down and not self._confirm_prev
        menu_left = left_down and not self._menu_left_prev
        menu_right = right_down and not self._menu_right_prev
        speed_up = speed_up_down and not self._speed_up_prev
        speed_down = speed_down_down and not self._speed_down_prev
        pause = pause_down and not self._pause_prev
        hold = hold_down and not self._hold_prev

        self._rotate_prev = rotate_down
        self._confirm_prev = confirm_down
        self._menu_left_prev = left_down
        self._menu_right_prev = right_down
        self._speed_up_prev = speed_up_down
        self._speed_down_prev = speed_down_down
        self._pause_prev = pause_down
        self._hold_prev = hold_down

        return {
            "move_left": move_left,
            "move_right": move_right,
            "soft_drop": soft_drop,
            "soft_drop_held": down_down,
            "rotate": rotate,
            "confirm": confirm,
            "menu_left": menu_left,
            "menu_right": menu_right,
            "speed_up": speed_up,
            "speed_down": speed_down,
            "pause": pause,
            "hold": hold,
        }
