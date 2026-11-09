"""Source-bound nine-method tables; bind interpretation only after actual viewing."""

import argparse
import csv
import shutil

from directional_trial_protocol import read, ref, save
from publish_cfa_innovation_wave import EVIDENCE, REPORT, STAGE
from review_cfa_innovation_wave import review_plan, source_guard
from spatial_trial_protocol import read as read_any
from train_cfa_innovation_wave import MODES, REPO, ROOT


def prepare():
    plan = review_plan()
    source_guard(plan)
    assert not (ROOT / "report-source-v1.json").exists()
    runner = ROOT / "report-tables-worker-v1.py"
    shutil.copyfile(__file__, runner)
    previous = (
        REPO / ".cache/quality-20261108/V195-directional-response-trial-v1/report-bindings-v1.json"
    )
    save(
        ROOT / "report-source-v1.json",
        {
            "runner": ref(runner),
            "training_plan": ref(ROOT / "plan-v1.json"),
            "previous_row_definitions": ref(previous),
            "scope": "Use14previousmetricrowdefinitions/unitswithoutoldnumericvalues. Allnewtablecellscomefromcompleted9methodpairedmeans;independentfinalverifierrechecks126main+48directioncells. Interpretationisrequiredafteractualviewingandnotpredetermined.",
        },
    )
    print("Prepared9method/14metric/16direction-row table helper")


def guard():
    plan = review_plan()
    source_guard(plan)
    seal = read(ROOT / "report-source-v1.json")
    assert seal["runner"] == ref(__file__) and seal["training_plan"] == ref(ROOT / "plan-v1.json")
    assert ref(seal["previous_row_definitions"]["path"]) == seal["previous_row_definitions"]
    return plan, seal


def tables():
    plan, seal = guard()
    assert STAGE.exists() and EVIDENCE.is_dir()
    paired = read_any(ROOT / "paired-comparisons-v1.json.gz")
    assert len(paired["methods"]) == 9 and len(paired["table_rows"]) == 122
    assert read(ROOT / "quality-audit-v1.json")["status"].startswith("pass-V198-two-endpoint")
    previous = read(seal["previous_row_definitions"]["path"])
    definitions = previous["cells"]
    assert len(definitions) == 14
    methods = paired["methods"]
    labels = {
        "V183-coherent-pair-EMA": "V183 EMA",
        "V187-pooled-wave-EMA": "V187 EMA",
        "V195-whole-response-EMA": "V195 Whole EMA",
    }
    labels.update(
        {
            f"V197-{mode}-wave-{e}": f"V197 {mode} {e}"
            for mode in ["RAW", "innovation"]
            for e in ["raw", "EMA"]
        }
    )
    for mode in MODES:
        for endpoint, method in plan["methods"][mode].items():
            labels[method] = "CFA " + endpoint
    core = [
        "| Metric | Cases | " + " | ".join(labels[m] for m in methods) + " |",
        "| --- | ---: | " + " | ".join(["---:"] * 9) + " |",
    ]
    bindings = []
    for index, definition in enumerate(definitions):
        matches = [
            r
            for r in paired["table_rows"]
            if [r[k] for k in ["kind", "condition", "cohort", "field"]] == definition["key"]
        ]
        assert len(matches) == 1
        source = matches[0]
        cells = []
        for method in methods:
            cell = format(source["values"][method] * definition["scale"], ".9g")
            cells.append(cell)
            bindings.append(
                {
                    **{k: source[k] for k in ["kind", "condition", "cohort", "field"]},
                    "row": index,
                    "method": method,
                    "scale": definition["scale"],
                    "format": ".9g",
                    "display": cell,
                }
            )
        core.append(f"| {definition['label']} | {source['cases']} | " + " | ".join(cells) + " |")
    path = ROOT / "report-core-table-v1.md"
    with path.open("x") as f:
        f.write("\n".join(core) + "\n")
    direction = read(ROOT / "directional-breakdown-v1.json")
    indexed = {
        (r["id"], r["method"]): r for r in direction["rows"] + direction["previous_context_rows"]
    }
    assert len(indexed) == 16
    direction_methods = (
        ["V187-pooled-wave-EMA", "V195-whole-response-EMA"]
        + [f"V197-{mode}-wave-{e}" for mode in ["RAW", "innovation"] for e in ["raw", "EMA"]]
        + [m for mode in MODES for m in plan["methods"][mode].values()]
    )
    text = [
        "| Example | State | Whole (% GT) | Region A (% GT) | Region B (% GT) |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    directional = []
    for case_id in sorted({key[0] for key in indexed}):
        for method in direction_methods:
            row = indexed[case_id, method]
            cells = []
            number = len(text) - 2
            for metric, value in [
                ("whole", row["whole_template_gain"]),
                ("regionA", row["sectors"][0]["gain"]),
                ("regionB", row["sectors"][1]["gain"]),
            ]:
                cell = format(value * 100, ".7f")
                cells.append(cell)
                directional.append(
                    {
                        "row": number,
                        "id": case_id,
                        "method": method,
                        "metric": metric,
                        "format": ".7f",
                        "display": cell,
                    }
                )
            text.append(
                "| "
                + case_id.split("seed")[1][:10]
                + " | "
                + labels[method]
                + " | "
                + " | ".join(cells)
                + " |"
            )
    with (ROOT / "report-direction-table-v1.md").open("x") as f:
        f.write("\n".join(text) + "\n")
    with (EVIDENCE / "metrics-table-v1.csv").open("x", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["kind", "condition", "cohort", "field", "cases"] + methods)
        for row in paired["table_rows"]:
            writer.writerow(
                [row[k] for k in ["kind", "condition", "cohort", "field", "cases"]]
                + [row["values"][m] for m in methods]
            )
    save(
        ROOT / "report-table-values-v1.json",
        {
            "core_numeric_bindings": bindings,
            "direction_numeric_bindings": directional,
            "direction_method_labels": labels,
            "core_table": ref(path),
            "direction_table": ref(ROOT / "report-direction-table-v1.md"),
            "metric_CSV": ref(EVIDENCE / "metrics-table-v1.csv"),
            "paired": ref(ROOT / "paired-comparisons-v1.json.gz"),
            "directional": ref(ROOT / "directional-breakdown-v1.json"),
            "source": ref(__file__),
        },
    )
    print("Generated1098CSVcells/126maincells/48directioncells;nointerpretationdeclared")


def bind(interpretation):
    guard()
    assert interpretation and interpretation.strip()
    assert read(ROOT / "native-viewing-completion-v1.json")["indices"] == list(range(60))
    values = read(ROOT / "report-table-values-v1.json")
    for key in ["core_table", "direction_table", "metric_CSV", "paired", "directional"]:
        assert ref(values[key]["path"]) == values[key]
    for name in ["report-core-table-v1.md", "report-direction-table-v1.md"]:
        assert (ROOT / name).read_text().strip() in REPORT.read_text()
    save(
        ROOT / "report-bindings-v1.json",
        {
            **values,
            "report": ref(REPORT),
            "interpretation": interpretation,
            "actual_viewing": ref(ROOT / "native-viewing-completion-v1.json"),
        },
    )
    print("Boundcompletedreportto126main/48direction/1098CSVcellsandactualviewing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["prepare", "tables", "bind"])
    parser.add_argument("--interpretation")
    args = parser.parse_args()
    if args.phase == "prepare":
        prepare()
    elif args.phase == "tables":
        tables()
    else:
        bind(args.interpretation)
