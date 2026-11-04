const fs = require('fs');
const vm = require('vm');
const assert = require('assert');

const htmlPath = fs.existsSync('dashboard.html') ? 'dashboard.html' : 'upload/dashboard.html';
const html = fs.readFileSync(htmlPath, 'utf8');
const scriptMatches = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)];
const script = scriptMatches.at(-1)[1];

function harness(opts={}) {
  const elements = new Map();
  const stored = {...opts.stored};
  const opened = [];
  const copied = [];
  const blobs = [];

  function element(id='') {
    return {
      id,
      value: '',
      textContent: '',
      className: '',
      _html: '',
      children: [],
      get innerHTML() { return this._html; },
      set innerHTML(v) { this._html = v; this.children = []; },
      classList: {
        add() {},
        remove() {},
        contains() { return false; }
      },
      focus() {},
      click() {},
      appendChild(x) { this.children.push(x); },
      getAttribute(k) { return ''; }
    };
  }

  const document = {
    getElementById(id) {
      if (!elements.has(id)) elements.set(id, element(id));
      return elements.get(id);
    },
    querySelectorAll() { return []; },
    createElement: element
  };

  const ctx = {
    document,
    localStorage: {
      getItem(k) {
        if (opts.storageDenied) throw Error('SecurityError');
        return stored[k] ?? null;
      },
      setItem(k, v) { stored[k] = v; }
    },
    navigator: {},
    window: {
      open(...a) {
        opened.push(a);
        return opts.popupBlocked ? null : {};
      }
    },
    setTimeout() {},
    Blob: class {
      constructor(parts) {
        this.parts = parts;
        blobs.push(this);
      }
    },
    URL: { createObjectURL() { return 'blob:test'; } },
    console
  };

  if (!opts.clipboardAbsent) {
    ctx.navigator.clipboard = {
      writeText(t) {
        copied.push(t);
        return opts.clipboardDenied ? Promise.reject(Error('NotAllowedError')) : Promise.resolve();
      }
    };
  }

  vm.createContext(ctx);
  let startError = null;
  try {
    vm.runInContext(script, ctx);
  } catch(e) {
    startError = e.message;
  }

  return {
    ctx,
    elements,
    stored,
    opened,
    copied,
    blobs,
    startError,
    run(s) { return vm.runInContext(s, ctx); },
    text(id) { return elements.get(id)?.textContent; }
  };
}

console.log("==================================================");
console.log("EJECUTANDO SUITE DE PRUEBAS DE DASHBOARD (NODE.JS)");
console.log("==================================================");

let h = harness();
assert.strictEqual(h.startError, null, `Error de inicio del dashboard: ${h.startError}`);
assert.strictEqual(h.text('kpi-total'), 41, `Esperado total 41, obtenido: ${h.text('kpi-total')}`);
assert.strictEqual(h.text('kpi-pending'), 41, `Esperado pendientes 41, obtenido: ${h.text('kpi-pending')}`);
assert.strictEqual(h.elements.get('cards-container')?.children.length, 41, 'Esperadas 41 tarjetas');
console.log("  [OK] Carga inicial verificada: 41 prospectos, 41 pendientes.");

// 1. Filtro por país (Argentina: 19)
h.run("setCountryFilter('Argentina')");
assert.ok(h.text('filtered-count').includes('19 de 41'), `Filtro Argentina falló: ${h.text('filtered-count')}`);
console.log("  [OK] Filtro por país Argentina: exactamente 19 prospectos.");

// 2. Filtro por materia combinada (Química: 5)
h.run("resetFilters();document.getElementById('filter-materia').value='Química';applyFilters()");
assert.ok(h.text('filtered-count').includes('5 de 41'), `Filtro Química falló: ${h.text('filtered-count')}`);
console.log("  [OK] Filtro por materia Química: exactamente 5 prospectos.");

// 3. Filtro por nivel educativo cerrado (Universitario: exactamente 16, 0 pre-universitarios)
h.run("resetFilters();document.getElementById('filter-nivel').value='Universitario';applyFilters()");
assert.ok(h.text('filtered-count').includes('16 de 41'), `Filtro Universitario contaminado: ${h.text('filtered-count')}`);
console.log("  [OK] Filtro nivel cerrado Universitario: exactamente 16 prospectos puros.");

// 4. Búsqueda sin acentos (Normalización NFD)
h.run("resetFilters();document.getElementById('search-input').value='hernan';applyFilters()");
assert.ok(h.text('filtered-count').includes('3 de 41'), `Búsqueda 'hernan' falló: ${h.text('filtered-count')}`);

h.run("resetFilters();document.getElementById('search-input').value='cordoba';applyFilters()");
assert.ok(h.text('filtered-count').includes('1 de 41'), `Búsqueda 'cordoba' falló: ${h.text('filtered-count')}`);

h.run("resetFilters();document.getElementById('search-input').value='peru';applyFilters()");
assert.ok(h.text('filtered-count').includes('2 de 41'), `Búsqueda 'peru' falló: ${h.text('filtered-count')}`);
console.log("  [OK] Búsqueda sin acentos verificada (hernan: 3, cordoba: 1, peru: 2).");

// 5. Saludo genérico en pitch para nombres no personales
h = harness();
h.run("sendAndOpenLead('test_id','https://test.com','Física','Universitario','Alumno UADE','Máquinas Hidráulicas')");
assert.ok(h.copied[0].includes('¡Hola!'), 'Debe saludar genéricamente sin decir Alumno UADE');
assert.ok(!h.copied[0].includes('¡Hola Alumno UADE!'), 'No debe decir ¡Hola Alumno UADE!');
assert.ok(h.copied[0].includes('Máquinas Hidráulicas'), 'Debe reemplazar {{tema}}');
console.log("  [OK] Sustitución inteligente de saludo y tema (excluye 'Alumno UADE').");

// 6. Cronoshare: botón y advertencia de créditos
h = harness();
h.run("setCountryFilter('España');applyFilters()");
const cardsHtml = h.elements.get('cards-container').children.map(c => c._html).join(' ');
assert.ok(cardsHtml.includes('btn-action-crono'), 'Debe incluir clase btn-action-crono');
assert.ok(cardsHtml.includes('Requiere Créditos Pagos (Cronos)'), 'Debe mostrar badge de créditos en Cronoshare');
console.log("  [OK] Manejo transparente de Cronoshare (CTA crediticio separado).");

// 7. Exportación CSV con columnas CRM
h = harness();
h.run('exportToCSV()');
assert.strictEqual(h.blobs.length, 1, 'Debe generar 1 Blob de CSV');
const csvContent = h.blobs[0].parts[0];
assert.strictEqual(csvContent.charCodeAt(0), 0xfeff, 'BOM UTF-8 requerido');
assert.ok(csvContent.includes('Notas_CRM') && csvContent.includes('Precio_Acordado'), 'Columnas de CRM en CSV');
assert.strictEqual(csvContent.trim().split('\n').length - 1, 41, 'Esperadas 41 filas en CSV exportado');
console.log("  [OK] Exportación CSV con BOM UTF-8 y campos de CRM.");

console.log("==================================================");
console.log("✅ TODAS LAS PRUEBAS DE DASHBOARD PASARON CON ÉXITO");
console.log("==================================================");
