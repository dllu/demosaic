const fs=require('fs'),path=require('path');
const {firefox}=require('/home/dllu/.cache/uv/archive-v0/OL6JBkxJbE2O3Mwj/lib/python3.12/site-packages/playwright/driver/package');
(async()=>{
 const file=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
 if(fs.existsSync(out))throw new Error('Output exists');fs.mkdirSync(out,{recursive:true});
 const browser=await firefox.launch({executablePath:'/home/dllu/.cache/ms-playwright/firefox-1532/firefox/firefox',headless:true,firefoxUserPrefs:{'datareporting.policy.dataSubmissionEnabled':false,'toolkit.telemetry.enabled':false}});
 try{
  const page=await browser.newPage({viewport:{width:1240,height:900},deviceScaleFactor:1});
  const errors=[];page.on('pageerror',error=>errors.push(String(error)));
  await page.goto('file://'+file);
  const parsed=JSON.parse(await page.locator('#native-data').textContent());
  if(parsed.cases.length!==48||parsed.fixture!==false)throw new Error('Expected actual48case viewer,not fixture');
  if((await page.locator('h1').textContent()).includes('CPU LAYOUT FIXTURE'))throw new Error('Actual viewer has fixture heading');
  if(await page.locator('#method-a').inputValue()!=='V197-innovation-wave-EMA'||await page.locator('#method-b').inputValue()!=='V198-CFA-wave-EMA')throw new Error('Wrong default matched pair');
  const methods=['V187-pooled-wave-EMA','V195-whole-response-EMA','V197-RAW-wave-EMA','V197-innovation-wave-EMA','V198-CFA-wave-raw','V198-CFA-wave-EMA'];
  if(JSON.stringify(Object.keys(parsed.checkpoints).sort())!==JSON.stringify([...methods].sort()))throw new Error('Expected all six method checkpoints');
  await page.evaluate(async()=>{await Promise.all([...document.querySelectorAll('#cards img')].map(img=>img.decode()))});
  await page.screenshot({path:path.join(out,'screen-first.png'),fullPage:true});
  const records=[],metadata=[];
  for(let i=0;i<48;i++){
   await page.selectOption('#case',String(i));
   for(let pair=0;pair<methods.length;pair++){
    const a=methods[pair],b=methods[(pair+1)%methods.length];
    await page.selectOption('#method-a',a);await page.selectOption('#method-b',b);
    await page.evaluate(async()=>{await Promise.all([...document.querySelectorAll('#cards img')].map(img=>img.decode()))});
    const description=await page.locator('#checkpoint').textContent();
    for(const label of [a,b])if(!description.includes(label+': '+parsed.checkpoints[label]))throw new Error('Missing exact state metadata '+label);
    metadata.push({case:i,pair,a,b,description});
    for(const id of ['noisy','a','b','flip','reference']){
     const node=page.locator(`[data-testid="${id}"]`),rect=await node.boundingBox(),label=await node.getAttribute('data-panel');
     if(rect.width!==160||rect.height!==160||rect.x%1||rect.y%1)throw new Error('Non-native rectangle '+JSON.stringify(rect));
     if((id==='a'&&label!==a)||(id==='b'&&label!==b))throw new Error('Wrong rendered matched method');
     const panel=parsed.cases[i].panels.find(p=>p.label===label),name=`case-${String(i).padStart(2,'0')}-${pair}-${id}.png`;
     await node.screenshot({path:path.join(out,name)});
     records.push({case:i,pair,id,label,rect,panel:panel.xywh,source:path.resolve(path.dirname(file),decodeURIComponent(parsed.cases[i].image)),screenshot:path.join(out,name)});
    }
    const before=await page.locator('[data-testid="flip"]').getAttribute('data-panel');
    await page.click('#flip');const after=await page.locator('[data-testid="flip"]').getAttribute('data-panel');
    if(before===after)throw new Error('Click flip failed');await page.keyboard.press('f');
    if(await page.locator('[data-testid="flip"]').getAttribute('data-panel')!==before)throw new Error('F flip failed');
   }
  }
  await page.click('#next');if(await page.locator('#case').inputValue()!=='0')throw new Error('Next wrap failed');
  await page.click('#previous');if(await page.locator('#case').inputValue()!=='47')throw new Error('Previous wrap failed');
  if(errors.length)throw new Error(errors.join('\n'));
  fs.writeFileSync(path.join(out,'browser-records-v1.json'),JSON.stringify({status:'pass48actualcases-six-methods-both-selectors-metadata-and-native-rectangles',viewer:file,records,metadata,methods,default_pair:parsed.defaults,JS_errors:errors,browser:browser.version(),fixture_only_no_V198_quality:false},null,2)+'\n');
  process.stdout.write('PASS48actualcases/288six-method-pairs/1440native-crops/allstate-metadata/click-key-flip/navigation\n');
 }finally{await browser.close()}
})().catch(e=>{process.stderr.write(String(e.stack)+'\n');process.exitCode=1});
