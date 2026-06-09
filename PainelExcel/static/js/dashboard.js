let RAW_DATA = [];
let CURRENT_CHART = null;

function detectColsAndTypes(data){
  const cols = Object.keys(data[0] || {});
  const types = {};
  cols.forEach(c=>{
    const sample = data.slice(0,20).map(r=>r[c]).filter(v=>v!==null && v!==undefined);
    const numCount = sample.filter(v=> typeof v === 'number' || (!isNaN(Number(v)) && v!=='')).length;
    const dateCount = sample.filter(v=> {
      const d = Date.parse(v);
      return !isNaN(d);
    }).length;
    if(numCount >= sample.length*0.6 && sample.length>0) types[c]='number';
    else if(dateCount >= sample.length*0.6 && sample.length>0) types[c]='date';
    else types[c]='string';
  });
  return {cols, types};
}

function renderTable(data){
  const tbody = document.getElementById('tbody');
  const thead = document.getElementById('thead');
  if(!data || data.length===0){
    thead.innerHTML = '<tr><th>No data</th></tr>';
    tbody.innerHTML = '';
    return;
  }
  const cols = Object.keys(data[0]);
  thead.innerHTML = '<tr>' + cols.map(c=>`<th>${c}</th>`).join('') + '</tr>';
  tbody.innerHTML = data.map(r=>'<tr>'+cols.map(c=>`<td>${(r[c]!==null&&r[c]!==undefined)?r[c]:' '}</td>`).join('')+'</tr>').join('');
}

function createFilters(cols, types, data){
  const container = document.getElementById('filters');
  container.innerHTML = '';

  // detect director and area columns
  const dirCol = cols.find(c=>/diretoria|direção|diretoria/i.test(c));
  const areaCol = cols.find(c=>/\barea\b|\bárea\b/i.test(c));

  // prioritized order: director first
  let ordered = [...cols];
  if(dirCol){ ordered = [dirCol, ...ordered.filter(c=>c!==dirCol)]; }
  // ensure area follows director in ordering when present
  if(areaCol && dirCol){ ordered = ordered.filter(c=>c!==areaCol); const dirPos = ordered.indexOf(dirCol); ordered.splice(dirPos+1,0,areaCol); }

  // detect year/month strategy: if explicit 'ano'/'mes' cols exist, use them; otherwise use first date column
  const hasAno = cols.find(c=>/^(ano|year)$/i.test(c));
  const hasMes = cols.find(c=>/^(mes|month)$/i.test(c));
  const dateCol = cols.find(c=> types[c]==='date');

  // render hierarchical Diretor/Area selects if available
  if(dirCol){
    const wrap = document.createElement('div');
    wrap.style.marginBottom='8px';
    const lbl = document.createElement('label'); lbl.textContent = dirCol + ':'; lbl.style.display='block'; wrap.appendChild(lbl);
    const selDir = document.createElement('select'); selDir.id='filter-diretoria'; selDir.dataset.col = dirCol;
    const dirVals = Array.from(new Set(RAW_DATA.map(r=>r[dirCol]).filter(v=>v!==null && v!==undefined))).sort();
    selDir.innerHTML = '<option value="">(All)</option>' + dirVals.map(v=>`<option value="${v}">${v}</option>`).join('');
    wrap.appendChild(selDir);
    container.appendChild(wrap);

    if(areaCol){
      const wrapA = document.createElement('div'); wrapA.style.marginBottom='8px';
      const lblA = document.createElement('label'); lblA.textContent = areaCol + ':'; lblA.style.display='block'; wrapA.appendChild(lblA);
      const selArea = document.createElement('select'); selArea.id='filter-area'; selArea.dataset.col = areaCol;
      const areaVals = Array.from(new Set(RAW_DATA.map(r=>r[areaCol]).filter(v=>v!==null && v!==undefined))).sort();
      selArea.innerHTML = '<option value="">(All)</option>' + areaVals.map(v=>`<option value="${v}">${v}</option>`).join('');
      wrapA.appendChild(selArea);
      container.appendChild(wrapA);

      selDir.addEventListener('change', ()=>{
        const selected = selDir.value;
        const filteredAreas = Array.from(new Set(RAW_DATA.filter(r=> selected==='' || String(r[dirCol])===String(selected)).map(r=>r[areaCol]).filter(v=>v!==null && v!==undefined))).sort();
        selArea.innerHTML = '<option value="">(All)</option>' + filteredAreas.map(v=>`<option value="${v}">${v}</option>`).join('');
      });
    }
  }

  ordered.forEach(c=>{
    // skip adding ano/mes here if we will handle them specially
    if(hasAno && /^ano$/i.test(c)) return;
    if(hasMes && /^mes$/i.test(c)) return;

    // we'll handle director/area specially above
    if(c === dirCol || c === areaCol) return;

    const t = types[c];
    const wrap = document.createElement('div');
    wrap.style.marginBottom='8px';
    const label = document.createElement('label');
    label.textContent = c + ':';
    label.style.display='block';
    wrap.appendChild(label);

    if(t==='string'){
      const vals = Array.from(new Set(data.map(r=>r[c]).filter(v=>v!==null && v!==undefined))).slice(0,200);
      const sel = document.createElement('select');
      sel.dataset.col = c;
      const optAll = document.createElement('option'); optAll.value=''; optAll.text='(All)'; sel.appendChild(optAll);
      vals.forEach(v=>{ const o=document.createElement('option'); o.value=v; o.text=v; sel.appendChild(o); });
      wrap.appendChild(sel);
    } else if(t==='number'){
      const nums = data.map(r=>Number(r[c])||0);
      const min = Math.min(...nums); const max = Math.max(...nums);
      const l = document.createElement('div'); l.textContent = `range: ${min} — ${max}`;
      const inpMin = document.createElement('input'); inpMin.type='number'; inpMin.placeholder=min; inpMin.dataset.col=c; inpMin.style.width='45%';
      const inpMax = document.createElement('input'); inpMax.type='number'; inpMax.placeholder=max; inpMax.dataset.col=c; inpMax.style.width='45%';
      wrap.appendChild(l); wrap.appendChild(inpMin); wrap.appendChild(inpMax);
    } else if(t==='date'){
      const inpFrom = document.createElement('input'); inpFrom.type='date'; inpFrom.dataset.col=c;
      const inpTo = document.createElement('input'); inpTo.type='date'; inpTo.dataset.col=c;
      wrap.appendChild(inpFrom); wrap.appendChild(inpTo);
    }
    container.appendChild(wrap);
  });

  // Year/Month controls: prefer explicit columns if present
  if(hasAno || hasMes || dateCol){
    const ymWrap = document.createElement('div'); ymWrap.style.marginTop='6px';
    if(hasAno && hasMes){
      // ano select
      const lblA = document.createElement('label'); lblA.textContent='Ano:'; lblA.style.display='block'; ymWrap.appendChild(lblA);
      const selA = document.createElement('select'); selA.id='filter-ano'; selA.dataset.col = hasAno; ymWrap.appendChild(selA);
      // mes select
      const lblM = document.createElement('label'); lblM.textContent='Mês:'; lblM.style.display='block'; ymWrap.appendChild(lblM);
      const selM = document.createElement('select'); selM.id='filter-mes'; selM.dataset.col = hasMes; ymWrap.appendChild(selM);

      // populate from distinct values
      const anos = Array.from(new Set(RAW_DATA.map(r=>r[hasAno]).filter(v=>v!==undefined && v!==null))).sort();
      selA.innerHTML = '<option value="">(All)</option>' + anos.map(a=>`<option value="${a}">${a}</option>`).join('');
      selA.addEventListener('change', ()=>{
        const ano = selA.value;
        const meses = Array.from(new Set(RAW_DATA.filter(r=> (ano===''||r[hasAno]==ano)).map(r=>r[hasMes]).filter(v=>v!==undefined && v!==null))).sort();
        selM.innerHTML = '<option value="">(All)</option>' + meses.map(m=>`<option value="${m}">${m}</option>`).join('');
      });
    } else if(dateCol){
      const lblA = document.createElement('label'); lblA.textContent='Ano:'; lblA.style.display='block'; ymWrap.appendChild(lblA);
      const selA = document.createElement('select'); selA.id='filter-ano'; selA.dataset.col = dateCol; ymWrap.appendChild(selA);
      const lblM = document.createElement('label'); lblM.textContent='Mês:'; lblM.style.display='block'; ymWrap.appendChild(lblM);
      const selM = document.createElement('select'); selM.id='filter-mes'; selM.dataset.col = dateCol; ymWrap.appendChild(selM);

      const years = Array.from(new Set(data.map(r=>{ const d = Date.parse(r[dateCol]); return isNaN(d)?null:(new Date(d)).getFullYear() }).filter(v=>v!==null))).sort();
      selA.innerHTML = '<option value="">(All)</option>' + years.map(y=>`<option value="${y}">${y}</option>`).join('');
      selA.addEventListener('change', ()=>{
        const year = selA.value;
        const months = Array.from(new Set(data.filter(r=>{ const d=Date.parse(r[dateCol]); if(isNaN(d)) return false; const dt=new Date(d); return year===''||dt.getFullYear()==Number(year) }).map(r=>{ const d=Date.parse(r[dateCol]); return new Date(d).getMonth()+1 })).filter(v=>v)).sort((a,b)=>a-b);
        selM.innerHTML = '<option value="">(All)</option>' + months.map(m=>`<option value="${m}">${m}</option>`).join('');
      });
    }
    container.appendChild(ymWrap);
  }
}

function readFilters(){
  const filters = {};
  document.querySelectorAll('#filters select').forEach(s=>{ if(s.value && s.dataset.col) filters[s.dataset.col]=s.value });
  document.querySelectorAll('#filters input[type=number]').forEach(i=>{
    const col=i.dataset.col; filters[col]=filters[col]||{}; if(!filters[col].range) filters[col].range={};
    if(i.placeholder && i.value==='') return; // ignore empty
    if(Number(i.value) || i.value==='0'){
      if(!filters[col].range) filters[col].range={};
      if(i === document.querySelectorAll(`#filters input[data-col='${col}']`)[0]) filters[col].range.min = Number(i.value);
      else filters[col].range.max = Number(i.value);
    }
  });
  document.querySelectorAll('#filters input[type=date]').forEach(i=>{ if(i.value){ const col=i.dataset.col; filters[col]=filters[col]||{}; filters[col].date = filters[col].date||{}; if(!i.previousElementSibling || i.previousElementSibling.tagName!=='INPUT' || i===document.querySelectorAll(`#filters input[data-col='${col}']`)[0]) filters[col].date.from = i.value; else filters[col].date.to = i.value } });

  // ano/mes selects (from either explicit ano/mes cols or derived from a date column)
  const selAno = document.getElementById('filter-ano');
  const selMes = document.getElementById('filter-mes');
  if(selAno){ const col = selAno.dataset.col; if(selAno.value){ if(/^(ano|year)$/i.test(col)) { filters[col]=filters[col]||{}; filters[col].equals = selAno.value } else { filters[col]=filters[col]||{}; filters[col].year = Number(selAno.value) } } }
  if(selMes){ const col = selMes.dataset.col; if(selMes.value){ if(/^(mes|month)$/i.test(col)) { filters[col]=filters[col]||{}; filters[col].equals = selMes.value } else { filters[col]=filters[col]||{}; filters[col].month = Number(selMes.value) } } }
  return filters;
}

function applyFilters(data, filters){
  return data.filter(r=>{
    for(const col in filters){
      const f = filters[col];
      if(f && (f.equals !== undefined)){
        if(!(String(r[col])==String(f.equals))) return false;
        continue;
      }
      if(f && (f.year !== undefined || f.month !== undefined)){
        const d = Date.parse(r[col]);
        if(isNaN(d)) return false;
        const dt = new Date(d);
        if(f.year !== undefined && dt.getFullYear() !== Number(f.year)) return false;
        if(f.month !== undefined && (dt.getMonth()+1) !== Number(f.month)) return false;
        continue;
      }
      if(typeof f === 'string' || typeof f === 'number'){
        if(!(r[col]==f)) return false;
      } else {
        if(f.range){
          const v = Number(r[col])||0;
          if(f.range.min !== undefined && v < f.range.min) return false;
          if(f.range.max !== undefined && v > f.range.max) return false;
        }
        if(f.date){
          const d = Date.parse(r[col]);
          if(isNaN(d)) return false;
          if(f.date.from && d < Date.parse(f.date.from)) return false;
          if(f.date.to && d > Date.parse(f.date.to)) return false;
        }
      }
    }
    return true;
  });
}

function aggregateForChart(data, xCol, yCol, agg){
  if(!xCol){
    // simple series of y values
    return {labels: data.map((_,i)=>i+1), values: data.map(r=> Number(r[yCol])||0)};
  }
  const map = new Map();
  data.forEach(r=>{
    const k = r[xCol]===undefined || r[xCol]===null ? '': String(r[xCol]);
    const v = yCol ? Number(r[yCol])||0 : 1;
    if(!map.has(k)) map.set(k, []);
    map.get(k).push(v);
  });
  const labels = Array.from(map.keys());
  const values = labels.map(k=>{
    const arr = map.get(k);
    if(agg==='sum') return arr.reduce((a,b)=>a+b,0);
    if(agg==='mean') return arr.reduce((a,b)=>a+b,0)/arr.length;
    return arr.length; // count
  });
  return {labels, values};
}

function updateChart(labels, values, label, type){
  const ctx = document.getElementById('myChart').getContext('2d');
  if(CURRENT_CHART){ CURRENT_CHART.destroy(); CURRENT_CHART=null }
  const config = {
    type: type,
    data: { labels, datasets: [{ label, data: values, backgroundColor: 'rgba(75,192,192,0.4)', borderColor: 'rgb(75,192,192)' }] },
    options: { responsive: true }
  };
  if(type==='pie'){
    config.data.datasets[0].backgroundColor = labels.map((_,i)=>`hsl(${i*40%360} 70% 60%)`);
  }
  CURRENT_CHART = new Chart(ctx, config);
}

async function loadData(){
  try{
    const res = await fetch('/data');
    const data = await res.json();
    if(!Array.isArray(data) || data.length===0){ document.getElementById('thead').innerHTML='<tr><th>No data</th></tr>'; return }
    RAW_DATA = data;
    const {cols, types} = detectColsAndTypes(RAW_DATA);
    createFilters(cols, types, RAW_DATA);
    // populate chart axis selects
    const selX = document.getElementById('chart-x'); const selY = document.getElementById('chart-y');
    selX.innerHTML = '<option value="">(index)</option>' + cols.map(c=>`<option value="${c}">${c}</option>`).join('');
    selY.innerHTML = '<option value="">(count)</option>' + cols.map(c=>`<option value="${c}">${c}</option>`).join('');
    // default selections
    const numCols = cols.filter(c=> types[c]==='number');
    if(numCols.length) selY.value = numCols[0];
    // initial render
    const filtered = RAW_DATA;
    renderTable(filtered);
    const defaultX = selX.value || null; const defaultY = selY.value || numCols[0] || null;
    const agg = document.getElementById('chart-agg').value;
    const ag = aggregateForChart(filtered, defaultX, defaultY, agg);
    updateChart(ag.labels, ag.values, defaultY||'count', document.getElementById('chart-type').value);
  }catch(e){ console.error(e); document.getElementById('thead').innerHTML='<tr><th>Error loading data</th></tr>' }
}

document.getElementById('apply-filters').addEventListener('click', ()=>{
  const filters = readFilters();
  const filtered = applyFilters(RAW_DATA, filters);
  renderTable(filtered);
  const x = document.getElementById('chart-x').value || null;
  const y = document.getElementById('chart-y').value || null;
  const agg = document.getElementById('chart-agg').value;
  const ag = aggregateForChart(filtered, x, y, agg);
  updateChart(ag.labels, ag.values, y||'count', document.getElementById('chart-type').value);
});

loadData().catch(e=>{console.error(e); document.getElementById('thead').innerHTML='<tr><th>Error loading data</th></tr>'});