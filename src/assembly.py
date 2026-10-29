"""
Smart Attendance Deck - full assembly.

  python assembly.py            -> builds parts + components, checks clearances,
                                   writes the STEP assembly and per-part files
Outputs (relative to --out, default ./build):
  smart_attendance_deck_assembly.step   coloured STEP assembly (opens as .iam in Inventor)
  parts/front_shell.step, parts/back_cover.step
  components/<name>.step                each bought-in part in its own local frame
  print/front_shell.stl, print/back_cover.stl   oriented for printing
"""
import argparse, itertools, json, os, base64, math
import cadquery as cq
import enclosure as E
import components as C

X = cq.Vector(1, 0, 0)
UP = cq.Vector(0, math.cos(E.A), math.sin(E.A))      # up the front face


def panel_loc(u, v, off):
    o = X*u + UP*v + E.N*off
    return cq.Location(cq.Plane(origin=o.toTuple(), xDir=(1, 0, 0), normal=E.N.toTuple()))


def back_loc(x, z, y, inward=True):
    """Frame on a plane y=const: local x = global x, local y = global z,
    local +z toward the front (inward=True) or toward the back."""
    n = (0, -1, 0) if inward else (0, 1, 0)
    pl = cq.Plane(origin=(x, y, z), xDir=(1, 0, 0), normal=n)
    if not inward:      # keep local y = global z when the normal is flipped
        pl = cq.Plane(origin=(x, y, z), xDir=(-1, 0, 0), normal=n)
    return cq.Location(pl)


def placements():
    """(instance name, catalog key, location, side) - side: 'front' rides with the front
    shell, 'cover' rides with the back cover (used for the exploded view)."""
    P = []
    P.append(("lcd_20x4_i2c", "lcd2004_i2c", panel_loc(*E.LCD_C, -E.T), "front"))
    P.append(("rfid_rc522", "rc522", panel_loc(*E.RFID_C, -E.TAP_T), "front"))
    P.append(("keypad_4x4", "keypad_4x4_hard", panel_loc(*E.KEY_C, -E.T), "front"))
    for u, key in zip(E.LED_U, ("led5_red", "led5_green", "led5_blue")):
        P.append((key.replace("led5", "led"), key, panel_loc(u, E.LED_V, -E.T-5.0), "front"))
    P.append(("buzzer", "buzzer12", panel_loc(*E.BUZ_C, -E.T), "front"))
    lcd_holes = [(E.LCD_C[0]+sx*E.LCD_HOLES[0]/2, E.LCD_C[1]+sy*E.LCD_HOLES[1]/2)
                 for sx in (-1, 1) for sy in (-1, 1)]
    for i, (u, v) in enumerate(lcd_holes):
        loc = cq.Location(cq.Plane(origin=(X*u + UP*v + E.N*(-E.T-E.LCD_BEZEL_H-1.6)).toTuple(),
                                   xDir=(1, 0, 0), normal=E.N.toTuple()))
        P.append((f"screw_m3x6_lcd_{i+1}", "m3x6_pan", loc, "front"))
    for i, (sx, y) in enumerate([(sx, y) for sx in (-1, 1) for y in (14, 72)]):
        P.append((f"rubber_foot_{i+1}", "rubber_foot", cq.Location(cq.Vector(sx*78, y, 1.0)), "front"))
    for i, (x, z) in enumerate(E.BOSS_POS):
        P.append((f"insert_m4_{i+1}", "m4_insert", back_loc(x, z, E.D), "front"))

    ax, az = E.ARD_ORIGIN
    P.append(("arduino_uno_r4_wifi", "arduino_uno_r4_wifi", back_loc(ax, az, E.D-E.ARD_STANDOFF), "cover"))
    for i, (hx, hz) in enumerate(E.ARD_HOLES):
        loc = cq.Location(cq.Plane(origin=(ax+hx, E.D-E.ARD_STANDOFF-1.6, az+hz), xDir=(1, 0, 0), normal=(0, 1, 0)))
        P.append((f"screw_m25x6_arduino_{i+1}", "m25x6_pan", loc, "cover"))
    bx = E.BAT_ORIGIN[0]+E.BAT_IN[0]/2; bz = E.BAT_ORIGIN[1]+E.BAT_IN[1]/2
    P.append(("battery_2x18650", "battery_2x18650", back_loc(bx-38.5, bz-20.5, E.D), "cover"))
    shelf_top = E.USB_C[1]-1.6-1.6-0.2
    P.append(("charge_board_2s_usbc", "charge_board_2s",
              cq.Location(cq.Vector(E.USB_C[0]+1, E.D-12.4, shelf_top+0.05)), "cover"))
    P.append(("power_switch", "rocker_kcd11", back_loc(*E.SW_C, E.D+E.TB), "cover"))
    for i, (x, z) in enumerate(E.BOSS_POS):
        P.append((f"screw_m4x12_{i+1}", "m4x12_csk", back_loc(x, z, E.D+E.TB-0.2), "cover"))
    return P


LABELS = {"lcd2004_i2c": "20x4 LCD + I2C backpack", "rc522": "RC522 RFID reader",
          "keypad_4x4_hard": "4x4 hard keypad", "led5_red": "LED 5 mm red", "led5_green": "LED 5 mm green",
          "led5_blue": "LED 5 mm blue", "buzzer12": "Piezo buzzer 12 mm",
          "arduino_uno_r4_wifi": "Arduino UNO R4 WiFi", "battery_2x18650": "2x18650 holder + cells",
          "charge_board_2s": "2S USB-C charge board", "rocker_kcd11": "KCD11 rocker switch",
          "m4x12_csk": "M4x12 countersunk screw", "m4_insert": "M4 heat-set insert",
          "m3x6_pan": "M3x6 pan self-tapper", "m25x6_pan": "M2.5x6 pan self-tapper",
          "rubber_foot": "Rubber foot 10x2.5"}


def build(out, check=True, explode=0.0):
    os.makedirs(f"{out}/parts", exist_ok=True); os.makedirs(f"{out}/components", exist_ok=True)
    os.makedirs(f"{out}/print", exist_ok=True)
    fs = E.front_shell(); bc = E.back_cover()
    cq.exporters.export(fs, f"{out}/parts/front_shell.step")
    cq.exporters.export(bc, f"{out}/parts/back_cover.step")

    cache = {}
    def comp(key):
        if key not in cache:
            cache[key] = C.CATALOG[key]()
            a = cq.Assembly(name=key)
            for g, (wp, col) in cache[key].items():
                a.add(wp, name=g, color=cq.Color(col))
            a.export(f"{out}/components/{key}.step", write_pcurves=False)
        return cache[key]

    off = cq.Location(cq.Vector(0, explode, 0))
    assy = cq.Assembly(name="smart_attendance_deck")
    assy.add(fs, name="front_shell", color=cq.Color("#e6e8ea"))
    assy.add(bc, name="back_cover", color=cq.Color("#7f8a94"), loc=off if explode else cq.Location())
    placed = {}
    for name, key, loc, side in placements():
        groups = comp(key)
        sub = cq.Assembly(name=name)
        for g, (wp, col) in groups.items():
            sub.add(wp, name=f"{name}_{g}", color=cq.Color(col))
        L = off*loc if (explode and side == "cover") else loc
        assy.add(sub, loc=L)
        placed[name] = (key, L, side, groups)
    tag = "_exploded" if explode else ""
    assy.export(f"{out}/smart_attendance_deck_assembly{tag}.step", write_pcurves=False)

    report = None
    if check:
        report = []
        shells = {"front_shell": fs.val(), "back_cover": bc.val()}
        solids = {n: cq.Compound.makeCompound([wp.val() for wp, _ in g.values()]).moved(L)
                  for n, (k, L, s, g) in placed.items()}
        for n, s in solids.items():
            for pn, p in shells.items():
                v = s.intersect(p).Volume()
                if v > 0.05:
                    report.append((n, pn, round(v, 2)))
        for (a, sa), (b, sb) in itertools.combinations(solids.items(), 2):
            bb1, bb2 = sa.BoundingBox(), sb.BoundingBox()
            if (bb1.xmax < bb2.xmin or bb2.xmax < bb1.xmin or bb1.ymax < bb2.ymin or bb2.ymax < bb1.ymin
                    or bb1.zmax < bb2.zmin or bb2.zmax < bb1.zmin):
                continue
            v = sa.intersect(sb).Volume()
            if v > 0.05:
                report.append((a, b, round(v, 2)))
        v = fs.val().intersect(bc.val()).Volume()
        if v > 0.05:
            report.append(("front_shell", "back_cover", round(v, 2)))
    return fs, bc, placed, report


def export_print_stls(out, fs, bc):
    fsp = fs.rotate((0, 0, 0), (1, 0, 0), 180-E.ANG)
    fsp = fsp.translate((0, 0, -fsp.val().BoundingBox().zmin))
    bcp = bc.rotate((0, 0, 0), (1, 0, 0), -90)
    bcp = bcp.translate((0, 0, -bcp.val().BoundingBox().zmin))
    cq.exporters.export(fsp, f"{out}/print/front_shell.stl", tolerance=0.02, angularTolerance=0.1)
    cq.exporters.export(bcp, f"{out}/print/back_cover.stl", tolerance=0.02, angularTolerance=0.1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="build")
    ap.add_argument("--no-check", action="store_true")
    a = ap.parse_args()
    fs, bc, placed, rep = build(a.out, check=not a.no_check)
    build(a.out, check=False, explode=70.0)
    export_print_stls(a.out, fs, bc)
    if rep is not None:
        print("interference check:", "PASS - no overlaps" if not rep else "")
        for r in rep:
            print("  CLASH", *r)
    print("instances:", len(placed))
