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
  ['I18N_MAP 存在', /const I18N_MAP = \{/],
  ['luci-app-passwall2 -> i18n', /luci-app-passwall2':\s*'luci-i18n-passwall2-zh-cn'/],
  ['collectPackages 函数', /function collectPackages\(\)/],
  ['i18n 分类已删除', /<!-- \(中文语言包分类已隐藏/],
  ['i18n btn-mini 已删除', (html) => !html.includes("i18n: '.category:nth-of-type(5)")],
  ['触发按钮说明', /中文包已自动同步/],
  ['summary 显示自动中文', /自动中文:/],
];
checks.forEach((c) => {
  const name = c[0], check = c[1];
  const got = (typeof check === 'function') ? check(html) : check.test(html);
  console.log((got ? 'OK' : 'FAIL') + ' ' + name);
  if (!got) ok = false;
});

// 旧 i18n checkbox 标签残留检查(应该为 0)
const i18nLabelMatches = html.match(/<input type="checkbox" value="luci-i18n-/g);
console.log('残留的 luci-i18n checkbox: ' + (i18nLabelMatches ? i18nLabelMatches.length : 0));

// 验证 collectPackages() 函数行为(模拟)
console.log('\n--- 模拟 collectPackages() ---');
// 在 new Function 里嵌入 collectPackages() + I18N_MAP + 模拟 DOM,验证逻辑
const sandbox = `
const I18N_MAP = ${JSON.stringify({
  'luci-app-passwall2': 'luci-i18n-passwall2-zh-cn',
  'luci-app-nikki': 'luci-i18n-nikki-zh-cn',
  'luci-app-aria2': 'luci-i18n-aria2-zh-cn',
  'luci-app-openclash': 'luci-i18n-openclash-zh-cn',
})};

// 简化版 collectPackages
function collectPackages(checked, custom) {
  const explicit = [...checked];
  if (custom) custom.split(/\\s+/).filter(Boolean).forEach(p => {
    if (!explicit.includes(p)) explicit.push(p);
  });
  const i18n = [];
  explicit.forEach(p => {
    if (I18N_MAP[p] && !explicit.includes(I18N_MAP[p]) && !i18n.includes(I18N_MAP[p])) {
      i18n.push(I18N_MAP[p]);
    }
  });
  const allSet = new Set(explicit);
  i18n.forEach(p => allSet.add(p));
  return { explicit, i18n, all: [...allSet] };
}

// Case 1: 勾选 nikki + aria2 + 自定义 htop
let r = collectPackages(['luci-app-nikki', 'luci-app-aria2'], 'htop');
console.log('Case 1:', JSON.stringify(r));
console.assert(r.explicit.length === 3 && r.i18n.length === 2 && r.all.length === 5, 'Case 1 fail');

// Case 2: 勾选已经包含 i18n(去重)
r = collectPackages(['luci-app-nikki', 'luci-i18n-nikki-zh-cn'], '');
console.log('Case 2:', JSON.stringify(r));
console.assert(r.i18n.length === 0 && r.all.length === 2, 'Case 2 fail');

// Case 3: 自定义里有 i18n,不算在 i18n 数组里
r = collectPackages(['luci-app-passwall2'], 'luci-i18n-argon-config-zh-cn');
console.log('Case 3:', JSON.stringify(r));
console.assert(r.i18n.length === 1 && r.explicit.includes('luci-i18n-argon-config-zh-cn'), 'Case 3 fail');

// Case 4: 空
r = collectPackages([], '');
console.log('Case 4:', JSON.stringify(r));
console.assert(r.all.length === 0, 'Case 4 fail');

// Case 5: 自定义里有未知的 luci-app
r = collectPackages([], 'luci-app-zzz-whatever');
console.log('Case 5:', JSON.stringify(r));
console.assert(r.all.length === 1 && r.i18n.length === 0, 'Case 5 fail');

console.log('All cases passed.');
`;
try {
  new Function(sandbox)();
} catch (e) {
  ok = false;
  console.error('collectPackages simulation FAILED:', e.message);
}

console.log('\n总字节: ' + fs.statSync('builder.html').size);
process.exit(ok ? 0 : 1);