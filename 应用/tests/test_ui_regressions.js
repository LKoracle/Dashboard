'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../static/app.js'),'utf8');
const home=fs.readFileSync(path.join(__dirname,'../static/home.js'),'utf8');
const section=(s,a,b)=>{assert(s.includes(a)&&s.includes(b));return s.slice(s.indexOf(a),s.indexOf(b,s.indexOf(a)));};
function context(){const c=vm.createContext({Map,Set,console,mtRequestVersion:0,mtProject:1,mtDate:'2026-10-29',mtDataReady:true,mtBoot:{projects:[{id:1,can_edit:true}]},mtValues:new Map(),mtVersions:new Map(),mtDraft:new Map(),mtStash:new Map(),mtStatus:'idle',mtSaving:false,mtCanEdit:true,render(){},notify(){},document:{querySelector(){return null}},CSS:{escape:x=>x},mtKey:(a,b)=>a+'_'+(b||0)});vm.runInContext(section(source,'async function mtLoadData(){','function mtSwitchProject('),c);return c;}
(async()=>{
 const c=context(),pending=[];c.api=()=>new Promise(resolve=>pending.push(resolve));
 const a=vm.runInContext('mtLoadData()',c);c.mtDate='2026-10-30';const b=vm.runInContext('mtLoadData()',c);
 pending[1]({items:[{metric_id:7,feature_id:null,value:'200',row_version:2}]});assert.equal(await b,true);
 pending[0]({items:[{metric_id:7,feature_id:null,value:'100',row_version:1}]});assert.equal(await a,false);
 assert.equal(c.mtValues.get('7_0'),'200');assert.equal(c.mtVersions.get('7_0'),2);
 vm.runInContext(section(source,'function mtSwitchProject(','function mtIsDirty('),c);c.mtToday=()=> '2026-10-31';c.mtSaving=true;
 vm.runInContext("mtSwitchDate('2026-10-29');mtSwitchProject(2)",c);assert.equal(c.mtDate,'2026-10-30');assert.equal(c.mtProject,1);
 // Failed reads cannot retain stale values or leave editing enabled.
 c.api=async()=>{throw Error('断网')};await vm.runInContext('mtLoadData()',c);assert.equal(c.mtDataReady,false);assert.equal(c.mtValues.size,0);assert.equal(c.mtStatus,'error');
 // Save callbacks cannot update a different context, even if a future caller bypasses switch guards.
 const d=context();d.mtValidateAll=(items)=>items.push({metric_id:7,value:'100'});let resolve;d.api=()=>new Promise(r=>resolve=r);
 vm.runInContext(section(source,'async function saveMaintain(){','function mtSection('),d);const saving=vm.runInContext('saveMaintain()',d);d.mtDate='2026-10-30';d.mtValues.set('7_0','200');resolve({saved:1,versions:[]});await saving;assert.equal(d.mtValues.get('7_0'),'200');
 const box={dataset:{features:'["旧功能"]'},replaceChildren(){},append(){}};
 const f=vm.createContext({document:{querySelector:()=>box},el:()=>({})});vm.runInContext(section(source,'function renderProjectFeatures(','function addProjectFeature('),f);vm.runInContext('renderProjectFeatures([])',f);assert.deepEqual(Array.from(vm.runInContext('currentProjectFeatures()',f)),[]);
 const h=vm.createContext({homeData:{metrics:[{id:7,name:'修改后的日活人数',semantic_name:'日活跃用户数'}]}});vm.runInContext(section(home,'function metric(','function value('),h);assert.equal(vm.runInContext("metric('日活跃用户数').id",h),7);
 assert(source.includes("menus:'menu',roles:'role',users:'user',projects:'project',metrics:'metric'"));
 assert(home.includes('vals.length<1'));
 console.log('前端回归通过：过期响应、保存上下文、保存中切换、读取失败、删除最后功能、改名保持图表、侧栏匹配、单步漏斗');
})().catch(e=>{console.error(e);process.exitCode=1});
const extras=vm.createContext({homeData:{features:[{id:9,name:'客户经营'},{id:10,name:'产品销售'}]}});
vm.runInContext(section(home,'function extraTrendSeries(','function renderExtraTrends('),extras);
assert.deepEqual(Array.from(vm.runInContext("extraTrendSeries({category:'feature',name:'使用率'})",extras),x=>x.label),['使用率 · 客户经营','使用率 · 产品销售']);
console.log('功能级自定义趋势按功能分别绑定检查通过');
(async()=>{
 const calls=[],state={file:'eGxzeA==',name:'多项目.xlsx',preview:null,result:null,busy:false,error:''};
 const c=vm.createContext({mtImport:state,mtSaving:false,mtHistory:{},notify(){},mtLoadData:async()=>true,mtImportDialogRefresh(){},document:{querySelector:()=>null},api:async(url,options)=>{calls.push({url,body:JSON.parse(options.body)});return url.endsWith('/preview')?{batch_id:'owned-batch',counts:{valid:3,insert:2,update:1}}:{phase:'completed',counts:{inserted:2,updated:1}};}});
 vm.runInContext('var capture={saving:null};render=function(){capture.saving=mtSaving;};',c);
 vm.runInContext(section(source,'async function validateMaintainImport(){','async function fetchMaintainHistory('),c);
 await vm.runInContext('validateMaintainImport()',c);
 assert.equal(calls[0].body.file_name,'多项目.xlsx');assert.equal('project_id' in calls[0].body,false);
 await vm.runInContext('commitMaintainImport()',c);
 assert.equal(calls[1].url,'/maintain/import/excel/owned-batch/commit');assert.deepEqual(calls[1].body,{});
 assert.equal(c.mtSaving,false);assert.equal(state.result.counts.updated,1);
 assert.equal(vm.runInContext('capture.saving',c),false);
 console.log('Excel 前端流程通过：跨项目文件校验、确认服务端批次、更新统计与保存锁');
})().catch(e=>{console.error(e);process.exitCode=1});
