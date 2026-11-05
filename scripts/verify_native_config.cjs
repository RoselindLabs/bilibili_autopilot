/* Render the current Host's actual FieldRenderer/SectionRenderer with SDK schema.
 * No Host server, login, provider or saved configuration is used. */
const fs = require('node:fs');
const path = require('node:path');
const { spawnSync } = require('node:child_process');
const assert = require('node:assert/strict');
const host = process.env.MAIBOT_SOURCE;
const out = process.env.JOURNAL_QA_DIR;
if (!host || !out) throw Error('Set MAIBOT_SOURCE and JOURNAL_QA_DIR');
const dashboard = path.join(host, 'dashboard');
const { build } = require(path.join(dashboard, 'node_modules/esbuild'));
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
fs.mkdirSync(out, { recursive: true });
const py = spawnSync(process.env.PLUGIN_PYTHON || path.join(root, '.venv/Scripts/python.exe'), ['-X','utf8','-c', `
import importlib,sys,types,json,importlib.metadata
p=types.ModuleType('local_bilibili_autopilot');p.__path__=[sys.argv[1]];sys.modules[p.__name__]=p
cls=importlib.import_module(p.__name__+'.plugin').BilibiliAutopilotPlugin
assert importlib.metadata.version('maibot-plugin-sdk')=='2.20.0'
cfg=cls.config_model.model_validate({'model':{'task':'custom_task','candidates':['first','second']},'browse':{'interval_seconds':780,'max_check_minutes':21},'comment':{'publish_enabled':False},'replies':{'enabled':False}})
print(json.dumps({'schema':cls.build_config_schema(),'config':cfg.model_dump()},ensure_ascii=False))
`, root], { encoding: 'utf8' });
if (py.status) throw Error(py.stderr);
const data = JSON.parse(py.stdout);
fs.writeFileSync(path.join(out,'native-schema.json'), JSON.stringify(data,null,2));
const source = fs.readFileSync(path.join(dashboard,'src/routes/plugin-config.tsx'),'utf8');
const functions = source.slice(source.indexOf('function getLocaleCandidates'), source.indexOf('interface PluginDetailItem'));
assert(functions.includes('const resolvedSectionName = section.name || sectionName'));
const imports = `import React,{useState} from 'react';import {createRoot} from 'react-dom/client';
import i18n from 'i18next';import {useTranslation,initReactI18next} from 'react-i18next';
import {Card,CardContent,CardDescription,CardHeader,CardTitle} from '@/components/ui/card';
import {Collapsible,CollapsibleContent,CollapsibleTrigger} from '@/components/ui/collapsible';
import {Select,SelectContent,SelectItem,SelectTrigger,SelectValue} from '@/components/ui/select';
import {DraftNumberInput} from '@/components/ui/draft-number-input';
import {Button} from '@/components/ui/button';import {Input} from '@/components/ui/input';
import {Label} from '@/components/ui/label';import {Switch} from '@/components/ui/switch';
import {Slider} from '@/components/ui/slider';import {Textarea} from '@/components/ui/textarea';
import {ListFieldEditor} from '@/components/ListFieldEditor';import {MultiSelect} from '@/components/ui/multi-select';
import {Eye,EyeOff,ChevronDown,ChevronRight} from 'lucide-react';import {cn} from '@/lib/utils';
import {getNestedRecord,setNestedField} from '@/routes/plugin-config/utils';
import {getComputedTokens,injectTokensAsCSS} from '@/lib/theme/pipeline';
import {DEFAULT_DASHBOARD_STYLE} from '@/lib/theme/tokens';
`;
const app = `const data=${JSON.stringify(data)};window.setQATheme=dark=>{document.documentElement.classList.toggle('dark',dark);document.documentElement.dataset.dashboardStyle=DEFAULT_DASHBOARD_STYLE;injectTokensAsCSS(getComputedTokens({dashboardStyle:DEFAULT_DASHBOARD_STYLE},dark),document.documentElement)};window.setQATheme(false);i18n.use(initReactI18next).init({lng:'zh',resources:{zh:{translation:{}}},interpolation:{escapeValue:false}});
function App(){const [config,setConfig]=useState(data.config),[tab,setTab]=useState('reading');window.qaConfig=config;
return <main style={{maxWidth:1000,margin:'auto',padding:24}}><h1 style={{fontSize:24,marginBottom:8}}>B站自主浏览 · 配置</h1><p style={{marginBottom:16}}>合成配置 · 使用当前宿主原生字段与章节组件</p><nav style={{display:'flex',gap:8,flexWrap:'wrap',marginBottom:24}}>{data.schema.layout.tabs.map(t=><Button key={t.id} variant="outline" onClick={()=>setTab(t.id)}>{t.title}</Button>)}</nav><div style={{display:'grid',gap:16}}>{data.schema.layout.tabs.find(t=>t.id===tab).sections.map(key=><SectionRenderer key={key} sectionName={key} section={data.schema.sections[key]} config={config} onChange={(s,f,v)=>setConfig(prev=>setNestedField(prev,s,f,v))}/>)}</div></main>};createRoot(document.getElementById('root')).render(<App/>);`;
(async()=>{
 const bundle = await build({stdin:{contents:imports+functions+app,resolveDir:dashboard,loader:'tsx'},bundle:true,write:false,format:'iife',platform:'browser',jsx:'automatic',alias:{'@':path.join(dashboard,'src')},define:{'process.env.NODE_ENV':'"production"'},logLevel:'warning'});
 const index=fs.readFileSync(path.join(dashboard,'dist/index.html'),'utf8');const cssPath=index.match(/href="(\/assets\/[^\"]+\.css)"/)[1];const css=fs.readFileSync(path.join(dashboard,'dist',cssPath),'utf8');
 const html='<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>'+css+'html,body,#root{height:auto!important;min-height:0!important;overflow:visible!important}</style><div id="root"></div><script>'+bundle.outputFiles[0].text.replaceAll('</script>','<\\/script>')+'</script></html>';
 fs.writeFileSync(path.join(out,'native-preview.html'),html);
 const browser=await chromium.launch({channel:process.env.PW_BROWSER_CHANNEL||'msedge',headless:true});const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',r=>r.abort());await page.setContent(html);await page.getByText('浏览节奏与活动时段',{exact:true}).waitFor();
 for(const width of [1440,768,390]){await page.setViewportSize({width,height:1000});await page.screenshot({path:path.join(out,`native-${width}.png`),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'native overflow');}
 const field=text=>page.locator('label').filter({hasText:text}).locator('..').locator('input');
 assert.equal(await field('最短浏览意愿').inputValue(),'780');await field('最短浏览意愿').fill('900');await field('最短浏览意愿').blur();
 assert.equal(await page.evaluate(()=>qaConfig.browse.interval_seconds),900);assert.equal(await page.evaluate(()=>qaConfig.browse.max_check_minutes),21);assert.equal(await page.evaluate(()=>qaConfig.rhythm),undefined);
 await page.getByRole('button',{name:'模型分工',exact:true}).click();assert.equal(await field('默认模型任务').inputValue(),'custom_task');
 await page.locator('label').filter({hasText:'模型任务（空为继承）'}).first().locator('..').locator('input').fill('planner');
 assert.equal(await page.evaluate(()=>qaConfig.decision_model.task),'planner');assert.equal(await page.evaluate(()=>qaConfig.model.task),'custom_task');assert.deepEqual(await page.evaluate(()=>qaConfig.model.candidates),['first','second']);
 await page.screenshot({path:path.join(out,'native-models-390.png'),fullPage:true});
 await page.getByRole('button',{name:'旧功能与高级',exact:true}).click();assert(await page.getByText('旧功能 · B站评论',{exact:true}).isVisible());assert.equal(await page.getByText('自动发表评论（开启即切旧评论模式）',{exact:true}).count(),0);
 await page.getByText('旧功能 · B站评论',{exact:true}).click();assert(await page.getByText('自动发表评论（开启即切旧评论模式）',{exact:true}).isVisible());
 assert.equal(await page.evaluate(()=>qaConfig.comment.publish_enabled),false);assert.equal(await page.evaluate(()=>qaConfig.replies.enabled),false);
 await page.evaluate(()=>window.setQATheme(true));await page.screenshot({path:path.join(out,'native-legacy-dark-390.png'),fullPage:true});assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(out,'native-report.json'),JSON.stringify({sdk:'2.20.0',renderer:'Actual Host FieldRenderer/SectionRenderer extracted unchanged; compiled Host CSS',checks:['schema-unit-labels','three-widths','original-key-edit','unrelated-values-preserved','stage-model-field','legacy-collapsed','legacy-switches-preserved','dark'],errors},null,2));await browser.close();console.log('Native Host renderer: 8 checks passed; no persistence/network');
})().catch(error=>{console.error(error);process.exit(1)});
