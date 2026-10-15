/* Painel CAGED - Baixada Fluminense
   Consome data/dashboard_data.json (gerado por build_data.py) */
(() => {
  "use strict";

  const COLOR = {
    adm: "#1d4ed8",
    des: "#e11d48",
    admSoft: "#93b4f7",
    desSoft: "#f4a0b3",
    pos: "#15803d",
    neg: "#dc2626",
    grid: "#eef2f7",
    tick: "#64748b",
    cat: ["#1d4ed8", "#e11d48", "#0ea5e9", "#f59e0b", "#14b8a6", "#a855f7",
          "#84cc16", "#ec4899", "#f97316", "#64748b", "#06b6d4", "#8b5cf6"],
  };

  const DATA = { ready: false };
  const state = { mun: new Set(), sex: "all" };
  const charts = {};

  /* ---------------- formatters ---------------- */
  const nfInt = new Intl.NumberFormat("pt-BR");
  const nfMoney = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  const nfMoney2 = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 2 });
  const nfPct = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1 });
  const fmtInt = (n) => nfInt.format(Math.round(n || 0));
  const fmtMoney = (n) => nfMoney.format(n || 0);
  const fmtMoney2 = (n) => nfMoney2.format(n || 0);
  const fmtPct = (n) => `${nfPct.format(n || 0)}%`;
  const short = (s, n = 30) => (s && s.length > n ? s.slice(0, n - 1) + "…" : s || "");

  /* ---------------- value-labels plugin ---------------- */
  const valueLabels = {
    id: "valueLabels",
    afterDatasetsDraw(chart) {
      const opts = (chart.options.plugins && chart.options.plugins.valueLabels) || {};
      if (opts.display === false) return;
      const fmt = opts.fmt || fmtInt;
      const horizontal = chart.options.indexAxis === "y";
      const ctx = chart.ctx;
      chart.data.datasets.forEach((ds, di) => {
        if (ds.hidden) return;
        const meta = chart.getDatasetMeta(di);
        if (!meta || meta.hidden) return;
        meta.data.forEach((el, i) => {
          const v = ds.data[i];
          if (v === null || v === undefined || v === 0) return;
          const txt = fmt(Math.abs(v));
          ctx.save();
          ctx.font = "600 10px Inter, system-ui, sans-serif";
          ctx.fillStyle = "#475569";
          if (horizontal) {
            const sign = el.x >= el.base ? 1 : -1;
            ctx.textAlign = sign > 0 ? "left" : "right";
            ctx.textBaseline = "middle";
            ctx.fillText(txt, el.x + sign * 5, el.y);
          } else {
            ctx.textAlign = "center";
            ctx.textBaseline = "bottom";
            ctx.fillText(txt, el.x, el.y - 3);
          }
          ctx.restore();
        });
      });
    },
  };

  /* ---------------- chart helpers ---------------- */
  function draw(id, config) {
    const host = document.getElementById(id);
    if (!host) return;
    const canvas = host.querySelector("canvas");
    if (charts[id]) charts[id].destroy();
    config.plugins = (config.plugins || []).concat([valueLabels]);
    charts[id] = new Chart(canvas.getContext("2d"), config);
  }

  function barOpts({ horizontal = false, money = false, legend = false } = {}) {
    const yAxis = horizontal
      ? { grid: { display: false }, ticks: { font: { size: 10 }, color: COLOR.tick }, border: { display: false } }
      : { grid: { display: true, color: COLOR.grid }, ticks: { font: { size: 10 }, color: COLOR.tick }, border: { display: false } };
    const xAxis = horizontal
      ? { grid: { display: true, color: COLOR.grid }, ticks: { font: { size: 10 }, color: COLOR.tick }, border: { display: false } }
      : { grid: { display: false }, ticks: { font: { size: 10 }, color: COLOR.tick }, border: { display: false } };
    const valueFmt = money ? fmtMoney : fmtInt;
    return {
      responsive: true,
      maintainAspectRatio: false,
      indexAxis: horizontal ? "y" : "x",
      layout: { padding: { top: 6, right: 14 } },
      plugins: {
        legend: legend
          ? { display: true, position: "top", align: "end",
              labels: { boxWidth: 9, boxHeight: 9, usePointStyle: true, pointStyle: "circle", font: { size: 11 }, color: "#334155" } }
          : { display: false },
        valueLabels: { display: true, fmt: valueFmt },
        tooltip: {
          callbacks: {
            label: (c) => `${c.dataset.label}: ${valueFmt(c.parsed[horizontal ? "x" : "y"])}`,
          },
        },
      },
      scales: { x: xAxis, y: yAxis },
    };
  }

  function admDesDatasets(adm, des) {
    return [
      { label: "Admissões", data: adm, backgroundColor: COLOR.adm, borderRadius: 4, maxBarThickness: 34 },
      { label: "Desligamentos", data: des, backgroundColor: COLOR.des, borderRadius: 4, maxBarThickness: 34 },
    ];
  }

  /* ---------------- filters ---------------- */
  const inMun = (mi) => state.mun.has(mi);
  const inSex = (xi) => state.sex === "all" || String(state.sex) === String(xi);

  /* ---------------- aggregations ---------------- */
  function totals() {
    const t = { adm: 0, des: 0, nadm: 0, ndes: 0, asal: 0, dsal: 0 };
    for (const r of DATA.cube) {
      const [mi, , xi, , classe, n, ns, sal] = r;
      if (!inMun(mi) || !inSex(xi)) continue;
      if (classe === 0) { t.adm += n; t.nadm += ns; t.asal += sal; }
      else { t.des += n; t.ndes += ns; t.dsal += sal; }
    }
    return t;
  }

  function byKey(rows, keyIdx, dimLen, valueSelector) {
    const out = Array.from({ length: dimLen }, () => ({ adm: 0, des: 0 }));
    for (const r of rows) {
      if (!inMun(r[0]) || !inSex(r[2])) continue;
      valueSelector(r, out[r[keyIdx]]);
    }
    return out;
  }

  /* ---------------- renderers ---------------- */
  function renderMeta() {
    const m = DATA.meta;
    document.getElementById("meta-competencia").textContent = `competência ${m.competencia.slice(4)}/${m.competencia.slice(0, 4)}`;
    document.getElementById("meta-chips").innerHTML = [
      `<span class="mchip">Fonte: <b>Novo CAGED / MTE</b></span>`,
      `<span class="mchip">Competência: <b>${m.competencia}</b></span>`,
      `<span class="mchip">Registros: <b>${fmtInt(m.total_registros)}</b></span>`,
      `<span class="mchip">Atualizado: <b>${m.gerado_em}</b></span>`,
    ].join("");
    document.getElementById("footer-gen").textContent = `Agregados gerados em ${m.gerado_em}.`;
  }

  function renderFilters() {
    const mun = document.getElementById("f-mun");
    const sex = document.getElementById("f-sex");

    const options = [`<option value="all">Todos os municípios (${DATA.municipios.length})</option>`];
    DATA.municipios
      .map((m, i) => ({ ...m, i }))
      .sort((a, b) => a.name.localeCompare(b.name, "pt-BR"))
      .forEach((m) => options.push(`<option value="${m.i}">${m.name}</option>`));
    mun.innerHTML = options.join("");
    mun.value = "all";

    sex.innerHTML = `<option value="all">Todos</option>` +
      DATA.sexos.map((s, i) => `<option value="${i}">${s.name}</option>`).join("");
    sex.value = "all";

    mun.addEventListener("change", () => {
      state.mun = mun.value === "all" ? new Set(DATA.municipios.map((_, i) => i)) : new Set([Number(mun.value)]);
      syncChips();
      renderAll();
    });
    sex.addEventListener("change", () => {
      state.sex = sex.value;
      renderAll();
    });

    document.querySelectorAll(".chip[data-preset]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const p = btn.dataset.preset;
        if (p === "all") {
          state.mun = new Set(DATA.municipios.map((_, i) => i));
          mun.value = "all";
        } else {
          const idx = DATA.municipios.map((m, i) => (m.baixada ? i : -1)).filter((i) => i >= 0);
          state.mun = new Set(idx);
          mun.value = "all";
        }
        syncChips();
        renderAll();
      });
    });

    state.mun = new Set(DATA.municipios.map((_, i) => i));
    syncChips();
  }

  function syncChips() {
    const all = state.mun.size === DATA.municipios.length;
    const baix = DATA.municipios.map((m, i) => (m.baixada ? i : -1)).filter((i) => i >= 0);
    const isBaix = !all && baix.length === state.mun.size && baix.every((i) => state.mun.has(i));
    document.querySelectorAll(".chip[data-preset]").forEach((b) => {
      b.classList.toggle("is-active", (b.dataset.preset === "all" && all) || (b.dataset.preset === "baixada" && isBaix));
    });
    const names = [...state.mun].map((i) => DATA.municipios[i].name);
    document.getElementById("filter-note").textContent =
      all ? "Exibindo toda a região metropolitana presente na base." :
      isBaix ? "Exibindo o núcleo da Baixada Fluminense." :
      `${names.length} município(s): ${names.join(", ")}`;
  }

  function renderKpis() {
    const t = totals();
    const saldo = t.adm - t.des;
    const cards = [
      { label: "Admissões", value: fmtInt(t.adm), sub: "saldomovimentação = +1", c: COLOR.adm },
      { label: "Desligamentos", value: fmtInt(t.des), sub: "saldomovimentação = -1", c: COLOR.des },
      { label: "Saldo", value: (saldo >= 0 ? "+" : "") + fmtInt(saldo), sub: "admissões − desligamentos", c: saldo >= 0 ? COLOR.pos : COLOR.neg },
      { label: "Salário médio · admissões", value: fmtMoney(t.nadm ? t.asal / t.nadm : 0), sub: `${fmtInt(t.nadm)} salários válidos`, c: "#0ea5e9" },
      { label: "Salário médio · desligamentos", value: fmtMoney(t.ndes ? t.dsal / t.ndes : 0), sub: `${fmtInt(t.ndes)} salários válidos`, c: "#f59e0b" },
      { label: "Movimentações", value: fmtInt(t.adm + t.des), sub: "admissões + desligamentos", c: "#a855f7" },
    ];
    document.getElementById("kpis").innerHTML = cards.map((c) => `
      <div class="kpi" style="--kpi-c:${c.c}">
        <div class="kpi__label">${c.label}</div>
        <div class="kpi__value">${c.value}</div>
        <div class="kpi__sub">${c.sub}</div>
      </div>`).join("");
  }

  function renderMunicipio() {
    const agg = Array.from({ length: DATA.municipios.length }, () => ({ adm: 0, des: 0 }));
    for (const r of DATA.cube) {
      const [mi, , xi, , classe, n] = r;
      if (!inMun(mi) || !inSex(xi)) continue;
      if (classe === 0) agg[mi].adm += n; else agg[mi].des += n;
    }
    const items = agg.map((a, i) => ({ ...a, i, total: a.adm + a.des }))
      .filter((a) => a.total > 0)
      .sort((a, b) => a.total - b.total); // ascending -> maior no topo (eixo y)
    if (!items.length) { draw("c-municipio", { type: "bar", data: { labels: [], datasets: [] }, options: barOpts({ horizontal: true }) }); return; }
    draw("c-municipio", {
      type: "bar",
      data: {
        labels: items.map((a) => DATA.municipios[a.i].name),
        datasets: admDesDatasets(items.map((a) => a.adm), items.map((a) => a.des)),
      },
      options: barOpts({ horizontal: true, legend: true }),
    });
  }

  function renderSetor() {
    const agg = Array.from({ length: DATA.secoes.length }, () => ({ adm: 0, des: 0, asal: 0, dsal: 0, nadm: 0, ndes: 0 }));
    for (const r of DATA.cube) {
      const [mi, si, xi, , classe, n, ns, sal] = r;
      if (!inMun(mi) || !inSex(xi)) continue;
      if (classe === 0) { agg[si].adm += n; agg[si].asal += sal; agg[si].nadm += ns; }
      else { agg[si].des += n; agg[si].dsal += sal; agg[si].ndes += ns; }
    }
    const items = agg.map((a, i) => ({ ...a, i, saldo: a.adm - a.des, total: a.adm + a.des }))
      .filter((a) => a.total > 0).sort((a, b) => a.saldo - b.saldo);

    draw("c-setor", {
      type: "bar",
      data: {
        labels: items.map((a) => short(DATA.secoes[a.i].name, 40)),
        datasets: [{
          label: "Saldo",
          data: items.map((a) => a.saldo),
          backgroundColor: items.map((a) => (a.saldo >= 0 ? COLOR.pos : COLOR.neg)),
          borderRadius: 4, maxBarThickness: 22,
        }],
      },
      options: (() => {
        const o = barOpts({ horizontal: true });
        o.plugins.tooltip.callbacks.label = (c) => {
          const a = items[c.dataIndex];
          return [`Saldo: ${fmtInt(a.saldo)}`, `Admissões: ${fmtInt(a.adm)} · Desligamentos: ${fmtInt(a.des)}`];
        };
        return o;
      })(),
    });

    const salItems = agg.map((a, i) => ({
      i,
      mean: (a.nadm + a.ndes) ? (a.asal + a.dsal) / (a.nadm + a.ndes) : 0,
      total: a.adm + a.des,
    })).filter((a) => a.total > 0 && a.mean > 0).sort((a, b) => a.mean - b.mean);

    draw("c-sal-setor", {
      type: "bar",
      data: {
        labels: salItems.map((a) => short(DATA.secoes[a.i].name, 38)),
        datasets: [{ label: "Salário médio", data: salItems.map((a) => a.mean), backgroundColor: COLOR.admSoft, borderRadius: 4, maxBarThickness: 22 }],
      },
      options: barOpts({ horizontal: true, money: true }),
    });
  }

  function renderDesl() {
    const rows = DATA.desl; // [mi,xi,ti,n,ns,sal]
    const agg = Array.from({ length: DATA.tipos_desl.length }, () => 0);
    for (const r of rows) {
      if (!inMun(r[0]) || !inSex(r[1])) continue;
      agg[r[2]] += r[3];
    }
    const items = agg.map((n, i) => ({ n, i })).filter((a) => a.n > 0).sort((a, b) => b.n - a.n);
    const shortName = (s) => s
      .replace(/^Desligamento por /i, "")
      .replace(/^Desligamento /i, "")
      .replace(/demissão sem justa causa/i, "sem justa causa")
      .replace(/demissão com justa causa/i, "com justa causa")
      .replace(/Término contrato trabalho prazo determinado/i, "Fim de contrato")
      .replace(/Acordo entre empregado e empregador/i, "Acordo")
      .replace(/de Tipo Ignorado/i, "Ignorado");
    draw("c-desl", {
      type: "doughnut",
      data: {
        labels: items.map((a) => shortName(DATA.tipos_desl[a.i].name)),
        datasets: [{
          data: items.map((a) => a.n),
          backgroundColor: items.map((_, k) => COLOR.cat[k % COLOR.cat.length]),
          borderColor: "#fff", borderWidth: 2,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false, cutout: "58%",
        plugins: {
          valueLabels: { display: false },
          legend: { position: "right", labels: { boxWidth: 9, boxHeight: 9, usePointStyle: true, pointStyle: "circle", font: { size: 10.5 }, color: "#334155" } },
          tooltip: { callbacks: { label: (c) => `${c.label}: ${fmtInt(c.parsed)}` } },
        },
      },
    });
  }

  function renderSexo() {
    const agg = byKey(DATA.cube, 2, DATA.sexos.length, (r, o) => { if (r[4] === 0) o.adm += r[5]; else o.des += r[5]; });
    const items = agg.map((a, i) => ({ ...a, i })).filter((a) => a.adm + a.des > 0);
    draw("c-sexo", {
      type: "bar",
      data: { labels: items.map((a) => DATA.sexos[a.i].name), datasets: admDesDatasets(items.map((a) => a.adm), items.map((a) => a.des)) },
      options: barOpts({ legend: true }),
    });
  }

  function renderRaca() {
    const agg = byKey(DATA.raca, 2, DATA.racas.length, (r, o) => { if (r[3] === 0) o.adm += r[4]; else o.des += r[4]; });
    const items = agg.map((a, i) => ({ ...a, i })).filter((a) => a.adm + a.des > 0).sort((a, b) => (b.adm + b.des) - (a.adm + a.des));
    draw("c-raca", {
      type: "bar",
      data: { labels: items.map((a) => DATA.racas[a.i].name), datasets: admDesDatasets(items.map((a) => a.adm), items.map((a) => a.des)) },
      options: barOpts({ legend: true }),
    });
  }

  function renderFaixa() {
    const agg = byKey(DATA.cube, 3, DATA.faixas.length, (r, o) => { if (r[4] === 0) o.adm += r[5]; else o.des += r[5]; });
    const items = agg.map((a, i) => ({ ...a, i }));
    draw("c-faixa", {
      type: "bar",
      data: { labels: items.map((a) => DATA.faixas[a.i].name), datasets: admDesDatasets(items.map((a) => a.adm), items.map((a) => a.des)) },
      options: (() => { const o = barOpts({ legend: true }); o.scales.x.ticks.maxRotation = 40; o.scales.x.ticks.minRotation = 40; return o; })(),
    });
  }

  function renderGrau() {
    const agg = byKey(DATA.grau, 2, DATA.graus.length, (r, o) => { if (r[3] === 0) o.adm += r[4]; else o.des += r[4]; });
    const items = agg.map((a, i) => ({ ...a, i })).filter((a) => a.adm + a.des > 0);
    draw("c-grau", {
      type: "bar",
      data: { labels: items.map((a) => DATA.graus[a.i].name), datasets: admDesDatasets(items.map((a) => a.adm), items.map((a) => a.des)) },
      options: (() => { const o = barOpts({ legend: true }); o.scales.x.ticks.maxRotation = 40; o.scales.x.ticks.minRotation = 40; return o; })(),
    });
  }

  function renderCbo() {
    const agg = Array.from({ length: DATA.ocupacoes.length }, () => ({ adm: 0, des: 0 }));
    for (const r of DATA.cbo) {
      if (!inMun(r[0]) || !inSex(r[1])) continue;
      agg[r[2]].adm += r[3];
      agg[r[2]].des += r[4];
    }
    const items = agg.map((a, i) => ({ ...a, i, total: a.adm + a.des }))
      .filter((a) => a.total > 0).sort((a, b) => b.total - a.total).slice(0, 10);
    const ordered = items.slice().sort((a, b) => a.total - b.total);
    draw("c-cbo", {
      type: "bar",
      data: {
        labels: ordered.map((a) => short(DATA.ocupacoes[a.i].name, 46)),
        datasets: admDesDatasets(ordered.map((a) => a.adm), ordered.map((a) => a.des)),
      },
      options: barOpts({ horizontal: true, legend: true }),
    });
  }

  function renderFlags() {
    const agg = { intermitente: 0, parcial: 0, aprendiz: 0, pcd: 0, adm: 0 };
    for (const r of DATA.flags) {
      const [mi, xi, classe, inter, parc, apre, pcd, n] = r;
      if (!inMun(mi) || !inSex(xi)) continue;
      if (classe === 0) {
        agg.intermitente += inter; agg.parcial += parc; agg.aprendiz += apre; agg.pcd += pcd; agg.adm += n;
      }
    }
    const cards = [
      { t: "Trabalho intermitente", v: agg.intermitente, base: agg.adm, c: "#0ea5e9" },
      { t: "Trabalho parcial", v: agg.parcial, base: agg.adm, c: "#14b8a6" },
      { t: "Aprendizes", v: agg.aprendiz, base: agg.adm, c: "#f59e0b" },
      { t: "Pessoas com deficiência", v: agg.pcd, base: agg.adm, c: "#a855f7" },
    ];
    document.getElementById("c-flags").innerHTML = cards.map((c) => {
      const pct = c.base ? (c.v / c.base) * 100 : 0;
      return `<div class="mini" style="--kpi-c:${c.c}">
        <div class="mini__t">${c.t}</div>
        <div class="mini__v">${fmtInt(c.v)} <small>(${fmtPct(pct)} das admissões)</small></div>
        <div class="mini__bar"><i style="width:${Math.min(100, pct * 4)}%;background:${c.c}"></i></div>
      </div>`;
    }).join("");
  }

  function renderAll() {
    renderKpis();
    renderMunicipio();
    renderSetor();
    renderDesl();
    renderSexo();
    renderRaca();
    renderFaixa();
    renderGrau();
    renderCbo();
    renderFlags();
  }

  function boot(payload) {
    Object.assign(DATA, payload, { ready: true });
    renderMeta();
    renderFilters();
    renderAll();
  }

  fetch("data/dashboard_data.json", { cache: "no-store" })
    .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
    .then(boot)
    .catch((err) => {
      document.getElementById("kpis").innerHTML =
        `<div class="kpi" style="--kpi-c:#dc2626"><div class="kpi__label">Erro</div><div class="kpi__value">Falha ao carregar</div><div class="kpi__sub">${err.message}. Execute <code>python3 build_data.py</code>.</div></div>`;
    });
})();
