"""
Smart Attendance Deck enclosure  -  parametric CadQuery model (By Kwabs Studios)
Units: mm.  Global axes: X = width (left/right, +X is right seen from the front),
Y = depth (front y=0 -> back), Z = up.  Device sits on its base at Z=0.

Parts
  front_shell : sloped front panel + sides + base + top, open at the back
  back_cover  : flat back plate carrying the Arduino, 2S battery holder, charge board,
                USB-C + power switch, keyhole wall-mount slots
"""
import cadquery as cq, math, os

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# ---------------------------------------------------------------- main dimensions
W   = 200.0          # width
L   = 120.0          # sloped front-face height (along the slope)
ANG = 65.0           # front face angle from horizontal (deg)
D   = 85.0           # depth of front shell (base length)
T   = 2.5            # wall thickness
TB  = 3.5            # back plate thickness
R_EDGE  = 5.0        # body edge fillet
CH_FRONT = 3.0       # front-face perimeter chamfer
TAP_T = 1.8          # panel thickness over the RFID antenna

A  = math.radians(ANG)
HT = L*math.sin(A)          # overall height (~108.8)
YT = L*math.cos(A)          # where the top of the slope lands (~50.7)
N  = cq.Vector(0, -math.sin(A), math.cos(A))   # outward normal of front face

# ---------------------------------------------------------------- component data
# 20x4 LCD (2004A + I2C backpack)
LCD_PCB = (98.0, 60.0); LCD_HOLES = (93.0, 55.0); LCD_WIN = (77.0, 26.5)
LCD_BEZEL_H = 9.5           # metal bezel/glass height above PCB -> standoff height
LCD_C = (-38.0, 84.0)       # (u, v) centre on front face
# RC522 RFID (landscape, header pins on the right-hand short edge)
RFID = (60.0, 39.0); RFID_C = (-45.0, 30.0)
# 4x4 hard-plastic matrix keypad (8-pin): flange sits behind the panel, raised key
# plateau pokes through a cut-out. Published sizes vary by seller -> measure yours.
KEY_C = (54.0, 51.5)            # (u, v) centre on front face
KP_FLANGE = (68.0, 66.0)        # base plate W x H
KP_HOLES = (60.0, 58.0)         # corner hole spacing (c-c)
KP_HOLE_D = 2.0
KP_PLATEAU = (58.0, 56.0); KP_PLATEAU_R = 6.0   # raised key area W x H, corner radius
KP_BACK = 3.5                   # back of PCB to front of flange
KP_TOTAL = 10.0                 # back of PCB to top of keys
KP_KEYS_PROUD = 3.5             # keys stand this far above the plateau
KP_CLEAR = 0.4                  # clearance per side around the plateau
KP_PIN_D = 1.8; KP_PIN_L = KP_BACK + 1.5   # locating / heat-stake pins
# Status LEDs (5 mm) and buzzer grille
LED_U = (28.0, 43.0, 58.0); LED_V = 94.0; LED_D = 5.2
BUZ_C = (82.0, 94.0); BUZ_ID = 12.4
# Name plate: engraved into the top band of the front face (prints cleanly face-down)
NAME = "Smart Attendance Deck"; NAME_SIZE = 8.0; NAME_DEPTH = 0.6; NAME_C = (0.0, 108.5)
NAME_FONT = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
# Maker's mark: engraved on the underside (base), between the rubber feet
MARK = "By Kwabs Studios"; MARK_SIZE = 8.0; MARK_DEPTH = 0.6; MARK_C = (0.0, 43.0)


def base_wp(z=0.0):
    """Workplane on the underside, normal pointing down; text reads correctly when
    the unit is tipped onto its back and the base is viewed, top of letters toward the front."""
    return cq.Workplane(cq.Plane(origin=(MARK_C[0], MARK_C[1], z), xDir=(1, 0, 0), normal=(0, 0, -1)))

# back cover parts (global x, z)
ARD_ORIGIN = (26.0, 15.0)   # lower-left corner of UNO R4 (seen from inside)
ARD_HOLES  = [(13.97, 2.54), (15.24, 50.8), (66.04, 7.62), (66.04, 35.56)]
ARD_STANDOFF = 6.0
BAT_IN = (78.0, 42.0)       # 2 x 18650 series holder (77 x 41 x 20) + clearance
BAT_ORIGIN = (-94.4, 15.6)  # inner lower-left corner of tray
USB_C = (-4.0, 22.0); USB_SIZE = (9.6, 3.8)
SW_C = (13.0, 22.0); SW_SIZE = (13.2, 8.8)   # KCD11-style mini rocker
KEYHOLE_X = 45.0; KEYHOLE_Z = 78.0
BOSS_POS = [(sx*93.0, z) for sx in (-1, 1) for z in (7.0, HT-7.0)]
BOSS_D = 10.0; BOSS_LEN = 14.0; INSERT_D = 5.6; INSERT_DEPTH = 9.5   # M4 heat-set


def panel_wp(offset=0.0):
    """Workplane on the front face; local (u, v) -> global (u, v*cosA, v*sinA)
    shifted by offset along the outward normal (negative = inwards)."""
    o = N*offset
    return cq.Workplane(cq.Plane(origin=(o.x, o.y, o.z), xDir=(1, 0, 0), normal=N.toTuple()))


def back_wp(y, outward=False):
    """Workplane in a plane y=const; local (x, y) -> global (x, z).
    extrude(+) goes towards the front (-Y) unless outward=True."""
    if outward:
        return cq.Workplane(cq.Plane(origin=(0, y, 0), xDir=(-1, 0, 0), normal=(0, 1, 0)))
    return cq.Workplane(cq.Plane(origin=(0, y, 0), xDir=(1, 0, 0), normal=(0, -1, 0)))


def outer_body():
    prof = (cq.Workplane("YZ").polyline([(0, 0), (YT, HT), (D, HT), (D, 0)]).close()
            .extrude(W/2, both=True))
    prof = prof.edges("|Y").fillet(R_EDGE)
    prof = prof.faces(cq.selectors.DirectionMinMaxSelector(N, True)).edges().chamfer(CH_FRONT)
    return prof


def back_outline(wp, inset=0.0):
    r = max(R_EDGE - inset, 0.5)
    return wp.center(0, HT/2).rect(W-2*inset, HT-2*inset).val(), r


def rrect(wp, w, h, r):
    return wp.sketch().rect(w, h).vertices().fillet(r).finalize()


# ================================================================= FRONT SHELL
def front_shell():
    body = outer_body()
    shell = body.faces(">Y").shell(-T)

    # ---- internal features (added, then clipped to the outer envelope)
    adds = []
    ins = -T + 0.3                          # start slightly inside the wall to fuse
    # LCD standoffs
    pts = [(LCD_C[0]+sx*LCD_HOLES[0]/2, LCD_C[1]+sy*LCD_HOLES[1]/2) for sx in (-1, 1) for sy in (-1, 1)]
    adds.append(panel_wp(ins).pushPoints(pts).circle(3.0).extrude(-(LCD_BEZEL_H+0.3)))
    # RC522 slide-in cradle (rails on top, bottom, left; open on the header side)
    bu0 = RFID_C[0]-RFID[0]/2-0.5; bu1 = RFID_C[0]+RFID[0]/2
    bv0 = RFID_C[1]-RFID[1]/2-0.5; bv1 = RFID_C[1]+RFID[1]/2+0.5
    rail_h = 2.4; rw = 1.6
    rails = (panel_wp(ins)
             .pushPoints([((bu0-rw+bu1)/2, bv1+rw/2), ((bu0-rw+bu1)/2, bv0-rw/2)])
             .rect(bu1-bu0+rw, rw).extrude(-(rail_h+0.3)))
    rails = rails.union(panel_wp(ins).center(bu0-rw/2, (bv0+bv1)/2)
                        .rect(rw, bv1-bv0+2*rw).extrude(-(rail_h+0.3)))
    lip_t = 1.2                               # lips at 1.2..2.4 mm off the inner face
    lips = (panel_wp(-T-1.2)
            .pushPoints([((bu0+bu1)/2-rw/2, bv1-0.75+0.8), ((bu0+bu1)/2-rw/2, bv0+0.75-0.8)])
            .rect(bu1-bu0+rw, 3.1).extrude(-lip_t))
    lips = lips.union(panel_wp(-T-1.2).center(bu0+0.75-0.8, (bv0+bv1)/2)
                      .rect(3.1, bv1-bv0).extrude(-lip_t))
    adds += [rails, lips]
    # keypad locating / heat-stake pins through the flange holes
    kp_holes = [(KEY_C[0]+sx*KP_HOLES[0]/2, KEY_C[1]+sy*KP_HOLES[1]/2) for sx in (-1, 1) for sy in (-1, 1)]
    adds.append(panel_wp(ins).pushPoints(kp_holes).circle(KP_PIN_D/2).extrude(-(KP_PIN_L+0.3)))
    # LED sleeves
    adds.append(panel_wp(ins).pushPoints([(u, LED_V) for u in LED_U]).circle(4.0).extrude(-5.3))
    # Buzzer ring
    adds.append(panel_wp(ins).center(*BUZ_C).circle(BUZ_ID/2+1.5).circle(BUZ_ID/2).extrude(-6.3))
    # M4 screw bosses (along Y)
    for (x, z) in BOSS_POS:
        adds.append(back_wp(D).center(x, z).circle(BOSS_D/2).extrude(BOSS_LEN))
    for a in adds:
        shell = shell.union(a.intersect(body))

    # ---- cuts
    cuts = []
    # LCD window
    cuts.append(rrect(panel_wp(1).center(*LCD_C), *LCD_WIN, 1.0).extrude(-(T+2)))
    # RFID thin zone (pocket from inside, runs past the open end so the board slides in)
    pk = rrect(panel_wp(-T).center((bu0+bu1+6)/2, (bv0+bv1)/2), bu1+6-bu0, bv1-bv0, 0.5)
    cuts.append(pk.extrude(T-TAP_T))
    # keypad plateau cut-out
    cuts.append(rrect(panel_wp(1).center(*KEY_C), KP_PLATEAU[0]+2*KP_CLEAR, KP_PLATEAU[1]+2*KP_CLEAR,
                      KP_PLATEAU_R+KP_CLEAR).extrude(-(T+2)))
    # LED holes
    cuts.append(panel_wp(1).pushPoints([(u, LED_V) for u in LED_U]).circle(LED_D/2).extrude(-(T+8)))
    # buzzer grille (hex pattern)
    gp = []
    p = 2.6
    for i in range(-3, 4):
        for j in range(-3, 4):
            u = i*p + (j % 2)*p/2; v = j*p*math.sqrt(3)/2
            if math.hypot(u, v) <= 5.3:
                gp.append((BUZ_C[0]+u, BUZ_C[1]+v))
    cuts.append(panel_wp(1).pushPoints(gp).circle(0.8).extrude(-(T+2)))
    # standoff pilot holes (M3 self-tapping)
    cuts.append(panel_wp(-T+0.6).pushPoints(pts).circle(1.3).extrude(-(LCD_BEZEL_H+1)))
    # heat-set insert holes
    for (x, z) in BOSS_POS:
        cuts.append(back_wp(D+0.01).center(x, z).circle(INSERT_D/2).extrude(INSERT_DEPTH))
    # rubber-foot recesses in the base
    feet = (cq.Workplane("XY").pushPoints([(sx*78, y) for sx in (-1, 1) for y in (14, 72)])
            .circle(5.25).extrude(1.0))
    cuts.append(feet)
    # engraved name
    cuts.append(panel_wp(0.01).center(*NAME_C)
                .text(NAME, NAME_SIZE, -(NAME_DEPTH+0.01), combine=False, fontPath=NAME_FONT,
                      halign="center", valign="center"))
    # engraved maker's mark on the base
    cuts.append(base_wp(-0.01).text(MARK, MARK_SIZE, -(MARK_DEPTH+0.01), combine=False,
                                     fontPath=NAME_FONT, halign="center", valign="center"))
    for c in cuts:
        shell = shell.cut(c)
    return shell


# ================================================================= BACK COVER
def back_cover():
    wp_o = back_wp(D)                      # inner face of plate is at y = D
    plate = (wp_o.center(0, HT/2).sketch().rect(W, HT).vertices().fillet(R_EDGE)
             .finalize().extrude(-TB))     # goes +Y (outwards)
    plate = plate.faces(">Y").edges().fillet(1.2)

    # locating rim inside the shell opening
    gap = 0.3
    rim = rrect(back_wp(D).center(0, HT/2), W-2*(T+gap), HT-2*(T+gap), R_EDGE-T-gap).extrude(4.0)
    rim = rim.cut(rrect(back_wp(D+0.1).center(0, HT/2), W-2*(T+gap+1.6), HT-2*(T+gap+1.6), 0.5).extrude(4.2))
    for (x, z) in BOSS_POS:
        rim = rim.cut(back_wp(D).center(x, z).circle(BOSS_D/2+1.2).extrude(5))
    cover = plate.union(rim)

    adds = []
    # Arduino UNO R4 WiFi standoffs
    ah = [(ARD_ORIGIN[0]+px, ARD_ORIGIN[1]+pz) for px, pz in ARD_HOLES]
    adds.append(back_wp(D+0.2).pushPoints(ah).circle(3.0).extrude(ARD_STANDOFF+0.2))
    # battery tray
    bw, bh = BAT_IN; bx = BAT_ORIGIN[0]+bw/2; bz = BAT_ORIGIN[1]+bh/2
    tray = (back_wp(D+0.2).center(bx, bz).rect(bw+3.2, bh+3.2).rect(bw, bh).extrude(8.2))
    for sx in (-20, 19):                  # zip-tie / strap slots through the long walls
        tray = tray.cut(back_wp(D).center(bx+sx, bz).rect(5, bh+6).extrude(2.2))
    adds.append(tray)
    # charge-board shelf under the USB-C (top-mount USB-C: centre 1.6 above PCB top)
    shelf_top = USB_C[1] - 1.6 - 1.6 - 0.2
    adds.append(back_wp(D+0.2).center(USB_C[0]+1, shelf_top-1).rect(18, 2).extrude(26.2))
    adds.append(back_wp(D+0.2).center(USB_C[0]+1-8, (shelf_top-2 + T)/2)   # gusset
                .rect(2, shelf_top-2-T).extrude(12.2))
    # keyhole housings
    for sx in (-1, 1):
        adds.append(back_wp(D+0.2).center(sx*KEYHOLE_X, KEYHOLE_Z+5.5).sketch()
                    .rect(13.4, 26.4).vertices().fillet(3).finalize().extrude(5.7))
    for a in adds:
        cover = cover.union(a)

    cuts = []
    # USB-C and switch openings
    cuts.append(rrect(back_wp(D+TB+1).center(*USB_C), *USB_SIZE, 1.6).extrude(TB+3))
    cuts.append(rrect(back_wp(D+TB+1).center(*SW_C), *SW_SIZE, 0.5).extrude(TB+3))
    # keyholes: dia 9 entry, 4.6 slot upward, head cavity behind
    for sx in (-1, 1):
        x = sx*KEYHOLE_X
        cuts.append(back_wp(D+TB+1).center(x, KEYHOLE_Z).circle(4.5).extrude(TB+1.1))
        cuts.append(back_wp(D+TB+1).center(x, KEYHOLE_Z+5.5).rect(4.6, 11).extrude(TB+1.1))
        cuts.append(back_wp(D+0.01).center(x, KEYHOLE_Z+5.5).sketch()
                    .rect(9.2, 20.2).vertices().fillet(4.5).finalize().extrude(3.5))
    # standoff pilot holes (M2.5 self-tapping)
    cuts.append(back_wp(D).pushPoints(ah).circle(1.05).extrude(ARD_STANDOFF+0.5))
    for c in cuts:
        cover = cover.cut(c)
    # countersunk M4 holes (from outside)
    csk = []
    for (x, z) in BOSS_POS:
        cyl = back_wp(D+TB+1).center(x, z).circle(2.25).extrude(TB+2)
        cone = cq.Solid.makeCone(4.3, 0.0, 4.3, pnt=cq.Vector(x, D+TB, z), dir=cq.Vector(0, -1, 0))
        csk += [cyl, cq.Workplane().add(cone)]
    for c in csk:
        cover = cover.cut(c)
    return cover


if __name__ == "__main__":
    fs = front_shell(); bc = back_cover()
    for n, s in (("front_shell", fs), ("back_cover", bc)):
        v = s.val()
        print(n, "valid", v.isValid(), "solids", len(s.solids().vals()),
              "vol cm3", round(v.Volume()/1000, 1), "bbox", v.BoundingBox().__dict__ if False else
              [round(q, 1) for q in (v.BoundingBox().xmin, v.BoundingBox().xmax, v.BoundingBox().ymin,
                                     v.BoundingBox().ymax, v.BoundingBox().zmin, v.BoundingBox().zmax)])
        cq.exporters.export(s, f"{n}.step")
        cq.exporters.export(s, f"{n}.stl", tolerance=0.05, angularTolerance=0.15)
