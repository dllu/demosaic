"""Build a local, offline viewer of existing native comparison panels."""

import argparse
import html
import json
from pathlib import Path
from urllib.parse import quote

from PIL import Image

TEMPLATE = r"""<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Native denoising comparisons</title>
<style>
*{box-sizing:border-box}body{margin:24px;background:#f4f4f1;color:#202321;font:14px/20px system-ui,sans-serif}
h1{font-size:24px;line-height:32px;margin:0 0 12px}p{max-width:960px;margin:8px 0 16px}
.controls{display:flex;flex-wrap:wrap;align-items:end;gap:12px;margin:16px 0}
label{display:block;font-size:12px}select,button{display:block;max-width:100%;font:14px/20px system-ui;padding:6px;border:1px solid #969c95;background:white;border-radius:3px;color:inherit}
#case{width:720px}button{cursor:pointer}button:focus-visible,select:focus-visible{outline:3px solid #317f66;outline-offset:2px}
.cards{display:flex;flex-wrap:wrap;align-items:start;gap:16px;margin:20px 0}
.card{width:178px;flex-shrink:0;padding:8px;border:1px solid #bbbfb8;background:white}
.title{height:40px;font-size:12px;line-height:20px;overflow:hidden;margin:0 0 8px}
.crop{position:relative;width:160px;height:160px;overflow:hidden;background:#777}
.crop img{position:absolute;max-width:none!important;width:auto;height:auto;display:block}
#metadata,#checkpoint{white-space:pre-wrap;overflow-wrap:anywhere;font:12px/20px ui-monospace,monospace;max-width:1100px}
.badge{font-weight:600;color:#216a50}a{color:#216a50}footer{margin-top:24px}
</style>
<h1>Denoising at 100%</h1>
<p>Each crop is 160 × 160 native pixels. Compare A and B side by side, then use
<strong>Flip A/B</strong> or press <strong>F</strong> to compare them in the same position.
Exposure and contrast stay fixed for every method within a case.</p>
<label for="case">Case and display</label><select id="case"></select>
<div class="controls"><div><label for="method-a">A</label><select id="method-a"></select></div>
<div><label for="method-b">B</label><select id="method-b"></select></div>
<button id="previous" type="button">Previous case</button><button id="next" type="button">Next case</button>
<button id="flip" type="button">Flip A/B · F</button></div>
<div id="metadata"></div><div class="cards" id="cards"></div>
<div class="badge" id="flip-status" role="status" aria-live="polite"></div><div id="checkpoint"></div>
<p>Constructed targets are labeled exact GT. Real ISO100/AHD/JPEG references differ in
capture or processing; they are qualitative references, not exact GT.</p>
<footer><a href="manifest-v1.json">Source, ROI, noise and checkpoint manifest</a> ·
<a href="../../__REPORT__">Report and limitations</a></footer>
<script id="native-data" type="application/json">__DATA__</script>
<script>
'use strict';
const data=JSON.parse(document.getElementById('native-data').textContent);
const byId=id=>document.getElementById(id), picker=byId('case'), a=byId('method-a'), b=byId('method-b');
let showingB=true;
function options(select,labels,value){select.replaceChildren(...labels.map((label,index)=>{const o=document.createElement('option');o.value=label;o.textContent=label;return o}));select.value=labels.includes(value)?value:labels[0]}
data.cases.forEach((row,index)=>{const o=document.createElement('option');o.value=index;o.textContent=`${index+1}. ${row.id} · contrast ${row.contrast} · exposure ${row.exposure}`;picker.append(o)});
function card(title,label,id){
 const row=data.cases[Number(picker.value)],panel=row.panels.find(p=>p.label===label);if(!panel)return;
 const box=document.createElement('section');box.className='card';const heading=document.createElement('div');heading.className='title';heading.textContent=`${title}: ${label}`;
 const crop=document.createElement('div');crop.className='crop';crop.dataset.panel=label;crop.dataset.testid=id;
 const picture=document.createElement('img');picture.src=row.image;picture.alt=label;picture.style.left=`${-panel.xywh[0]}px`;picture.style.top=`${-panel.xywh[1]}px`;
 crop.append(picture);box.append(heading,crop);byId('cards').append(box);
}
function render(){
 const row=data.cases[Number(picker.value)];byId('cards').replaceChildren();
 card('Noisy',row.panels[0].label,'noisy');card('A',a.value,'a');card('B',b.value,'b');card('Flip',showingB?b.value:a.value,'flip');
 const reference=row.panels.find(p=>p.label==='Exact constructed GT')||row.panels.find(p=>p.label==='ISO100 AHD, not GT');if(reference)card('Reference',reference.label,'reference');
 byId('flip-status').textContent=`Flip is showing ${showingB?'B':'A'}: ${showingB?b.value:a.value}`;
 byId('metadata').textContent=`${row.id}\nROI [${row.roi.join(', ')}] · exposure ${row.exposure} · contrast ${row.contrast}\nAnchor [${row.anchor.join(', ')}]`;
 const descriptions=[a.value,b.value].map(label=>data.checkpoints[label]?`${label} checkpoint SHA256 ${data.checkpoints[label]}`:`${label}: retained source panel; see manifest`);byId('checkpoint').textContent=descriptions.join('\n');
}
function selectCase(){const row=data.cases[Number(picker.value)],labels=row.panels.map(p=>p.label),previousA=a.value,previousB=b.value;
 const latest=row.predictions.find(label=>label.endsWith('EMA'))||labels[labels.length-1];
 const prior=labels.filter(label=>/V[0-9]+[- ]EMA/.test(label)&&label!==latest).at(-1)||labels[1];
 options(a,labels,previousA||prior);options(b,labels,previousB||latest);showingB=true;render();}
picker.addEventListener('change',selectCase);a.addEventListener('change',render);b.addEventListener('change',render);
function flip(){showingB=!showingB;render()}byId('flip').addEventListener('click',flip);
document.addEventListener('keydown',e=>{if(e.code==='KeyF'&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement.tagName)){e.preventDefault();flip()}});
for(const [id,direction] of [['previous',-1],['next',1]])byId(id).addEventListener('click',()=>{picker.value=(Number(picker.value)+direction+data.cases.length)%data.cases.length;selectCase()});
selectCase();
</script></html>
"""


def build(manifest, output, report):
    data = json.loads(manifest.read_text())
    cases = []
    checkpoints = {}
    for item in data["images"]:
        if item["triplet"]:
            continue
        assert item["no_resize"]
        image = Path(item["image"]["path"])
        assert image.parent == output.parent and image.is_file()
        with Image.open(image) as pixels:
            width, height = pixels.size
        for panel in item["panels"]:
            x, y, w, h = panel["xywh"]
            assert w == h == 160 and 0 <= x <= width - w and 0 <= y <= height - h
        for label in item["predictions"]:
            if label.endswith(("-raw", "-EMA")):
                endpoint = label.rsplit("-", 1)[1]
                checkpoints[label] = data["checkpoints"][endpoint]["export"]["sha256"]
        cases.append(
            {
                "id": item["case"]["id"],
                "image": quote(image.name),
                "roi": item["ROI_xywh"],
                "anchor": item["anchor"],
                "exposure": item["exposure"],
                "contrast": item["contrast"],
                "panels": item["panels"],
                "predictions": list(item["predictions"]),
            }
        )
    assert cases
    payload = json.dumps({"cases": cases, "checkpoints": checkpoints}, ensure_ascii=True).replace(
        "<", "\\u003c"
    )
    rendered = TEMPLATE.replace("__DATA__", payload).replace("__REPORT__", html.escape(report))
    with output.open("x") as stream:
        stream.write(rendered)
    print(f"Built {len(cases)} native cases, without resampling pixels: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--report", required=True)
    args = parser.parse_args()
    build(
        args.manifest.resolve(),
        (args.output or args.manifest.with_name("native-viewer.html")).resolve(),
        args.report,
    )
