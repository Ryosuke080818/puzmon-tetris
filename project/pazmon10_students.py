import pygame as pg
import sys, os, random, time
from typing import List, Tuple, Optional

# ---------------- サウンド安全化 ----------------
class _NullSound:
    def play(self, *args, **kwargs):
        return None

    def set_volume(self, *args, **kwargs):
        return None
    
class AnimeEffect:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.frame = 0
        self.finished = False
        self.last_update = pg.time.get_ticks()
    def update(self):
        now = pg.time.get_ticks()
        if now - self.last_update > 20:  # アニメーション速度
            if self.frame < len(EFFECT_IMAGES) - 1:
                self.frame += 1
                self.last_update = now
            else:
                self.finished = True

    def draw(self, screen):
        img = EFFECT_IMAGES[self.frame]
        screen.blit(img, (self.x - img.get_width()//2, self.y - img.get_height()//2))

def load_sound(path: str):
    """存在しない効果音で落ちないようにする。"""
    if os.path.exists(path):
        return pg.mixer.Sound(path)
    return _NullSound()

# BGM 音量（0.0〜1.0）
MUSIC_VOLUME = 0.3


def set_music_volume(vol: float):
    global MUSIC_VOLUME
    MUSIC_VOLUME = max(0.0, min(1.0, float(vol)))
    if pg.mixer.get_init():
        pg.mixer.music.set_volume(MUSIC_VOLUME)

# ---------------- フォント解決 ----------------
def get_jp_font(size: int) -> pg.font.Font:
    bundle = os.path.join("assets", "fonts", "BestTen-CRT.ttf")
    if os.path.exists(bundle):
        return pg.font.Font(bundle, size)
    candidates = [
        "NotoSansJP-Regular", "Noto Sans CJK JP", "Noto Sans JP",
        "Yu Gothic UI", "Yu Gothic",
        "Meiryo", "MS Gothic",
        "Hiragino Sans", "Hiragino Kaku Gothic ProN",
    ]
    for name in candidates:
        path = pg.font.match_font(name)
        if path:
            return pg.font.Font(path, size)
    return pg.font.SysFont(None, size)

# ---------------- 可変パラメータ ----------------
FRAME_DELAY = 0.5
ENEMY_DELAY = 1.0
WIN_W, WIN_H = 1010, 730 
FIELD_Y = WIN_H-230
SLOT_W = 65
SLOT_PAD = 3
LEFT_MARGIN = 30
GEM_IMG_SIZE = (SLOT_W - 4, SLOT_W - 4) #宝石の画像サイズ

# ドラッグ演出のための変数
DRAG_SCALE = 1.18
DRAG_SHADOW = (0, 0, 0, 90)

EFFECT_IMAGES = []
active_effects = []

#敵画像アニメーションのための変数
anim_timer = 0
show_frame = 0

# ---------------- 定義 ----------------
ELEMENT_SYMBOLS = {"火": "火", "水": "水", "風": "風", "土": "土", "命": "命", "無": " "}
COLOR_RGB = {
    "火": (230, 70, 70), "水": (70, 150, 230), "風": (90, 200, 120),
    "土": (200, 150, 80), "命": (220, 90, 200), "無": (160,160,160)
}
GEMS = ["火", "水", "風", "土", "命"]
SLOTS = [chr(ord('A')+i) for i in range(14)]

# ---------------- 画像 ----------------
def load_gem_image(elem: str) -> pg.Surface: #宝石の画像をロードする関数
    m = {
        "火":"fire.png", "水":"water.png",
        "風":"wind.png", "土":"earth.png",
        "命":"life.png", "無":"void.png"
    }
    fn = m.get(elem)
    if fn:
        path = os.path.join("assets","gems",fn)
        if os.path.exists(path):
            img = pg.image.load(path).convert_alpha()
            return pg.transform.smoothscale(img, GEM_IMG_SIZE)
    surf = pg.Surface(GEM_IMG_SIZE, pg.SRCALPHA); surf.fill((60,60,60,200))
    return surf

def load_monster_images(name: str) -> list[pg.Surface]:
    m = {
        "スライム":["slime1.png", "slime2.png"],
        "ゴブリン":["goblin1.png","goblin2.png"],
        "オオコウモリ":["bat1.png","bat2.png"],
        "ウェアウルフ":["werewolf1.png","werewolf2.png"],
        "ドラゴン":["dragon1.png","dragon2.png"],
        "宝箱":["chest1.png","chest2.png"]
    }
    fn = m.get(name)
    surfaces = []
    if fn:
        for f in fn:
            path = os.path.join("assets","monsters",f)
            if os.path.exists(path):
                img = pg.image.load(path).convert_alpha()
                surfaces.append(pg.transform.smoothscale(img, (400,400)))
    if not surfaces:
        surf = pg.Surface((400,400), pg.SRCALPHA); surf.fill((60,60,60,200))
        return [surf, surf]
    return surfaces

# ---------------- HPバー ----------------
def hp_bar_surf(current: int, max_hp: int, w: int, h: int) -> pg.Surface:
    """HPバー（max600基準でスケーリング）"""
    # HP比（0〜1）
    ratio = max(0, min(1, current / max_hp if max_hp > 0 else 0))
    # 600を基準にスケール（例：max_hp=100なら1/6）
    scale = min(1.0, max_hp)
    bar_w = int(w * scale)

    # HP割合で塗り幅を決定
    fill_w = int(bar_w * ratio)

    # 色（体力残量による）
    if ratio >= 0.6:
        col = (40, 200, 90)
    elif ratio >= 0.3:
        col = (230, 200, 60)
    else:
        col = (230, 70, 70)

    # バー描画
    surf = pg.Surface((w, h), pg.SRCALPHA)
    # 背景（透明）
    bg = pg.Surface((bar_w, h), pg.SRCALPHA)
    bg.fill((0, 0, 0, 120))
    surf.blit(bg, (0, 0))
    # 緑バー
    fg = pg.Surface((fill_w, h), pg.SRCALPHA)
    fg.fill(col)
    surf.blit(fg, (0, 0))
    return surf

# ---------------- 盤面ロジック ----------------
def init_field(rows=3, cols=14)->List[List[str]]:
    return [[random.choice(GEMS) for _ in range(cols)]for _ in range(rows)]

def leftmost_run(field:List[List[str]])->Optional[Tuple[int,int]]:
       rows = len(field)
       cols = len(field[0])
       for r in range(rows):
        row = field[r]
        i = 0
        while i < cols:
            j = i + 1
            while j < cols and row[j] == row[i]:
                j += 1
            L = j - i
            if L >= 3 and row[i] in GEMS:
                return (r, i, L)
            i = j
       return None

def collapse_left(row:List[str], start:int, length:int):
    for k in range(start, start+length):
        row[k]="無"
    rest=[e for e in row if e!="無"]
    row[:] = rest + ["無"]*(len(row) - len(rest))

def fill_random(row:List[str]):
    for i,e in enumerate(row):
        if e=="無": 
            row[i]=random.choice(GEMS)
def find_runs(field: List[List[str]]):
    global active_effects
    
    rows = len(field)
    cols = len(field[0])
    runs = []

    for r in range(rows):
        c = 0
        while c < cols:
            j = c + 1
            while j < cols and field[r][j] == field[r][c]:
                j += 1
            length = j - c
            if length >= 3 and field[r][c] in GEMS:
                runs.append((r, c, length, 'h'))
            c = j

    for c in range(cols):
        r = 0
        while r < rows:
            j = r + 1
            while j < rows and field[j][c] == field[r][c]:
                j += 1
            length = j - r
            if length >= 3 and field[r][c] in GEMS:
                runs.append((r, c, length, 'v'))
            r = j

    if runs:
        for (r, c, L, direction) in runs:
            for i in range(L):
                curr_r = r + (i if direction == 'v' else 0)
                curr_c = c + (i if direction == 'h' else 0)
                
                rect = slot_rect(curr_r, curr_c)
                
                active_effects.append(AnimeEffect(rect.centerx, rect.centery))

    return runs

def apply_runs(field: List[List[str]], runs):
    """run の部分を '無' にし、全行に対して左詰め・ランダム補充を行う"""
    # 消去
    for (r, c, length, direction) in runs:
        if direction == 'h':  # 横
            for x in range(c, c + length):
                field[r][x] = "無"
        else:  # 縦
            for y in range(r, r + length):
                field[y][c] = "無"

    # 全行を左詰めして補充
    for r in range(len(field)):
        collapse_left(field[r], 0, 0)
        fill_random(field[r])
    return runs            

# ---------------- ダメージ/回復 ----------------
def jitter(v:float, r:float=0.10)->int:
    return max(1, int(v*random.uniform(1-r,1+r)))

def attr_coeff(att,defe):
    cyc={"火":"風","風":"土","土":"水","水":"火"}
    if att in cyc and cyc[att]==defe: return 2.0
    if defe in cyc and cyc[defe]==att: return 0.5
    return 1.0

def party_attack_from_gems(elem:str, run_len:int, combo:int, party:dict, monster:dict)->int:
    combo_coeff = 1.5 ** ((run_len - 3) + combo)
    if elem=="命":
        heal=jitter(20*combo_coeff); party["hp"]=min(party["max_hp"], party["hp"]+heal); return 0
    ally = next((a for a in party["allies"] if a["element"]==elem), None)
    if not ally: return 0
    base=max(1, ally["ap"]-monster["dp"])
    dmg=jitter(base*attr_coeff(elem,monster["element"])*combo_coeff)
    monster["hp"]=max(0,monster["hp"]-dmg); return dmg

def enemy_attack(party:dict, monster:dict)->int:
    base=max(1, monster["ap"]-party["dp"])
    dmg=jitter(base); party["hp"]=max(0,party["hp"]-dmg); return dmg

# ---------------- 描画ユーティリティ ----------------
def slot_rect(r:int, c:int) -> pg.Rect:
    tx = LEFT_MARGIN + c * (SLOT_W + SLOT_PAD)
    ty = FIELD_Y + r * (SLOT_W + SLOT_PAD)
    return pg.Rect(tx,ty, SLOT_W, SLOT_W)

def draw_gem_at(screen, elem: str, x: int, y: int, scale=1.0, with_shadow=False, gem_images=None):
    r = int((SLOT_W // 2 - 10) * scale)
    img = gem_images.get(elem)
    if img is None:
        return
    iw, ih = img.get_size()
    sw, sh = int(iw * scale), int(ih * scale)
    img_scl = pg.transform.smoothscale(img, (sw, sh))
    rect = img_scl.get_rect(center=(x, y))
    if with_shadow:
        shadow = pg.Surface((sw + 10, sh + 10), pg.SRCALPHA)
        pg.draw.ellipse(shadow, DRAG_SHADOW, shadow.get_rect())
        screen.blit(shadow, (rect.x - 5, rect.y - 5 + 4))
    screen.blit(img_scl, rect.topleft)

def draw_field(
    screen,
    field: List[List[str]],
    font,
    hover_idx: Optional[Tuple[int, int]] = None,
    drag_src: Optional[Tuple[int, int]] = None,
    drag_elem: Optional[str] = None,
    gem_images=None,
):
    rows = len(field)
    cols = len(field[0]) if rows > 0 else 0 
    # スロット下地 & ホバー強調
    for r in range(rows):
        for c in range(cols):
            rect = slot_rect(r, c)
            base = (60, 60, 80) if hover_idx == (r, c) else (35, 35, 40)
            pg.draw.rect(screen, base, rect, border_radius=8)
    
    # 宝石（ドラッグ開始スロットは空に見せる）
    for r in range(rows):
        for c in range(cols):
            if drag_src is not None and (r, c) == drag_src:
                continue
            elem = field[r][c]
            rect = slot_rect(r, c)
            cx, cy = rect.center
            draw_gem_at(screen, elem, cx, cy, gem_images=gem_images)
        
    # ドラッグ中の宝石（ゴースト）をカーソル位置に拡大表示
    if drag_elem is not None:
        mx, my = pg.mouse.get_pos()
        draw_gem_at(
            screen,
            drag_elem,
            mx,
            my - 4,
            scale=DRAG_SCALE,
            with_shadow=True,
            gem_images=gem_images,
        )

def draw_top(screen, enemy, party, font, enemy_frames, show_frame=0):
    current_time = pg.time.get_ticks()
    
    # 敵画像/名前
    actual_frame = show_frame % len(enemy_frames)
    img = enemy_frames[actual_frame]
    if enemy["name"] == "ゴブリン":
        screen.blit(img, (130, 70))
    else:
        screen.blit(img, (50, 70))

    if enemy["max_hp"] > 0:
        # 敵名とHPバー
        if current_time - enemy.get('enemy_damage_time', 0) < 400:
            e_name_color = (255, 50, 50) 
        else:
            e_name_color = (240, 240, 240)
        name = font.render(enemy["name"], True, e_name_color)
        screen.blit(name, (525, WIN_H-682))
        enemy_bar = hp_bar_surf(enemy['hp'], enemy['max_hp'], 420, 18)
        screen.blit(enemy_bar, (525, WIN_H-640))
    
        # 敵HP数値（バー右側に）
        if current_time - enemy.get('enemy_damage_time', 0) < 400: 
            hp_color = (255, 50, 50) 
        else:
            hp_color = (240, 240, 240)
        enemy_hp_text = font.render(f"{int(max(0, enemy['hp']))}/{enemy['max_hp']}", True, hp_color)
        screen.blit(enemy_hp_text, (838, WIN_H-682))

        # 「パーティ」ラベル
        if current_time - party.get('last_damage_time', 0) < 400:
            if party.get('hp_event_type') == 'heal':
                p_name_color = (50, 255, 50)
            else:
                p_name_color = (255, 50, 50) 
        else:
            p_name_color = (240, 240, 240)
        label = font.render("パーティ", True, p_name_color)
        screen.blit(label, (525, WIN_H-582))

        # パーティHPバー
        party_bar = hp_bar_surf(party['hp'], party['max_hp'], 420, 18)
        screen.blit(party_bar, (525, WIN_H-540))

        # パーティHP数値
        if current_time - party.get('last_damage_time', 0) < 400:
            if party.get('hp_event_type') == 'heal':
                hp_color = (50, 255, 50)
            else:
                hp_color = (255, 50, 50) 
        else:
            hp_color = (240, 240, 240)
        party_hp_text = font.render(f"{int(max(0, party['hp']))}/{party['max_hp']}", True, hp_color)
        screen.blit(party_hp_text, (838, WIN_H-582))

def draw_message(screen, text, font):
    lines = text.split('\n')
    for i, line in enumerate(lines):
        surf = font.render(line, True, (230,230,230))
        screen.blit(surf,(525,WIN_H-455+i*40))

# ---------------- タイトル画面 ----------------

def settings_screen(screen: pg.Surface) -> None:
    
    title_font = get_jp_font(44)
    font = get_jp_font(24)
    small = get_jp_font(22)
    clock = pg.time.Clock()

    back_btn = pg.Rect(30, 30, 140, 44)
    button = load_sound(os.path.join("assets", "sounds", "button.wav"))
    # スライダー
    bar = pg.Rect(WIN_W // 2 - 220, 320, 440, 10)
    knob_r = 14
    dragging = False

    while True:
        mx, my = pg.mouse.get_pos()
        for e in pg.event.get():
            if e.type == pg.QUIT:
                return
            if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                return
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                if back_btn.collidepoint(e.pos):
                    button.play() 
                    return
                # つまみ判定 or バークリック
                knob_x = int(bar.x + MUSIC_VOLUME * bar.w)
                knob_y = bar.y + bar.h // 2
                if (mx - knob_x) ** 2 + (my - knob_y) ** 2 <= knob_r ** 2 or bar.collidepoint(e.pos):
                    dragging = True
            if e.type == pg.MOUSEBUTTONUP and e.button == 1:
                dragging = False

        if dragging:
            t = (mx - bar.x) / bar.w
            set_music_volume(t)

        # 描画
        screen.fill((12, 12, 18))
        screen.blit(title_font.render("設定", True, (240, 240, 240)), (WIN_W // 2 - 40, 120))

        # 戻るボタン
        back_hover = back_btn.collidepoint(mx, my)
        pg.draw.rect(screen, (80, 80, 110) if back_hover else (55, 55, 75), back_btn, border_radius=10)
        pg.draw.rect(screen, (230, 230, 230), back_btn, width=2, border_radius=10)
        bt = small.render("戻る", True, (245, 245, 245))
        screen.blit(bt, (back_btn.centerx - bt.get_width() // 2, back_btn.centery - bt.get_height() // 2))

        # 音量スライダー
        screen.blit(font.render("BGM 音量", True, (235, 235, 235)), (bar.x, bar.y - 48))
        pg.draw.rect(screen, (60, 60, 70), bar, border_radius=6)
        fill = pg.Rect(bar.x, bar.y, int(bar.w * MUSIC_VOLUME), bar.h)
        pg.draw.rect(screen, (70, 120, 220), fill, border_radius=6)
        knob_x = int(bar.x + MUSIC_VOLUME * bar.w)
        knob_y = bar.y + bar.h // 2
        pg.draw.circle(screen, (245, 245, 245), (knob_x, knob_y), knob_r)
        pg.draw.circle(screen, (30, 30, 35), (knob_x, knob_y), knob_r, width=2)

        screen.blit(small.render(f"{int(MUSIC_VOLUME*100)}%", True, (230, 230, 230)), (bar.right + 12, bar.y - 10))
        screen.blit(small.render("（ドラッグで調整 / ESCで戻る）", True, (200, 200, 200)), (bar.x, bar.bottom + 20)) ###################

        pg.display.flip()
        clock.tick(60)


def title_screen(screen: pg.Surface, font: pg.font.Font) -> bool:
    button = load_sound(os.path.join("assets", "sounds", "button.wav"))

    # ボタンはクリックのみ　True: ゲーム開始 / False: 終了
    title_font = get_jp_font(70)
    sub_font = get_jp_font(28)
    clock = pg.time.Clock()

    # ボタン
    btn_w, btn_h = 320, 64
    start_btn = pg.Rect(WIN_W // 2 - btn_w // 2, 300, btn_w, btn_h)
    settings_btn = pg.Rect(WIN_W // 2 - btn_w // 2, 380, btn_w, btn_h)
    quit_btn = pg.Rect(WIN_W // 2 - btn_w // 2, 460, btn_w, btn_h)

    while True:
        mx, my = pg.mouse.get_pos()  # マウスの座標

        for e in pg.event.get():
            if e.type == pg.QUIT:
                return False
            if e.type == pg.KEYDOWN and e.key == pg.K_ESCAPE:
                return False
            if e.type == pg.MOUSEBUTTONDOWN and e.button == 1:
                if start_btn.collidepoint(e.pos):
                    button.play()  # 効果音再生
                    return True
                if settings_btn.collidepoint(e.pos):
                    button.play()
                    settings_screen(screen)
                if quit_btn.collidepoint(e.pos):
                    button.play()
                    return False

        screen.fill((12, 12, 18))

        t = title_font.render("Puzzle & Monsters", True, (240, 240, 240))  # タイトル
        screen.blit(t, (WIN_W // 2 - t.get_width() // 2, 170))

        # ボタン描画（ホバー）
        start_hover = start_btn.collidepoint(mx, my)
        settings_hover = settings_btn.collidepoint(mx, my)
        quit_hover = quit_btn.collidepoint(mx, my)

        pg.draw.rect(screen, (70, 120, 220) if start_hover else (50, 90, 170), start_btn, border_radius=12)
        pg.draw.rect(screen, (90, 160, 120) if settings_hover else (60, 120, 90), settings_btn, border_radius=12)
        pg.draw.rect(screen, (220, 90, 90) if quit_hover else (170, 60, 60), quit_btn, border_radius=12)

        pg.draw.rect(screen, (230, 230, 230), start_btn, width=2, border_radius=12)
        pg.draw.rect(screen, (230, 230, 230), settings_btn, width=2, border_radius=12)
        pg.draw.rect(screen, (230, 230, 230), quit_btn, width=2, border_radius=12)

        # ボタン文字
        s1 = sub_font.render("スタート", True, (245, 245, 245))
        screen.blit(s1, (start_btn.centerx - s1.get_width() // 2, start_btn.centery - s1.get_height() // 2))

        sset = sub_font.render("設定", True, (245, 245, 245))
        screen.blit(sset, (settings_btn.centerx - sset.get_width() // 2, settings_btn.centery - sset.get_height() // 2))

        s2 = sub_font.render("終了", True, (245, 245, 245))
        screen.blit(s2, (quit_btn.centerx - s2.get_width() // 2, quit_btn.centery - s2.get_height() // 2))

        pg.display.flip()
        clock.tick(60)

# ---------------- メイン ----------------
def main():
    pg.init()

    
    try:
        pg.mixer.init()  # BGMと効果音追加
        mixer_ok = True
    except Exception:
        mixer_ok = False

    bgm_title = os.path.join("assets","sounds","maou_bgm_8bit01_opening.mp3")
    bgm_battle = os.path.join("assets","sounds","maou_bgm_8bit25_battle.mp3")
    bgm_boss = os.path.join("assets","sounds","maou_bgm_8bit18_boss.mp3")

    move = pg.mixer.Sound(os.path.join("assets","sounds","move.wav"))
    attack = pg.mixer.Sound(os.path.join("assets","sounds","attack.wav"))
    damage = pg.mixer.Sound(os.path.join("assets","sounds","damage.wav"))
    lifeup = pg.mixer.Sound(os.path.join("assets","sounds","life.wav"))
    clear = pg.mixer.Sound(os.path.join("assets","sounds","clear.wav"))
    button = pg.mixer.Sound(os.path.join("assets","sounds","button.wav"))
    gameover = pg.mixer.Sound(os.path.join("assets","sounds","gameover.wav"))
    
    move.set_volume(1.0) #音量
    attack.set_volume(3.0)
    damage.set_volume(1.0)
    lifeup.set_volume(1.0)
    clear.set_volume(1.0)
    button.set_volume(3.0)
    gameover.set_volume(1.0) 

    if mixer_ok:
        set_music_volume(MUSIC_VOLUME)
    
    screen = pg.display.set_mode((WIN_W, WIN_H))
    gem_images = {elem: load_gem_image(elem) for elem in GEMS + ["無"]}
    pg.display.set_caption("Puzzle & Monsters - GUI Prototype")
    font = get_jp_font(26)
    
    # アニメーション画像
    global EFFECT_IMAGES
    for i in range(7):
        img = pg.image.load(f"sprite_{i}.png").convert_alpha()
        # リサイズ
        img = pg.transform.scale(img, (SLOT_W*1.6, SLOT_W*1.6))
        EFFECT_IMAGES.append(img)

    if os.path.exists(bgm_title): #タイトル画面のBGM再生
        pg.mixer.music.fadeout(500)
        pg.mixer.music.load(bgm_title)
        pg.mixer.music.play(-1)

    if not title_screen(screen, font):
        pg.quit()
        sys.exit()
    back_btn = pg.Rect(WIN_W - 1000, 10, 150, 38) #タイトルへ戻るボタン

    if os.path.exists(bgm_battle): #バトルBGM再生
        pg.mixer.music.fadeout(500)
        pg.mixer.music.load(bgm_battle)
        pg.mixer.music.play(-1)

    #アニメーション用変数
    anim_timer = pg.time.get_ticks()
    show_frame = 0
    
    global active_effects
    active_effects = []
    
    party = {
        "player_name":"Player",
        "allies":[
            {"name":"青龍","element":"風","hp":150,"max_hp":150,"ap":15,"dp":10,"last_damage_time":0,"hp_event_type":"none"}, 
            {"name":"朱雀","element":"火","hp":150,"max_hp":150,"ap":25,"dp":10,"last_damage_time":0,"hp_event_type":"none"},
            {"name":"白虎","element":"土","hp":150,"max_hp":150,"ap":20,"dp":5,"last_damage_time":0,"hp_event_type":"none"},
            {"name":"玄武","element":"水","hp":150,"max_hp":150,"ap":20,"dp":15,"last_damage_time":0,"hp_event_type":"none"},
        ],
        "hp":600, "max_hp":600, "dp":(10+10+5+15)/4
    }
    enemies = [
        {"name":"スライム","element":"水","hp":100,"max_hp":100,"ap":10,"dp":1,"enemy_damage_time":0}, 
        {"name":"ゴブリン","element":"土","hp":200,"max_hp":200,"ap":20,"dp":5,"enemy_damage_time":0},
        {"name":"オオコウモリ","element":"風","hp":300,"max_hp":300,"ap":30,"dp":10,"enemy_damage_time":0},
        {"name":"ウェアウルフ","element":"風","hp":300,"max_hp":300,"ap":40,"dp":15,"enemy_damage_time":0},
        {"name":"ドラゴン","element":"火","hp":500,"max_hp":500,"ap":50,"dp":20,"enemy_damage_time":0},
    ]
    enemy_idx=0
    enemy = enemies[enemy_idx]
    field = init_field()

    rows = len(field)
    cols = len(field[0]) if rows > 0 else 0 

    monster_images = load_monster_images(enemy["name"])

    drag_src: Optional[int] = None
    drag_elem: Optional[str] = None
    hover_idx: Optional[int] = None
    message = "ドラッグで宝石を移動"

    clock = pg.time.Clock()
    running=True
    combo=0
    waiting_for_effects = False
    wait_timer = 0 
    state = "PLAYER_TURN"

    while running:
        current_time = pg.time.get_ticks()
        if current_time - anim_timer > 400:
            show_frame = (show_frame + 1) % len(monster_images)
            anim_timer = current_time

        # エフェクトの更新
        for eff in active_effects[:]:
            eff.update()
            if eff.finished:
                active_effects.remove(eff)
        if waiting_for_effects and not active_effects:
            if wait_timer == 0:
                combo += 1 # コンボ加算
                current_messages = []
                
                for (r, c, L, direction) in current_runs:
                    elem = field[r][c]
                    if elem == "命":
                        heal = jitter(20 * (1.5 ** ((L - 3) + combo)))
                        party['hp'] = min(party['max_hp'], party['hp'] + int(heal))
                        party['last_damage_time'] = current_time
                        party['hp_event_type'] = 'heal'
                        lifeup.play()
                        current_messages.append(f"HP +{int(heal)}")
                    else:
                        dmg = party_attack_from_gems(elem, L, combo, party, enemy)
                        if dmg > 0:
                            enemy['hp'] -= int(dmg)
                            attack.play()
                            current_messages.append(f"{elem}攻撃！ {int(dmg)}ダメージ")
                    
                    field[r][c] = "無"
                    
                    if current_messages:
                        message = "\n".join(current_messages)
                    
                    wait_timer = current_time + 300
            
            elif current_time > wait_timer:
                wait_timer = 0
                
                apply_runs(field, current_runs)

                next_runs = find_runs(field)
                if next_runs:
                    current_runs = next_runs
                    waiting_for_effects = True
                else:
                    waiting_for_effects = False
                    wait_timer = current_time + 800
                    
        if not waiting_for_effects and wait_timer > 0:
            if current_time > wait_timer:
                wait_timer = 0        
                
                if enemy['hp'] > 0:
                    # 敵ターン
                    edmg = enemy_attack(party, enemy)
                    party['hp'] -= int(edmg)
                    party['last_damage_time'] = current_time
                    party['hp_event_type'] = 'damage'
                    damage.play()
                    message = f"{enemy['name']}の攻撃！ -{int(edmg)}"
                    if party['hp']<=0:
                                pg.mixer.music.fadeout(500) #BGM停止・効果音
                                gameover.play()
                                message="パーティは力尽きた…（ESCで終了）"
                else:
                    enemy['hp'] = 0 
                    
                    enemy_idx += 1
                    if enemy_idx < len(enemies):
                        enemy = enemies[enemy_idx]
                        monster_images = load_monster_images(enemy["name"])
                        field = init_field() # 盤面リセット
                        message = f"{enemies[enemy_idx-1]['name']}を倒した！\n次は {enemy['name']}！"
                    else:
                        # 全クリ処理
                        pg.mixer.music.fadeout(500)
                        clear.play()
                        enemy = {"name":"宝箱","element":"無","hp":0,"max_hp":0}
                        monster_images = load_monster_images("宝箱")
                        message = "ダンジョン制覇！おめでとう！"
        
        for e in pg.event.get():
            if e.type == pg.QUIT: running = False
            if waiting_for_effects or wait_timer > 0 or party['hp'] <= 0:
                continue
            if e.type == pg.MOUSEBUTTONUP and e.button == 1:
                if drag_src:
                    runs = find_runs(field)
                    if runs:
                        current_runs = runs
                        combo = 0
                        waiting_for_effects = True # エフェクト待機モード
                    drag_src = None
                    
            if e.type==pg.QUIT:
                running=False

            elif e.type==pg.MOUSEBUTTONDOWN and e.button==1:
              if party['hp'] <= 0 or enemy['name'] == "宝箱" or waiting_for_effects or wait_timer > 0:
                    continue
              # タイトルへ戻る
              if enemy["name"] != "宝箱":
                if back_btn.collidepoint(e.pos):
                    if os.path.exists(bgm_title): #タイトル画面BGM再生
                        pg.mixer.music.fadeout(500)
                        button.play() 
                        pg.mixer.music.load(bgm_title)
                        pg.mixer.music.play(-1)
                    
                    if not title_screen(screen, font):
                        pg.quit()
                        sys.exit()

                    if os.path.exists(bgm_battle): #バトルBGM再生
                        pg.mixer.music.fadeout(500)
                        pg.mixer.music.load(bgm_battle)
                        pg.mixer.music.play(-1)
                    
                    # ゲーム状態を初期化
                    party['hp'] = party['max_hp']
                    enemy_idx = 0
                    enemy = enemies[enemy_idx]
                    enemy['hp'] = enemy['max_hp']
                    field = init_field()
                    message = "ドラッグで宝石を移動"
                    drag_src = None
                    drag_elem = None
                    hover_idx = None
                    continue
                    
                mx,my = e.pos
                if FIELD_Y <= my <= FIELD_Y + rows * (SLOT_W + SLOT_PAD):
                    r = (my - FIELD_Y) // (SLOT_W + SLOT_PAD)
                    c = (mx - LEFT_MARGIN) // (SLOT_W + SLOT_PAD)
                    if 0 <= r < rows and 0 <= c < cols:
                        drag_src = (r, c)
                        drag_elem = field[r][c] 

            elif e.type==pg.MOUSEMOTION:
                mx, my = e.pos
                if FIELD_Y <= my <= FIELD_Y + rows * (SLOT_W + SLOT_PAD):
                    r = (my - FIELD_Y) // (SLOT_W + SLOT_PAD)
                    c = (mx - LEFT_MARGIN) // (SLOT_W + SLOT_PAD)
                    if 0 <= r < rows and 0 <= c < cols:
                        hover_idx = (r, c)
                        if drag_src is not None and hover_idx != drag_src:
                            move.play()  # 効果音
                            r0, c0 = drag_src
                            r1, c1 = hover_idx
                            field[r0][c0], field[r1][c1] = field[r1][c1], field[r0][c0]
                            drag_src = hover_idx
                    else:
                        hover_idx = None
                else:
                    hover_idx = None
    
            elif e.type == pg.MOUSEBUTTONUP and e.button == 1:
                if drag_src is not None:
                    runs = find_runs(field)
                    if runs:
                        current_runs = runs
                        combo = 0
                        waiting_for_effects = True
                    
                    drag_src = None
                    drag_elem = None
                    hover_idx = None

                # ドラッグ終了
                drag_src = None
                drag_elem = None
                hover_idx = None

         # 常時描画
        screen.fill((22,22,28))
        draw_top(screen, enemy, party, font, monster_images, show_frame)
        draw_field(screen, field, font, hover_idx, drag_src, drag_elem, gem_images=gem_images)
        draw_message(screen, message, font)
        for eff in active_effects:
            eff.draw(screen)

        # 「タイトルへ」ボタン
        if enemy["name"] != "宝箱":
            mx, my = pg.mouse.get_pos()
            back_hover = back_btn.collidepoint(mx, my)
            pg.draw.rect(screen, (80, 80, 110) if back_hover else (55, 55, 75), back_btn, border_radius=10)
            pg.draw.rect(screen, (230, 230, 230), back_btn, width=2, border_radius=10)
            btxt = get_jp_font(18).render("タイトルへ", True, (245, 245, 245))
            screen.blit(btxt, (back_btn.centerx - btxt.get_width()//2, back_btn.centery - btxt.get_height()//2))
        pg.display.flip()
        clock.tick(60)

        keys=pg.key.get_pressed()
        if keys[pg.K_ESCAPE]:
            running=False

    pg.quit()
    sys.exit()

if __name__=="__main__":
    main()
