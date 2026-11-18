"""Compare the preview and query scales in observed training and standing frames."""
import json
from pathlib import Path

import numpy as np

from demosaic.experiments.artifacts import checked, read_json, reference, write_json

HERE = Path(__file__).resolve().parent
RUN = HERE.parents[1]
REPO = RUN.parents[2]
STRIDES = (4,8,16,32)

def grid(native_hw, max_side):
    h,w = native_hw
    ph,pw = h//2,w//2
    reduction = min(1.0,max_side/max(ph,pw))
    return np.array([round(ph*reduction),round(pw*reduction)],dtype=float)

def ranges(values):
    return dict(zip(("min","p10","median","p90","max"),
                    np.quantile(np.asarray(values),[0,.1,.5,.9,1],axis=0).tolist(),strict=True))

def measure(native_hw, query_hw, max_side):
    query = np.array(query_hw,dtype=float)
    native = np.array(native_hw,dtype=float)
    ratio = grid(native_hw,max_side)/native
    return {
        "native_long_side":float(max(native)),
        "preview_long_side":float(max(grid(native_hw,max_side))),
        "native_pixels_per_preview_pixel_hw": (1/ratio).tolist(),
        "query_percent_native_area":float(100*query.prod()/native.prod()),
        "query_extent_in_preview_cells_hw": (query*ratio).tolist(),
        "query_extent_at_largest_stride_hw": (query*ratio/max(STRIDES)).tolist(),
        "native_pixels_per_largest_stride_hw": (max(STRIDES)/ratio).tolist(),
    }

def main():
    checkpoint = RUN/"plain-spatial-verified.json"
    verified = read_json(checkpoint)
    trace = checked(verified["observations"])
    rows = [json.loads(line) for line in trace.read_text().splitlines()]
    assert len(rows) == 4800 and len({row["source_id"] for row in rows}) == 4800
    train_plan = checked(read_json(checked(verified["completed"]))["plan"])
    plan = read_json(train_plan)
    queries = []
    for row in rows:
        assert row["native_hw"] == [2*v for v in row["scene_packed"]["shape"][-2:]]
        for _,_,width,height in row["boxes_xywh"]:
            queries.append(measure(row["native_hw"],(height,width),plan["preview_long_side"]))
    assert len(queries)==19200
    observed = {k:ranges([row[k] for row in queries]) for k in queries[0]}
    cache = REPO/".cache/gfx-qualitative-20231231"
    collected = RUN/"reviews/standing/plain/spatial/collection.json"
    assert read_json(collected)["checkpoint"] == verified["checkpoint"]
    standing_plan=checked(read_json(collected)["plan"])
    inputs = {}
    for capture,prefix in (("DSCF3879","main-"),("DSCF3842","mesh-")):
        meta, = cache.glob(f"*{capture}*metadata.json")
        shape = read_json(meta)["shape"]
        boxes = [box for row in read_json(collected)["records"] if row["id"].startswith(prefix)
                 for box in row["scene_box_xywh"]]
        sizes = {(b[3],b[2]) for b in boxes}
        assert len(sizes)==1
        inputs[capture] = {"metadata":reference(meta),"native_shape":shape,
             **measure(shape,next(iter(sizes)),read_json(standing_plan)["preview_long_side"])}
    write_json(HERE/"preview-scale.json",{
        "driver":reference(__file__),"training_checkpoint":reference(checkpoint),"training_plan":reference(train_plan),
        "training_observations":verified["observations"],"standing_collection":reference(collected),
        "preview_source":reference(REPO/"src/demosaic/scene_context.py"),
        "adapter_source":reference(REPO/"src/demosaic/scene_restoration.py"),
        "scope":"Actual ordinary training and standing camera geometry. Grid spacing is not the backbone's receptive field.",
        "training_scenes":len(rows),"queries":len(queries),"training_query_quantiles":observed,"standing":inputs
    })

if __name__=="__main__":
    main()
