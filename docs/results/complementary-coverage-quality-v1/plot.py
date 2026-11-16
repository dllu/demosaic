import json,pathlib,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
p=pathlib.Path('.cache/experiments/complementary-coverage-quality-v1');d=json.loads((p/'analysis.json').read_text())
fig,axes=plt.subplots(1,2,figsize=(11.5,4.5),layout='constrained')
categories=['added-only','inherited','neither'];groups=[next(r for r in d['groups'] if r['threshold_native_bins']==3 and r['state']=='ema' and r['profile']=='iso400' and r['placement']=='far' and r['category']==c) for c in categories]
x=np.arange(3)
for offset,key,color,label in [(-.18,'baseline_mean','#999999','V200 EMA'),(.18,'candidate_mean','#147d92','Complementary EMA')]:
 axes[0].bar(x+offset,[r['metrics']['weak_gain'][key]*100 for r in groups],width=.36,color=color,label=label)
axes[0].set_xticks(x,['New bank only\n32 views / 7 sources','Already in V200\n17 views / 4 sources','Neither\n15 views / 5 sources']);axes[0].set_ylabel('Signed weak increment response (% of exact GT)');axes[0].set_title('Weak-frequency proximity within 3 native DFT bins');axes[0].legend(frameon=False);axes[0].set_ylim(0,22)
axes[0].text(.02,.94,'Exact target response = 100%',transform=axes[0].transAxes,va='top',fontsize=9)
rows=[r for r in d['rows'] if r['profile']=='iso400' and r['placement']=='far']
for source in range(8):
 sub=[r for r in rows if r['source']==source]
 axes[1].scatter([r['weak_distance']['complementary'][2] for r in sub],[(r['candidate']['ema']['weak_gain']-r['baseline']['weak_gain'])*100 for r in sub],label=str(source),s=23,alpha=.75,color=plt.get_cmap('tab10')(source))
for limit,style in [(1,':'),(3,'--')]:axes[1].axvline(limit,color='#888888',ls=style,lw=1)
axes[1].axhline(0,color='#999999',lw=.8);axes[1].set_xscale('symlog',linthresh=1);axes[1].set_xlim(left=0);axes[1].set_xlabel('Nearest weak-fundamental distance (native DFT bins)');axes[1].set_ylabel('Complementary minus V200 weak response (points)');axes[1].set_title('Same 64 CFA/repeat views from eight sources');axes[1].legend(title='Source',ncol=4,frameon=False,fontsize=8,title_fontsize=8)
for ax in axes:ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
fig.suptitle('400 prior, far edge: new coverage coincides with small weak-response gains',fontsize=12)
folder=p/'figure-v2';folder.mkdir(exist_ok=False)
image=folder/'coverage-and-response.png';fig.savefig(image,dpi=160);plt.close(fig)
(folder/'figure.json').write_text(json.dumps({'image':{'path':str(image.resolve()),'sha256':hashlib.sha256(image.read_bytes()).hexdigest()},'analysis':{'path':str((p/'analysis.json').resolve()),'sha256':hashlib.sha256((p/'analysis.json').read_bytes()).hexdigest()},'script':{'path':str(pathlib.Path(__file__).resolve()),'sha256':hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()},'scope':'Descriptive selected groups and paired case differences; repeated views of eight sources, no significance or causal interpretation.'},indent=2)+'\n')
print('audit',d['audit'])
for profile in ['iso6400','iso1600','iso400']:
 for placement in ['near','far']:
  rows=[r for r in d['rows'] if r['profile']==profile and r['placement']==placement];close=[r for r in rows if r['weak_distance']['complementary'][2]<=1]
  print(profile,placement,'within1',len(close),'sources',len(set(r['source'] for r in close)),'conditionalweak%',np.mean([r['candidate']['ema']['weak_gain']*100 for r in close]) if close else None)
  o=next(x for x in d['overall'] if x['profile']==profile and x['placement']==placement);print('role0/1 coverage3',o['coverage']['3']['complementary'][:2])
