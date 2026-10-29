"""
Smart Attendance Deck - simplified but dimensionally faithful component models.

Every component is built in its own local frame (documented per function) so it can be
exported on its own, then placed in the enclosure by assembly.py.
Units: mm.
"""
import os
import cadquery as cq
from enclosure import FONT_DIR
from enclosure import (LCD_PCB, LCD_HOLES, LCD_WIN, LCD_BEZEL_H, RFID, KP_FLANGE, KP_HOLES,
                       KP_HOLE_D, KP_PLATEAU, KP_PLATEAU_R, KP_BACK, KP_TOTAL, KP_KEYS_PROUD,
                       ARD_HOLES, NAME_FONT)

MONO = os.path.join(FONT_DIR, "DejaVuSansMono-Bold.ttf")


def box(x0, x1, y0, y1, z0, z1):
    return (cq.Workplane("XY").box(x1-x0, y1-y0, z1-z0, centered=False)
            .translate((x0, y0, z0)))


def cyl(x, y, z0, z1, r):
    return cq.Workplane("XY").workplane(offset=z0).center(x, y).circle(r).extrude(z1-z0)


def rbox(cx, cy, w, h, z0, z1, r):
    return (cq.Workplane("XY").workplane(offset=z0).center(cx, cy).sketch()
            .rect(w, h).vertices().fillet(r).finalize().extrude(z1-z0))


def text(s, size, x, y, z0, t, font=NAME_FONT):
    return (cq.Workplane("XY").workplane(offset=z0).center(x, y)
            .text(s, size, t, combine=False, fontPath=font, halign="center", valign="center"))


def U(*ws):
    out = ws[0]
    for w in ws[1:]:
        out = out.union(w)
    return out


# --------------------------------------------------------------------- Arduino UNO R4 WiFi
def arduino_uno_r4_wifi():
    """Origin: lower-left corner of the PCB (USB-C / DC jack edge on the left), z=0 at the
    PCB underside, components on +z. Returns dict of colour groups."""
    outline = [(0, 0), (66.04, 0), (68.58, 2.54), (68.58, 38.1), (66.04, 40.64),
               (66.04, 51.82), (64.52, 53.34), (0, 53.34)]
    pcb = cq.Workplane("XY").polyline(outline).close().extrude(1.6)
    pcb = pcb.cut(cq.Workplane("XY").pushPoints(ARD_HOLES).circle(1.6).extrude(2))
    hdr = U(box(17.53, 42.93, 49.53, 52.07, 1.6, 10.1),   # D8-SCL (10 pin)
            box(44.45, 64.77, 49.53, 52.07, 1.6, 10.1),   # D0-D7  (8 pin)
            box(27.94, 48.26, 1.27, 3.81, 1.6, 10.1),     # power  (8 pin)
            box(50.80, 66.04, 1.27, 3.81, 1.6, 10.1),     # A0-A5  (6 pin)
            box(64.0, 66.54, 25.4, 30.48, 1.6, 10.1))     # ICSP-ish 2x3
    holes_h = cq.Workplane("XY").workplane(offset=6).pushPoints(
        [(18.8 + i*2.54, 50.8) for i in range(10)] + [(45.72 + i*2.54, 50.8) for i in range(8)] +
        [(29.21 + i*2.54, 2.54) for i in range(8)] + [(52.07 + i*2.54, 2.54) for i in range(6)]
    ).rect(1.0, 1.0).extrude(4.2)
    hdr = hdr.cut(holes_h)
    usb = box(-1.2, 6.15, 33.6, 42.54, 1.6, 4.86)          # USB-C receptacle
    usb = usb.cut(box(-1.3, 2.0, 34.5, 41.6, 2.2, 4.3))
    jack = U(box(-1.9, 11.6, 3.3, 12.3, 1.6, 12.6))
    jack = jack.cut(cq.Workplane("YZ").workplane(offset=-2).center(7.8, 7.6).circle(3.2).extrude(8))
    esp = U(box(40.0, 55.4, 22.0, 42.5, 1.6, 3.6))        # ESP32-S3-MINI module (can)
    mcu = box(26.0, 33.0, 26.0, 33.0, 1.6, 3.0)           # RA4M1 QFP
    matrix = cq.Workplane("XY").workplane(offset=1.6).pushPoints(
        [(25.0 + i*1.7, 8.0 + j*1.7) for i in range(12) for j in range(8)]).rect(1.0, 0.6).extrude(0.4)
    btn = U(box(57.5, 63.5, 41.5, 47.5, 1.6, 3.1), cyl(60.5, 44.5, 3.1, 3.6, 1.5))
    qwiic = box(62.0, 66.0, 13.5, 19.5, 1.6, 4.5)
    return {"pcb": (pcb, "#008184"), "black": (U(hdr, jack, mcu, qwiic, btn), "#1b1b1b"),
            "metal": (U(usb, esp), "#c9ced3"), "leds": (matrix, "#f2c14e")}


# --------------------------------------------------------------------- 20x4 LCD + I2C
def lcd2004_i2c():
    """Origin: centre of the LCD, z=0 at the front of the metal bezel, module extends to -z.
    Backpack is at the pin-1..16 header (top edge), I2C header exits to +x."""
    bz0, bz1 = 0.0, -LCD_BEZEL_H
    bezel = box(-48.5, 48.5, -20, 20, bz1, bz0)
    bezel = bezel.cut(box(-LCD_WIN[0]/2-1.5, LCD_WIN[0]/2+1.5, -LCD_WIN[1]/2-1.5, LCD_WIN[1]/2+1.5, -0.6, 0.1))
    glass = box(-LCD_WIN[0]/2-1.5, LCD_WIN[0]/2+1.5, -LCD_WIN[1]/2-1.5, LCD_WIN[1]/2+1.5, -1.6, -0.6)
    txt = U(text("READY TO SCAN", 3.6, -12, 6, -0.6, 0.05, MONO),
            text("PASS / MANUAL CODE", 3.6, -2.5, -0.5, -0.6, 0.05, MONO))
    pcb = box(-49, 49, -30, 30, bz1-1.6, bz1)
    pcb = pcb.cut(cq.Workplane("XY").workplane(offset=bz1-2).pushPoints(
        [(sx*LCD_HOLES[0]/2, sy*LCD_HOLES[1]/2) for sx in (-1, 1) for sy in (-1, 1)]).circle(1.75).extrude(3))
    # backpack (FC-113 / PCF8574) on 16-pin header
    pin1 = -39.3; row_y = 27.5
    hdr = box(pin1-1.27, pin1+15*2.54+1.27, row_y-1.27, row_y+1.27, bz1-1.6-2.5, bz1-1.6)
    bp_z0 = bz1-1.6-2.5
    bp = box(pin1-1.5, pin1+40.0, row_y-17.3, row_y+2.0, bp_z0-1.6, bp_z0)
    chip = box(-20, -10, 14, 21.5, bp_z0-3.4, bp_z0-1.6)
    pot = U(box(-34, -24.5, 12, 21.5, bp_z0-6.6, bp_z0-1.6), cyl(-29.25, 16.75, bp_z0-7.4, bp_z0-6.6, 1.5))
    i2c_hdr = box(pin1+40.0-2.5, pin1+40.0, row_y-12.7, row_y-2.5, bp_z0-4.1, bp_z0-1.6)
    i2c_pins = cq.Workplane("XY").pushPoints([(pin1+40.0+3, row_y-11.43+i*2.54) for i in range(4)]) \
        .rect(6, 0.64).extrude(0.64).translate((0, 0, bp_z0-3.2))
    return {"bezel": (bezel, "#b7bcc2"), "glass": (glass, "#2d5fd3"), "text": (txt, "#e9f1ff"),
            "pcb": (U(pcb, bp), "#1f7a3a"), "black": (U(hdr, chip, i2c_hdr), "#1b1b1b"),
            "pot": (pot, "#2f6fd6"), "pins": (i2c_pins, "#d4af37")}


# --------------------------------------------------------------------- RC522
def rc522():
    """Origin: centre of the board, z=0 at the antenna (front) face which sits against the
    1.8 mm tap window; parts on the back (-z). 8-pin header on the +x short edge."""
    w, h = RFID
    pcb = box(-w/2, w/2, -h/2, h/2, -1.6, 0)
    pcb = pcb.cut(cq.Workplane("XY").workplane(offset=-2).pushPoints([(-w/2+7, h/2-7), (-w/2+7, -h/2+7)])
                  .circle(1.6).extrude(3))
    ant = (cq.Workplane("XY").workplane(offset=-1.65).center(-6, 0).rect(40, 31).rect(37, 28)
           .extrude(-0.05))
    chip = box(8.0, 13.0, -2.5, 2.5, -2.6, -1.6)
    xtal = box(16.0, 20.5, -8.0, 3.0, -5.1, -1.6)
    caps = cq.Workplane("XY").workplane(offset=-2.2).pushPoints([(4, 9), (6, -9), (18, 8), (2, -6), (11, 9)]) \
        .rect(2.0, 1.25).extrude(0.6)
    hdr = box(w/2-4.0, w/2-1.5, -10.16, 10.16, -4.1, -1.6)
    pins = cq.Workplane("XY").pushPoints([(w/2-2.75, -8.89+i*2.54) for i in range(8)]).rect(0.64, 0.64) \
        .extrude(-10).translate((0, 0, -1.6))
    dupont = box(w/2-4.1, w/2-1.4, -10.2, 10.2, -20.0, -7.0)
    return {"pcb": (pcb, "#1e5bb8"), "ant": (ant, "#c8a24a"), "black": (U(chip, xtal, hdr), "#1b1b1b"),
            "caps": (caps, "#a0805a"), "pins": (pins, "#d4af37"), "dupont": (dupont, "#202020")}


# --------------------------------------------------------------------- 4x4 hard keypad
KEY_LABELS = [["1", "2", "3", "A"], ["4", "5", "6", "B"], ["7", "8", "9", "C"], ["*", "0", "#", "D"]]


def keypad_4x4_hard():
    """Origin: centre of the keypad, z=0 at the front of the base plate (sits against the
    inside of the panel). Plateau and keys on +z, PCB and pin tail on -z."""
    fw, fh = KP_FLANGE
    holes = [(sx*KP_HOLES[0]/2, sy*KP_HOLES[1]/2) for sx in (-1, 1) for sy in (-1, 1)]
    hole_cut = cq.Workplane("XY").workplane(offset=-KP_BACK-1).pushPoints(holes).circle(KP_HOLE_D/2) \
        .extrude(KP_BACK+2)
    base = box(-fw/2, fw/2, -fh/2, fh/2, -2.0, 0).cut(hole_cut)
    plateau_top = KP_TOTAL - KP_KEYS_PROUD - KP_BACK      # 3.0 above the base front
    plateau = rbox(0, 0, *KP_PLATEAU, -0.01, plateau_top, KP_PLATEAU_R)
    pcb = box(-fw/2, fw/2, -fh/2, fh/2, -KP_BACK, -2.0).cut(hole_cut)
    tail = box(-31, 15, -fh/2-6.1, -fh/2+0.1, -KP_BACK, -2.0)
    pads = cq.Workplane("XY").pushPoints([(-17.9+i*2.54, -fh/2-3.0) for i in range(8)]).circle(0.8) \
        .extrude(0.05).translate((0, 0, -2.0))
    hdr = box(-19.2, 1.0, -fh/2-4.3, -fh/2-1.7, -KP_BACK-2.5, -KP_BACK)
    dupont = box(-19.3, 1.1, -fh/2-4.6, -fh/2-1.4, -KP_BACK-15.0, -KP_BACK-2.5)
    pitch = (KP_PLATEAU[0]-12)/3
    keys, labels = [], []
    for j, row in enumerate(KEY_LABELS):
        for i, lab in enumerate(row):
            x = (i-1.5)*pitch; y = (1.5-j)*pitch
            k = rbox(x, y, 10, 10, plateau_top-0.01, plateau_top+KP_KEYS_PROUD, 1.2)
            k = k.faces(">Z").edges().fillet(0.6)
            keys.append(k)
            labels.append(text(lab, 5.2 if lab not in "*#" else 6.0, x, y, plateau_top+KP_KEYS_PROUD, 0.12))
    return {"black": (U(base, plateau, *keys), "#202326"), "labels": (U(*labels), "#f4f4f4"),
            "pcb": (U(pcb, tail), "#1f7a3a"), "pads": (pads, "#d4af37"),
            "dupont": (U(hdr, dupont), "#2a2a2a")}


# --------------------------------------------------------------------- 5 mm LED
def led5(color):
    """Origin: centre of the flange top; lens points +z (tip at z=7.6), legs to -z."""
    flange = cyl(0, 0, -1.0, 0, 2.9)
    flange = flange.cut(box(2.4, 3.0, -3, 3, -1.1, 0.1))           # cathode flat
    body = cyl(0, 0, 0, 5.1, 2.5).union(cq.Workplane("XY").sphere(2.5).translate((0, 0, 5.1)))
    legs = U(box(-1.52, -1.02, -0.25, 0.25, -14, -1), box(1.02, 1.52, -0.25, 0.25, -12, -1))
    return {"lens": (U(flange, body), color), "legs": (legs, "#c0c4c8")}


# --------------------------------------------------------------------- 12 mm piezo buzzer
def buzzer12():
    """Origin: centre of the front face (sound hole), body to -z, pins to -z."""
    body = cyl(0, 0, -9.5, 0, 6.0).cut(cyl(0, 0, -1, 0.1, 1.0))
    label = text("+", 3, 3.2, 0, -0.01, 0.05)
    pins = U(cyl(-3.8, 0, -16, -9.5, 0.3), cyl(3.8, 0, -16, -9.5, 0.3))
    return {"body": (body, "#151515"), "mark": (label, "#e9e9e9"), "pins": (pins, "#c0c4c8")}


# --------------------------------------------------------------------- 2 x 18650 holder
def battery_2x18650():
    """Origin: lower-left corner of the holder underside; 77 x 41 footprint, cells along x."""
    L_, W_, H_ = 77.0, 41.0, 20.5
    shell = box(0, L_, 0, W_, 0, H_)
    shell = shell.cut(box(2.5, L_-2.5, 1.5, W_-1.5, 1.5, H_+1))      # cavity
    shell = shell.cut(box(-1, L_+1, -1, W_+1, 12.5, H_+1).cut(box(-2, 2.5, -2, W_+2, 0, H_+2))
                      .cut(box(L_-2.5, L_+2, -2, W_+2, 0, H_+2)))    # low side walls
    shell = shell.cut(box(-1, 3.0, 15.0, 26.0, 3, 9))                  # wire exit
    cells, caps = [], []
    for yc in (W_/2-9.6, W_/2+9.6):
        cells.append(cq.Workplane("YZ").workplane(offset=6.0).center(yc, 10.6).circle(9.1).extrude(65))
        caps.append(cq.Workplane("YZ").workplane(offset=71.0).center(yc, 10.6).circle(3.5).extrude(1.0))
    springs = U(*[cq.Workplane("YZ").workplane(offset=2.5).center(yc, 10.6).circle(4.5).circle(3.5).extrude(3.5)
                  for yc in (W_/2-9.6, W_/2+9.6)])
    wrap_txt = text("18650  3.7V", 5, 38.5, W_/2+9.6, 19.6, 0.1).union(
        text("18650  3.7V", 5, 38.5, W_/2-9.6, 19.6, 0.1))
    return {"holder": (shell, "#151515"), "cells": (U(*cells), "#2f7ee0"),
            "metal": (U(*caps, springs), "#c9ced3"), "text": (wrap_txt, "#ffffff")}


# --------------------------------------------------------------------- 2S USB-C charge board
def charge_board_2s():
    """Origin: centre of the PCB underside. USB-C exits the +y edge (overhang 0.6 mm),
    centred at x=-1 to line up with the back-cover opening."""
    pcb = box(-8.5, 8.5, -12, 12, 0, 1.6)
    usb = (cq.Workplane("XZ").workplane(offset=-12.6).center(-1, 3.23).sketch().rect(8.94, 3.26).vertices()
           .fillet(1.3).finalize().extrude(7.35))
    usb = usb.cut(cq.Workplane("XZ").workplane(offset=-12.8).center(-1, 3.23).sketch().rect(7.4, 2.0).vertices()
                  .fillet(0.9).finalize().extrude(1.8))
    ic = box(-2.5, 2.5, -6, -2, 1.6, 2.6)
    ind = box(-7.5, -1.5, -11.5, -5.5, 1.6, 4.6)
    leds = cq.Workplane("XY").workplane(offset=1.6).pushPoints([(5.5, 2), (5.5, -1)]).rect(1.6, 0.8).extrude(0.6)
    pads = cq.Workplane("XY").workplane(offset=1.6).pushPoints([(-5, -10.5), (-2, -10.5), (1, -10.5), (4, -10.5)]) \
        .rect(2, 1.6).extrude(0.05)
    return {"pcb": (pcb, "#1d5a2e"), "metal": (U(usb, ind), "#c9ced3"), "black": (ic, "#1b1b1b"),
            "leds": (leds, "#ff5a36"), "pads": (pads, "#d4af37")}


# --------------------------------------------------------------------- KCD11 mini rocker
def rocker_kcd11():
    """Origin: centre of the panel hole on the OUTSIDE face of the back cover;
    +z points into the enclosure. Flange and rocker on -z."""
    flange = rbox(0, 0, 15.0, 10.5, -2.0, 0, 1.0)
    rock = (cq.Workplane("XZ").polyline([(-5.5, -2), (5.5, -2), (5.5, -4.6), (0, -3.4), (-5.5, -5.4)]).close()
            .extrude(3.5, both=True))
    mark = U(box(2.2, 3.2, -0.6, 0.6, -4.5, -4.0), cyl(-2.8, 0, -5.4, -4.6, 0.9).cut(cyl(-2.8, 0, -6, -4, 0.55)))
    body = box(-6.4, 6.4, -4.2, 4.2, 0, 11.5)
    clips = U(box(-6.9, -6.4, -2, 2, 3.6, 7), box(6.4, 6.9, -2, 2, 3.6, 7))
    terms = U(box(-0.4, 0.4, -3.5, -1.5, 11.5, 17.5), box(-0.4, 0.4, 1.5, 3.5, 11.5, 17.5))
    return {"black": (U(flange, rock, body, clips), "#151515"), "mark": (mark, "#f4f4f4"),
            "terms": (terms, "#c0c4c8")}


# --------------------------------------------------------------------- fasteners
def m4x12_csk():
    """ISO 10642 M4x12. Origin: centre of the head top face, shank along +z."""
    head = cq.Workplane("XY").add(cq.Solid.makeCone(4.0, 2.0, 2.0))
    head = head.cut(cq.Workplane("XY").polygon(6, 2.5/0.866).extrude(1.6).translate((0, 0, -0.01)))
    return {"steel": (head.union(cyl(0, 0, 1.9, 12.0, 1.95)), "#3a3d41")}


def m4_insert():
    """M4 heat-set insert OD 5.5 x 8.1. Origin: centre of the flush end, body along +z."""
    b = cyl(0, 0, 0, 8.1, 2.6).cut(cyl(0, 0, -0.1, 8.2, 2.0))
    knurl = cq.Workplane("XY").workplane(offset=1.0).polygon(12, 5.5).extrude(2.2).cut(cyl(0, 0, 0, 9, 2.0))
    knurl2 = cq.Workplane("XY").workplane(offset=4.6).polygon(12, 5.5).extrude(2.2).cut(cyl(0, 0, 0, 9, 2.0))
    return {"brass": (U(b, knurl, knurl2), "#c8a24a")}


def pan_screw(d, L, dk, k):
    """Pan-head self-tapping screw. Origin: centre of the head underside; head on -z, shank +z."""
    head = cyl(0, 0, -k, 0, dk/2).edges("<Z").fillet(k*0.45)
    head = head.cut(box(-dk/2, dk/2, -0.35, 0.35, -k-0.1, -k*0.45)).cut(box(-0.35, 0.35, -dk/2, dk/2, -k-0.1, -k*0.45))
    return {"steel": (head.union(cyl(0, 0, 0, L, d/2)), "#3a3d41")}


def rubber_foot():
    """10 x 2.5 mm bumper. Origin: centre of the flat (adhesive) face, dome on -z."""
    return {"rubber": (cyl(0, 0, -2.5, 0, 5.0).faces("<Z").edges().fillet(1.2), "#2a2a2a")}


CATALOG = {
    "arduino_uno_r4_wifi": arduino_uno_r4_wifi, "lcd2004_i2c": lcd2004_i2c, "rc522": rc522,
    "keypad_4x4_hard": keypad_4x4_hard, "led5_red": lambda: led5("#e8352e"),
    "led5_green": lambda: led5("#2fbf4a"), "led5_blue": lambda: led5("#2f6bff"),
    "buzzer12": buzzer12, "battery_2x18650": battery_2x18650, "charge_board_2s": charge_board_2s,
    "rocker_kcd11": rocker_kcd11, "m4x12_csk": m4x12_csk, "m4_insert": m4_insert,
    "m3x6_pan": lambda: pan_screw(2.5, 6.0, 5.5, 2.1), "m25x6_pan": lambda: pan_screw(2.0, 6.0, 4.5, 1.75),
    "rubber_foot": rubber_foot,
}
