const fs = require('fs');
const html = fs.readFileSync('builder.html', 'utf8');

// 语法检查
const m = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)];
let ok = true;
m.forEach((s, i) => {
  try {
    new Function(s[1]);
    console.log('Script block #' + (i + 1) + ': OK (' + s[1].length + ' bytes)');
  } catch (e) {
    ok = false;
    console.error('Script block #' + (i + 1) + ': SYNTAX ERROR');
    console.error(e.message);
  }
});

// 检查关键变化
const checks = [
  ['step-1 已改为 仓库与目标', /id="step-1">\s*<h2><span class="step">1<\/span> 仓库与目标/],
  ['原 GitHub 认证 card 已删除', (h) => !h.includes('GitHub 认证')],
  ['PAT 相关函数已删除', (h) => !h.includes('function loadPat') && !h.includes('function savePat') && !h.includes('function testPat')],
  ['轮询函数已删除', (h) => !h.includes('function startPolling') && !h.includes('checkLatestRun')],
  ['新按钮 copy-btn 存在', /id="copy-btn"/],
  ['新按钮 open-btn 存在', /id="open-btn"/],
  ['新按钮 copy-only-btn 存在', /id="copy-only-btn"/],
  ['inputs-preview 区域', /id="inputs-preview"/],
  ['buildInputs 函数', /function buildInputs/],
  ['inputsToText 函数', /function inputsToText/],
  ['copyToClipboard 函数', /function copyToClipboard/],
  ['copyAndOpen 函数', /function copyAndOpen/],
  ['githubActionsUrl 函数', /function githubActionsUrl/],
  ['fetchReleases 无 token', (h) => {
    // 找到 fetchReleases 函数体,确认没有 Authorization header
    const m = h.match(/async function fetchReleases[\s\S]*?\n\}/);
    return m && !m[0].includes('Bearer') && !m[0].includes("'v50-pat'");
  }],
  ['系统工具 5 项默认', (h) => {
    const count = (h.match(/value="(htop|curl|wget|nano|git)" checked disabled/g) || []).length;
    return count === 5;
  }],
  ['PAT 引用完全清除', (h) => {
    return !h.includes('ghp_') && !h.includes('github_pat_') && !h.includes('Bearer ');
  }],
  ['localStorage key 已升 v3', /v50-builder-form-v3/],
  ['I18N_MAP 仍存在', /const I18N_MAP = \{/],
  ['add_packages 拼接', /add_packages: all.join\(' '\)/],
  ['GitHub Actions URL 模板', /github\.com\/\$\{owner\}\/\$\{name\}\/actions\/workflows\/\$\{wf\}/],
];
checks.forEach((c) => {
  const name = c[0], check = c[1];
  const got = (typeof check === 'function') ? check(html) : check.test(html);
  console.log((got ? 'OK' : 'FAIL') + ' ' + name);
  if (!got) ok = false;
});

// 模拟 inputs 生成
console.log('\n--- 模拟 inputs 生成 ---');
try {
  new Function(`
    const I18N_MAP = ${JSON.stringify({
      'luci-app-passwall2': 'luci-i18n-passwall2-zh-cn',
      'luci-app-aria2': 'luci-i18n-aria2-zh-cn',
    })};
    // 模拟 explicit + i18n 拼接
    const explicit = ['luci-app-passwall2', 'luci-app-aria2'];
    const i18n = ['luci-i18n-passwall2-zh-cn', 'luci-i18n-aria2-zh-cn'];
    const all = [...new Set([...explicit, ...i18n])];
    const inputs = {
      release_tag: '',
      openwrt_version: 'v25.12.5',
      add_packages: all.join(' '),
      remove_packages: '',
      prerelease: 'true',
    };
    console.log(JSON.stringify(inputs, null, 2));
  `)();
} catch (e) {
  ok = false;
  console.error('Simulation failed:', e.message);
}

console.log('\n总字节: ' + fs.statSync('builder.html').size);
process.exit(ok ? 0 : 1);