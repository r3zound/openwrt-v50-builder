const fs = require('fs');
const html = fs.readFileSync('builder.html', 'utf8');

const checks = [
  ['步骤 1 card', /id="step-1"/],
  ['步骤 7 card', /id="step-7"/],
  ['代理分组', /代理 \/ 反审查/],
  ['LuCI 应用分组', /LuCI 应用/],
  ['主题分组', /LuCI 主题/],
  ['工具分组', /系统工具/],
  ['i18n 分组', /中文语言包/],
  ['全选按钮 proxy', /data-cat="proxy"/],
  ['全选按钮 i18n', /data-cat="i18n"/],
  ['表单保存按钮', /id="save-form"/],
  ['表单重置按钮', /id="reset-form"/],
  ['测试 PAT 按钮', /id="test-pat"/],
  ['取消轮询按钮', /id="cancel-poll-btn"/],
  ['releases 区块', /id="releases"/],
  ['refresh-releases-btn', /id="refresh-releases-btn"/],
  ['localStorage 保存 key', /v50-builder-form-v2/],
  ['localStorage PAT key', /v50-pat/],
  ['fetchReleases 函数', /async function fetchReleases/],
  ['startPolling 函数', /function startPolling/],
  ['stopPolling 函数', /function stopPolling/],
  ['汇总函数', /function updateSummary/],
  ['init 函数', /function init/],
  ['checkboxes 恢复', /obj\.checkboxes/],
];
let ok = true;
checks.forEach((c) => {
  const name = c[0], rx = c[1];
  const got = rx.test(html);
  console.log((got ? '✓' : '✗') + ' ' + name);
  if (!got) ok = false;
});

const ckCount = (html.match(/value="luci-/g) || []).length;
console.log('luci-* checkbox 数量: ' + ckCount);
console.log('总行数: ' + html.split('\n').length);
console.log('总字节: ' + fs.statSync('builder.html').size);

process.exit(ok ? 0 : 1);