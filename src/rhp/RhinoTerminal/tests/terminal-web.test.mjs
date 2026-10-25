import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

const html = fs.readFileSync(new URL('../src/web/terminal.html', import.meta.url), 'utf8');
function load() {
  const elements = Object.fromEntries([...html.matchAll(/id="([^"]+)"/g)].map(match => [match[1], {clientWidth:0, clientHeight:0, disabled:/^(almond|resume)$/.test(match[1])}]));
  const sent = [];
  let input;
  const term = {loadAddon(){}, open(){}, onResize(){}, onData(callback){input=callback;},
    attachCustomKeyEventHandler(){}, focus(){}, reset(){}, write(){}, paste(text){input(text);},
    getSelection(){return '';}, hasSelection(){return false;}};
  const window = {eto:{postMessage(text){sent.push(JSON.parse(text));}}};
  const context = {window, document:{getElementById:id=>elements[id]},
    Terminal:function(){return term;}, FitAddon:{FitAddon:function(){this.fit=()=>{};}},
    ResizeObserver:function(){this.observe=()=>{};}, requestAnimationFrame:callback=>callback()};
  vm.runInNewContext([...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1], context);
  return {elements, sent, window, input:text=>input(text)};
}
test('ready does not request a shell; almond/resume use existing input messages', () => {
  const {elements, sent, window} = load();
  assert.deepEqual(sent, [{type:'ready'}]);
  assert.ok(elements.almond, 'almond button missing');
  assert.ok(elements.resume, 'resume button missing');
  window.RhinoTerminal.meta({status:'PowerShell',cwd:'C:\\fixture',running:true,ready:true});
  elements.almond.onclick();
  elements.resume.onclick();
  assert.deepEqual(sent.slice(1), [{type:'input',text:'almond\r'},{type:'input',text:'almond resume\r'}]);
});
test('stopped runtime disables both shortcuts and retains manual keyboard input', () => {
  const {elements, sent, window, input} = load();
  assert.ok(elements.almond && elements.resume, 'shortcut buttons missing');
  window.RhinoTerminal.meta({status:'Off',cwd:'',running:false});
  assert.equal(elements.almond.disabled, true);
  assert.equal(elements.resume.disabled, true);
  window.RhinoTerminal.meta({status:'PowerShell',cwd:'',running:true,ready:true});
  assert.equal(elements.almond.disabled, false);
  assert.equal(elements.resume.disabled, false);
  input('echo 한글\r');
  assert.deepEqual(sent.at(-1), {type:'input',text:'echo 한글\r'});
});
test('shortcuts wait until the starting shell can accept input', () => {
  const {elements, window} = load();
  window.RhinoTerminal.meta({status:'PowerShell starting',cwd:'',running:true,ready:false});
  assert.equal(elements.stop.disabled, false);
  assert.equal(elements.almond.disabled, true);
  assert.equal(elements.resume.disabled, true);
});
