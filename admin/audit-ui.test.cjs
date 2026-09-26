const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync(__dirname + '/index.html', 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];

function setup(responder) {
  const elements = new Map();
  const element = id => {
    if (!elements.has(id)) elements.set(id, {value: '', innerHTML: '', textContent: ''});
    return elements.get(id);
  };
  const context = vm.createContext({
    document: {getElementById: element},
    localStorage: {getItem: () => null, setItem() {}},
    URLSearchParams,
    fetch: async url => ({ok: true, json: async () => ({data: await responder(url)})}),
  });
  vm.runInContext(script, context);
  return {context, element};
}

const payload = '<img src=x onerror="alert(1)">';
test('security filters and untrusted fields render as escaped text', async () => {
  let requested;
  const {context, element} = setup(url => {
    requested = url;
    return {items: [{created_at: payload, event_type: payload, outcome: payload,
      user_id: payload, request_id: payload, subject_hash: payload, client_hash: payload,
      details: {value: payload}}]};
  });
  element('securityEventType').value = 'LOGIN';
  element('securityOutcome').value = 'SUCCESS';
  await vm.runInContext('loadSecurityEvents()', context);
  assert.match(requested, /event_type=LOGIN&outcome=SUCCESS&limit=200/);
  const output = element('securityEvents').innerHTML;
  assert.ok(!output.includes('<img'));
  assert.ok(output.includes('&lt;img'));
  assert.ok(output.includes('&quot;'));
});

test('security API errors cannot inject markup', async () => {
  const {context, element} = setup(() => ({}));
  context.fetch = async () => ({ok: false, status: 500, json: async () => ({detail: payload})});
  await vm.runInContext('loadSecurityEvents()', context);
  assert.ok(!element('securityEvents').innerHTML.includes('<img'));
  assert.ok(element('securityEvents').innerHTML.includes('&lt;img'));
});

test('operational paths and request IDs cannot inject markup', async () => {
  const {context, element} = setup(url => url.includes('/summary') ?
    {status: 'OK', readiness: {ready: true}, metrics: {}, alerts: []} :
    {items: [{created_at: payload, event_type: payload, method: payload,
      path: payload, status_code: 500, duration_ms: 2, request_id: payload}]});
  await vm.runInContext('loadOperations()', context);
  const output = element('opsEvents').innerHTML;
  assert.ok(!output.includes('<img'));
  assert.ok(output.includes('&lt;img'));
});

test('empty security results remain readable', async () => {
  const {context, element} = setup(() => ({items: []}));
  await vm.runInContext('loadSecurityEvents()', context);
  assert.ok(element('securityEvents').innerHTML.includes('لا توجد أحداث مطابقة.'));
});
