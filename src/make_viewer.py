"""
Build the interactive 3D viewer (docs/index.html) from the assembly.
Run after assembly.py:   python src/make_viewer.py --build build --out docs/index.html
The page loads three.js from cdnjs, so it works on GitHub Pages (Settings -> Pages -> /docs).
"""
import argparse, base64, collections, json, os, tempfile
import cadquery as cq
import enclosure as E
import components as C
import assembly as A

HERE = os.path.dirname(os.path.abspath(__file__))
METAL = {"#c9ced3", "#c0c4c8", "#3a3d41", "#c8a24a", "#d4af37", "#b7bcc2"}


def stl_b64(shape, tol):
    fd, p = tempfile.mkstemp(suffix=".stl"); os.close(fd)
    cq.exporters.export(cq.Workplane().add(shape), p, tolerance=tol, angularTolerance=0.25, opt={"ascii": False})
    d = base64.b64encode(open(p, "rb").read()).decode(); os.remove(p)
    return d


def main(build_dir, out):
    meshes, legend = [], collections.OrderedDict()
    fs = cq.importers.importStep(f"{build_dir}/parts/front_shell.step").val()
    bc = cq.importers.importStep(f"{build_dir}/parts/back_cover.step").val()
    meshes.append(dict(id="front_shell", color="#e6e8ea", side="front", kind="body", data=stl_b64(fs, 0.05)))
    meshes.append(dict(id="back_cover", color="#7f8a94", side="cover", kind="body", data=stl_b64(bc, 0.05)))
    legend["Front shell"] = ["#e6e8ea", 1]; legend["Back cover"] = ["#7f8a94", 1]
    name = E.panel_wp(0.0).center(*E.NAME_C).text(E.NAME, E.NAME_SIZE, -(E.NAME_DEPTH-0.1), combine=False,
                                                  fontPath=E.NAME_FONT, halign="center", valign="center").val()
    mark = E.base_wp(0.0).text(E.MARK, E.MARK_SIZE, -(E.MARK_DEPTH-0.1), combine=False, fontPath=E.NAME_FONT,
                               halign="center", valign="center").val()
    meshes.append(dict(id="name_fill", color="#24313b", side="front", kind="deco", data=stl_b64(name, 0.02)))
    meshes.append(dict(id="mark_fill", color="#24313b", side="front", kind="deco", data=stl_b64(mark, 0.02)))
    cache = {}
    for inst, key, loc, side in A.placements():
        g = cache.setdefault(key, C.CATALOG[key]())
        tol = 0.03 if key in ("keypad_4x4_hard", "lcd2004_i2c") else 0.08
        for grp, (wp, col) in g.items():
            meshes.append(dict(id=f"{inst}__{grp}", color=col, side=side, kind="part", metal=col in METAL,
                               data=stl_b64(wp.val().moved(loc), tol)))
        lab = A.LABELS[key]
        if lab in legend:
            legend[lab][1] += 1
        else:
            legend[lab] = [list(g.values())[0][1], 1]
    tpl = open(os.path.join(HERE, "viewer_template.html")).read()
    page = (tpl.replace("/*MESHES*/[]", json.dumps(meshes))
               .replace("/*LEGEND*/[]", json.dumps([[k, v[0], v[1]] for k, v in legend.items()])))
    html = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<style>:root{color-scheme:light}body{margin:0;font:14px system-ui,sans-serif}'
            '[hidden]{display:none!important}</style></head><body>\n' + page + '\n</body></html>\n')
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    open(out, "w").write(html)
    print(f"wrote {out} ({len(html)//1024} KB, {len(meshes)} meshes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", default="build")
    ap.add_argument("--out", default="docs/index.html")
    a = ap.parse_args()
    main(a.build, a.out)
