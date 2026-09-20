// Run from any directory: node docs/manual/repository-structure.check.cjs
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { execFileSync } = require('node:child_process');
const { createRequire } = require('node:module');
const { JSDOM } = createRequire(path.resolve(__dirname, '../../apps/desktop/package.json'))('jsdom');
const root = path.resolve(__dirname, '../..');
const page = fs.readFileSync(path.join(__dirname, 'repository-structure.html'), 'utf8');
const dom = new JSDOM(page, { runScripts: 'outside-only' });
const document = dom.window.document;
const rows = [...document.querySelectorAll('.file')];
const paths = rows.map(row => row.dataset.path);
const expected = execFileSync('git', ['ls-files', '-z'], { cwd: root, encoding: 'utf8' }).split('\0').filter(name => name && fs.existsSync(path.join(root, name)));
for (const name of ['repository-structure.html', 'repository-structure-overview.html', 'repository-structure.architecture.json', 'repository-structure.receipt.json', 'repository-structure.check.cjs']) {
  expected.push(`docs/manual/${name}`);
}
assert.equal(paths.length, new Set(paths).size, 'duplicate file paths');
assert.deepEqual(new Set(paths), new Set(expected), 'file tree differs from repository snapshot');
for (const row of rows) {
  assert(fs.statSync(path.join(root, row.dataset.path)).isFile());
  const href = decodeURIComponent(row.querySelector('a').getAttribute('href'));
  assert.equal(path.resolve(__dirname, href), path.join(root, row.dataset.path));
}
for (const directory of document.querySelectorAll('.directory')) {
  assert.equal(Number(directory.querySelector('.count').textContent), directory.querySelectorAll('.file').length);
}
for (const script of document.querySelectorAll('script')) dom.window.eval(script.textContent);
const input = document.querySelector('#search');
const search = query => {
  input.value = query;
  input.dispatchEvent(new dom.window.Event('input'));
  return rows.filter(row => !row.hidden).map(row => row.dataset.path);
};
const initialOpen = [...document.querySelectorAll('details')].map(node => node.open);
assert.deepEqual(search('MARKDOWN_IO.PY'), ['apps/desktop/python/keikeu_core/markdown_io.py']);
const nested = document.querySelector('[data-path="apps/desktop/python/keikeu_core"]');
assert.equal(nested.hidden, false);
assert.equal(nested.querySelector('details').open, true);
assert.deepEqual(search('apps/desktop/src/'), paths.filter(value => value.startsWith('apps/desktop/src/')));
assert.deepEqual(search('no-such-file-12345'), []);
assert.equal(document.querySelector('#empty').hidden, false);
assert.equal(search('').length, paths.length);
assert.deepEqual([...document.querySelectorAll('details')].map(node => node.open), initialOpen);
for (const [button, open] of [['expand', true], ['collapse', false]]) {
  document.querySelector(`#${button}`).click();
  assert([...document.querySelectorAll('details')].every(node => node.open === open));
}
document.querySelector('#overview-tab').click();
assert.equal(document.querySelector('#files').hidden, true);
assert.equal(document.querySelector('#overview').hidden, false);
assert.equal(document.querySelector('iframe').getAttribute('src'), 'repository-structure-overview.html');
document.querySelector('#files-tab').click();
assert.equal(document.querySelector('#files').hidden, false);
assert.equal(document.querySelector('#files-tab').getAttribute('aria-pressed'), 'true');
dom.window.close();
console.log(`PASS: ${paths.length} unique paths, local links, directory counts, search, expand/collapse and view switching.`);
