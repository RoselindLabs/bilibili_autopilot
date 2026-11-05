/* Offline browser exercise; fixture bridge denies network and never reaches a Host. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const root = path.resolve(__dirname, '..');
const out = process.env.JOURNAL_QA_DIR;
if (!out) throw Error('Set JOURNAL_QA_DIR to a private output directory');
fs.mkdirSync(out, { recursive: true });
const html = fs.readFileSync(path.join(root, 'journal.html'), 'utf8');
const fixture = `(()=>{
window.qa={fail:false,failJournal:false,empty:false,account:'合成账号',commands:[],calls:[],polls:[]};
window.setInterval=fn=>qa.polls.push(fn);
const entries=[
{id:'a'.repeat(32),bvid:'BV1234567890',started:1,status:'noted',time:'2026-11-05T10:32:00+08:00',topic:'深海里的信号',video:{title:'深海生物的光',up_name:'科普频道（合成）'},thought:'原来深海里的光不只是为了照明，也可能是在传递信号。昨天还觉得这种发光很浪漫，今天反而更在意：同一个信号，会不会也把自己暴露给猎物？',source:'字幕',evidence_quote:'不同颜色与闪烁频率也能在黑暗环境中传递信号。',related:[{title:'昨天的海洋生物手记',thought:'当时只注意到了发光器官，没往沟通这层想。'}],sharing:'已提供给主动聊天'},
{id:'b'.repeat(32),bvid:'BV0987654321',started:2,status:'passed',time:'2026-11-05T11:08:00+08:00',video:{title:'另一条相关阅读',up_name:'科普频道（合成）'},reason:'这条解释得挺直白，不过暂时没有更多想说的。'},
{id:'c'.repeat(32),bvid:'BV1111111111',started:3,status:'noted',time:'2026-11-04T20:20:00+08:00',video:{title:'昨天的海洋生物手记',up_name:'科普频道（合成）'},thought:'发光器官是适应环境的一种方式。',source:'平台摘要',evidence_quote:'海洋生态的一种适应方式。'}];
window.maibot={ready:Promise.resolve(),query:async(name,args={})=>{qa.calls.push([name,args]);if(qa.fail)throw Error('合成离线失败');if(name==='overview')return {account:qa.account,state:'自主浏览中',mode:'浏览手记 · 不发表评论',choice:'想读一两条海洋生物内容',next_check:'11:40',last_round:'留下了新的感想',model_usage:'沿用现有模型预算',unresolved:'无',operation:'',pause_reason:'无'};if(name!=='journal')throw Error('Forbidden query');if(qa.failJournal)throw Error('合成换号后查询失败');const selected=args.day==='today'?'2026-11-05':args.day;let rows=qa.empty?[]:entries.filter(e=>(!selected||e.time.startsWith(selected))&&(!args.query||JSON.stringify(e).includes(args.query)));if(args.query==='unsafe')rows=[{...entries[0],thought:'<img src=x onerror="window.pwned=true">',video:{title:'<script>unsafe</script>',up_name:'合成'}}];if(args.before)rows=rows.slice(1);return {today:'2026-11-05',day:selected,timezone:'Asia/Shanghai',logged_in:true,entries:rows.slice(0,2),next:!args.before&&rows.length>2?rows[0].id:''}},action:async(name,args)=>{if(name!=='command')throw Error('Forbidden action');qa.commands.push(args.command);return {ok:true,message:'合成操作已接收'}}};})();`;
const historyFixture=`const originalQuery=maibot.query;maibot.query=async(name,args)=>name==='records'?{rows:[{time:'11-04 12:30',outcome:'已人工核对',mode:'实际发送',bvid:'BV1234567890',title:'合成旧记录',comment:'原评论内容',reason:'保留核对记录'}],pagination:{page:args.page,pages:2,total:21}}:originalQuery(name,args);`;
const document = '<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>浏览手记 · 合成预览</title><script>' + fixture.replaceAll('</script>', '<\\/script>') + historyFixture + '</script>' + html + '</html>';
fs.writeFileSync(path.join(out, 'preview.html'), document, 'utf8');
(async()=>{
 const browser=await chromium.launch({channel:process.env.PW_BROWSER_CHANNEL||'msedge',headless:true});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>r.abort());
 await page.setContent(document);await page.waitForSelector('.entry');
 assert.equal(await page.locator('.entry').count(),2);
 for(const width of [1440,768,390]){await page.setViewportSize({width,height:900});await page.screenshot({path:path.join(out,`journal-${width}.png`),fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'horizontal overflow');}
 await page.locator('.entry summary').first().click();assert(await page.locator('.quote').first().isVisible());
 await page.locator('#all').click();await page.waitForFunction(()=>!document.querySelector('#more').hidden);
 await page.locator('#more').click();await page.waitForFunction(()=>document.querySelector('#journal').getAttribute('aria-busy')==='false');
 assert((await page.locator('#journal').innerText()).includes('2026-11-04'));
 await page.locator('#day').fill('2026-11-04');await page.locator('#day').dispatchEvent('change');await page.waitForFunction(()=>document.querySelector('#journal').getAttribute('aria-busy')==='false');assert.equal(await page.locator('.entry').count(),1);
 await page.locator('#search').fill('unsafe');await page.locator('#filters').evaluate(f=>f.requestSubmit());await page.waitForFunction(()=>document.querySelector('#journal').getAttribute('aria-busy')==='false');assert.equal(await page.evaluate(()=>Boolean(window.pwned)),false);assert.equal(await page.locator('.entry img').count(),0);
 await page.evaluate(()=>qa.fail=true);await page.locator('#refresh').click();await page.waitForSelector('#notice.error');assert((await page.locator('#notice').innerText()).includes('读取失败'));
 await page.evaluate(()=>{qa.fail=false;qa.empty=true});await page.locator('#search').fill('');await page.locator('#refresh').click();await page.waitForSelector('#journal .empty');
 await page.locator('#manage > summary').click();await page.locator('[data-command="pause"]').click();await page.waitForFunction(()=>qa.commands.length===1);assert.deepEqual(await page.evaluate(()=>qa.commands),['/bili_auto pause']);
 await page.locator('#archive > summary').click();await page.waitForSelector('#archiveRows .entry');assert((await page.locator('#archiveRows').innerText()).includes('原评论内容'));await page.locator('#archiveNext').click();await page.waitForFunction(()=>document.querySelector('#archivePage').textContent==='2 / 2');assert.equal(await page.locator('table').count(),0);await page.screenshot({path:path.join(out,'journal-history-390.png'),fullPage:true});
 await page.evaluate(()=>{qa.empty=false;qa.account='另一个合成账号'});await page.locator('#search').fill('');await page.locator('#today').click();await page.waitForSelector('.entry');
 await page.evaluate(async()=>{qa.account='轮询切换的账号';qa.failJournal=true;document.querySelector('#manage').open=true;await qa.polls[0]()});
 await page.waitForSelector('#notice.error');assert.equal(await page.locator('.entry').count(),0);assert(await page.locator('#more').isHidden());assert.equal(await page.locator('#archiveRows .entry').count(),0);
 await page.evaluate(()=>qa.failJournal=false);await page.locator('#refresh').click();await page.waitForSelector('.entry');
 await page.evaluate(()=>{document.documentElement.classList.add('dark');document.documentElement.style.cssText='--maibot-background:#111111;--maibot-foreground:#eeeeee;--maibot-surface:#191919;--maibot-soft:#242424;--maibot-border:#444444;--maibot-muted:#b4b4b4;--maibot-primary:#78b9ed;--maibot-primary-foreground:#111111';document.querySelector('#manage').open=false});
 await page.screenshot({path:path.join(out,'journal-dark-390.png'),fullPage:true});
 assert.deepEqual(errors,[]);
 const report={viewports:[1440,768,390],checks:['initial','overflow','source-disclosure','date','search','load-more','xss','error','empty','management','account-change','poll-account-failure-clear','dark','inline-history-pagination'],externalRequests:0,pageErrors:errors};
 fs.writeFileSync(path.join(out,'browser-report.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
