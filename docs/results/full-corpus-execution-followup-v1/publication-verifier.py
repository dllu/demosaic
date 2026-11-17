"""Verify sealed bytes and retain exact failed first-case output bindings."""
import hashlib
import shutil
import tarfile
from pathlib import Path
from demosaic.experiments.artifacts import read_json,reference,write_json
repo=Path.cwd();out=repo/'docs/results/full-corpus-execution-followup-v1';publication=read_json(out/'publication.json')
assert reference(publication['archive']['path'])==publication['archive']
with tarfile.open(publication['archive']['path'],'r:gz')as archive:
    assert len(archive.getmembers())==len(publication['members'])
    for member in publication['members']:
        data=archive.extractfile(member['member']).read();assert hashlib.sha256(data).hexdigest()==member['source']['sha256']
        assert reference(member['source']['path'])==member['source']
manifest=read_json(repo/'docs/images/training-execution-quality-v1/manifest.json')
for row in manifest['images']:
    assert reference(row['image']['path'])==row['image']
    assert row['image']['sha256']==row['original_image']['sha256']
failed=repo/'.cache/experiments/training-execution-quality-v1';current=repo/'.cache/experiments/training-execution-quality-v2';first=read_json(current/'collection/case-000.json');outputs=[]
for variant in first['variants']:
    old=failed/'collection'/variant['label']/'prediction-000.npy';binding=reference(old)
    assert binding['sha256']==variant['prediction']['sha256']
    outputs.append({'failed_original':binding,'completed_collection_first_case':variant['prediction'],'exact_file_bytes_match':True})
assert len(outputs)==6
source=out/'publication-verifier.py';shutil.copyfile(__file__,source)
write_json(out/'verification-addendum.json',{'publication':reference(out/'publication.json'),'verifier':reference(source),
 'archive_members_verified':len(publication['members']),'original_PNGs_verified':len(manifest['images']),
 'failed_v1_first_case_outputs':outputs,
 'scope':'Independent archived-byte/SHA/current-source and all60 original/published PNG checks. All six preserved failed-v1 first-case arrays are byte-identical to the corrected successful first case; failed log/source/plan preserved in archive. This does not mark the failed attempt complete or invent lost counters. Zero neural/RAW/noise/GPU/optimizer calls.'})
print('Verified',len(publication['members']),'archived files,60 PNGs and6 exact preserved failed-case arrays')
