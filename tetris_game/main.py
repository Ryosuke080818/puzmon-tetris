# -*- coding: utf-8 -*-
"""
main.py
-------
テトリス風パズルゲームのエントリーポイント。

実行方法 (Windows PC):
    pip install -r requirements.txt
    python main.py
"""

from game import TetrisGame


def main():
    game = TetrisGame()
    game.run()


if __name__ == "__main__":
    main()
