const fs = require('fs');
const vm = require('vm');

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
      appendChild(x) { this.children.push(x); }
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

const results = [];
function record(name, details) { results.push({name, ...details}); }

let h = harness();
record('initial', {
  startError: h.startError,
  total: h.text('kpi-total'),
  pending: h.text('kpi-pending'),
  cards: h.elements.get('cards-container')?.children.length || 0
});

h.run("setCountryFilter('Argentina')");
record('country_filter', {
  result: h.text('filtered-count'),
  kpiTotal: h.text('kpi-total')
});

h.run("resetFilters();document.getElementById('filter-materia').value='Química';applyFilters()");
record('subject_includes_combined', { result: h.text('filtered-count') });

h.run("resetFilters();document.getElementById('search-input').value='zzzz-no-match';applyFilters()");
record('empty_filter', {
  result: h.text('filtered-count'),
  cards: h.elements.get('cards-container')?.children.length || 0
});

// Test unique ID / Cronoshare
h = harness();
if (h.run("typeof RAW_DATA !== 'undefined' && RAW_DATA.length > 0")) {
  h.run("saveStatus(getLeadId(RAW_DATA[35]),'Contactado')");
  const storedObj = h.stored.alumnos_lead_statuses ? JSON.parse(h.stored.alumnos_lead_statuses) : {};
  record('shared_cronoshare_id', {
    contacted: h.text('kpi-contacted'),
    pending: h.text('kpi-pending'),
    storedKeys: Object.keys(storedObj).length,
    affectedCsvRows: h.run("RAW_DATA.map((r,i)=>({r,i})).filter(x=>getLeadId(x.r)===getLeadId(RAW_DATA[35])).map(x=>x.i+2)")
  });
}

// Clipboard denied test
h = harness({clipboardDenied: true});
if (h.run("typeof RAW_DATA !== 'undefined' && RAW_DATA.length > 0")) {
  h.run("sendAndOpenLead(getLeadId(RAW_DATA[0]),RAW_DATA[0]['enlace al anuncio'],RAW_DATA[0].materia,RAW_DATA[0]['nivel educativo'])");
  record('clipboard_denied_contacted', {
    contacted: h.text('kpi-contacted'),
    openCalls: h.opened.length
  });
}

// Clipboard absent test
h = harness({clipboardAbsent: true});
let err = null;
if (h.run("typeof RAW_DATA !== 'undefined' && RAW_DATA.length > 0")) {
  try {
    h.run("sendAndOpenLead(getLeadId(RAW_DATA[0]),RAW_DATA[0]['enlace al anuncio'],RAW_DATA[0].materia,RAW_DATA[0]['nivel educativo'])");
  } catch(e) {
    err = e.message;
  }
  record('clipboard_absent', {
    error: err,
    openCalls: h.opened.length,
    contacted: h.text('kpi-contacted')
  });
}

// Popup blocked test
h = harness({popupBlocked: true});
if (h.run("typeof RAW_DATA !== 'undefined' && RAW_DATA.length > 0")) {
  h.run("sendAndOpenLead(getLeadId(RAW_DATA[0]),RAW_DATA[0]['enlace al anuncio'],RAW_DATA[0].materia,RAW_DATA[0]['nivel educativo'])");
  record('popup_blocked_contacted', { contacted: h.text('kpi-contacted') });
}

// Closed regression test
h = harness();
if (h.run("typeof RAW_DATA !== 'undefined' && RAW_DATA.length > 0")) {
  h.run("saveStatus(getLeadId(RAW_DATA[0]),'Cerrado');sendAndOpenLead(getLeadId(RAW_DATA[0]),RAW_DATA[0]['enlace al anuncio'],RAW_DATA[0].materia,RAW_DATA[0]['nivel educativo'])");
  record('closed_regression', {
    closed: h.text('kpi-closed'),
    contacted: h.text('kpi-contacted')
  });
}

// Export test
h.run('exportToCSV()');
if (h.blobs.length > 0) {
  record('export', {
    header: h.blobs[0].parts[0].split('\n')[0],
    bom: h.blobs[0].parts[0].charCodeAt(0) === 0xfeff,
    rows: h.blobs[0].parts[0].trim().split('\n').length - 1
  });
}

record('storage_null', { startError: harness({stored: {alumnos_lead_statuses: 'null'}}).startError });
record('storage_invalid_json', { startError: harness({stored: {alumnos_lead_statuses: 'broken'}}).startError });
record('storage_denied', { startError: harness({storageDenied: true}).startError });

h = harness();
h.run("saveStoredPitch('{{materia}} y {{materia}}: {{nivel}} / {{nivel}}');copyLeadPitchOnly('Física','Secundario')");
record('placeholder_repeated', { copied: h.copied[0] });

h = harness();
h.run("RAW_DATA[0].materia=\"Física d'ejemplo\";applyFilters()");
const firstCardHtml = h.elements.get('cards-container')?.children[0]?._html || '';
const handlerMatch = firstCardHtml.match(/onclick="([^"]+)"/);
let syntaxError = null;
if (handlerMatch) {
  try {
    new vm.Script(handlerMatch[1]);
  } catch(e) {
    syntaxError = e.message;
  }
}
record('apostrophe_inline_handler', { syntaxError, hasInlineHandler: !!handlerMatch });

h = harness();
h.run("RAW_DATA[0]['mensaje/descripción']='<b id=untrusted-marker>test</b>';applyFilters()");
const cardUnescapedHtml = h.elements.get('cards-container')?.children[0]?._html || '';
record('unescaped_html_sink', {
  markupPassedThrough: cardUnescapedHtml.includes('<b id=untrusted-marker>test</b>')
});

if (!fs.existsSync('audit_work')) fs.mkdirSync('audit_work');
fs.writeFileSync('audit_work/behavior_results.json', JSON.stringify(results, null, 2));
console.log(JSON.stringify(results, null, 2));
