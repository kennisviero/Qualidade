// Busca ao digitar em selects de consulta — enhancement global e aditivo.
// NÃO substitui o <select>: ele continua no DOM com o mesmo id, .value, .onchange
// e repopulação por innerHTML. Sobrepõe um campo de texto que filtra as opções.
// Regras: aplica a selects com >= MIN_OPCOES opções (ou com [data-search]);
// ignora [multiple], [data-no-search] e os já enfeitados.
(function () {
  "use strict";
  var MIN_OPCOES = 6;

  function label(opt) { return (opt.textContent || "").trim(); }

  function eligivel(sel) {
    if (!(sel instanceof HTMLSelectElement)) return false;
    if (sel.multiple) return false;
    if (sel.dataset.ss) return false;
    if (sel.hasAttribute("data-no-search")) return false;
    if (sel.hasAttribute("data-search")) return true;
    return sel.options.length >= MIN_OPCOES;
  }

  function enhance(sel) {
    if (!eligivel(sel)) return;
    sel.dataset.ss = "1";

    var wrap = document.createElement("div");
    wrap.className = "ss-wrap";
    sel.parentNode.insertBefore(wrap, sel);
    wrap.appendChild(sel);
    sel.classList.add("ss-native");
    sel.setAttribute("tabindex", "-1");
    sel.setAttribute("aria-hidden", "true");

    var input = document.createElement("input");
    input.type = "text";
    input.className = "ss-input";
    input.autocomplete = "off";
    input.setAttribute("role", "combobox");
    input.setAttribute("aria-expanded", "false");
    input.placeholder = sel.getAttribute("data-ss-ph") || "Digite para filtrar…";
    if (sel.disabled) input.disabled = true;

    var panel = document.createElement("div");
    panel.className = "ss-panel";
    panel.hidden = true;

    wrap.appendChild(input);
    wrap.appendChild(panel);

    // Intercepta atribuições programáticas de .value para refletir no campo.
    var desc = Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value");
    Object.defineProperty(sel, "value", {
      configurable: true,
      get: function () { return desc.get.call(this); },
      set: function (v) { desc.set.call(this, v); sync(); }
    });

    var ativo = -1; // índice destacado no painel

    function sync() {
      var o = sel.options[sel.selectedIndex];
      input.value = o ? label(o) : "";
      if (sel.disabled && !input.disabled) input.disabled = true;
      if (!sel.disabled && input.disabled) input.disabled = false;
    }

    function build(filtro) {
      var f = (filtro || "").toLowerCase();
      panel.innerHTML = "";
      ativo = -1;
      var achou = false;
      Array.prototype.forEach.call(sel.options, function (o, i) {
        var lbl = label(o);
        if (f && lbl.toLowerCase().indexOf(f) === -1) return;
        achou = true;
        var it = document.createElement("div");
        it.className = "ss-opt" + (i === sel.selectedIndex ? " sel" : "");
        it.textContent = lbl || "—";
        it.dataset.i = String(i);
        it.addEventListener("mousedown", function (e) { e.preventDefault(); pick(i); });
        panel.appendChild(it);
      });
      if (!achou) {
        var e = document.createElement("div");
        e.className = "ss-empty";
        e.textContent = "Nada encontrado";
        panel.appendChild(e);
      }
    }

    function abrir() {
      if (sel.disabled) return;
      build(input.value === label(sel.options[sel.selectedIndex]) ? "" : input.value);
      panel.hidden = false;
      input.setAttribute("aria-expanded", "true");
    }
    function fechar() {
      panel.hidden = true;
      ativo = -1;
      input.setAttribute("aria-expanded", "false");
    }
    function pick(i) {
      if (sel.selectedIndex !== i) {
        sel.selectedIndex = i;
        sel.dispatchEvent(new Event("change", { bubbles: true }));
      }
      sync();
      fechar();
    }
    function visiveis() { return panel.querySelectorAll(".ss-opt"); }
    function destaca(n) {
      var its = visiveis();
      if (!its.length) return;
      ativo = (n + its.length) % its.length;
      its.forEach(function (el, k) { el.classList.toggle("active", k === ativo); });
      its[ativo].scrollIntoView({ block: "nearest" });
    }

    input.addEventListener("focus", function () { input.select(); abrir(); });
    input.addEventListener("click", abrir);
    input.addEventListener("input", function () { build(input.value); panel.hidden = false; });
    input.addEventListener("keydown", function (e) {
      if (e.key === "ArrowDown") { e.preventDefault(); if (panel.hidden) abrir(); destaca(ativo + 1); }
      else if (e.key === "ArrowUp") { e.preventDefault(); if (panel.hidden) abrir(); destaca(ativo - 1); }
      else if (e.key === "Enter") {
        if (!panel.hidden) {
          e.preventDefault();
          var its = visiveis();
          if (ativo >= 0 && its[ativo]) pick(Number(its[ativo].dataset.i));
          else if (its.length === 1) pick(Number(its[0].dataset.i));
        }
      } else if (e.key === "Escape") { if (!panel.hidden) { e.preventDefault(); sync(); fechar(); } }
    });
    input.addEventListener("blur", function () { setTimeout(function () { if (!panel.contains(document.activeElement)) sync(); }, 0); });
    document.addEventListener("mousedown", function (e) { if (!wrap.contains(e.target)) fechar(); });

    // Repopulação do select (innerHTML trocado por outro código) → re-sincroniza.
    new MutationObserver(function () {
      sync();
      if (!panel.hidden) build(input.value);
    }).observe(sel, { childList: true });

    sync();
  }

  function scan(root) {
    try { (root || document).querySelectorAll("select").forEach(enhance); } catch (e) {}
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { scan(); });
  } else { scan(); }

  // Pega selects inseridos depois e selects populados após a inserção.
  var mo = new MutationObserver(function (muts) {
    for (var i = 0; i < muts.length; i++) {
      var m = muts[i];
      if (m.target && m.target.tagName === "SELECT") enhance(m.target);
      if (m.addedNodes) {
        for (var j = 0; j < m.addedNodes.length; j++) {
          var n = m.addedNodes[j];
          if (n.nodeType !== 1) continue;
          if (n.tagName === "SELECT") enhance(n);
          else if (n.querySelectorAll) scan(n);
        }
      }
    }
  });
  mo.observe(document.documentElement, { childList: true, subtree: true });
})();
