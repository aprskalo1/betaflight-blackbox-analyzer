import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';

// Adapt only module resolution and the unused UI settings dependency for Node.
// The official parser and binary decoding algorithms are unmodified.
const base = path.resolve('analysis/tools/blackbox-log-viewer/src');
const dest = path.resolve('analysis/tools/parser-node');
fs.mkdirSync(dest, {recursive:true});
fs.writeFileSync(path.join(dest,'package.json'), '{"type":"module"}');
const require = createRequire(import.meta.url);
const semverPath = require.resolve('C:/Program Files/nodejs/node_modules/npm/node_modules/semver');
fs.writeFileSync(path.join(dest,'semver.js'), `import {createRequire} from 'node:module'; export default createRequire(import.meta.url)(${JSON.stringify(semverPath)});`);
for(const name of ['flightlog_parser','flightlog_fields_presenter','flightlog_fielddefs','tools','datastream','decoders']) {
  let src=fs.readFileSync(path.join(base,name+'.js'),'utf8');
  src=src.replace(/from "semver"/g, 'from "./semver.js"');
  src=src.replace(/"\.\/([a-z_]+)"/g, '"./$1.js"');
  src=src.replace('import { useSettingsStore } from "./stores/settings.js";', 'function useSettingsStore() { throw new Error("UI formatting is not used in raw decoding"); }');
  fs.writeFileSync(path.join(dest,name+'.js'),src);
}
const {FlightLogParser}=await import('./tools/parser-node/flightlog_parser.js');
const defs=await import('./tools/parser-node/flightlog_fielddefs.js');
const input=path.resolve(process.argv[2] || '.');
const out=path.resolve(process.argv[3] || 'analysis/decoded'); fs.mkdirSync(out,{recursive:true});
for(const name of fs.readdirSync(input).filter(x=>x.toUpperCase().endsWith('.BFL')).sort()) {
 const data=fs.readFileSync(path.join(input,name)); const p=new FlightLogParser(data); p.parseHeader(0,data.length);
 const stem=name.replace('.BFL',''); const handles={}; const buffers={};
 for(const kind of ['I','G','H','S']) if(p.frameDefs[kind]) {
   handles[kind]=fs.openSync(path.join(out,`${stem}.${kind}.csv`),'w'); buffers[kind]='';
   fs.writeSync(handles[kind],(kind==='S'||kind==='H'?'last_main_time,':'')+p.frameDefs[kind].name.join(',')+'\n');
 }
 let lastTime=0; const events=[]; let invalid=0;
 p.onFrameReady=(valid,frame,kind,offset,size)=>{
   if(!valid){invalid++;return;}
   if(kind==='E'){events.push({last_main_time:lastTime,...structuredClone(frame)});return;}
   if(kind==='P')kind='I';
   if(kind==='I')lastTime=frame[1];
   if(handles[kind]===undefined)return;
   buffers[kind]+=(kind==='S'||kind==='H'?lastTime+',':'')+frame.join(',')+'\n';
   if(buffers[kind].length>1024*1024){fs.writeSync(handles[kind],buffers[kind]);buffers[kind]='';}
 };
 p.parseLogData(false);
 for(const kind in handles){fs.writeSync(handles[kind],buffers[kind]);fs.closeSync(handles[kind]);}
 let headerEnd=0;while(data[headerEnd]===72&&data[headerEnd+1]===32)headerEnd=data.indexOf(10,headerEnd)+1;
 fs.writeFileSync(path.join(out,`${stem}.headers.txt`),data.subarray(0,headerEnd));
 const meta={file:name,invalidCallbacks:invalid,sysConfig:p.sysConfig,frameDefs:p.frameDefs,stats:p.stats,events,flightModeNames:defs.FLIGHT_LOG_FLIGHT_MODE_NAME,eventNames:defs.FlightLogEvent,failsafeNames:defs.FLIGHT_LOG_FAILSAFE_PHASE_NAME};
 fs.writeFileSync(path.join(out,`${stem}.metadata.json`),JSON.stringify(meta,null,2));
 console.log(name,JSON.stringify({invalid,frames:Object.fromEntries(Object.entries(p.stats.frame).map(([k,v])=>[k,{valid:v.validCount,corrupt:v.corruptCount,desync:v.desyncCount}]))}));
}
