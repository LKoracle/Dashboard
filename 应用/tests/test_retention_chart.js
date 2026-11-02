'use strict';
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const charts=fs.readFileSync(path.join(__dirname,'../static/home-charts.js'),'utf8'),home=fs.readFileSync(path.join(__dirname,'../static/home.js'),'utf8');
const nodes={'#retentionPlot':{clientWidth:1100,clientHeight:240,innerHTML:''},'#retentionPeriod':{textContent:''}};
const c=vm.createContext({selectedDate:'2026-10-30',today:'2026-10-31',homeData:{metrics:[{id:31,name:'7日留存率',show_trend:true}],values:[]},$:s=>nodes[s],$$:()=>[],esc:String});
vm.runInContext(charts.slice(0,charts.indexOf('function renderSessionTrend(')),c);
vm.runInContext(home.slice(home.indexOf('function metric('),home.indexOf('function storedData(')),c);
vm.runInContext("homeData.values=Array.from({length:14},(_,i)=>({metric_id:31,feature_id:null,date:shift(selectedDate,i-20),value:String(60+i)}));renderRetentionTrend({name:'测试项目'},[])",c);
assert.equal((nodes['#retentionPlot'].innerHTML.match(/class="plot-point retention-point"/g)||[]).length,14);
assert.equal(nodes['#retentionPeriod'].textContent,'统计日期 2026.10.17 — 2026.10.30 · 近14天');
assert(nodes['#retentionPlot'].innerHTML.includes('统计日期 2026.10.17 · 60.0%'));
assert(nodes['#retentionPlot'].innerHTML.includes('统计日期 2026.10.30 · 73.0%'));
assert(nodes['#retentionPlot'].innerHTML.includes('>10.17</text>'));
assert(nodes['#retentionPlot'].innerHTML.includes('>10.30</text>'));
// Missing dates remain gaps; a missing result must not become zero.
vm.runInContext("homeData.values.splice(6,1);renderRetentionTrend({name:'测试项目'},[])",c);
assert.equal((nodes['#retentionPlot'].innerHTML.match(/class="plot-point retention-point"/g)||[]).length,13);
// Today's observation period is not finished, even when a stored value exists.
c.today='2026-10-30';vm.runInContext("renderRetentionTrend({name:'测试项目'},[])",c);
assert(!nodes['#retentionPlot'].innerHTML.includes('统计日期 2026.10.30 · 73.0%'));
console.log('留存趋势通过：14 天、填写统计日期对齐、首尾日期、缺失断线、未完成观察不展示');
