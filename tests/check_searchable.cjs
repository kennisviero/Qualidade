// Verifica o enhancer de busca em selects (app/static/js/searchable_select.js)
// com um shim mínimo de DOM (HTMLSelectElement real p/ instanceof + descriptor de value).
"use strict";
const assert = require("assert");
const fs = require("fs");
const path = require("path");
const vm = require("vm");

// ---- shim de DOM ----
function listeners() { return Object.create(null); }

class Node {
  constructor(tag) {
    this.tagName = (tag || "").toUpperCase();
    this.childNodes = [];
    this.nodeType = 1;
    this._attr = Object.create(null);
    this.dataset = Object.create(null);
    this.style = {};
    this.textContent = "";
    this.hidden = false;
    this.disabled = false;
    this._on = listeners();
    this.parentNode = null;
    const self = this;
    this.classList = {
      _s: new Set(),
      add(...c) { c.forEach(x => this._s.add(x)); self._syncClass(); },
      remove(...c) { c.forEach(x => this._s.delete(x)); self._syncClass(); },
      toggle(c, on) { on ? this._s.add(c) : this._s.delete(c); self._syncClass(); },
      contains(c) { return this._s.has(c); },
    };
  }
  _syncClass() { this._attr["class"] = Array.from(this.classList._s).join(" "); }
  get className() { return Array.from(this.classList._s).join(" "); }
  set className(v) { this.classList._s = new Set(String(v).split(/\s+/).filter(Boolean)); this._syncClass(); }
  setAttribute(k, v) { this._attr[k] = String(v); }
  getAttribute(k) { return k in this._attr ? this._attr[k] : null; }
  hasAttribute(k) { return k in this._attr; }
  appendChild(n) { n.parentNode = this; this.childNodes.push(n); return n; }
  insertBefore(n, ref) {
    n.parentNode = this;
    const i = this.childNodes.indexOf(ref);
    if (i < 0) this.childNodes.push(n); else this.childNodes.splice(i, 0, n);
    return n;
  }
  removeChild(n) { const i = this.childNodes.indexOf(n); if (i >= 0) this.childNodes.splice(i, 1); n.parentNode = null; return n; }
  set innerHTML(v) { this._innerHTML = v; if (v === "") this.childNodes = []; }
  get innerHTML() { return this._innerHTML || ""; }
  addEventListener(t, fn) { (this._on[t] = this._on[t] || []).push(fn); }
  dispatchEvent(ev) {
    ev.target = ev.target || this;
    const arr = this._on[ev.type] || [];
    arr.slice().forEach(fn => fn.call(this, ev));
    const h = this["on" + ev.type];
    if (typeof h === "function") h.call(this, ev);
    return true;
  }
  _descendants(out) { for (const c of this.childNodes) { out.push(c); if (c._descendants) c._descendants(out); } return out; }
  querySelectorAll(sel) {
    const all = this._descendants([]);
    if (sel === "select") return all.filter(n => n.tagName === "SELECT");
    if (sel.charAt(0) === ".") { const cls = sel.slice(1); return all.filter(n => n.classList && n.classList.contains(cls)); }
    return [];
  }
  scrollIntoView() {}
  focus() {}
  select() {}
  contains(n) { let p = n; while (p) { if (p === this) return true; p = p.parentNode; } return false; }
}

class HTMLSelectElement extends Node {
  constructor() {
    super("select");
    this.options = [];
    this.selectedIndex = 0;
    this.multiple = false;
  }
  addOption(value, text) {
    const o = new Node("option");
    o.value = value; o.textContent = text;
    this.options.push(o); this.appendChild(o);
    return o;
  }
}
Object.defineProperty(HTMLSelectElement.prototype, "value", {
  configurable: true,
  get() { const o = this.options[this.selectedIndex]; return o ? o.value : ""; },
  set(v) { const i = this.options.findIndex(o => o.value === v); this.selectedIndex = i; },
});

class Event { constructor(type, opts) { this.type = type; this.bubbles = !!(opts && opts.bubbles); } preventDefault() {} stopPropagation() {} }
class MutationObserver { constructor(cb) { this.cb = cb; } observe() {} disconnect() {} }

const documentElement = new Node("html");
const body = new Node("body");
documentElement.appendChild(body);

const document = {
  readyState: "complete",
  documentElement,
  body,
  _on: listeners(),
  addEventListener(t, fn) { (this._on[t] = this._on[t] || []).push(fn); },
  createElement(tag) { return tag.toLowerCase() === "select" ? new HTMLSelectElement() : new Node(tag); },
  querySelectorAll(sel) { return documentElement.querySelectorAll(sel); },
  get activeElement() { return null; },
};

// select "grande" (>=6 opções) → deve ser enfeitado
const big = new HTMLSelectElement();
body.appendChild(big);
["Empresa Alfa", "Beta Ltda", "Gamma SA", "Delta ME", "Epsilon EPP", "Zeta Group", "Omega Corp"]
  .forEach((t, i) => big.addOption("e" + i, t));
big.selectedIndex = 0;

// select "pequeno" (3 opções) → NÃO deve ser mexido
const small = new HTMLSelectElement();
body.appendChild(small);
["Alto", "Médio", "Baixo"].forEach((t, i) => small.addOption("s" + i, t));

// ---- carrega o módulo no sandbox ----
const code = fs.readFileSync(path.join(__dirname, "..", "app", "static", "js", "searchable_select.js"), "utf8");
const sandbox = { document, HTMLSelectElement, MutationObserver, Event, setTimeout, console };
vm.createContext(sandbox);
vm.runInContext(code, sandbox);

// ---- asserts ----
// 1) grande foi enfeitado: embrulhado, com ss-input, e ss-native no select
assert.equal(big.dataset.ss, "1", "select grande deveria ser enfeitado");
const wrap = big.parentNode;
assert.ok(wrap && wrap.classList.contains("ss-wrap"), "select deveria estar dentro de .ss-wrap");
const input = wrap.querySelectorAll(".ss-input")[0];
assert.ok(input, "deveria existir um .ss-input");
assert.ok(big.classList.contains("ss-native"), "select deveria receber classe ss-native");

// 2) pequeno intacto
assert.ok(!small.dataset.ss, "select pequeno NÃO deveria ser enfeitado");
assert.ok(!small.classList.contains("ss-native"), "select pequeno deveria ficar intacto");

// 3) digitar filtra as opções no painel
input.value = "corp";
input.dispatchEvent(new Event("input"));
const panel = wrap.querySelectorAll(".ss-panel")[0];
let opts = panel.querySelectorAll(".ss-opt");
assert.equal(opts.length, 1, "filtro 'corp' deveria achar 1 opção");
assert.equal(opts[0].textContent, "Omega Corp");

// 4) escolher dispara change e seta o value
let mudou = false;
big.addEventListener("change", () => { mudou = true; });
opts[0].dispatchEvent(new Event("mousedown"));
assert.ok(mudou, "escolher uma opção deveria disparar evento change");
assert.equal(big.value, "e6", "value deveria refletir a opção escolhida (Omega Corp)");
assert.equal(input.value, "Omega Corp", "campo deveria exibir o rótulo escolhido");

// 5) atribuição programática de .value reflete no campo
big.value = "e1";
assert.equal(input.value, "Beta Ltda", "set programático de value deveria atualizar o campo");

// 6) repopular opções e sincronizar (simula innerHTML + nova carga)
big.options = []; big.childNodes = big.childNodes.filter(n => n.tagName !== "OPTION");
big.addOption("x0", "Novo Único");
big.selectedIndex = 0;
input.value = ""; input.dispatchEvent(new Event("input"));
opts = (wrap.querySelectorAll(".ss-panel")[0]).querySelectorAll(".ss-opt");
assert.equal(opts.length, 1, "após repopular, painel deveria listar a nova opção");
assert.equal(opts[0].textContent, "Novo Único");

console.log("OK: enhancer embrulha selects grandes, filtra ao digitar, dispara change, reflete value e preserva selects pequenos.");
