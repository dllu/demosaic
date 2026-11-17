"""Verify published evidence bytes and seal omitted preparer/failure aliases."""
import hashlib
import json
import tarfile
import shutil
from pathlib import Path
from demosaic.experiments.artifacts import reference,read_json,write_json
repo=Path.cwd();root=repo/'.cache/experiments/full-corpus-control10k-review-v1';out=repo/'docs/results/full-corpus-control10k-review-v1'
verified=0
for directory in [out,repo/'docs/results/full-corpus-checkpoint-cpu-recovery-v1']:
    publication=read_json(directory/'publication.json')
    assert reference(publication['archive']['path'])==publication['archive']
    with tarfile.open(publication['archive']['path'],'r:gz')as archive:
        assert len(archive.getmembers())==len(publication['members'])
        for member in publication['members']:
            binding=member['source'];data=archive.extractfile(member['member']).read()
            assert hashlib.sha256(data).hexdigest()==binding['sha256']
            assert reference(binding['path'])==binding
            verified+=1
manifest=read_json(repo/'docs/images/full-corpus-control10k-review-v1/manifest.json')
for row in manifest['images']:
    assert reference(row['image']['path'])==row['image']
    assert row['image']['sha256']==row['original_image']['sha256']
a=root/'training-prefix-v1/source-crop-resumed6001-10000.jsonl';b=root/'training-prefix-v2/source-crop-resumed6001-10000.jsonl'
assert a.read_bytes()==b.read_bytes()
addendum=out/'source-addendum';addendum.mkdir()
sources=[]
for source in [repo/'.cache/prepare-full-corpus-control10k-review-v1.py',repo/'.cache/prepare-full-corpus-control10k-review-v1.log',Path(__file__).resolve()]:
    dest=addendum/source.name;shutil.copyfile(source,dest);assert reference(dest)['sha256']==reference(source)['sha256'];sources.append({'original':reference(source),'published':reference(dest)})
write_json(out/'verification-addendum.json',{'producer':reference(__file__),'verified_archive_members':verified,'verified_native_PNGs':len(manifest['images']),
 'source_addendum':sources,'failed_coverage_v1_snapshot':reference(a),'archived_final_snapshot':reference(b),'failed_snapshot_bytes_identical_to_archived_snapshot':True,
 'scope':'Independent archived-byte/SHA/current-source and all54 original/published PNG verification. Original failing coverage prefix retained locally and byte-identical to archived final prefix. Adds original preparer source/log without changing sealed publication receipts. No neural/RAW/noise/optimizer calls.'})
print('Verified',verified,'archive members,54 original PNGs; preserved preparer/failure aliases')
