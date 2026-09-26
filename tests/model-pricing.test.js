const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const apiSource = fs.readFileSync('web/js/api.js','utf8');
const appSource = fs.readFileSync('web/js/app.js','utf8');
function api(fetch){
  const sandbox={window:{location:{protocol:'http:',hostname:'localhost'},localStorage:{getItem:()=> 'test'}},fetch,URLSearchParams,console};
  sandbox.window.window=sandbox.window;
  vm.runInNewContext(apiSource,sandbox);
  return sandbox.window.TokenLedgerAPI;
}
test('pricing requests encode exact key, preserve decimal strings and report conflict',async()=>{
  let request;
  const a=api((url,opts)=>{request={url,opts}; return Promise.resolve({ok:false,status:409,json:()=>Promise.resolve({detail:'Price changed'})});});
  const r=await a.pricingCall('versions','POST',{input_per_million:'0.10',expected_revision:4},'or:vendor/a+b c');
  assert.match(request.url,/catalog_key=or%3Avendor%2Fa%2Bb%20c/);
  assert.equal(JSON.parse(request.opts.body).input_per_million,'0.10');
  assert.equal(r.ok,false); assert.equal(r.message,'Price changed');
});
test('backend null estimate never falls through latest prices; recorded zero wins',()=>{
  const source=appSource.slice(appSource.indexOf('function costOrNull('),appSource.indexOf('function isExcludedDepartment('));
  const ctx={state:{pricing:{m:{i:100,o:100}}},num:x=>Number(x)||0}; vm.createContext(ctx); vm.runInContext(source,ctx);
  assert.equal(ctx.costOrNull({m:'m',ti:1e6,estimated_cost_usd:null}),null);
  assert.equal(ctx.costOrNull({m:'m',ti:1e6,estimated_cost_usd:3}),3);
  assert.equal(ctx.costOrNull({cost:0,estimated_cost_usd:3}),0);
});

test('account totals use backend estimates and retain partial coverage',()=>{
  const source=appSource.slice(appSource.indexOf('function applyRealAccountUsage('),appSource.indexOf('  /* NGƯỜI DÙNG QUY ƯỚC',appSource.indexOf('function applyRealAccountUsage(')))+'}';
  const user={id:1,login:'a'};
  const ctx={USER_ACCOUNTS:[user],REAL_BY_ACCOUNT:[{account_id:1,model_id:1,estimated_cost_usd:3},{account_id:1,model_id:1,estimated_cost_usd:null}],state:{filters:{},modelNameById:{},pricingById:{1:{i:999,o:999}}},selectedOrganizationIds:()=>null,num:x=>Number(x)||0};
  vm.createContext(ctx);vm.runInContext(source,ctx);ctx.applyRealAccountUsage([]);
  assert.equal(user.costDerived,3);assert.equal(user.costRows,2);assert.equal(user.costRowsPriced,1);
});

test('pricing editor previews before saving, retains draft on conflict',async()=>{
  const calls=[];
  const ctx={window:{TokenLedgerAPI:{pricingCall:async(endpoint,method,body,key)=>{calls.push(endpoint);return endpoint==='preview'?{ok:true,data:{revision:7}}:{ok:false,message:'conflict'};}}}};
  const start=appSource.indexOf('async function savePricingDraft(');
  assert.notEqual(start,-1);
  vm.createContext(ctx);vm.runInContext(appSource.slice(start,appSource.indexOf('\nfunction ',start+1)),ctx);
  const draft={mode:'price',input_per_million:'0.10'};
  const result=await ctx.savePricingDraft('or:v/m',draft,async()=>true);
  assert.equal(result.ok,false); assert.equal(draft.input_per_million,'0.10');
  assert.deepEqual(calls,['preview','versions']);
});

test('existing pricing renderer loads persistent catalog not local state',async()=>{
  const nodes={};
  function element(){return {style:{},children:[],appendChild(x){this.children.push(x);return x;},setAttribute(){},addEventListener(){},querySelectorAll(){return [];}};}
  nodes['price-grid']=element();
  const ctx={document:{getElementById:id=>nodes[id]||null,createElement:element},window:{TokenLedgerAPI:{pricingCall:async()=>({ok:true,data:{rows:[{catalog_key:'or:vendor/<unsafe>',provider:'vendor',display_name:'<unsafe>',applied:null,automatic:null,manual:null}],write_enabled:false}})}},state:{pricing:{}},configMsg:()=>{},pricingOffset:0};
  const start=appSource.indexOf('var pricingOffset = 0;'),end=appSource.indexOf('function priceInput(',start);
  vm.createContext(ctx);vm.runInContext(appSource.slice(start,end),ctx);
  await ctx.renderPricing();
  assert.ok(nodes['price-grid'].children.length>0);
  assert.ok(JSON.stringify(nodes['price-grid']).includes('or:vendor/<unsafe>'));
});

test('translated rows retain estimate provenance and null rates',()=>{
  const start=apiSource.indexOf('function buildState('),end=apiSource.indexOf('  /* Gọi một endpoint hạn mức.',start);
  assert.ok(start>=0);
  assert.match(apiSource.slice(start,end),/estimated_cost_usd: x.estimated_cost_usd/);
  assert.doesNotMatch(apiSource.slice(start,end),/price_cached \|\| 0/);
  assert.doesNotMatch(appSource,/savePriceBtn.onclick=function\(\)\{ saveState/);
  assert.match(appSource,/pricingOffset = 0/);
});

test('sync panel labels queued and absent heartbeat without touching drafts',async()=>{
  const nodes={}; ['pricing-sync','pricing-enabled','pricing-hours','pricing-schedule','pricing-now'].forEach(k=>nodes[k]={});
  const ctx={document:{getElementById:id=>nodes[id]},window:{TokenLedgerAPI:{pricingCall:async()=>({ok:true,data:{status:'queued',enabled:false,interval_hours:24,last_worker_seen:null,revision:2}})}}};
  const start=appSource.indexOf('function renderPricingSync(');assert.ok(start>=0);
  Object.assign(ctx,{pricingSyncRequest:0,pricingSyncBusy:false,pricingDirty:new Set()});
  vm.createContext(ctx);vm.runInContext(appSource.slice(start,appSource.indexOf('\nasync function ',start+1)),ctx);
  await ctx.renderPricingSync();assert.match(nodes['pricing-sync'].textContent,/queued/);assert.match(nodes['pricing-sync'].textContent,/offline/);
});

// Minimal DOM contract, matching the repository's dependency-free Node harnesses.
function pricingDOM(call){
  function element(tag='div'){
    return {tagName:tag.toUpperCase(),style:{},children:[],attrs:{},value:'',disabled:false,checked:false,
      set textContent(v){this.text=String(v);this.children=[];},get textContent(){return (this.text||'')+this.children.map(x=>x.textContent).join(' ');},
      set innerHTML(v){assert.equal(v,'');this.text='';this.children=[];},
      appendChild(x){this.children.push(x);return x;},setAttribute(k,v){this.attrs[k]=String(v);},
      addEventListener(k,fn){this['on'+k]=fn;},
      querySelectorAll(selector){return this.children.flatMap(x=>[...(selector.split(',').includes(x.tagName.toLowerCase())?[x]:[]),...x.querySelectorAll(selector)]);}};
  }
  const nodes={};
  ['price-grid','pricing-provider','pricing-search','pricing-prev','pricing-next','pricing-filter','pricing-status','pricing-sync','pricing-enabled','pricing-hours','pricing-schedule','pricing-now'].forEach(k=>nodes[k]=element());
  const ctx={document:{getElementById:id=>nodes[id]||null,createElement:element},window:{TokenLedgerAPI:{pricingCall:call},confirm:()=>true,addEventListener(){}},configMsg(){},loadFromBackend(){},setInterval:()=>1,clearInterval(){},console};
  vm.createContext(ctx);vm.runInContext(appSource.slice(appSource.indexOf('var pricingOffset = 0;'),appSource.indexOf('function priceInput(')),ctx);
  return {ctx,nodes};
}
const modelRow={catalog_key:'or:vendor/<unsafe>',provider:'vendor',display_name:'<unsafe>',available:true,stale:true,price_last_verified_at:null,applied:{source:'manual',mode:'price',status:'valid',valid_from:'2026-09-22',valid_to:null,pricing:{input:'0',output:'2',cache_read:null}},manual:null,automatic:null};
test('pricing DOM presents readable rates, history and preview with unknowns distinct from zero',async()=>{
  const {ctx,nodes}=pricingDOM(async endpoint=>({ok:true,data:endpoint==='models'?{rows:[modelRow],write_enabled:true}:{rows:[{...modelRow.applied,id:1,principal:'shared_key',reason:'<script>reason</script>'}]}}));
  await ctx.renderPricing();
  assert.doesNotMatch(nodes['price-grid'].textContent,/\{"source"/);
  assert.match(nodes['price-grid'].textContent,/Input: 0/);
  assert.match(nodes['price-grid'].textContent,/Cache read: —/);
  await nodes['price-grid'].querySelectorAll('button').find(b=>b.textContent==='Lịch sử').onclick();
  assert.match(nodes['price-grid'].textContent,/shared_key/);
  assert.match(nodes['price-grid'].textContent,/<script>reason<\/script>/);
  assert.doesNotMatch(nodes['price-grid'].textContent,/\{"id"/);
  const preview=ctx.pricingPreviewText({rows_affected:0,agents_affected:0,old_known_subtotal:0,new_known_subtotal:2,old_unknown_rows:3,new_unknown_rows:1,as_of:'now',warning:'estimate only'});
  assert.match(preview,/0.*→.*2/);assert.match(preview,/3.*→.*1/);assert.match(preview,/estimate only/);
});

test('catalog loading rejects stale replies and protects dirty drafts on navigation',async()=>{
  const pending=[];const {ctx,nodes}=pricingDOM(()=>new Promise(resolve=>pending.push(resolve)));
  const first=ctx.renderPricing();assert.equal(nodes['price-grid'].attrs['aria-busy'],'true');
  const second=ctx.renderPricing();
  pending[1]({ok:true,data:{rows:[modelRow],write_enabled:true}});await second;
  pending[0]({ok:true,data:{rows:[],write_enabled:true}});await first;
  assert.match(nodes['price-grid'].textContent,/vendor/);
  const input=nodes['price-grid'].querySelectorAll('input')[0];input.value='3';input.oninput();
  ctx.window.confirm=()=>false;
  assert.equal(ctx.leavePricing(),false);assert.equal(input.value,'3');
  await ctx.renderPricing();assert.equal(pending.length,2,'background refresh must not destroy drafts');
  ctx.window.confirm=()=>true;assert.equal(ctx.leavePricing(),true);
});

test('save locks inputs and navigation, sends captured decimals and keeps all drafts after conflict',async()=>{
  let finish;const calls=[];
  const {ctx,nodes}=pricingDOM(async(endpoint,method,body)=>{
    calls.push({endpoint,body});
    if(endpoint==='models')return {ok:true,data:{rows:[modelRow,{...modelRow,catalog_key:'or:other'}],write_enabled:true}};
    if(endpoint==='preview')return new Promise(resolve=>finish=resolve);
    return {ok:false,message:'Price changed'};
  });
  await ctx.renderPricing();
  const inputs=nodes['price-grid'].querySelectorAll('input');inputs[0].value='0.10';inputs[0].oninput();
  inputs[7].value='5';inputs[7].oninput();
  const button=nodes['price-grid'].querySelectorAll('button')[0],saving=button.onclick();
  assert.equal(inputs[0].disabled,true);assert.equal(ctx.leavePricing(),false);
  assert.equal(calls.filter(c=>c.endpoint==='preview').length,1);
  await button.onclick();assert.equal(calls.filter(c=>c.endpoint==='preview').length,1);
  finish({ok:true,data:{revision:4}});await saving;
  assert.equal(inputs[0].disabled,false);assert.equal(inputs[0].value,'0.10');assert.equal(inputs[7].value,'5');
  assert.equal(calls.find(c=>c.endpoint==='versions').body.input_per_million,'0.10');
  let prevented=false;ctx.pricingUnload({preventDefault(){prevented=true;}});assert.equal(prevented,true);
});

test('provider selector loads all catalog pages, deduplicates exact namespaces and filters models',async()=>{
  const requests=[];
  const a=api(async url=>{requests.push(url);const offset=Number(new URL(url,'http://localhost').searchParams.get('offset'));return {ok:true,json:async()=>({rows:offset===0?Array.from({length:200},()=>({provider:'vendor'})):[{provider:'<other>'}]})};});
  const result=await a.pricingProviders();assert.equal(result.ok,true);assert.deepEqual(Array.from(result.data),['<other>','vendor']);assert.equal(requests.length,2);
  const {ctx,nodes}=pricingDOM(async(endpoint,method,body,key,query)=>{assert.equal(query.provider,'vendor');return {ok:true,data:{rows:[],write_enabled:false}};});
  ctx.window.TokenLedgerAPI.pricingProviders=async()=>result;
  await ctx.renderPricingProviders();assert.equal(nodes['pricing-provider'].children.length,3);
  nodes['pricing-provider'].value='vendor';await ctx.renderPricing();
  assert.match(fs.readFileSync('web/index.html','utf8'),/<select id="pricing-provider"/);
});

test('sync refresh ignores older responses and never overwrites edited schedule',async()=>{
  const pending=[];const {ctx,nodes}=pricingDOM(()=>new Promise(resolve=>pending.push(resolve)));
  const first=ctx.renderPricingSync(),second=ctx.renderPricingSync();
  pending[1]({ok:true,data:{status:'queued',enabled:false,interval_hours:24,last_worker_seen:null,revision:2}});await second;
  nodes['pricing-hours'].value='48';nodes['pricing-hours'].oninput();
  pending[0]({ok:true,data:{status:'old',enabled:true,interval_hours:1,last_worker_seen:'old',revision:1}});await first;
  assert.match(nodes['pricing-sync'].textContent,/queued/);assert.equal(nodes['pricing-hours'].value,'48');
  const third=ctx.renderPricingSync();pending[2]({ok:true,data:{status:'running',enabled:false,interval_hours:24,revision:3}});await third;
  assert.equal(nodes['pricing-hours'].value,'48');
  assert.match(nodes['pricing-sync'].textContent,/running/);
  ctx.window.confirm=()=>false;assert.equal(ctx.leavePricing(),false);
});

test('CSV preserves unknown cost and estimate provenance',()=>{
  let output;
  const start=appSource.indexOf('function csv('),end=appSource.indexOf('/* ═══════════════ RENDER TỔNG',start);
  const ctx={scopedRows:()=>[{day:'2026-09-22',m:'x',cost:null,estimated_cost_usd:null,estimate_status:'unsupported',unpriced_rows:1}],state:{range:{start:'2026-09-22',end:'2026-09-22'}},modelProvider:()=> 'v',num:x=>Number(x)||0,costOrNull:r=>r.estimated_cost_usd,cost:()=>0,toVnd:x=>x*25000,VND_RATE:25000,Blob:class {constructor(parts){output=parts.join('');}},URL:{createObjectURL:()=>'',revokeObjectURL(){}},document:{createElement:()=>({click(){}})}};
  vm.createContext(ctx);vm.runInContext(appSource.slice(start,end),ctx);ctx.exportCSV();
  assert.match(output,/unsupported/);assert.match(output,/Price version/);assert.doesNotMatch(output,/,0.00,0,25000/);
});
