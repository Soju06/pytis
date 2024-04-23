from collections import namedtuple
import ctypes
from io import StringIO
import math
import os
import sys
import time
from typing import Literal, Any, Callable
import msvcrt
from random import Random
import threading
import winsound

ANSI_COLOR = True
# Windows 터미널에서 UNIX Color Code를 지원하지 않는 경우 ANSI Color Code를 사용합니다.

##############################
##           ANSI           ##
##############################

RGB_ANSI_MAP: dict[tuple[int, int, int], int] = {
    (0, 0, 0): 0,
    (0, 0, 128): 1,
    (0, 128, 0): 2,
    (0, 128, 128): 3,
    (128, 0, 0): 4,
    (128, 0, 128): 5,
    (128, 128, 0): 6,
    (192, 192, 192): 7,
    (128, 128, 128): 8,
    (0, 0, 255): 9,
    (0, 255, 0): 10,
    (0, 255, 255): 11,
    (255, 0, 0): 12,
    (255, 0, 255): 13,
    (255, 255, 0): 14,
    (255, 255, 255): 15,
}

CACHED_RGB_ANSI_MAP: dict[tuple[int, int, int], int] = {}
# 유사색 계산을 빠르게 하기 위한 캐시

def rgb_to_ansi(r: int, g: int, b: int) -> int:
    # 24bit 색상을 가장 유사한 ANSI 색상으로 변환합니다.

    if (r, g, b) in CACHED_RGB_ANSI_MAP:
        return CACHED_RGB_ANSI_MAP[(r, g, b)]

    # 가장 유사한 ANSI 색상을 찾습니다.
    eq: int | None = None
    d: int | None = None

    for rgb, ansi in RGB_ANSI_MAP.items():
        _d = (rgb[0] - r) ** 2 + (rgb[1] - g) ** 2 + (rgb[2] - b) ** 2
        if d is None or d > _d:
            eq = ansi
            d = _d

    CACHED_RGB_ANSI_MAP[(r, g, b)] = eq  # type: ignore
    return eq  # type: ignore

def set_console_color(fr: int, fg: int, fb: int, br: int, bg: int, bb: int):
    # Windows Console을 색상을 설정합니다.

    ansi_fg = rgb_to_ansi(fr, fg, fb)
    ansi_bg = rgb_to_ansi(br, bg, bb)

    ctypes.windll.kernel32.SetConsoleTextAttribute(
        ctypes.windll.kernel32.GetStdHandle(-11), ansi_fg + ansi_bg * 16
    )

##############################
##          CONFIG          ##
##############################

max_score: int | None = None

def get_max_score():
    # 최고 점수를 가져옵니다.
    global max_score
    if max_score != None: return max_score
    
    try:
        with open('score', 'r') as f:
            return int(f.read())
    except:
        return 0

def set_max_score(score):
    # 최고 점수를 설정합니다.
    global max_score
    max_score = score
    
    with open('score', 'w') as f:
        f.write(str(score))

##############################
##       VIEW ENGINE        ##
##############################

def __Color___eq__(self, __o: object) -> bool:
    if isinstance(__o, Color):
        return self.r == __o.r and self.g == __o.g and self.b == __o.b
    return False

def __Color___add__(self, __o: object) -> 'Color':  # type: ignore
    # Color 데이터를 다른 Color 데이터와 더합니다.
    if isinstance(__o, Color):
        return Color(self.r + __o.r, self.g + __o.g, self.b + __o.b)
    return NotImplemented

Color = namedtuple('Color', 'r g b')

Color.__eq__ = __Color___eq__
Color.__add__ = __Color___add__

def __Colors_gray(n: int):
    return Color(n, n, n)

Colors = type('Colors', (), {
    'BLACK': Color(0, 0, 0),
    'WHITE': Color(255, 255, 255),
    'RED': Color(255, 0, 0),
    'gray': __Colors_gray,
})

RESET = '\033[0m'

def rgb_fg(r: int, g: int, b: int):
    r, g, b = max(min(r, 255), 0), max(min(g, 255), 0), max(min(b, 255), 0)
    return f'\x1b[38;2;{r};{g};{b}m'

def rgb_bg(r: int, g: int, b: int):
    r, g, b = max(min(r, 255), 0), max(min(g, 255), 0), max(min(b, 255), 0)
    return f'\x1b[48;2;{r};{g};{b}m'


def __Chars_char(char: str):
    # 캐릭터 데이터 길이가 2로 보장합니다.
    return char.ljust(2, ' ')

Chars = type('Chars', (), {
    'BLOCK': __Chars_char('██'),
    'EMPTY': __Chars_char('  '),
    'char': __Chars_char,
})

def __Pixel__init__(self, fg: Color = Colors.WHITE, bg: Color = Colors.BLACK, char: str = Chars.EMPTY):  # type: ignore
    self.fg = fg
    self.bg = bg
    self.char = char

def __Pixel_copy(self):
    return Pixel(self.fg, self.bg, self.char)  # type: ignore

def __Pixel_str(self, without_fg: bool = False, without_bg: bool = False):
    # Pixel 데이터를 콘솔에 출력할 수 있는 문자열로 변환합니다.
    return f'{"" if without_fg else rgb_fg(self.fg.r, self.fg.g, self.fg.b)}{"" if without_bg else rgb_bg(self.bg.r, self.bg.r, self.bg.b)}{self.char}'

def __Pixel___str__(self):
    return self.str()

def __Pixel___eq__(self, __o: object) -> bool:
    if isinstance(__o, Pixel):
        return self.fg == __o.fg and self.bg == __o.bg and self.char == __o.char  # type: ignore
    return False

Pixel = type('Pixel', (), {
    '__init__': __Pixel__init__,
    'copy': __Pixel_copy,
    'str': __Pixel_str,
    '__str__': __Pixel___str__,
    '__eq__': __Pixel___eq__,
})

Pixels = type('Pixels', (), {
    'EMPTY': Pixel(char=Chars.EMPTY),  # type: ignore
    'WHITE': Pixel(bg=Colors.WHITE, char=Chars.EMPTY),  # type: ignore
    'BLACK': Pixel(Colors.BLACK, char=Chars.BLOCK),  # type: ignore
    'BLACK_TEXT': Pixel(Colors.BLACK, Colors.WHITE),  # type: ignore
    'WHITE_TEXT': Pixel(Colors.WHITE, Colors.BLACK),  # type: ignore
    'BR': Pixel(bg=Color(40, 49, 62)),  # type: ignore
})

def __Mat___init__(self, width: int, height: int, repaint: bool = False, pixel: Pixel = Pixel()):
    self.width = width
    self.height = height
    self.data = [pixel for _ in range(width * height)]
    self.mx = width - 1
    self.my = height - 1
    self.repaint = repaint

def __Mat___getitem__(self, index: tuple[int, int]) -> Pixel:
    x, y = index
    return self.data[y * self.width + x]

def __Mat___setitem__(self, index: tuple[int, int], value: Pixel):
    x, y = index
    self.data[y * self.width + x] = value

def __Mat_copy(self):
    mat = Mat(self.width, self.height)  # type: ignore
    mat.data = [pixel.copy() for pixel in self.data]  # type: ignore
    return mat

def __Mat_scale(self, scale: int):
    # 2차원 이미지 데이터를 확대합니다.
    mat = Mat(self.width * scale, self.height * scale)  # type: ignore
    for i in range(self.width):
        for j in range(self.height):
            pixel = self[i, j]
            for k in range(scale):
                for l in range(scale):
                    mat[i * scale + k, j * scale + l] = pixel  # type: ignore
    return mat

def __Mat_rotate(self, angle: Literal[0, 90, 180, 270, -90, -180, -270]):
    # 2차원 이미지 데이터를 회전합니다.
    if angle == 0: return self.copy()

    mat = Mat(self.width if angle % 180 == 0 else self.height, self.height if angle % 180 == 0 else self.width)  # type: ignore
    
    for i in range(self.width):
        for j in range(self.height):
            if angle == 90 or angle == -270:
                mat[j, self.mx - i] = self[i, j]  # type: ignore
            elif angle == 180 or angle == -180:
                mat[self.mx - i, self.my - j] = self[i, j]  # type: ignore
            elif angle == 270 or angle == -90:
                mat[self.my - j, i] = self[i, j]  # type: ignore

    return mat

def __Mat_paste(self, mat: 'Mat', x: int, y: int):
    # 2차원 이미지 데이터에 다른 2차원 이미지 데이터를 붙여넣습니다.
    for i in range(mat.width):  # type: ignore
        for j in range(mat.height):  # type: ignore
            self[x + i, y + j] = mat[i, j]  # type: ignore

def __Mat_paste_mask(self, mat: 'Mat', x: int, y: int, mask_fg: Color | None = None, mask_bg: Color | None = None, mask_char: str | None = None):
    # 2차원 이미지 데이터에 다른 2차원 이미지 데이터를 마스크하여 붙여넣습니다.
    for i in range(mat.width):  # type: ignore
        for j in range(mat.height):  # type: ignore
            pixel = mat[i, j]  # type: ignore
            if (mask_fg is not None and pixel.fg == mask_fg) or (mask_bg is not None and pixel.bg == mask_bg) or (mask_char is not None and pixel.char == mask_char):
                continue
            self[x + i, y + j] = pixel

def __Mat_fill(self, pixel: Pixel):
    # 2차원 이미지 데이터를 특정 Pixel 데이터로 채웁니다.
    for i in range(self.width * self.height):
        self.data[i] = pixel

def __Mat_fill_rect(self, x: int, y: int, width: int, height: int, pixel: Pixel):
    # 2차원 이미지 데이터의 특정 영역을 특정 Pixel 데이터로 채웁니다.
    for i in range(width):
        for j in range(height):
            self[x + i, y + j] = pixel

def __Mat_draw_rect(self, x: int, y: int, width: int, height: int, pixel: Pixel):
    # 2차원 이미지 데이터의 특정 영역의 외각선을 특정 Pixel 데이터로 채웁니다.
    self.fill_rect(x, y, width, 1, pixel)
    self.fill_rect(x, y + height - 1, width, 1, pixel)
    self.fill_rect(x, y, 1, height, pixel)
    self.fill_rect(x + width - 1, y, 1, height, pixel)

def __Mat_draw_line(self, x1: int, y1: int, x2: int, y2: int, pixel: Pixel):
    # 2차원 이미지 데이터에 특정 Pixel 데이터로 선을 그립니다.
    dx = abs(x2 - x1)
    dy = abs(y2 - y1)
    sx = 1 if x1 < x2 else -1
    sy = 1 if y1 < y2 else -1
    err = dx - dy
    while True:
        self[x1, y1] = pixel
        if x1 == x2 and y1 == y2:
            break
        e2 = err * 2
        if e2 > -dy:
            err -= dy
            x1 += sx
        if e2 < dx:
            err += dx
            y1 += sy

def __Mat_draw_circle(self, x: int, y: int, radius: int, pixel: Pixel):
    # 2차원 이미지 데이터에 특정 Pixel 데이터로 원을 그립니다.
    f = 1 - radius
    ddF_x = 1
    ddF_y = -2 * radius
    xx = 0
    yy = radius
    self[x, y + radius] = pixel
    self[x, y - radius] = pixel
    self[x + radius, y] = pixel
    self[x - radius, y] = pixel
    while xx < yy:
        if f >= 0:
            yy -= 1
            ddF_y += 2
            f += ddF_y
        xx += 1
        ddF_x += 2
        f += ddF_x
        self[x + xx, y + yy] = pixel
        self[x - xx, y + yy] = pixel
        self[x + xx, y - yy] = pixel
        self[x - xx, y - yy] = pixel
        self[x + yy, y + xx] = pixel
        self[x - yy, y + xx] = pixel
        self[x + yy, y - xx] = pixel
        self[x - yy, y - xx] = pixel

def __Mat_draw_text(self, x: int, y: int, text: str, pixel: Pixel = Pixels.BLACK_TEXT, double: bool = False):  # type: ignore
    # 2차원 이미지 데이터에 특정 Pixel 데이터로 텍스트를 그립니다.
    if double:
        for i in range(math.ceil(len(text) / 2)):
            self[x + i, y] = Pixel(pixel.fg, pixel.bg, Chars.char(text[i*2:i*2+2]))  # type: ignore
    else:
        for i, char in enumerate(text):
            self[x + i, y] = Pixel(pixel.fg, pixel.bg, Chars.char(char))  # type: ignore

def __Mat_draw_text_center(self, x: int, y: int, width: int, text: str, pixel: Pixel = Pixels.BLACK_TEXT, double: bool = False):  # type: ignore
    # 2차원 이미지 데이터에 특정 Pixel 데이터로 텍스트를 중앙 정렬하여 그립니다.
    if width < 0: width = self.width - x
    self.draw_text(x + (width - len(text)//(2 if double else 1))//2, y, text, pixel, double)

def __Mat_draw_text_center_vertical(self, x: int, y: int, height: int, text: str, pixel: Pixel = Pixels.BLACK_TEXT, double: bool = False):  # type: ignore
    # 2차원 이미지 데이터에 특정 Pixel 데이터로 텍스트를 수직 중앙 정렬하여 그립니다.
    if height < 0: height = self.height - y
    self.draw_text_center(x, y + ((height - len(text))//(2 if double else 1)) // 2, -1, text, pixel, double)

def __Mat_padding(self, left: int, top: int, right: int, bottom: int) -> tuple[int, int, int, int]:
    # 2차원 이미지 데이터의 패딩을 계산합니다.
    return left, top, self.width - left - right - 1, self.height - top - bottom - 1

def __Mat_padding_horizontal(self, left: int, right: int, height: int, top: int | None = None, bottom: int | None = None) -> tuple[int, int, int, int]:
    # 2차원 이미지 데이터의 수평 패딩을 계산합니다.
    if top is None and bottom is None: top = (self.my - height) // 2
    elif top is None and bottom is not None: top = self.my - height - bottom
    elif top is not None and bottom is None: top = top
    else: raise ValueError('top and bottom cannot be specified at the same time')
    return left, top, self.width - left - right - 1, height  # type: ignore

def __Mat_padding_vertical(self, top: int, bottom: int, width: int, left: int | None = None, right: int | None = None) -> tuple[int, int, int, int]:
    # 2차원 이미지 데이터의 수직 패딩을 계산합니다.
    if left is None and right is None: left = (self.mx - width) // 2
    elif left is None and right is not None: left = self.mx - width - right
    elif left is not None and right is None: left = left
    else: raise ValueError('left and right cannot be specified at the same time')
    return left, top, width, self.height - top - bottom - 1  # type: ignore

def __Mat_print(self):
    # 2차원 이미지 데이터를 출력합니다.
    if not ANSI_COLOR:
        sys.stdout.write(self.__str__())
    else:
        os.system('cls')

        for i in range(self.height):
            for j in range(self.width):
                pixel = self[j, i]
                set_console_color(*pixel.fg, *pixel.bg)  # type: ignore
                sys.stdout.write(pixel.char)
                sys.stdout.flush()

            sys.stdout.write('\n')
        
    sys.stdout.flush()    

def __Mat___str__(self):
    # 2차원 이미지 데이터를 문자열로 변환합니다.
    sb = StringIO()
    lfg = lbg = None
    
    if self.repaint:
        sb.write('\x1b[0m\x1b[2J\x1b[1;1H')

    for y in range(self.height):
        for x in range(self.width):
            p = self[x, y]
            sb.write(p.str(without_fg=lfg == p.fg, without_bg=lbg == p.bg))
            lfg = p.fg
            lbg = p.bg
    
        sb.write('\r\n')

    return sb.getvalue()

def __Mat___iadd__(self, other: Color):
    # 2차원 이미지 데이터에 특정 색상을 더합니다.
    for i in range(self.width * self.height):
        self.data[i].fg += other
        self.data[i].bg += other

    return self

Mat = type('Mat', (), {
    '__init__': __Mat___init__,
    '__getitem__': __Mat___getitem__,
    '__setitem__': __Mat___setitem__,
    'copy': __Mat_copy,
    'scale': __Mat_scale,
    'rotate': __Mat_rotate,
    'paste': __Mat_paste,  # type: ignore
    'paste_mask': __Mat_paste_mask,  # type: ignore
    'fill': __Mat_fill,
    'fill_rect': __Mat_fill_rect,
    'draw_rect': __Mat_draw_rect,
    'draw_line': __Mat_draw_line,
    'draw_circle': __Mat_draw_circle,
    'draw_text': __Mat_draw_text,
    'draw_text_center': __Mat_draw_text_center,
    'draw_text_center_vertical': __Mat_draw_text_center_vertical,
    'padding': __Mat_padding,
    'padding_horizontal': __Mat_padding_horizontal,
    'padding_vertical': __Mat_padding_vertical,
    'print': __Mat_print,
    '__str__': __Mat___str__,
    '__iadd__': __Mat___iadd__,
})

##############################
##          ENGINE          ##
##############################

def __Engine_collide(source: Mat, target: Mat, x: int, y: int) -> bool:
    # 소스 이미지가 타겟 이미지와 충돌하는지 확인합니다.

    if x < 0 or y < 0 or x + target.width > source.width or y + target.height > source.height:  # type: ignore
        return True

    for i in range(target.width):  # type: ignore
        for j in range(target.height):  # type: ignore
            if target[i, j] != Pixels.EMPTY and source[x + i, y + j] != Pixels.EMPTY:  # type: ignore
                return True

    return False

def __Engine_rander_number(mat: Mat, number: str, x: int, y: int):
    # 숫자 에셋으로 숫자를 렌더링합니다.
    for i in number:
        num = assets.dash if i == '-' else assets.numbers[int(i)]  # type: ignore
        mat.paste_mask(num, x, y, mask_char=Chars.EMPTY)  # type: ignore
        x += num.width + 1

Engine = type('Engine', (), {
    'collide': __Engine_collide,
    'rander_number': __Engine_rander_number,
})

##############################
##          ASSETS          ##
##############################

CODE_MAP: dict[str, Pixel] = {
    '0': Pixels.EMPTY,  # type: ignore
    '1': Pixel(Color(255, 112, 0), char=Chars.BLOCK),  # type: ignore
    '2': Pixel(Color(0, 87, 217), char=Chars.BLOCK),  # type: ignore
    '3': Pixel(Color(59, 164, 36), char=Chars.BLOCK),  # type: ignore
    '4': Pixel(Color(112, 12, 179), char=Chars.BLOCK),  # type: ignore
    '5': Pixel(Color(201, 51, 50), char=Chars.BLOCK),  # type: ignore
    '6': Pixel(Color(93, 70, 150), char=Chars.BLOCK),  # type: ignore
    '7': Pixel(Color(86, 133, 229), char=Chars.BLOCK),  # type: ignore
    '8': Pixel(Color(159, 17, 255), char=Chars.BLOCK),  # type: ignore
    'T': Pixel(Color(0, 85, 255), char=Chars.BLOCK),  # type: ignore
    'V': Pixel(Color(0, 114, 255), char=Chars.BLOCK),  # type: ignore
    'E': Pixel(Color(0, 150, 250), char=Chars.BLOCK),  # type: ignore
    'G': Pixel(Colors.gray(120), char=Chars.BLOCK),  # type: ignore
}

def build_asset(src: str) -> Mat:
    # 에셋의 데이터 코드를 2차원 이미지로 변환합니다.
    lines = [line.strip() for line in src.splitlines() if line.strip()]
    
    width = len(lines[0])
    height = len(lines)
    mat = Mat(width, height)  # type: ignore
    
    for y, line in enumerate(lines):
        for x, code in enumerate(line):
            mat[x, y] = CODE_MAP[code]  # type: ignore
        
    return mat  # type: ignore

BuildedAssets = type('BuildedAssets', (), {})

def __Assets_build() -> BuildedAssets:
    # 에셋을 빌드합니다.
    assets = BuildedAssets()

    for key, value in Assets.__dict__.items():
        if key.startswith('_'):
            continue

        if isinstance(value, list):
            assets.__dict__[key] = [build_asset(item) for item in value]  # type: ignore
        elif isinstance(value, str):
            assets.__dict__[key] = build_asset(value)  # type: ignore

    return assets

Assets = type('Assets', (), dict(
    pieces = [
        """
            10
            10
            11
        """,
        """
            03
            03
            33
        """,
        """
            05
            55
            50
        """,
        """
            60
            66
            06
        """,
        """
            070
            777
        """,
        """
            2
            2
            2
            2
        """,
        """
            44
            44
        """
    ],
    small_logo = """
        TTTTTTTTT
        TTTTTTTTT
        TTTTTVVVV
        000TTV000
        000TTV000
        000TTV000
        000TTVE00
        000TTVE00
    """,
    logo = """
        TTTTTTTTTTTTTTTTT
        TTTTTTTTTTTTTTTTT
        TTTTTTTTTTTTTTTTT
        TTTTTTTTTTTTTTTTT
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVV000000
        00000TTTTVVEEE000
        00000TTTTVVEEE000
        00000TTTTVVEEE000
    """,
    dash = """
        00
        00
        GG
        00
        00
    """,
    numbers = [
        """
            0GG0
            G00G
            G00G
            G00G
            0GG0
        """,
        """
            0G0
            GG0
            0G0
            0G0
            GGG
        """,
        """
            GGG
            00G
            GGG
            G00
            GGG
        """,
        """
            GGG
            00G
            GGG
            00G
            GGG
        """,
        """
            G0G
            G0G
            GGG
            00G
            00G
        """,
        """
            GGG
            G00
            GGG
            00G
            GGG
        """,
        """
            GGG
            G00
            GGG
            G0G
            GGG
        """,
        """
            GGG
            G0G
            00G
            00G
            00G
        """,
        """
            GGG
            G0G
            GGG
            G0G
            GGG
        """,
        """
            GGG
            G0G
            GGG
            00G
            GGG
        """,
    ],
    gameover = """
        111102222033333044440000555506060777708880
        100002002030303040000000500506060700008008
        101102222030303044440000500506060777708880
        100102002030303040000000500506060700008080
        111102002030303044440000555500600777708008
    """,
    build = __Assets_build
))

##############################
##          SOUND           ##
##############################

def play_sound(freq: int, duration: float) -> None:
    threading.Thread(target=winsound.Beep, args=(freq, int(duration * 1000))).start()

def play_sounds(*sounds: tuple[int, float]) -> None:
    def _play_sounds():
        for freq, duration in sounds:
            play_sound(freq, duration)
            time.sleep(duration)

    threading.Thread(target=_play_sounds).start()

def move_sound(moved: bool) -> None:
    if moved:
        play_sound(210, 0.1)

def rotate_sound(moved: bool) -> None:
    if moved:
        play_sound(230, 0.1)
    
def down_sound(reach: bool) -> None:
    if reach:
        play_sound(240, 0.1)
    else:
        play_sound(160, 0.1)

def drop_sound() -> None:
    play_sound(270, 0.1)

def hold_sound():
    play_sound(180, 0.1)

def line_clear_sound() -> None:
    play_sounds((280, 0.1),
                (300, 0.1),
                (320, 0.1),
                (340, 0.1),)

def game_over_sound() -> None:
    play_sounds((230, 0.1),
                (210, 0.1),
                (190, 0.1),
                (180, 0.1),)

##############################
##           GAME           ##
##############################


def __Analytics_add_score(self, score: int):
    self.score += score * max(1, self.combo)

Analytics = type('Analytics', (), {
    'lines': 0,
    'score': 0,
    'speed': 0,
    'combo': 0,
    'add_score': __Analytics_add_score,
})

def __Game___init__(self, screen: Mat, assets: BuildedAssets, scale: int = 1):
    self.screen = screen
    self.assets = assets
    self.mat = Mat(10, 20, pixel=Pixels.EMPTY)  # type: ignore
    self.hint = Mat(10, 20, pixel=Pixels.EMPTY)  # type: ignore
    self.scale = scale
    self._build_bg()
    self.random = Random()
    self.new_pieces()
    self.analytics = Analytics()
    threading.Thread(target=self._run).start()

def __Game_reset_hover(self):
    self.hover_locate = (self.mat.width // 2 - self.hover.width // 2, 0)

def __Game_build_hover_hint(self):
    mat = self.hover.copy()
    mat += Color(90, 90, 90)
    self.hover_hint = mat

def __Game_new_pieces(self):
    pieces = self.assets.pieces

    def random_piece():
        return pieces[self.random.randint(0, len(pieces) - 1)].copy()

    self.hover = self.next or random_piece()
    self.next = random_piece()
    self.reset_hover()
    self.build_hover_hint()

    if Engine.collide(self.mat, self.hover, *self.hover_locate):  # type: ignore
        self.game_over()

def __Game_holding(self):
    if self.holded:
        return
    
    self.holded = True

    if self.hold:
        self.hover, self.hold = self.hold, self.hover
        self.build_hover_hint()
    else:
        self.hold = self.hover
        self.new_pieces()

    self.reset_hover()
    hold_sound()

def __Game_run(self):
    self.input()

def __Game_input(self):
    while self.running:
        key = msvcrt.getch()

        if key == b'\xe0':
            # 화살표 키를 눌렀을 때
            key = msvcrt.getch()
            if key == b'H': key = b'w'
            elif key == b'P': key = b's'
            elif key == b'M': key = b'd'
            elif key == b'K': key = b'a'
        elif key == b'0': key = b'c'

        if key == b's':
            # 떨어지는 조각을 한 칸 아래로 이동합니다.
            self.move(0, 1)
            down_sound(False)
        elif key == b'a':
            # 떨어지는 조각을 한 칸 왼쪽으로 이동합니다.
            move_sound(self.move(-1, 0))
        elif key == b'd':
            # 떨어지는 조각을 한 칸 오른쪽으로 이동합니다.
            move_sound(self.move(1, 0))
        elif key == b'w':
            # 떨어지는 조각을 회전합니다.
            rotate_sound(self.rotate(True))
        elif key == b'e':
            # 떨어지는 조각을 반시계 방향으로 회전합니다.
            rotate_sound(self.rotate(False))
        elif key == b'c':
            # 떨어지는 조각을 홀드합니다.
            self.holding()
        elif key == b' ':
            # 떨어지는 조각을 한 번에 아래로 이동합니다.
            while self.move(0, 1):
                pass
            drop_sound()
        elif key == b'p':
            # 게임을 종료합니다.
            self.exit()
        elif key == b'\t':
            # 게임을 초기화합니다.
            self.req_reset = True
            self.exit()
        else: continue

        def update(mat: Mat):  # type: ignore
            if key == b' ':
                self.commit(mat)

        self.draw(update)

def __Game__run(self):
    def update(mat: Mat):  # type: ignore
        if not self.move(0, 1):
            # 떨어지는 조각을 한 칸 아래로 이동하고 조각이 땅에 닿았다면
            self.commit(mat)
            down_sound(True)

    while self.running:
        self.draw(update)
        self.delay = max(.08, .8 - self.analytics.score // 100 * .05)
        time.sleep(self.delay)

def __Game_draw_hud(self, left_hud: tuple[int, int, int, int], right_hud: tuple[int, int, int, int]):
    screen = self.screen
    lx, ly, lw, lh = left_hud
    rx, ry, rw, rh = right_hud
    
    # 왼쪽 HUD

    # 스코어
    Engine.rander_number(screen, f'{self.analytics.score:05}', lx + 1, ly + 1)  # type: ignore
    screen.draw_line(lx, 2+5, lx + lw - 1, 2+5, Pixels.BR)  # type: ignore

    # 오른쪽 HUD

    # 게임 로고
    sml = self.assets.small_logo
    smlp = rx + rw - sml.width - 1
    screen.paste_mask(sml, smlp, rh-sml.height-1, mask_char=Chars.EMPTY)  # type: ignore

    # 다음 조각 그리기
    nxc_w, nxc_h = 9, 11
    screen.draw_rect(rx - 1, ry, nxc_w+1, nxc_h+1, Pixels.BR)  # type: ignore
    screen.draw_text_center(rx - 1, ry, nxc_w+1, 'Next', Pixels.BR)  # type: ignore
    nx = self.next.scale(self.scale)
    
    # 다음 조각 그리기
    nxp_x = rx + nxc_w // 2 - nx.width // 2
    nxp_y = ry + nxc_h // 2 - nx.height // 2 + 1
    screen.paste_mask(nx, nxp_x, nxp_y, mask_char=Chars.EMPTY)  # type: ignore

    # 홀드 조각 그리드
    hpc_w, hpc_h = 9, 11
    screen.draw_rect(rx - 1, ry + nxc_h, hpc_w+1, hpc_h+1, Pixels.BR)  # type: ignore
    screen.draw_text_center(rx - 1, ry + nxc_h, hpc_w+1, 'Hold', Pixels.BR)  # type: ignore

    if self.hold:
        # 홀드한 조각이 있다면 그리기
        hp = self.hold.scale(self.scale)
        hpp_x = rx + hpc_w // 2 - hp.width // 2
        hpp_y = ry + nxc_h + hpc_h // 2 - hp.height // 2 + 1
        screen.paste_mask(hp, hpp_x, hpp_y, mask_char=Chars.EMPTY)  # type: ignore

    # 게임 통계
    an_w, an_h = 9, 11
    anx = rx
    analy = self.analytics
    screen.draw_rect(rx - 1, ry + nxc_h + hpc_h, an_w+1, an_h+1, Pixels.BR)  # type: ignore
    screen.draw_text_center(rx - 1, ry + nxc_h + hpc_h, an_w+1, 'Analys', Pixels.BR)  # type: ignore
    hpc_h += 1
    screen.draw_text(anx, ry + nxc_h + hpc_h + 1, '[Lines]')
    screen.draw_text(anx, ry + nxc_h + hpc_h + 2, f'{analy.lines:7d}')
    screen.draw_text(anx, ry + nxc_h + hpc_h + 4, f'[Speed]')
    screen.draw_text(anx, ry + nxc_h + hpc_h + 5, f' {(1 - self.delay + .08)*100:.2f}%')
    screen.draw_text(anx, ry + nxc_h + hpc_h + 7, f'[Combo]')
    screen.draw_text(anx, ry + nxc_h + hpc_h + 8, f'{analy.combo:7d}')

def __Game_draw_hint(self):
    self.hint.fill(Pixels.EMPTY)  # type: ignore
    x, y = self.hover_locate

    # 조각이 떨어지는 위치를 찾습니다.
    while not Engine.collide(self.mat, self.hover, x, y + 1):  # type: ignore
        y += 1

    self.hint.paste_mask(self.hover_hint, x, y, mask_char=Chars.EMPTY)  # type: ignore

def __Game_draw(self, proc: Callable[[Mat], Any] | None = None):
    mat = self.mat.copy()
    mat.paste_mask(self.hover, *self.hover_locate, mask_char=Chars.EMPTY)  # type: ignore

    self.draw_hint()

    if proc: proc(mat)
    
    self.update(mat)

def __Game_commit(self, mat: Mat):
    self.holded = False
    self.mat = mat
    self.analytics.add_score(5)
    # 점수를 추가합니다.
    self.new_pieces()
    # 새로운 조각을 생성합니다.
    self.remove_lines(mat, self.find_complete_lines(mat))
    # 완성된 줄을 제거합니다.

def __Game_move(self, mx: int, my: int):
    # 조각을 이동합니다.
    x, y = self.hover_locate
    np = (x + mx, y + my)

    if Engine.collide(self.mat, self.hover, *np):  # type: ignore
        return False
    else:
        self.hover_locate = np
        return True

def __Game_rotate(self, clockwise: bool):
    # 조각을 회전합니다.
    angle = 270 if clockwise else 90
    mat = self.hover.rotate(angle)
    # 회전한 조각을 생성합니다.

    if self.hover_locate[0] + mat.width > self.mat.width:
        # 조각이 화면 밖으로 나가면 이동합니다.
        self.move(self.mat.width - mat.width - self.hover_locate[0], 0)
        
    if Engine.collide(self.mat, mat, *self.hover_locate):  # type: ignore
        # 충돌이 발생하면 정반대 방향으로 회전합니다.
        mat = self.hover.rotate(-angle)
    
    if Engine.collide(self.mat, mat, *self.hover_locate):  # type: ignore
        return False

    self.hover = mat
    self.build_hover_hint()
    return True

def __Game_find_complete_lines(self, mat: Mat) -> list[int]:
    # 완성된 줄을 찾습니다.
    lines = []
    for i in range(mat.height):  # type: ignore
        b = True

        for j in range(mat.width):  # type: ignore
            if mat[j, i].char == Chars.EMPTY:  # type: ignore
                b = False
                break
        
        if b: lines.append(i)

    return lines

def __Game_remove_lines(self, mat: Mat, lines: list[int]):
    # 완성된 줄을 제거합니다.
    ln = len(lines)
    analy = self.analytics
    analy.add_score(ln * 10 + ln * 2)
    # 점수를 추가합니다.
    analy.lines += ln

    if ln <= 0: analy.combo = 0
    else: analy.combo += ln
    # 콤보를 추가합니다.

    for i in lines:
        for j in range(mat.width):  # type: ignore
            mat[j, i] = Pixels.EMPTY  # type: ignore

    for i in lines:
        for j in range(i, 0, -1):
            for k in range(mat.width):  # type: ignore
                mat[k, j] = mat[k, j-1]  # type: ignore

    if ln > 0:
        line_clear_sound()

def __Game_game_over(self):
    self.running = False
    screen = self.screen
    
    # 게임 오버 화면을 그립니다.
    dialog = Mat(screen.width, 9, pixel=Pixels.WHITE)  # type: ignore
    game = self.assets.gameover
    dialog.paste_mask(game, dialog.width // 2 - game.width // 2, 1, mask_char=Chars.EMPTY)  # type: ignore
    dy = game.height + 2
    dialog.draw_text_center(0, dy, dialog.width, '[ Press any key to continue ]', double=True)  # type: ignore

    screen.paste(dialog, screen.width // 2 - dialog.width // 2, screen.height // 2 - dialog.height // 2)  # type: ignore
    self.refresh()
    game_over_sound()
    # 게임 오버 소리를 재생합니다.
    time.sleep(1)
    msvcrt.getch()
    # 아무 키나 누르면 게임을 종료합니다.
    self.exit = True

def __Game_exit(self):
    self.running = False
    game_over_sound()
    self.exit = True

def __Game_update(self, mat: Mat):
    if not self.running: return

    width = mat.width * self.scale  # type: ignore
    height = mat.height * self.scale  # type: ignore
    screen = self.screen
    x = self.screen.mx // 2 - width // 2 + 2

    # 화면을 지웁니다.
    screen.fill(Pixels.WHITE)  # type: ignore

    # 인게임 화면의 외각선을 그립니다.
    screen.draw_line(x-1, 0, x-1, height-1, Pixels.BR)  # type: ignore
    screen.draw_line(x+width, 0, x+width, height-1, Pixels.BR)  # type: ignore
    # 인게임 화면의 배경을 그립니다.
    screen.paste(self.bg, x, 0)
    # 인게임 화면의 힌트를 그립니다.
    screen.paste_mask(self.hint.scale(self.scale), x, 0, mask_char=Chars.EMPTY)  # type: ignore
    # 인게임 화면을 그립니다.
    screen.paste_mask(mat.scale(self.scale), x, 0, mask_char=Chars.EMPTY)  # type: ignore

    ep = x+width+1
    self.draw_hud((0, 0, x-1, height), (ep, 0, screen.width - ep, height))
    # HUD를 그립니다.

    self.refresh()
    # 화면을 갱신합니다.

def __Game_refresh(self):
    # 화면을 갱신합니다.
    self.screen.print()

def __Game__build_bg(self):
    scale = self.scale
    mat = self.mat
    width = mat.width * self.scale
    height = mat.height * self.scale
    r, g, b = 255, 255, 255
    bg = Mat(width, height, pixel=Pixel(bg=Color(r, g, b)))  # type: ignore

    # 배경을 그립니다.
    for y in range(height):
        for x in range(width):
            c = (x // scale % 2 == 0 and y // scale % 2 == 0) or (x // scale % 2 == 1 and y // scale % 2 == 1)
            # 격자를 그립니다.
            bg[x, y] = Pixel(bg=Color(r, g, b), char=Chars.BLOCK if c else Chars.EMPTY)  # type: ignore
    
        if y % 3 == 0:
            # 그라데이션을 그립니다.
            r -= 1
            g -= 1
    
    bg.fill_rect(0, 0, width, 6, Pixel(bg=Color(255, 240, 240)))  # type: ignore

    self.bg = bg
        
Game = type('Game', (), {
    'hover': None,
    'hover_hint': None,
    'hold': None,
    'holded': False,
    'next': None,
    'running': True,
    'delay': .8,
    'exit': False,
    'req_reset': False,
    '__init__': __Game___init__,
    'reset_hover': __Game_reset_hover,
    'build_hover_hint': __Game_build_hover_hint,
    'new_pieces': __Game_new_pieces,
    'holding': __Game_holding,
    'run': __Game_run,
    'input': __Game_input,
    '_run': __Game__run,
    'draw_hud': __Game_draw_hud,
    'draw_hint': __Game_draw_hint,
    'draw': __Game_draw,
    'commit': __Game_commit,
    'move': __Game_move,
    'rotate': __Game_rotate,
    'find_complete_lines': __Game_find_complete_lines,
    'remove_lines': __Game_remove_lines,
    'game_over': __Game_game_over,
    'exit': __Game_exit,
    'update': __Game_update,
    'refresh': __Game_refresh,
    '_build_bg': __Game__build_bg
})

##############################
##         SCREENS          ##
##############################

def draw_logo(screen: Mat):
    logo = assets.logo  # type: ignore
    screen.fill(Pixels.WHITE)  # type: ignore
    screen.paste_mask(logo, screen.mx // 2 - logo.width // 2, screen.my // 2 - logo.height // 2, mask_char=Chars.EMPTY)  # type: ignore

def draw_loading(screen: Mat, message: str):
    draw_logo(screen)
    screen.draw_text_center(0, screen.my - 2, screen.mx, message, Pixel(fg=Colors.BLACK, bg=Colors.WHITE), double=True)  # type: ignore

def mainmenu_choice(screen: Mat, choice: int, e: bool, ms: int):
    tp = screen.my - 6 - 1  # type: ignore
    draw_logo(screen)
    np = Pixel(fg=Colors.WHITE, bg=Colors.BLACK)  # type: ignore
    cp = Pixel(fg=Colors.BLACK, bg=Colors.gray(230))  # type: ignore

    screen.draw_text_center(0, tp, screen.mx, f'Max Score: {ms}', double=True)  # type: ignore
    screen.draw_text_center(0, tp+2, screen.mx, '[ Play ]', cp if choice == 0 else np)  # type: ignore
    screen.draw_text_center(0, tp+3, screen.mx, f'[ {"En" if e else "Dis"}able UNIX Color ]', cp if choice == 1 else np)  # type: ignore
    screen.draw_text_center(0, tp+4, screen.mx, '[ Quit ]', cp if choice == 2 else np)  # type: ignore

    screen.draw_text_center(0, screen.my - 1, screen.mx, 'Use arrow keys to navigate and enter to select', double=True)  # type: ignore

    # 조작 방법을 그립니다.
    board_w, board_h = 17, 13
    bx, by = screen.mx - board_w - 6, screen.height // 2 - board_h // 2  # type: ignore
    bpx = Pixel(Colors.BLACK, Colors.gray(240))  # type: ignore
    screen.fill_rect(bx, by, board_w, board_h, bpx)  # type: ignore

    screen.draw_text(bx + 1, by + 1, 'Controls', bpx)  # type: ignore
    screen.draw_text(bx + 1, by + 3, 'Move      -  L R Arrow or A D', bpx, double=True)  # type: ignore
    screen.draw_text(bx + 1, by + 5, 'Rotate    -  Up Arrow or W', bpx, double=True)  # type: ignore
    screen.draw_text(bx + 1, by + 4, 'Hard Drop -  Space', bpx, double=True)  # type: ignore
    screen.draw_text(bx + 1, by + 6, 'Soft Drop -  Down Arrow or S', bpx, double=True)  # type: ignore
    screen.draw_text(bx + 1, by + 8, 'Game', bpx)  # type: ignore
    screen.draw_text(bx + 1, by + 10,'Quit Game -  P', bpx, double=True)  # type: ignore
    screen.draw_text(bx + 1, by + 11, 'Reset     -  Tab', bpx, double=True)  # type: ignore

    if ANSI_COLOR:
        screen.fill_rect(0, 3, screen.mx, 3, Pixel(bg=Colors.RED))  # type: ignore
        screen.draw_text_center(0, 4, screen.width, 'WARNING! ANSI Color is enabled. This may cause some issues. ', Pixel(fg=Colors.WHITE, bg=Colors.RED), double=True)  # type: ignore

def _game_loading(screen: Mat, progress: float):
    screen.fill(Pixels.WHITE)  # type: ignore

    logo = assets.small_logo  # type: ignore
    w, h = sum(p.width + 2 for p in assets.pieces), max(p.height for p in assets.pieces)   # type: ignore

    xp = screen.mx // 2 - w // 2  # type: ignore
    yp = screen.my // 2 - h // 2 + 4  # type: ignore
    pc = len(assets.pieces) * progress  # type: ignore

    screen.paste_mask(logo, screen.mx // 2 - logo.width // 2, 6, mask_char=Chars.EMPTY)  # type: ignore
    
    for i, p in enumerate(assets.pieces):  # type: ignore
        if i > pc: break
        screen.paste_mask(p, xp, yp, mask_char=Chars.EMPTY)  # type: ignore

        xp += p.width + 2

DEBUG = False
INGAME_DEBUG = False

assets: BuildedAssets

if DEBUG:
    ANSI_COLOR = False

def update():
    screen.print()  # type: ignore

def clear():
    screen.fill(Pixels.WHITE)  # type: ignore
    update()

def game_loading():
    if INGAME_DEBUG: return
    for i in range(10):
        _game_loading(screen, i / 10)  # type: ignore
        update()
        time.sleep(.08)

def run_game():
    game = Game(screen, assets, scale=2)  # type: ignore
    game.run()  # type: ignore
    return game

SCREEN_WIDTH, SCREEN_HEIGHT = (72, 40)

print('screen assign...')
screen = Mat(SCREEN_WIDTH, SCREEN_HEIGHT, repaint=False)  # type: ignore
print('building assets...')
assets = Assets.build()  # type: ignore

os.system(f'mode con: cols={SCREEN_WIDTH*2} lines={SCREEN_HEIGHT+1}')
os.system('cls')
os.system('color 0f')

if not DEBUG:
    game_loading()
    draw_loading(screen, 'ⓒ 2022 Soju06. All Rights Reserved.')  # type: ignore
    update()

    if not INGAME_DEBUG:
        time.sleep(1.5)

while True:
    choice = 0

    while not INGAME_DEBUG:
        mainmenu_choice(screen, choice, ANSI_COLOR, get_max_score())  # type: ignore
        update()
        key = msvcrt.getch()

        if key == b'\xe0':
            # 화살표 키가 입력됬다면
            key = msvcrt.getch()
            if key == b'H': key = b'w'
            elif key == b'P': key = b's'
            elif key == b'M': key = b'd'
            elif key == b'K': key = b'a'
        elif key == b'0': key = b'\r'

        if key == b'w':
            choice = max(choice - 1, 0)
            play_sound(260, .1)
        elif key == b's':
            choice = min(choice + 1, 2)
            play_sound(260, .1)
        elif key == b'\r':
            play_sounds((240, .1),
                        (260, .1),
                        (280, .1))
            break

    if choice == 2:
        # 종료
        print(RESET)
        sys.exit()
    elif choice == 1:
        # ANSI 색상을 토글합니다.
        ANSI_COLOR = not ANSI_COLOR
        continue

    time.sleep(.2)
    clear()
    time.sleep(.2)
    game_loading()
    game = run_game()
    while game.req_reset:  # type: ignore
        # 게임이 리셋이 요청되었다면
        game = run_game()

    set_max_score(max(get_max_score(), game.analytics.score))  # type: ignore
    # 최고 점수를 갱신합니다.
    game_loading()
