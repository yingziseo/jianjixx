// 从飞书“赛罗素材库”（公开表格，访客身份即可）读取全部视频附件并下载，按型号分文件夹保存
// 用法：node scripts/feishu_sync.cjs --out materials [--model R18] [--assets a.mp4,b.mp4] [--existing existing.txt]
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const args = process.argv.slice(2);
const opt = (name, fallback = '') => { const i = args.indexOf(name); return i >= 0 && args[i + 1] !== undefined ? args[i + 1] : fallback; };
const OUT = opt('--out', 'materials');
const ONLY = opt('--model', '');
const ASSETS = new Set(opt('--assets', '').split(',').map(x => x.trim()).filter(Boolean));   // 只下载这些文件（逗号分隔）
const EXISTING = new Set(fs.existsSync(opt('--existing', '')) ? fs.readFileSync(opt('--existing'), 'utf8').split('\n').map(s => s.trim()).filter(Boolean) : []);
const cfg = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config', 'source.json'), 'utf8'));
const F = cfg.feishu;

function assetName(title) {
  let s = title;
  for (const [zh, py] of Object.entries(cfg.photographers)) s = s.split(zh).join(py);
  return s.replace(/[^A-Za-z0-9._-]+/g, '-').replace(/-+/g, '-').replace(/^-|-$/g, '') + '.mp4';
}

(async () => {
  const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined, args: ['--no-sandbox'] });
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  let table = null;
  page.on('response', async (r) => {
    const u = r.url();
    if (u.includes(`/bitable/${F.base}/clientvars`) && u.includes(`tableID=${F.table}`) && !table) {
      try {
        const body = JSON.parse(await r.text());
        const raw = body?.data?.table;
        if (typeof raw === 'string') table = JSON.parse(zlib.gunzipSync(Buffer.from(raw, 'base64')).toString('utf8'));
      } catch (e) { console.error('解析表格失败', e.message); }
    }
  });
  await page.goto(F.url, { waitUntil: 'networkidle', timeout: 120000 }).catch(e => console.error('打开页面：', e.message));
  for (let i = 0; i < 30 && !table; i++) await page.waitForTimeout(1000);
  if (!table) throw new Error('没有读到表格数据（飞书页面结构可能变了）');

  const fieldId = {};
  for (const [id, f] of Object.entries(table.fieldMap)) fieldId[f.name] = id;
  const opts = (name) => Object.fromEntries(((table.fieldMap[fieldId[name]] || {}).property?.options || []).map(o => [o.id, o.name]));
  const modelOpt = opts(F.fields.model), reviewOpt = opts(F.fields.review), kindOpt = opts(F.fields.kind);

  const manifest = [];
  for (const [rid, rec] of Object.entries(table.recordMap)) {
    const v = (name) => (rec[fieldId[name]] || {}).value;
    const code = modelOpt[v(F.fields.model)] || '';
    const model = cfg.models[code] || (code ? code.replace(/[^A-Za-z0-9-]/g, '-') : 'unknown');
    const title = (v(F.fields.title) || []).map(x => x.text || '').join('') || rid;
    for (const a of v(F.fields.attachment) || []) {
      if (!String(a.mimeType || '').startsWith('video/')) continue;
      manifest.push({ model, code, title, record: rid, review: reviewOpt[v(F.fields.review)] || '', kind: kindOpt[v(F.fields.kind)] || '',
        plays: v(F.fields.plays) ?? null, file: a.name, size_mb: +(a.size / 1e6).toFixed(1), token: a.attachmentToken, asset: assetName(title) });
    }
  }
  manifest.sort((x, y) => (x.model + x.asset).localeCompare(y.model + y.asset, 'en', { numeric: true }));
  fs.mkdirSync(OUT, { recursive: true });
  fs.writeFileSync(path.join(OUT, 'manifest.json'), JSON.stringify(manifest, null, 2));
  console.log(`表格共 ${Object.keys(table.recordMap).length} 条记录，视频 ${manifest.length} 个`);

  let done = 0, skipped = 0;
  for (const m of manifest) {
    if (ONLY && m.model !== ONLY) continue;
    if (ASSETS.size && !ASSETS.has(m.asset)) continue;
    if (EXISTING.has(`${m.model}/${m.asset}`)) { skipped++; continue; }
    const dir = path.join(OUT, m.model); fs.mkdirSync(dir, { recursive: true });
    const dest = path.join(dir, m.asset);
    if (fs.existsSync(dest)) { skipped++; continue; }
    const extra = encodeURIComponent(JSON.stringify({ bitablePerm: { tableId: F.table, attachments: { [fieldId[F.fields.attachment]]: { [m.record]: [m.token] } } } }));
    const url = `https://my.feishu.cn/space/api/box/stream/download/all/${m.token}/?mount_point=bitable_file&extra=${extra}`;
    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const r = await ctx.request.get(url, { timeout: 600000 });
        if (r.status() !== 200) throw new Error(`HTTP ${r.status()}`);
        fs.writeFileSync(dest, await r.body()); done++;
        console.log(`下载 ${m.model}/${m.asset} ${m.size_mb}MB`); break;
      } catch (e) {
        console.error(`第${attempt}次失败 ${m.asset}: ${e.message}`);
        if (attempt === 3) throw e;
        await page.waitForTimeout(3000 * attempt);
      }
    }
    await page.waitForTimeout(800);
  }
  console.log(`完成：新下载 ${done} 个，已存在跳过 ${skipped} 个`);
  await browser.close();
})().catch(e => { console.error(e); process.exit(1); });
