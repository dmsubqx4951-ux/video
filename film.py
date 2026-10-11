"""A 36-second, code-drawn cartoon: Zhuge Liang meets Shanghai in 2026.

All scenery, characters, props and motion are procedural vector/raster art.
No stock imagery, image generator, browser recording or video generation API.
"""
from pathlib import Path
import argparse
import math
import re
import subprocess
import json

import aggdraw
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

from audio import make_audio, wav_read, ROOT, SR

W, H = 1280, 720
R = 1.5
INK = '#18313a'
FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
SERIF = '/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc'
FONT_CACHE = {}


def font(size, serif=False):
    key = (size, serif)
    if key not in FONT_CACHE:
        FONT_CACHE[key] = ImageFont.truetype(SERIF if serif else FONT, round(size * R), index=2)
    return FONT_CACHE[key]


def ease(x):
    x = np.clip(x, 0, 1)
    return float(x * x * (3 - 2 * x))


def lerp(a, b, t):
    return a + (b - a) * t


def beat(t, start, peak, end):
    """A deliberate gesture with anticipation and a slower settling motion."""
    return ease((t-start)/(peak-start)) * (1-ease((t-peak)/(end-peak)))


class Pen:
    def __init__(self, image):
        self.im = image
        self.d = ImageDraw.Draw(image)

    def path(self, description, fill=None, stroke=INK, width=2):
        tokens = re.findall(r'[MLCQZmlcqz]|[-+]?(?:\d*\.\d+|\d+)', description)
        p = aggdraw.Path()
        i, current = 0, (0, 0)
        while i < len(tokens):
            command = tokens[i].upper()
            i += 1
            count = {'M': 2, 'L': 2, 'C': 6, 'Q': 4, 'Z': 0}[command]
            values = [float(v) * R for v in tokens[i:i + count]]
            i += count
            if command == 'M':
                p.moveto(*values)
                current = tuple(values)
            elif command == 'L':
                p.lineto(*values)
                current = tuple(values)
            elif command == 'C':
                p.curveto(*values)
                current = tuple(values[-2:])
            elif command == 'Q':
                x0, y0 = current
                x1, y1, x2, y2 = values
                p.curveto(x0 + 2 / 3 * (x1 - x0), y0 + 2 / 3 * (y1 - y0),
                          x2 + 2 / 3 * (x1 - x2), y2 + 2 / 3 * (y1 - y2), x2, y2)
                current = (x2, y2)
            else:
                p.close()
        context = aggdraw.Draw(self.im)
        context.path(p, aggdraw.Brush(fill) if fill else None, aggdraw.Pen(stroke, width * R) if stroke else None)
        context.flush()

    def line(self, points, color, width=1):
        self.d.line([(round(x * R), round(y * R)) for x, y in points], fill=color, width=max(1, round(width * R)))

    def ellipse(self, box, color, outline=None, width=1):
        self.d.ellipse(tuple(round(a * R) for a in box), fill=color, outline=outline, width=max(1, round(width * R)))

    def rect(self, box, color, radius=0, outline=None, width=1):
        box = tuple(round(a * R) for a in box)
        if radius:
            self.d.rounded_rectangle(box, radius=radius * R, fill=color, outline=outline, width=round(width * R))
        else:
            self.d.rectangle(box, fill=color, outline=outline, width=round(width * R))

    def text(self, xy, text, size, color, anchor='la', serif=False, stroke=0):
        self.d.text(tuple(a * R for a in xy), text, font=font(size, serif), fill=color,
                    anchor=anchor, stroke_width=round(stroke * R), stroke_fill='#091420')


def canvas(size=(W, H), color=(0, 0, 0, 0)):
    return Image.new('RGBA', (round(size[0] * R), round(size[1] * R)), color)


def gradient(size, top, bottom):
    width, height = round(size[0] * R), round(size[1] * R)
    ys = np.linspace(0, 1, height)[:, None, None]
    a, b = np.array(top)[None, None, :], np.array(bottom)[None, None, :]
    pixels = np.repeat((a * (1 - ys) + b * ys).astype(np.uint8), width, axis=1)
    return Image.fromarray(pixels).convert('RGBA')


def paste(frame, layer, x, y, scale=1., angle=0.):
    if scale != 1:
        layer = layer.resize((max(1, round(layer.width * scale)), max(1, round(layer.height * scale))), Image.Resampling.BICUBIC)
    if angle:
        layer = layer.rotate(angle, Image.Resampling.BICUBIC, expand=False)
    frame.alpha_composite(layer, (round(x * R), round(y * R)))


def city_background():
    image = gradient((W, H), (10, 22, 43), (42, 66, 82))
    p = Pen(image)
    rng = np.random.default_rng(4951)
    # A restrained amber/cyan haze rather than flat black behind the skyline.
    glow = canvas()
    gp = Pen(glow)
    gp.ellipse((130, 150, 800, 690), (211, 113, 81, 25))
    gp.ellipse((550, 10, 1360, 590), (37, 147, 187, 35))
    image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90 * R)))
    p = Pen(image)
    for x, y, size in zip(rng.uniform(0, W, 50), rng.uniform(65, 275, 50), rng.uniform(.35, 1.2, 50)):
        p.ellipse((x, y, x + size, y + size), '#678495')
    # Distant riverfront blocks with individual windows.
    for x in range(-15, 1300, 44):
        top = int(rng.uniform(270, 415))
        width = int(rng.uniform(30, 51))
        p.rect((x, top, x + width, 505), '#203648')
        for wx in range(x + 6, x + width - 3, 8):
            for wy in range(top + 9, 475, 14):
                if rng.random() > .34:
                    p.rect((wx, wy, wx + 2, wy + 5), '#728783' if rng.random() > .35 else '#b9a37e')
    # Shanghai Tower: tapered, twisting glass outline.
    p.path('M 990 477 L 1002 236 C 1003 181 1021 117 1048 76 C 1073 139 1091 207 1093 257 L 1106 477 Z', '#264653', '#77b4ba', 1.3)
    p.path('M 1048 77 C 1055 202 1024 329 1032 477', None, '#789fa1', 1.5)
    p.path('M 1050 78 C 1095 184 1057 333 1078 477', None, '#53a6b5', 1)
    for y in range(160, 474, 10):
        left = 1000 + max(0, 235 - y) * .18
        right = 1098 - max(0, 240 - y) * .2
        p.line([(left, y), (right, y - 10)], '#42687a', .7)
    p.line([(1048, 63), (1048, 79)], '#b7d4d4', 1)
    # Shanghai World Financial Center, including the bottle-opener aperture.
    p.path('M 820 474 L 832 185 L 893 155 L 918 474 Z', '#243f50', '#86a8af', 1.5)
    p.path('M 843 182 L 885 164 L 889 207 L 843 218 Z', '#13293f', '#85a0b0', 2)
    p.path('M 861 224 L 858 474', None, '#5d7f88', 2)
    for y in range(238, 471, 9):
        p.line([(834, y), (904, y - 4)], '#446775', .65)
    # Jin Mao Tower, its stepped Art Deco crown.
    p.path('M 932 481 L 932 267 L 945 267 L 945 235 L 954 235 L 954 216 L 966 216 L 972 178 L 977 216 L 989 216 L 989 240 L 998 240 L 998 479 Z', '#344d5a', '#9eaaa2', 1.2)
    for y in range(278, 477, 10):
        p.line([(935, y), (995, y)], '#91a099', 1)
    p.line([(972, 160), (972, 192)], '#a2b6ad', 1)
    # Oriental Pearl: a recognizable three-legged tower with pink spheres.
    p.path('M 237 496 L 272 348 L 306 496 Z', '#324859', '#7d99a4', 1.5)
    p.path('M 260 496 L 276 306 L 286 306 L 297 496', '#677782', '#7a8d96', 1)
    p.rect((275, 139, 287, 381), '#768c97')
    p.line([(281, 67), (281, 163)], '#9ebbc3', 2)
    p.ellipse((271, 116, 290, 145), '#75b0be', '#9fc8c9', 1)
    p.ellipse((252, 164, 309, 217), '#b0769d', '#f2a9c2', 2)
    p.ellipse((232, 289, 330, 376), '#975f88', '#ed9bad', 2)
    p.path('M 240 323 C 261 292 311 294 323 319', None, '#ffb9bd', 2)
    p.path('M 241 344 C 269 366 305 367 323 343', None, '#f1a3bd', 2)
    p.path('M 258 186 C 273 170 295 171 304 186', None, '#ffd0cf', 1)
    for yy in (317, 332, 348):
        p.line([(240, yy), (322, yy)], '#713d66', 1)
    p.ellipse((265, 413, 298, 441), '#6e638b', '#bbb4ca', 1)
    # Foreground towers, offices and neon billboards.
    for x, y, width, color in [(70, 266, 98, '#243d4e'), (355, 224, 87, '#23475a'), (471, 296, 118, '#294457'), (1132, 221, 110, '#263d4b')]:
        p.rect((x, y, x + width, 507), color)
        p.path(f'M {x} {y} L {x+12} {y-13} L {x+width+10} {y-13} L {x+width} {y}', '#395263', '#4b6c76', 1)
        for wx in range(x + 8, x + width - 5, 12):
            for wy in range(y + 15, 481, 15):
                if rng.random() > .22:
                    p.rect((wx, wy, wx + 4, wy + 6), '#8eaaa7' if rng.random() > .5 else '#b7a281')
    p.rect((375, 278, 423, 368), '#203b54', 4, '#5fbec8', 1)
    p.text((399, 291), '上', 23, '#b4e5e9', 'ma')
    p.text((399, 322), '海', 23, '#b4e5e9', 'ma')
    p.rect((1165, 343, 1227, 427), '#603d48', 3, '#e79983', 1)
    p.text((1196, 355), '夜', 24, '#ffe2bd', 'ma')
    p.text((1196, 387), '色', 24, '#ffe2bd', 'ma')
    # Traffic lanes beneath the pedestrian overpass.
    p.path('M -20 578 C 250 471 710 468 1290 470 L 1290 585 C 740 490 382 560 100 719 L -20 719 Z', '#172a38', None)
    for offset in (0, 20, 38):
        p.path(f'M -10 {616+offset} C 320 {496+offset*.25} 745 {494+offset*.3} 1280 {503+offset}', None, '#687168', 1)
    # Low parapet and a broad tiled pedestrian deck.
    p.path('M 0 563 L 1280 537 L 1280 720 L 0 720 Z', '#2d424c', None)
    p.path('M 0 595 L 1280 562 L 1280 720 L 0 720 Z', '#3a4e55', None)
    for y in (605, 631, 676):
        p.line([(0, y + 24), (1280, y - 10)], '#5b6869', 1)
    for x in range(-400, 1800, 170):
        p.line([(650 + (x - 650) * .48, 568), (x, 720)], '#526166', 1)
    p.path('M 0 563 L 1280 537', None, '#a6a9a1', 2)
    return image


def railing(image):
    p = Pen(image)
    for x in range(-25, 1320, 90):
        y = 459 - x * .018
        p.line([(x, y), (x + 8, 572 - x * .02)], '#142b34', 7)
        p.line([(x + 2, y), (x + 10, 572 - x * .02)], '#72949a', 1.2)
    p.path('M -20 466 L 1300 442', None, '#142c37', 10)
    p.path('M -20 464 L 1300 440', None, '#87a5aa', 2.4)
    p.path('M -20 494 L 1300 470', None, '#345364', 3)
    p.path('M -20 535 L 1300 510', None, '#46606b', 2)


def hero_base(back=False, part='all'):
    im = canvas((440, 800))
    p = Pen(im)
    # Cloth tassels behind the shoulder.
    p.path('M 173 100 C 141 165 146 240 120 298 L 152 293 C 165 226 188 185 190 108 Z', '#7a9293', INK, 2)
    p.path('M 186 101 C 164 187 178 260 155 337 L 181 315 C 201 254 203 178 202 110 Z', '#afc0b8', INK, 2)
    # Layered robe silhouette, generous sleeves and flowing hem.
    p.path('M 185 275 C 148 279 132 301 117 338 L 78 476 C 111 514 122 526 159 523 L 138 710 C 196 745 302 745 348 710 L 326 523 C 368 521 403 506 413 480 L 367 331 C 358 302 328 277 277 272 Z', '#c5c8b2', INK, 3)
    p.path('M 186 283 C 169 318 169 394 164 479 L 145 708 C 169 718 190 723 203 722 L 222 399 Z', '#9aafaa', None)
    p.path('M 281 280 L 260 402 L 287 725 C 312 723 331 717 345 708 L 322 527 L 330 323 Z', '#829d9c', None)
    p.path('M 124 338 C 132 363 143 415 149 466 L 132 496 C 123 505 105 493 86 479', '#aabbb2', '#657f80', 2)
    p.path('M 337 333 C 354 367 355 418 376 450 L 391 484 C 375 491 362 496 343 497', '#b7c4b4', '#607d7e', 2)
    p.path('M 170 445 C 194 466 277 471 321 447 L 325 468 C 276 495 200 488 166 468 Z', '#546d70', INK, 1.5)
    p.path('M 209 475 L 208 583 L 226 564 L 239 585 L 240 478', '#446369', INK, 1.5)
    p.path('M 254 477 L 259 554 L 278 571 L 277 482', '#799390', INK, 1.2)
    for description in [
        'M 180 510 C 173 590 177 646 161 697',
        'M 215 590 C 204 643 206 684 199 717',
        'M 246 559 C 244 635 253 692 255 724',
        'M 294 510 C 307 587 309 647 327 700',
        'M 118 388 C 113 424 104 455 100 465',
        'M 342 374 C 352 420 358 445 363 460',
    ]:
        p.path(description, None, '#6f8988', 1.5)
    p.path('M 147 710 C 198 733 299 739 344 712', None, '#e8dfc1', 4)
    p.path('M 155 724 C 170 735 197 739 204 738 L 205 750 L 154 750 Z', '#263b42', INK, 2)
    p.path('M 285 735 C 309 735 331 728 341 725 L 348 746 L 288 748 Z', '#263b42', INK, 2)
    # Neck and the crossed Han collar.
    p.path('M 196 239 L 191 283 L 228 312 L 274 278 L 270 230 Z', '#c8a889', INK, 2)
    p.path('M 190 271 L 226 307 L 274 270 L 294 287 L 232 384 L 174 290 Z', '#e9e2c8', INK, 2)
    p.path('M 174 290 L 232 384 L 246 363 L 189 277 Z', '#647f81', INK, 1)
    p.path('M 282 272 L 231 345 L 240 365 L 301 288 Z', '#77928f', INK, 1)
    if back:
        p.path('M 180 278 C 195 269 265 269 291 279 L 326 443 C 279 466 205 465 171 443 Z', '#b4c3b4', INK, 1.5)
        p.path('M 226 294 C 217 336 230 393 225 446 M 280 300 C 285 342 296 388 299 445', None, '#8aa29c', 1.5)
    # A hand held loosely at the waist.
    p.path('M 136 474 C 145 461 153 455 162 455 L 184 459 C 194 464 195 474 187 480 L 168 481 L 149 490 Z', '#dbb497', INK, 2)
    p.path('M 148 477 L 176 469 M 154 482 L 179 475', None, '#a77d64', 1)
    if part == 'body':
        return im
    if part == 'head':
        im = canvas((440, 800))
        p = Pen(im)
    # Face, ear, temple hair and gentle rim lights.
    if back:
        p.path('M 169 104 C 158 161 161 219 191 250 C 213 266 250 266 274 246 C 304 213 303 152 282 111 Z', '#596d69', INK, 2.1)
        p.path('M 180 140 C 175 200 194 238 227 254 C 252 240 280 185 280 138', '#3f5551', None)
    else:
        # Fuller cheeks, a small rounded nose and warm skin soften his silhouette.
        p.ellipse((158, 162, 186, 204), '#e4b698', INK, 1.7)
        p.ellipse((284, 161, 306, 203), '#e4b698', INK, 1.7)
        p.path('M 176 119 C 164 142 164 182 174 208 C 182 237 205 258 233 260 C 259 259 283 239 293 212 C 304 184 298 142 282 123 Z', '#ecc4a3', INK, 2.2)
        p.path('M 193 126 C 186 157 185 186 199 211 C 212 238 242 249 265 234 C 282 212 285 176 279 135 Z', '#f5d4b2', None)
        p.path('M 175 151 C 168 175 171 205 181 218 L 188 205 L 184 140 Z', '#4e625a', INK, .9)
        p.path('M 282 139 C 294 161 299 185 290 211 L 280 200 L 278 151 Z', '#4e625a', INK, .9)
        p.path('M 234 190 Q 231 204 232 210 Q 241 216 249 208', None, '#b78a70', 1.2)
        p.path('M 238 202 Q 242 197 245 201', None, '#ffe6c7', 1.5)
        blush = canvas((440, 800))
        cheeks = Pen(blush)
        cheeks.ellipse((181, 199, 213, 218), (226, 140, 128, 92))
        cheeks.ellipse((259, 198, 291, 216), (226, 140, 128, 82))
        im.alpha_composite(blush.filter(ImageFilter.GaussianBlur(3.3 * R)))
        p = Pen(im)
        # Beard and moustache are part of the same face across every shot.
        p.path('M 185 216 C 194 234 208 242 230 242 C 253 243 274 232 286 214 C 286 245 276 276 262 294 C 250 307 237 315 230 319 C 214 312 202 296 195 278 C 186 254 181 234 185 216 Z', '#465c54', INK, 1.8)
        p.path('M 200 228 C 210 240 218 244 231 243 C 243 245 255 240 269 228 C 261 254 239 263 219 254 C 210 248 204 239 200 228 Z', '#c3b99e', None)
        p.path('M 201 258 C 211 278 220 294 230 307 M 225 267 C 227 284 230 295 231 307 M 260 256 C 255 278 243 298 234 308', None, '#7d9280', 1.1)
        p.path('M 217 223 C 211 226 202 226 198 231 C 209 235 222 231 233 228 C 245 233 259 232 271 226 C 259 227 253 222 244 222 Z', '#40564f', None)
    # The lunjin scholar's cloth cap, with layered folds.
    p.path('M 161 123 L 169 73 L 207 41 C 216 37 233 40 244 46 L 282 72 L 290 127 C 264 118 190 118 161 123 Z', '#b4c2b7', INK, 3)
    p.path('M 169 77 L 215 88 L 209 43 Z', '#ced2bf', '#688383', 1)
    p.path('M 216 87 L 280 72 L 243 45 L 230 48 Z', '#94aaa6', '#688383', 1)
    p.path('M 161 121 L 169 104 C 208 97 251 100 287 109 L 291 126 C 252 118 201 120 161 127 Z', '#536f75', INK, 2)
    p.path('M 179 90 C 212 96 251 90 276 87', None, '#ecdfc5', 1.6)
    p.path('M 169 125 C 204 118 258 123 284 128', None, '#dcc9a7', 1.2)
    p.path('M 287 74 L 296 113 L 284 111', '#799494', INK, 1)
    # Warm neon light on one sleeve, cooler rim light on the other.
    p.path('M 93 460 C 103 470 117 477 128 478', None, '#d3b694', 3)
    p.path('M 375 377 L 402 472', None, '#b6d7cf', 2)
    return im


def hero_profile(part='all'):
    """An actual side-facing drawing for the turn toward the skyline."""
    im = hero_base(part='body')
    head = hero_base(back=True, part='head')
    p = Pen(head)
    p.path('M 208 128 C 238 120 268 130 276 150 L 283 168 Q 292 176 299 183 Q 298 190 284 190 L 285 210 Q 282 232 260 247 L 225 246 C 206 214 201 169 208 128 Z', '#ecc4a3', INK, 2)
    p.path('M 211 129 C 199 163 210 196 222 205 L 230 189 L 223 157 Z', '#4e625a', None)
    p.ellipse((218, 173, 239, 203), '#e4b698', '#a98065', 1)
    p.path('M 254 172 Q 264 165 275 171 Q 266 179 254 172 Z', '#fff4df', '#544d3e', 1.2)
    p.ellipse((267, 167, 274, 177), '#594f38')
    p.ellipse((269, 168, 272, 171), '#fff7e7')
    p.path('M 251 156 Q 264 151 277 159', None, '#576052', 2.2)
    p.path('M 237 210 Q 248 229 278 218 C 279 248 263 278 242 304 C 226 287 218 256 221 227 Z', '#465c54', INK, 1.5)
    p.path('M 253 222 Q 266 226 280 220 M 236 245 Q 243 276 241 293', None, '#7d9280', 1)
    p.path('M 272 210 Q 280 213 284 209', None, '#79513e', 1.4)
    if part == 'head':
        return head
    im.alpha_composite(head)
    return im


def fan_base():
    im = canvas((310, 300))
    p = Pen(im)
    # A real feather-fan silhouette, thirteen separately drawn feathers.
    for i in range(13):
        angle = math.radians(-71 + i * 11.8)
        x = 155 + math.sin(angle) * 121
        y = 233 - math.cos(angle) * 187
        leftx = x - math.cos(angle) * 13
        lefty = y - math.sin(angle) * 13
        rightx = x + math.cos(angle) * 13
        righty = y + math.sin(angle) * 13
        p.path(f'M 155 239 C {leftx} {lefty+56} {leftx} {lefty} {x} {y} C {rightx} {righty} {rightx} {righty+56} 155 239 Z',
               '#e3dec5' if i % 2 else '#cbd0bb', '#63817f', 1)
        p.path(f'M 155 237 Q {x} {y+40} {x} {y+6}', None, '#8fa197', .9)
        for portion in (.3, .48, .65, .8):
            sx, sy = lerp(155, x, portion), lerp(237, y, portion)
            p.line([(sx, sy), (sx + math.cos(angle) * 8, sy + math.sin(angle) * 8 - 6)], '#b1b6a2', .65)
    p.path('M 151 224 L 146 281 L 157 282 L 164 225 Z', '#9d8764', INK, 1.5)
    p.ellipse((145, 275, 160, 289), '#c0a985', INK, 1)
    p.path('M 156 286 Q 167 296 176 280', None, '#718b84', 1.7)
    return im


def eyes_and_mouth(im, t, emotion='shock', speech=0.):
    p = Pen(im)
    blink = any(a < t < a+.14 for a in (3.8, 7.25, 8.36, 10.1, 13.7, 17.6, 19.95, 23.3, 26.2, 30.9, 33.4))
    # Discrete glances settle on a subject instead of constantly oscillating.
    direction = (-3+7*ease((t-3.1)/.3)-6*ease((t-5.6)/.4)
                 if t < 8 else -2+6*ease((t-9.6)/.4) if t < 16
                 else 5+2*ease((t-19)/.5)-5*ease((t-24)/.7))
    open_amount = {'shock': 1.12, 'wary': .92, 'curious': 1., 'sad': .82}[emotion]
    for x in (211, 260):
        if blink:
            p.path(f'M {x-14} 182 Q {x} 188 {x+14} 181', None, '#604d3e', 1.5)
        else:
            upper = 18 - 14 * open_amount
            lower = 18 + 12 * open_amount
            shape = f'M 5 18 Q 19 {upper-4} 34 16 Q 21 {lower+4} 5 18 Z'
            eye = canvas((40, 36))
            Pen(eye).path(shape, '#fff4df', None)
            iris = canvas((40, 36))
            q = Pen(iris)
            px = 20 + direction
            q.ellipse((px-6.1, 10.1, px+6.1, 26.1), '#806344')
            q.ellipse((px-3.3, 12.2, px+3.3, 24.1), '#393b30')
            q.ellipse((px-3.6, 11.1, px-.2, 14.5), '#fff7e7')
            q.ellipse((px+1.2, 20.7, px+2.8, 22.3), '#d8d7bd')
            iris.putalpha(ImageChops.multiply(iris.getchannel('A'), eye.getchannel('A')))
            eye.alpha_composite(iris)
            Pen(eye).path(shape, None, '#544d3e', 1.3)
            paste(im, eye, x-20, 163)
    p = Pen(im)
    if emotion == 'shock':
        p.path('M 196 160 Q 208 150 224 157 M 247 158 Q 260 149 275 157', None, '#576052', 2.5)
    elif emotion == 'wary':
        p.path('M 196 159 Q 209 155 224 162 M 247 162 Q 261 154 275 158', None, '#576052', 2.4)
    elif emotion == 'curious':
        p.path('M 196 158 Q 210 150 224 157 M 247 157 Q 261 151 275 157', None, '#576052', 2.3)
    else:
        p.path('M 196 162 Q 210 157 224 155 M 247 155 Q 261 158 275 162', None, '#576052', 2.3)
    if speech > .11:
        amount = min(1, speech)
        width = 7 + amount*5 + 2*math.sin(t*29)
        p.ellipse((233-width, 232, 233+width, 236 + amount * 10), '#69463c', '#574d3c', .8)
        if amount > .45:
            p.ellipse((228, 238, 239, 240 + amount * 2), '#c08b77')
    elif emotion == 'curious':
        p.path('M 219 234 Q 232 246 247 233', None, '#79513e', 1.5)
        p.ellipse((216, 233, 219, 236), '#bd9877')
        p.ellipse((247, 232, 250, 235), '#bd9877')
    elif emotion == 'shock':
        p.ellipse((228, 234, 239, 243), '#785547', '#65503d', .8)
    else:
        p.path('M 221 236 Q 233 240 245 235', None, '#79513e', 1.3)
    return im


def young_base(part='all'):
    im = canvas((350, 720))
    p = Pen(im)
    p.path('M 110 372 L 218 372 L 233 638 L 202 647 L 164 487 L 144 654 L 99 650 Z', '#2c4558', INK, 3)
    p.path('M 173 412 L 188 506 L 207 633 M 120 425 L 108 637', None, '#53717f', 2)
    p.path('M 99 640 L 146 640 L 152 665 L 93 666 Z', '#dedbc7', INK, 2)
    p.path('M 203 636 L 233 633 L 259 656 L 253 669 L 200 665 Z', '#d5d7ca', INK, 2)
    p.path('M 95 235 C 122 212 168 200 201 218 C 230 234 241 277 249 310 L 223 383 C 186 402 124 402 92 379 L 75 298 Z', '#c79776', INK, 3)
    p.path('M 139 212 L 133 245 L 176 278 L 197 215', '#e1b696', INK, 1.5)
    p.path('M 118 212 C 112 238 125 255 151 267 L 174 295 L 203 248 L 200 215', '#b6d1c9', INK, 2)
    p.path('M 82 277 C 79 310 81 339 96 370 L 125 343 L 115 279', '#b08367', INK, 2)
    p.path('M 196 266 C 193 291 188 310 178 324 L 130 302 L 114 333 L 170 364 C 190 373 206 354 216 337 L 234 282', '#d3a27c', INK, 2)
    p.path('M 130 300 C 131 288 143 282 155 286 L 177 294 L 166 310 L 145 321 Z', '#dfb594', INK, 1.5)
    p.path('M 147 206 L 145 184 L 187 173 L 190 225 L 166 238 Z', '#c59779', INK, 1.5)
    if part == 'body':
        # Raised phone, camera facing the scholar.
        p.rect((108, 255, 144, 314), '#172b34', 5, '#91a5a6', 1.5)
        p.ellipse((113, 260, 122, 269), '#729391', '#9fbbaf', 1)
        p.ellipse((126, 260, 135, 269), '#577783')
        return im
    if part == 'head':
        im = canvas((350, 720))
        p = Pen(im)
    p.ellipse((197, 136, 216, 167), '#d7ac8c', INK, 1.5)
    p.path('M 123 111 C 116 139 118 175 134 196 C 149 217 179 210 196 190 C 207 172 207 137 193 113 Z', '#e4bfa0', INK, 2.5)
    p.path('M 119 140 L 110 103 C 123 81 139 82 154 89 C 174 78 196 94 210 109 L 202 145 L 190 126 L 177 125 L 170 114 L 145 131 L 129 126 Z', '#243e47', INK, 2)
    p.path('M 136 157 Q 145 151 156 157 M 176 154 Q 183 149 192 153', None, '#263e45', 2)
    p.path('M 164 156 L 161 172 L 167 173', None, '#a67860', 1.5)
    p.path('M 143 182 Q 161 197 181 181', '#f1ddc2', '#7e5e4d', 1.5)
    p.path('M 137 144 Q 147 137 157 143 M 175 141 Q 184 136 193 140', None, '#2a4147', 2.5)
    if part == 'head':
        return im
    # Raised phone, camera facing the scholar.
    p.rect((108, 255, 144, 314), '#172b34', 5, '#91a5a6', 1.5)
    p.ellipse((113, 260, 122, 269), '#729391', '#9fbbaf', 1)
    p.ellipse((126, 260, 135, 269), '#577783')
    p.ellipse((122, 284, 130, 291), '#66878b')
    return im


def passer(color='#26444f'):
    im = canvas((210, 700))
    p = Pen(im)
    p.ellipse((61, 67, 126, 143), color)
    p.path('M 69 141 L 58 165 C 30 182 32 248 45 363 L 71 381 L 64 621 L 88 623 L 109 406 L 139 620 L 162 615 L 136 373 C 161 302 162 215 145 177 L 110 146 Z', color, None)
    p.path('M 43 196 L 20 361 L 33 369 L 65 261 M 136 192 L 174 344 L 158 354 L 128 259', color, None)
    p.path('M 66 612 L 62 636 L 96 636 L 89 614 M 137 610 L 140 633 L 182 633 L 158 611', color, None)
    return im


class Film:
    def __init__(self, lines=None):
        self.background = city_background()
        self.hero = hero_base()
        self.back = hero_base(back=True)
        self.bodies = [hero_base(part='body'), hero_base(back=True, part='body')]
        self.heads = [hero_base(part='head'), hero_base(back=True, part='head')]
        self.profile = hero_profile(part='head')
        self.fan = fan_base()
        self.young = young_base()
        self.young_body = young_base(part='body')
        self.young_head = young_base(part='head')
        self.silhouettes = [passer('#203947'), passer('#1d323e')]
        self.lines = lines or []
        # Closing background dissolves gently into a soft photographic-like bokeh.
        self.blurred = self.background.filter(ImageFilter.GaussianBlur(4 * R))

    def speaking(self, t, young=False):
        for line in self.lines:
            if (line['name'] == 'young') != young:
                continue
            i = round((t - line['start']) * SR)
            if 0 <= i < len(line['samples']):
                chunk = line['samples'][i:min(i+1600, len(line['samples']))]
                return min(1., float(np.sqrt(np.mean(chunk ** 2))) * 8)
        return 0.

    def scholar(self, t, emotion, back=False, profile=False):
        # Head, shoulders, sleeve and fan react independently to the encounter.
        im = self.bodies[int(back)].copy()
        head = (self.profile if profile else self.heads[int(back)]).copy()
        if not back and not profile:
            eyes_and_mouth(head, t, emotion, self.speaking(t))
        astonished = beat(t, 1.8, 2.7, 4.2)
        question = beat(t, 10.4, 11.3, 13.6)
        listening = beat(t, 16.4, 17.3, 19.3)
        inspect = ease((t-19.1)/.9) * (1-ease((t-23.4)/.7))
        realization = beat(t, 23.1, 24.0, 25.0)
        nod = beat(t, 25.0, 25.35, 25.9)
        tilt = -4.5*astonished + 6.5*question + 4*listening + 8*inspect - 3*realization
        tilt += .6*math.sin(t*1.4+.5) + 2.8*nod
        head = head.crop((round(110*R), 0, round(350*R), round(338*R)))
        head = head.rotate(tilt, Image.Resampling.BICUBIC, center=(123*R, 275*R))
        paste(im, head, 110+inspect*5, -astonished*4+inspect*3+nod*5)
        # A natural fan stroke has a quick forward sweep and a soft return.
        rhythm = math.sin(t*2.15+.35*math.sin(t*.83))
        amplitude = 0 if t < 8 else (3 if t < 16 else 9 if t < 28 else 3*(1-ease((t-31)/4)))
        fan_angle = 9 + amplitude*rhythm - 9*question + 5*realization
        lift = 10*question + 9*listening - 13*inspect + 8*realization
        shift = -5*question + 9*inspect
        p = Pen(im)
        p.path(f'M 353 448 Q 316 431 {320+shift} {401-lift} L {350+shift} {384-lift} Q 384 418 389 468 Z', '#b7c4b4', INK, 1.8)
        prop = canvas((440, 800))
        rotated = self.fan.rotate(fan_angle, Image.Resampling.BICUBIC, center=(155*R, 270*R))
        paste(prop, rotated, 216, 172, .78)
        q = Pen(prop)
        q.path('M 324 390 C 321 377 324 369 331 369 L 345 378 C 352 381 354 393 346 400 L 331 404 Z', '#e0b99b', INK, 2)
        q.path('M 329 380 L 342 389 M 327 387 L 339 396', None, '#a37b63', 1)
        paste(im, prop, shift, -lift)
        # Quiet breathing and weight shifts, with an extra lean toward the phone.
        lean = .42*math.sin(t*.9) - 1.4*inspect + .9*question
        im = im.rotate(lean, Image.Resampling.BICUBIC, center=(233*R, 710*R))
        return im

    def young_actor(self, t):
        im = self.young_body.copy()
        head = self.young_head.copy()
        speech = self.speaking(t, young=True)
        p = Pen(head)
        if speech > .08:
            p.ellipse((148, 179, 178, 184+speech*12), '#61443a', '#7e5e4d', 1)
            p.path('M 151 180 Q 162 185 175 180 L 174 184 Q 161 188 152 183 Z', '#f1ddc2', None)
        if any(a < t < a+.12 for a in (15.5, 18.8, 24.5, 27.2)):
            p.path('M 135 156 Q 145 160 156 155 M 175 152 Q 184 156 193 151', None, '#263e45', 2)
        greeting = beat(t, 16.1, 16.8, 18.5)
        nod = beat(t, 17.4, 17.7, 18.15) + beat(t, 19.3, 19.6, 20.0)
        head = head.crop((round(105*R), round(76*R), round(219*R), round(216*R)))
        head = head.rotate(-3*greeting+3*nod, Image.Resampling.BICUBIC, center=(60*R, 121*R))
        paste(im, head, 105, 76+3.5*nod)
        return im.rotate(.8*math.sin(t*1.15)-1.8*greeting, Image.Resampling.BICUBIC, center=(165*R, 645*R))

    def walking_passer(self, t, index):
        color = ('#203947', '#1d323e')[index]
        im = canvas((210, 700))
        p = Pen(im)
        phase = t*6.8+index*2.2
        stride = 27*math.sin(phase)
        bob = -2.5*abs(math.sin(phase))
        p.ellipse((61, 67+bob, 126, 143+bob), color)
        p.path(f'M 69 {141+bob} L 58 165 C 30 182 32 248 45 363 L 71 390 L 136 390 C 161 302 162 215 145 177 L 110 {146+bob} Z', color, None)
        for hip, delta in ((83,stride),(121,-stride)):
            knee = hip+delta*.6
            ankle = hip+delta
            p.path(f'M {hip-13} 372 L {knee-10} 495 L {ankle-11} 622 L {ankle+11} 622 L {knee+12} 495 L {hip+13} 372 Z', color, None)
            p.path(f'M {ankle-12} 613 L {ankle-14} 636 L {ankle+25} 636 L {ankle+12} 615 Z', color, None)
        p.path(f'M 43 196 L {23-stride*.5} 345 L {38-stride*.5} 354 L 65 261 M 136 192 L {170+stride*.5} 331 L {156+stride*.5} 346 L 128 259', color, None)
        return im

    def traffic(self, im, t):
        lights = canvas()
        p = Pen(lights)
        for i in range(21):
            phase = (i / 21 + t * (.047 + (i % 3) * .011)) % 1
            x = -120 + phase * 1530
            y = 496 + ((x - 830) / 160) ** 2 * 2.2
            y += (i % 3) * 13
            color = '#ffe6b0' if i % 2 else '#ef9983'
            p.line([(x - 16, y), (x + 13, y - 1)], color, 2)
            p.line([(x - 25, y + 4), (x + 10, y + 3)], color, 1)
        im.alpha_composite(lights.filter(ImageFilter.GaussianBlur(3.5 * R)))
        im.alpha_composite(lights)

    def phone(self, t):
        # Macro shot: anonymous local messages, no actual personal data.
        im = self.background.filter(ImageFilter.GaussianBlur(18 * R))
        shade = canvas(color=(4, 15, 25, 90))
        im.alpha_composite(shade)
        p = Pen(im)
        p.path('M 286 650 C 297 576 374 510 447 494 L 784 483 C 898 513 964 610 976 679 Z', '#b7856d', INK, 3)
        p.path('M 794 644 C 835 623 866 602 842 567 L 773 475 C 760 454 731 463 733 487 L 772 560 L 729 615 Z', '#dfb294', INK, 2)
        p.rect((473, 80, 794, 648), '#101d27', 31, '#7b959d', 3)
        p.rect((486, 97, 781, 628), '#dce8e4', 24)
        p.rect((570, 102, 699, 126), '#101d27', 11)
        p.text((507, 125), '21:06', 15, '#405960')
        p.text((758, 125), '▰', 18, '#405960', 'ra')
        p.rect((488, 163, 779, 230), '#427a80')
        p.text((634, 177), '消息', 23, '#f6f2db', 'ma')
        messages = [('朋友', '到陆家嘴了吗？', 20.5), ('朋友', '我们在天桥这边。', 21.3), ('朋友', '抬头，看东方明珠。', 22.1)]
        for i, (who, text, start) in enumerate(messages):
            a = ease((t-start) / .25)
            if a <= 0:
                continue
            layer = canvas()
            q = Pen(layer)
            y = 260 + i * 103 + (1-a) * 15
            q.ellipse((504, y+4, 539, y+39), '#b0c3b5')
            q.text((521, y+4), '友', 17, '#315258', 'ma')
            q.text((552, y), who, 15, '#6f8785')
            q.rect((550, y+30, 762, y+84), '#f5f6e9', 8)
            q.text((563, y+40), text, 18, '#355558')
            layer.putalpha(layer.getchannel('A').point(lambda x: round(x*a)))
            im.alpha_composite(layer)
        p = Pen(im)
        p.rect((506, 557, 761, 602), '#c5d5cc', 8)
        p.text((527, 566), '轻触输入…', 17, '#7a918e')
        p.rect((585, 611, 684, 616), '#5e757c', 3)
        return im

    def caption(self, im, text, opacity=1., final=False):
        if opacity <= 0:
            return
        layer = canvas()
        p = Pen(layer)
        y = 574 if final else 625
        if not final:
            text_width = ImageDraw.Draw(layer).textlength(text, font=font(26)) / R
            p.rect(((W-text_width)/2 - 24, y-2, (W+text_width)/2 + 24, y+44), (7, 20, 28, 180), 5)
        p.text((640, y), text, 37 if final else 26, '#eee2c5', 'ma', serif=True, stroke=.8)
        if final:
            p.line([(574, y-21), (706, y-21)], '#b99b78', 1)
        layer.putalpha(layer.getchannel('A').point(lambda x: round(x*opacity)))
        im.alpha_composite(layer)

    def frame(self, t):
        if 20.3 <= t < 23.0:
            im = self.phone(t)
        else:
            im = (self.blurred if 8 <= t < 16 else self.background).copy()
            self.traffic(im, t)
            railing(im)
            if t < 8:
                # Medium shot, an uninterrupted slow push toward his shock.
                progress = ease((t-1) / 7)
                scale = .79 + .16 * progress
                x = 699 - 226 * scale
                y = 168 - 170 * scale - progress * 10
                paste(im, self.scholar(t, 'shock'), x, y, scale)
                for i in range(2):
                    px = (t*55 + i*460) % 1700 - 260
                    paste(im, self.walking_passer(t, i), px, 221, .64)
            elif t < 16:
                # A handheld close-up with a shallow depth-of-field city.
                shake_x = math.sin(t * 5.3) * 1.5 + math.sin(t * 11) * .4
                shake_y = math.cos(t * 4.7) * .95
                emotion = 'wary' if t < 11 else 'curious'
                scale = 1.84 + .04 * ease((t-8)/8)
                paste(im, self.scholar(t, emotion), 562-226*scale+shake_x, 272-172*scale+shake_y, scale)
                if t > 12.8:
                    young = self.young_actor(t).filter(ImageFilter.GaussianBlur(2.5*R))
                    paste(im, young, 930-(ease((t-12.8)/2)*80), 195, .68)
                if 8.7 < t < 10.5:
                    px = 1280 - (t-8.7) * 930
                    paste(im, self.walking_passer(t, 1).filter(ImageFilter.GaussianBlur(3*R)), px, 100, 1.1)
            elif t < 28:
                # Two-shot, with the young man's raised phone visible.
                paste(im, self.young_actor(t), 795, 118+math.sin(t*1.3), .82)
                emotion = 'curious' if t < 25.9 else 'sad'
                scale = .94 + .10 * ease((t-23)/5) if t >= 23 else .94
                paste(im, self.scholar(t, emotion), 305, 12-(scale-.94)*290, scale)
            else:
                # He turns toward the skyline; the camera leaves room for the city.
                turn = ease((t-28)/1.6)
                young = self.young_actor(t).filter(ImageFilter.GaussianBlur(5*R))
                paste(im, young, 888+turn*190, 178, .69)
                scale = .91 + .07 * ease((t-28)/8)
                # Drawn side profile between front/back poses; shoulders foreshorten.
                actor = self.scholar(t, 'sad', back=turn >= .72, profile=.28 <= turn < .72)
                width = .80 + .20*abs(math.cos(turn*math.pi))
                narrowed = actor.resize((round(actor.width*width), actor.height), Image.Resampling.BICUBIC)
                turned = canvas((440, 800))
                paste(turned, narrowed, 233*(1-width), 0)
                paste(im, turned, 555-20*turn, 32-(scale-.91)*310, scale)
                # Glimmering lamp halo on the cloth emphasizes the quiet ending.
                light = canvas()
                q = Pen(light)
                q.ellipse((540, 198, 938, 712), (245, 159, 100, 12))
                im.alpha_composite(light.filter(ImageFilter.GaussianBlur(40*R)))
        if 10.95 <= t < 13.35:
            self.caption(im, '此乃何方城池？', ease((t-10.95)/.15)*ease((13.35-t)/.25))
        elif 16.35 <= t < 19.4:
            self.caption(im, '大叔，你这诸葛亮扮得挺像！', ease((t-16.35)/.15)*ease((19.4-t)/.2))
        elif 23.25 <= t < 27.3:
            self.caption(im, '此物……不用烽火，亦能传讯！', ease((t-23.25)/.2)*ease((27.3-t)/.3))
        if t >= 31:
            self.caption(im, '两千载……弹指之间', ease((t-31)/1.15)*ease((35.3-t)/.7), final=True)
        if 2 < t < 6:
            layer = canvas()
            p = Pen(layer)
            p.text((68, 67), '上海 · 陆家嘴', 17, '#d6e2dd')
            p.text((68, 94), '2026  /  夜', 12, '#91afb4')
            alpha = ease((t-2)/.6)*ease((6-t)/.8)
            layer.putalpha(layer.getchannel('A').point(lambda x: round(x*alpha)))
            im.alpha_composite(layer)
        # Cinematic framing; the opening starts with sound and true black.
        p = Pen(im)
        p.rect((0, 0, W, 40), '#07131b')
        p.rect((0, 680, W, H), '#07131b')
        visibility = ease((t-.65)/1.55) * ease((35.55-t)/1.3)
        if visibility < 1:
            black = canvas(color=(0, 0, 0, 255))
            im = Image.blend(black, im, visibility)
        return im.convert('RGB').resize((W, H), Image.Resampling.LANCZOS)


def render(args):
    output = ROOT / 'output'
    output.mkdir(exist_ok=True)
    lines = []
    if args.stills:
        timing_file = output / 'dialogue-timing.json'
        if timing_file.exists():
            for line in json.loads(timing_file.read_text()):
                wave_path = output / 'dialogue' / (line['name'] + '.wav')
                samples, rate = wav_read(wave_path)
                if rate == SR:
                    line['samples'] = samples
                    lines.append(line)
        film = Film(lines)
        times = [5.5, 12.3, 18.1, 21.7, 25.6, 32.5]
        contact = Image.new('RGB', (1280, 1080), '#0c1c28')
        for i, t in enumerate(times):
            frame = film.frame(t)
            frame.save(output / f'frame-{t:04.1f}.png')
            contact.paste(frame.resize((640, 360), Image.Resampling.LANCZOS), ((i%2)*640, (i//2)*360))
        contact.save(output / 'storyboard.jpg', quality=95)
        print('Saved six preview frames and storyboard.jpg', flush=True)
        return
    lines = make_audio()
    film = Film(lines)
    target = args.output if args.output.is_absolute() else ROOT / args.output
    target.parent.mkdir(parents=True, exist_ok=True)
    command = ['ffmpeg', '-hide_banner', '-loglevel', 'warning', '-y',
               '-f', 'rawvideo', '-vcodec', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}',
               '-r', str(args.fps), '-i', 'pipe:0', '-i', str(output/'soundtrack.wav'),
               '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-threads', '3',
               '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
               '-movflags', '+faststart', '-t', '36', str(target)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for index in range(args.fps * 36):
            process.stdin.write(film.frame(index / args.fps).tobytes())
            if index % args.fps == 0:
                print(f'Rendered {index // args.fps:2d}/36 seconds', flush=True)
    finally:
        process.stdin.close()
    status = process.wait()
    if status:
        raise RuntimeError(f'FFmpeg exited with {status}')
    print('Video complete:', target, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stills', action='store_true', help='Render a six-frame contact sheet without synthesizing audio.')
    parser.add_argument('--fps', type=int, default=24)
    parser.add_argument('--output', type=Path, default=Path('output/zhuge-shanghai-2026.mp4'), help='Destination MP4 path.')
    args = parser.parse_args()
    if not 1 <= args.fps <= 60:
        parser.error('--fps must be between 1 and 60')
    render(args)
