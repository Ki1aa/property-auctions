"""Ad-hoc: pick 16-item sample of Tyumen lots from the local OpenData union.

This is a one-off reconnaissance helper; it does not touch the DB.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "data" / "raw" / "torgi_opendata_tyumen_union.json"
OUT = ROOT / "data" / "raw" / "_sample_hrefs_tmp.json"

random.seed(42)
data = json.loads(SRC.read_text(encoding="utf-8"))
items = data["items"]

notices_zk = [i for i in items if i.get("documentType") == "notice" and i.get("biddTypeCode") == "ZK"]
notices_other = [i for i in items if i.get("documentType") == "notice" and i.get("biddTypeCode") != "ZK"]
cancels = [i for i in items if i.get("documentType") == "noticeCancel"]

random.shuffle(notices_zk)
random.shuffle(notices_other)
random.shuffle(cancels)

sample = notices_zk[:12] + notices_other[:3] + cancels[:1]
print(f"sample size: {len(sample)}")
print("sample regNums and biddType:")
for i in sample:
    src = (i.get("_source_file") or "")[5:13]
    print(
        f"  {i['regNum']:25}  {i['biddTypeCode']:18}  {i['documentType']:12}  "
        f"estate={i.get('subjectEstateCode')}/right={i.get('subjectRightHolderCode')}  src={src}"
    )

minimal_keys = (
    "regNum",
    "href",
    "documentType",
    "biddTypeCode",
    "subjectEstateCode",
    "subjectRightHolderCode",
    "publishDate",
    "bidderOrgCode",
    "rightHolderCode",
    "ownershipFormsCode",
    "_source_file",
)
OUT.write_text(
    json.dumps([{k: i.get(k) for k in minimal_keys} for i in sample], ensure_ascii=False, indent=2),
    encoding="utf-8",
)
print(f"saved sample list to {OUT.relative_to(ROOT)}")
