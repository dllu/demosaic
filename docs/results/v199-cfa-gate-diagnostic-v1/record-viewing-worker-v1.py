import argparse,json,time
from pathlib import Path
from directional_trial_protocol import read,ref,save
root=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--sheets',type=int,nargs='+',required=True);p.add_argument('--notes',required=True);a=p.parse_args()
figures=read(root/'figures-v1.json');journal=root/'native-viewing-v1.jsonl'
events=[json.loads(s) for s in journal.read_text().splitlines()] if journal.exists() else []
seen={n for e in events for n in e['sheets']}
assert len(a.sheets)==len(set(a.sheets)) and set(a.sheets)<=set(range(12)) and not seen.intersection(a.sheets)
for n in a.sheets:assert ref(figures['sheets'][n]['image']['path'])==figures['sheets'][n]['image']
with journal.open('a') as stream:stream.write(json.dumps({'recorded_unix_UTC':time.time(),'sheets':a.sheets,'detail':'original','notes':a.notes,'source':ref(__file__)})+'\n')
seen.update(a.sheets)
if seen==set(range(12)):save(root/'native-viewing-completion-v1.json',{'status':'actually-viewed46-native-gate-diagnostic-figures-and8triplets-in12original-sheets','figures':ref(root/'figures-v1.json'),'journal':ref(journal),'indices':list(range(46)),'sheets':list(range(12)),'no_resize':True})
print('Recorded',a.sheets,'seen',len(seen),'/12')
