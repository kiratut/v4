// // Chg_PANEL_JS_2409: новая панель под мокап, data-driven
let PANEL_CFG = null;
let REFRESH_TIMER = null;

async function loadPanelConfig() {
  try {
    const r = await fetch('/api/dashboard/config');
    const cfg = await r.json();
    PANEL_CFG = cfg.dashboard_config || {};
    return PANEL_CFG;
  } catch (e) {
    console.error('loadPanelConfig error', e);
    PANEL_CFG = {};
    return PANEL_CFG;
  }
}

function el(tag, cls, text) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined) e.textContent = text;
  return e;
}

function buildStatusCard(cardCfg) {
  const card = el('div', 'card status-card');
  card.id = cardCfg.id;
  const title = el('div', 'status-title', cardCfg.title || '');
  if (cardCfg.subtitle) {
    const sub = el('div');
    sub.style.fontSize = '11px';
    sub.style.opacity = '0.8';
    sub.textContent = cardCfg.subtitle;
    title.appendChild(sub);
  }
  const value = el('div', 'status-value');
  value.id = cardCfg.value_id || `${cardCfg.id}_value`;
  if (cardCfg.value) value.textContent = cardCfg.value;
  if (cardCfg.unix_time_id) {
    const sep = el('span', null, ' , Unix: ');
    value.appendChild(sep);
    const s = el('span'); s.id = cardCfg.unix_time_id; value.appendChild(s);
  }
  
  card.appendChild(title);
  card.appendChild(value);
  
  // // Chg_EXTRA_ELEMENTS_FIX_2409: поддержка дополнительных элементов ПОСЛЕ title и value
  if (cardCfg.extra_elements) {
    cardCfg.extra_elements.forEach(elem => {
      const extraEl = el('div');
      extraEl.id = elem.id;
      extraEl.textContent = elem.text || '';
      if (elem.style) {
        extraEl.style.cssText = elem.style;
      }
      card.appendChild(extraEl);
    });
  }
  return card;
}

function buildMainCard(cardCfg) {
  const card = el('div', 'card');
  card.id = cardCfg.id;
  const header = el('div', 'card-header');
  header.appendChild(el('div', 'card-title', cardCfg.title || ''));
  card.appendChild(header);

  const c = cardCfg.content || {};
  // status_display
  if (c.status_display) {
    const b = el('div'); b.style.fontSize = '16px'; b.style.marginBottom = '8px'; b.style.textAlign = 'center';
    const s1 = el('div'); s1.style.color = c.status_display.color || '#28a745'; s1.style.fontWeight = 'bold'; s1.textContent = c.status_display.text || '';
    const s2 = el('div'); s2.style.fontSize = '12px'; s2.style.color = '#666'; s2.textContent = `Last check: ${c.status_display.last_check || '-'}`;
    b.appendChild(s1); b.appendChild(s2); card.appendChild(b);
  }
  // actions
  if (Array.isArray(c.actions) && c.actions.length) {
    const g = el('div'); g.style.display='grid'; g.style.gridTemplateColumns='1fr 1fr'; g.style.gap='4px'; g.style.marginBottom='8px';
    c.actions.forEach(a => {
      const btn = el('button');
      btn.textContent = a.text;
      btn.title = a.tooltip || '';
      btn.style.padding='6px 8px'; btn.style.fontSize='12px'; btn.style.border='1px solid #ddd'; btn.style.borderRadius='4px'; btn.style.cursor='pointer';
      if (a.style === 'success') { btn.style.background='#28a745'; btn.style.color='#fff'; }
      if (a.style === 'danger')  { btn.style.background='#dc3545'; btn.style.color='#fff'; }
      if (a.style === 'info')    { btn.style.background='#17a2b8'; btn.style.color='#fff'; }
      if (a.style === 'secondary') { btn.style.background='#6c757d'; btn.style.color='#fff'; }
      btn.addEventListener('click', () => { try { eval(a.action); } catch(e){ console.error(e);} });
      g.appendChild(btn);
    });
    card.appendChild(g);
  }
  // activity_log
  if (c.activity_log) {
    const log = el('div', 'scrollbox');
    log.id = `${cardCfg.id}_activity_log`;
    log.style.height = c.activity_log.height || '60px';
    if (Array.isArray(c.activity_log.entries)) {
      c.activity_log.entries.forEach(t => log.appendChild(el('div', null, t)));
    }
    card.appendChild(log);
  }
  // config_editor
  if (c.config_editor) {
    const wrap = el('div'); wrap.style.borderTop='1px solid #eee'; wrap.style.paddingTop='8px'; wrap.style.marginTop='8px';
    const title = el('div', null, c.config_editor.title || 'Config Editor'); title.style.fontSize='12px'; title.style.fontWeight='600'; title.style.marginBottom='4px'; wrap.appendChild(title);
    if (Array.isArray(c.config_editor.controls)) {
      const ctr = el('div'); ctr.style.display='grid'; ctr.style.gridTemplateColumns='1fr 1fr 1fr'; ctr.style.gap='4px'; ctr.style.marginBottom='4px';
      c.config_editor.controls.forEach(k => {
        const b = el('button'); b.textContent = k.text; b.title = k.tooltip || ''; b.style.padding='4px 6px'; b.style.fontSize='10px'; b.style.border='1px solid #ddd'; b.style.borderRadius='3px'; b.style.cursor='pointer';
        if (k.style==='primary'){ b.style.background='#007bff'; b.style.color='#fff'; }
        if (k.style==='success'){ b.style.background='#28a745'; b.style.color='#fff'; }
        if (k.style==='secondary'){ b.style.background='#6c757d'; b.style.color='#fff'; }
        b.addEventListener('click', ()=>{ try { eval(k.action); } catch(e){ console.error(e);} });
        ctr.appendChild(b);
      });
      wrap.appendChild(ctr);
    }
    const ta = el('textarea'); ta.id='configEditor'; ta.style.width='100%'; ta.style.height=c.config_editor.height||'200px'; ta.style.fontFamily='"Courier New", monospace'; ta.style.fontSize='11px'; ta.style.border='1px solid #ddd'; ta.style.borderRadius='4px'; ta.style.padding='4px'; ta.placeholder='JSON config will be loaded here...';
    wrap.appendChild(ta); card.appendChild(wrap);
    // // Chg_CFG_AUTOLOAD_2409: автозагрузка конфига в редактор при построении
    setTimeout(()=>{ try{ readConfigFromDisk(); }catch(e){ console.error(e);} }, 0);
  }
  // schedule_control
  if (c.schedule_control) {
    const box = el('div'); box.style.fontSize='14px'; box.style.marginBottom='8px';
    if (c.schedule_control.frequency) {
      const r = el('div'); r.style.display='flex'; r.style.justifyContent='space-between'; r.style.alignItems='center'; r.style.marginBottom='4px';
      r.appendChild(el('span', null, c.schedule_control.frequency.label || 'Frequency (h):'));
      const input = el('input'); input.id = c.schedule_control.frequency.input_id || 'loadFrequency'; input.type='number'; input.value=c.schedule_control.frequency.value||1; input.min=c.schedule_control.frequency.min||0; input.max=c.schedule_control.frequency.max||24; input.title=c.schedule_control.frequency.tooltip || ''; input.style.width='50px'; input.style.padding='2px'; input.style.fontSize='12px';
      input.addEventListener('change', updateFrequency);
      r.appendChild(input); box.appendChild(r);
    }
    if (c.schedule_control.next_load) {
      const r2 = el('div'); r2.style.display='flex'; r2.style.justifyContent='space-between';
      r2.appendChild(el('span', null, c.schedule_control.next_load.label || 'Next Load:'));
      const span = el('span'); span.id = c.schedule_control.next_load.value_id || 'nextLoadTime'; span.textContent = c.schedule_control.next_load.value || '-'; r2.appendChild(span);
      box.appendChild(r2);
    }
    card.appendChild(box);
  }
  // filters_table
  if (c.filters_table) {
    const box = el('div'); box.style.marginTop='8px';
    // controls
    if (Array.isArray(c.filters_table.controls)){
      const ctr = el('div'); ctr.style.display='flex'; ctr.style.gap='6px'; ctr.style.marginBottom='6px';
      c.filters_table.controls.forEach(k=>{ const b = el('button'); b.textContent=k.text; b.title=k.tooltip||''; b.style.padding='4px 8px'; b.style.fontSize='11px'; b.addEventListener('click', ()=>{ try{ eval(k.action);}catch(e){console.error(e);} }); ctr.appendChild(b); });
      box.appendChild(ctr);
    }
    // summary
    if (c.filters_table.summary){ const sum = el('div'); sum.style.fontSize='12px'; sum.appendChild(el('span', null, `Active:`)); const af = el('b'); af.id = c.filters_table.summary.active_id || 'activeFilters'; af.style.marginLeft='4px'; sum.appendChild(af); box.appendChild(sum); }
    // table
    const tbl = el('table'); tbl.style.width='100%'; tbl.style.fontSize='12px'; tbl.style.borderCollapse='collapse';
    const thead = el('thead'); const hr = el('tr'); (c.filters_table.columns||[]).forEach(h=>{ const th=el('th',null,h); th.style.textAlign='left'; th.style.borderBottom='1px solid #eee'; th.style.padding='2px 4px'; hr.appendChild(th); }); thead.appendChild(hr); tbl.appendChild(thead);
    const tbody = el('tbody'); tbody.id = 'filtersTableBody'; tbl.appendChild(tbody);
    box.appendChild(tbl); card.appendChild(box);
  }
  // tasks_table
  if (c.tasks_table){
    const box = el('div');
    if (c.tasks_table.title) box.appendChild(el('div', null, c.tasks_table.title));
    if (c.tasks_table.unix_time){ const r=el('div'); r.style.fontSize='12px'; r.appendChild(el('span',null, c.tasks_table.unix_time.label||'Unix:')); const v=el('b'); v.id=c.tasks_table.unix_time.value_id||'tasksUnixTime'; v.style.marginLeft='4px'; r.appendChild(v); box.appendChild(r); }
    const tbl = el('table'); tbl.style.width='100%'; tbl.style.fontSize='12px'; tbl.style.borderCollapse='collapse';
    const thead = el('thead'); const hr = el('tr'); (c.tasks_table.columns||[]).forEach(h=>{ const th=el('th',null,h); th.style.textAlign='left'; th.style.borderBottom='1px solid #eee'; th.style.padding='2px 4px'; hr.appendChild(th); }); thead.appendChild(hr); tbl.appendChild(thead);
    const tbody = el('tbody'); tbody.id='tasksTableBody'; tbl.appendChild(tbody); box.appendChild(tbl); card.appendChild(box);
  }
  // workers controls/tasks
  if (c.controls && cardCfg.id==='workers_status'){
    const ctr = el('div'); ctr.style.display='flex'; ctr.style.gap='6px'; ctr.style.marginBottom='6px';
    c.controls.forEach(k=>{ const b=el('button'); b.textContent=k.text; b.title=k.tooltip||''; b.style.padding='4px 8px'; b.style.fontSize='11px'; b.addEventListener('click', ()=>{ try{ eval(k.action);}catch(e){console.error(e);} }); ctr.appendChild(b); });
    card.appendChild(ctr);
  }
  if (c.worker_tasks){ const box=el('div'); const ul=el('ul'); ul.id='workerTasksList'; ul.style.maxHeight=c.worker_tasks.height||'120px'; ul.style.overflowY='auto'; box.appendChild(ul); card.appendChild(box); }
  
  // // Chg_APP_LOG_CONTAINER_2409: добавляем контейнер для app.log
  if (c.app_log_display) {
    const logWrapper = el('div');
    logWrapper.style.borderTop = '1px solid #eee';
    logWrapper.style.paddingTop = '8px';
    logWrapper.style.marginTop = '8px';
    
    const logTitle = el('div', null, c.app_log_display.title || 'Application Log');
    logTitle.style.fontSize = '12px';
    logTitle.style.fontWeight = '600';
    logTitle.style.marginBottom = '4px';
    logWrapper.appendChild(logTitle);
    
    const logContainer = el('div');
    logContainer.id = 'appLogContainer';
    logContainer.style.height = c.app_log_display.height || '120px';
    logContainer.style.overflow = 'auto';
    logContainer.style.background = c.app_log_display.background || '#f8f9fa';
    logContainer.style.border = '1px solid #ddd';
    logContainer.style.borderRadius = '4px';
    logContainer.style.padding = '4px';
    
    logWrapper.appendChild(logContainer);
    card.appendChild(logWrapper);
  }
  
  return card;
}

async function buildPanel() {
  const cfg = await loadPanelConfig();
  // header
  const titleEl = document.getElementById('headerTitle'); if (titleEl && cfg.header && cfg.header.title) titleEl.textContent = cfg.header.title;
  const verEl = document.getElementById('headerVersion'); if (verEl && cfg.header && cfg.header.version) verEl.textContent = cfg.header.version;
  const refreshBtn = document.getElementById('manualRefreshBtn'); if (refreshBtn) {
    refreshBtn.textContent = (cfg.header?.refresh_button?.text) || '🔄 Refresh';
    refreshBtn.title = (cfg.header?.refresh_button?.tooltip) || 'Обновить';
    refreshBtn.onclick = manualRefresh;
  }
  // rows
  const statusRow = document.querySelector('.status-row'); if (statusRow) {
    statusRow.innerHTML = '';
    (cfg.status_row?.cards || []).forEach(c => statusRow.appendChild(buildStatusCard(c)));
  }
  const grid = document.querySelector('.dashboard-grid'); if (grid) {
    grid.innerHTML = '';
    (cfg.main_grid?.cards || []).forEach(c => grid.appendChild(buildMainCard(c)));
  }
  // interval
  const intMs = cfg.refresh_interval_ms || 5000; startAutoRefresh(intMs);
  // initial update
  updateAllMetrics();
}

function formatHealthSubtitle(cpu, mem, disk) {
  const toInt = (v)=>Math.round((v||0));
  const score = (100 - toInt(cpu) + 100 - toInt(mem) + 100 - toInt(disk)) / 3;
  return `${score.toFixed(1)}% = CPU ${toInt(cpu)}% + RAM ${toInt(mem)}% + Disk ${toInt(disk)}%`;
}

async function updateSystemHealth() {
  try {
    const r = await fetch('/api/stats/system_health');
    const d = await r.json();
    const card = document.getElementById('system_health');
    if (card) {
      const title = card.querySelector('.status-title');
      if (title) {
        let sub = title.querySelector('div');
        if (!sub) { sub = document.createElement('div'); sub.style.fontSize='11px'; sub.style.opacity='0.8'; title.appendChild(sub); }
        sub.textContent = formatHealthSubtitle(d.cpu_percent, d.memory_percent, d.disk_percent);
      }
    }
    // Также обновим основной статус и время проверки в карточке system_resources
    try{
      const srCard = document.getElementById('system_resources');
      if (srCard){
        const block = Array.from(srCard.children).find(x=>x.textContent && x.textContent.includes('Systems') || x.textContent && x.textContent.includes('Last check')) || null;
        const ok = (d.cpu_percent<=80 && d.memory_percent<=85 && d.disk_percent<=90);
        // Ищем элемент status_display: это два div подряд сверху карточки
        const headers = srCard.querySelectorAll('div');
        const nowStr = new Date().toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit', second:'2-digit'});
        // Найдем первый контейнер под status_display (после заголовка)
        const statusBlocks = Array.from(srCard.querySelectorAll('div'));
        // Прямо обновим по id, если есть
        // Создадим/обновим два div: основной текст и Last check
        const statusBox = document.createElement('div');
        statusBox.style.fontSize='16px'; statusBox.style.marginBottom='8px'; statusBox.style.textAlign='center';
        const s1 = document.createElement('div'); s1.style.fontWeight='bold'; s1.style.color = ok? '#28a745':'#dc3545'; s1.textContent = ok? 'OK':'Degraded';
        const s2 = document.createElement('div'); s2.style.fontSize='12px'; s2.style.color='#666'; s2.textContent = `Last check: ${nowStr}`;
        statusBox.appendChild(s1); statusBox.appendChild(s2);
        // Вставим (заменим) после заголовка карточки
        const header = srCard.querySelector('.card-header');
        if (header){
          // Удалим старый блок при наличии
          const old = header.nextElementSibling;
          if (old && old.style && old.style.textAlign==='center') old.remove();
          header.insertAdjacentElement('afterend', statusBox);
        }
      }
    }catch(e){ /* ignore */ }
  } catch(e){ console.error('updateSystemHealth', e); }
}

async function updateDaemon() {
  try {
    const r = await fetch('/api/daemon/status');
    const d = await r.json();
    const elVal = document.getElementById('daemonStatus');
    if (elVal) {
      // Формат: YYYY-MM-DD HH:MM:SS unix:<unix>
      const fmt = (iso)=>{
        try{ const dt = new Date(iso); const pad=n=>String(n).padStart(2,'0'); return `${dt.getFullYear()}-${pad(dt.getMonth()+1)}-${pad(dt.getDate())} ${pad(dt.getHours())}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}`; }catch(_){ return 'N/A'; }
      };
      const startedText = d.started ? fmt(d.started) : 'N/A';
      const unixText = (d.unix_time!=null)? ` unix:${d.unix_time}` : '';
      elVal.textContent = `PID: ${d.pid ?? 'N/A'} • Started: ${startedText}${unixText}`;
      elVal.style.fontSize = '12px'; // уменьшенный шрифт
    }
    const u = document.getElementById('daemonUnixTime');
    if (u) u.textContent = d.unix_time ? `${d.unix_time}` : `${Math.floor(Date.now()/1000)}`;
  } catch(e){ console.error('updateDaemon', e); }
}

async function updateQueueAndWorkers() {
  try {
    const r1 = await fetch('/api/daemon/tasks'); const d1 = await r1.json();
    const r2 = await fetch('/api/daemon/tasks/active'); const d2 = await r2.json();
    const r3 = await fetch('/api/workers/status'); const d3 = await r3.json();
    const taskStats = document.getElementById('taskStats');
    if (taskStats) {
      const running = (d2.summary?.running) || 0; const pending = (d2.summary?.pending) || 0;
      taskStats.textContent = `${running} running, ${pending} pending`;
    }
    const tux = document.getElementById('tasksUnixTime'); if (tux) { const ut = (d2.summary?.unix_time) || Math.floor(Date.now()/1000); tux.textContent = `${ut}`; }
    const vac = document.getElementById('vacancyCount'); if (vac) vac.textContent = d2.summary?.vacancies ?? (d1.vacancies_count ?? '0');
    const emp = document.getElementById('employerCount'); if (emp) emp.textContent = d2.summary?.employers ?? (d1.employers_count ?? '0');
    const eta = document.getElementById('queueEta'); if (eta) eta.textContent = d2.summary?.queue_eta ?? (d1.queue_eta ?? '~0min');
    const aw = document.getElementById('activeWorkers'); if (aw) aw.textContent = `${d3.active_workers || 0}/${d3.total_workers || 5}`;
  } catch(e){ console.error('updateQueueAndWorkers', e); }
}

async function updateApiStatus() {
  try { 
    const r = await fetch('/api/stats/api_status'); 
    const d = await r.json(); 
    const elVal = document.getElementById('apiHealth'); 
    if (elVal) {
      // // Chg_API_TIME_FIX_2409: добавляем время последнего обновления
      const now = new Date();
      const timeStr = now.toLocaleTimeString('ru-RU', {hour: '2-digit', minute: '2-digit', second: '2-digit'});
      elVal.textContent = `${d.status} • ${d.bans||0} bans (${timeStr})`;
      elVal.style.fontSize = '12px';
    } 
  } catch(e){ console.error('updateApiStatus', e); }
}

async function updateFiltersBlock() {
  try { const r = await fetch('/api/filters/list'); const d = await r.json(); const af = document.getElementById('activeFilters'); if (af && d.filters) af.textContent = d.filters.filter(f=>f.active).length; } catch(e){ console.error('updateFiltersBlock', e); }
}

function startAutoRefresh(ms) { if (REFRESH_TIMER) clearInterval(REFRESH_TIMER); REFRESH_TIMER = setInterval(updateAllMetrics, ms); }
function manualRefresh(){ updateAllMetrics(); }

function setLastRefreshNow(){ const lr=document.getElementById('lastRefresh'); if (lr){ const now=new Date(); lr.textContent = now.toLocaleTimeString('ru-RU'); } }

function updateAllMetrics(){ updateSystemHealth(); updateDaemon(); updateQueueAndWorkers(); updateApiStatus(); updateFiltersBlock(); updateTablesFromSources(); updateTestStatus(); updateScheduleInfo(); updateAppLog(); setLastRefreshNow(); }

// // Chg_TABLES_UPDATE_2409: наполнение таблиц/списков по источникам из конфига
async function updateTablesFromSources(){
  try{
    // // Chg_FILTERS_TABLE_FIX_2409: полные JSON тексты фильтров
    const ftb = document.getElementById('filtersTableBody');
    if (ftb){
      const r = await fetch('/api/filters/list');
      const d = await r.json();
      ftb.innerHTML='';
      (d.filters||[]).forEach((f,i)=>{
        const tr=el('tr');
        const queryText = f.query || f.text || f.name || JSON.stringify(f.params || {}) || '-';
        // // Chg_FILTERS_UI_2609: интерактивные чекбоксы активности
        const tdChk = el('td');
        const cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = !!f.active;
        cb.title = 'Активировать/деактивировать фильтр';
        cb.addEventListener('change', ()=>{ try{ setFilterActive(f.id ?? i, cb.checked); }catch(e){ console.error(e);} });
        tdChk.appendChild(cb);
        tdChk.style.padding='2px 4px'; tdChk.style.fontSize='11px';
        tr.appendChild(tdChk);

        const tdType = el('td', null, String(f.type||'-'));
        tdType.style.padding='2px 4px'; tdType.style.fontSize='11px';
        tr.appendChild(tdType);

        const tdStatus = el('td', null, String(f.active?'ON':'OFF'));
        tdStatus.style.padding='2px 4px'; tdStatus.style.fontSize='11px';
        tr.appendChild(tdStatus);

        const tdQuery = el('td', null, String(queryText));
        tdQuery.style.padding='2px 4px'; tdQuery.style.fontSize='11px';
        if (String(queryText).length > 80) { tdQuery.title = String(queryText); tdQuery.textContent = String(queryText).slice(0,80) + '...'; }
        tr.appendChild(tdQuery);

        ftb.appendChild(tr);
      });
    }
    // tasks active
    const ttb = document.getElementById('tasksTableBody');
    if (ttb){ const r=await fetch('/api/daemon/tasks/active'); const d=await r.json(); ttb.innerHTML=''; (d.tasks||[]).forEach(row=>{ const tr=el('tr'); const cols=[row.num,row.worker,row.task_type,row.status]; cols.forEach(c=>{ const td=el('td',null,String(c)); td.style.padding='2px 4px'; tr.appendChild(td); }); ttb.appendChild(tr); }); const tux=document.getElementById('tasksUnixTime'); if (tux && d.summary?.unix_time){ tux.textContent = `${d.summary.unix_time}`; } }
    // workers list
    const wul = document.getElementById('workerTasksList');
    if (wul){ const r=await fetch('/api/workers/status'); const d=await r.json(); wul.innerHTML=''; (d.workers||[]).forEach(w=>{ const li=el('li',null,`${w.worker_id}: ${w.running} running, ${w.pending} pending`); wul.appendChild(li); }); const aw=document.getElementById('activeWorkers'); if (aw) aw.textContent=`${d.active_workers||0}/${d.total_workers||5}`; }
  }catch(e){ console.error('updateTablesFromSources', e); }
}

// // Chg_SCHEDULE_INFO_2509: обновление Next Scheduled Load (HH:MM)
async function updateScheduleInfo(){
  try{
    const r = await fetch('/api/schedule/next');
    const d = await r.json();
    const el = document.getElementById('nextLoadTime');
    if (el && d && d.next){ el.textContent = d.next; }
  }catch(e){ /* ignore */ }
}

// Controls
async function toggleAllFilters(enable){ try{ await fetch('/api/filters/toggle-all',{method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({enable: !!enable})}); updateFiltersBlock(); updateTablesFromSources(); }catch(e){console.error(e);} }
async function invertFilters(){ try{ await fetch('/api/filters/invert',{method:'POST'}); updateFiltersBlock(); updateTablesFromSources(); }catch(e){console.error(e);} }
// // Chg_FILTERS_SET_ACTIVE_2609: установка активности одного фильтра
async function setFilterActive(filterId, active){
  try{
    await fetch('/api/filters/set-active', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({filter_id: filterId, active: !!active})});
    updateFiltersBlock();
    updateTablesFromSources();
  }catch(e){ console.error('setFilterActive', e); }
}
// // Chg_LOAD_NOW_2609: немедленный запуск загрузки активных/выделенных фильтров
async function loadNowSelected(){
  try{
    const btns = Array.from(document.querySelectorAll('button')).filter(b=>/Load Now/i.test(b.textContent));
    btns.forEach(b=>{ b.disabled = true; });
    const r = await fetch('/api/filters/load-now', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({})});
    const d = await r.json();
    if (!r.ok || d.status !== 'ok'){
      alert('Load failed: ' + (d.message || r.statusText));
    } else {
      alert(`Создано задач: ${d.count}`);
      try{ await updateQueueAndWorkers(); }catch(_){ }
      try{ await updateTablesFromSources(); }catch(_){ }
    }
  }catch(e){ console.error('loadNowSelected', e); alert('Ошибка: '+e.message); }
  finally{
    const btns = Array.from(document.querySelectorAll('button')).filter(b=>/Load Now/i.test(b.textContent));
    btns.forEach(b=>{ b.disabled = false; });
  }
}
// // Chg_CONFIG_LOAD_FIX_2409: улучшенная загрузка config с fallback
async function readConfigFromDisk(){ 
  const ed = document.getElementById('configEditor');
  if (!ed) return;
  
  try{ 
    const r = await fetch('/api/config/read'); 
    if (!r.ok) {
      throw new Error(`HTTP ${r.status}: ${r.statusText}`);
    }
    const d = await r.json(); 
    ed.value = JSON.stringify(d, null, 2);
    ed.style.color = '#000'; // успешная загрузка
  }catch(e){
    console.error('Config load error:', e);
    ed.value = `// Error loading config: ${e.message}\n// Check if web server is running\n{\n  "error": "Config unavailable"\n}`;
    ed.style.color = '#dc3545'; // красный текст при ошибке
  } 
}
async function writeConfigToDisk(){ const ed=document.getElementById('configEditor'); if(!ed) return; try{ const data=JSON.parse(ed.value); const r = await fetch('/api/config/write',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)}); if(!r.ok) alert('Save failed'); else alert('Saved'); }catch(e){ alert('Invalid JSON'); }}
async function updateFrequency(){ const inp = document.getElementById('loadFrequency'); if(!inp) return; const v = parseInt(inp.value||'0'); try{ const r = await fetch('/api/schedule/frequency',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({frequency_hours: v})}); if (r.ok) { try{ await updateScheduleInfo(); }catch(_){} } }catch(e){console.error(e);} }
async function startSystem(){ try{ await fetch('/api/daemon/start',{method:'POST'}); updateDaemon(); }catch(e){console.error(e);} }
async function stopSystem(){ try{ await fetch('/api/daemon/stop',{method:'POST'}); updateDaemon(); }catch(e){console.error(e);} }
// // Chg_RESTART_UI_2509: перезапуск демона с опросом статуса
async function restartSystem(){
  // Модалка прогресса
  const modal = document.createElement('div');
  modal.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,0.6);display:flex;align-items:center;justify-content:center;z-index:9999;';
  const inner = document.createElement('div'); inner.style.cssText='background:#fff;padding:16px 20px;border-radius:8px;min-width:320px;max-width:80%';
  inner.innerHTML = '<div style="font-weight:600;margin-bottom:8px">Restarting daemon...</div><div id="rstMsg" style="font-size:12px;color:#666">Please wait up to 25s</div>';
  modal.appendChild(inner); document.body.appendChild(modal);
  const btns = Array.from(document.querySelectorAll('button')).filter(b=>/Restart/i.test(b.textContent));
  btns.forEach(b=>{ b.disabled = true; b.textContent = '↻ Restarting...'; });
  try{
    const ctrl = new AbortController();
    const timer = setTimeout(()=>ctrl.abort(), 25000);
    let resp;
    try{
      resp = await fetch('/api/daemon/restart', {method:'POST', signal: ctrl.signal});
    }catch(e){
      if (e && (e.name === 'AbortError' || String(e).includes('AbortError'))){
        // Продолжаем с проверкой статуса, даже если запрос оборван по таймауту
        inner.querySelector('#rstMsg').textContent = 'Request timeout, checking status...';
        resp = null;
      } else { throw e; }
    }
    clearTimeout(timer);
    let data = {};
    try { data = await resp.json(); } catch(_){ data = {}; }
    if (resp && (!resp.ok || data.status === 'error')) {
      const errText = (data && (data.message || data.stderr || data.stdout)) || ('HTTP '+resp.status+' '+resp.statusText);
      inner.innerHTML = `<div style="font-weight:600;color:#dc3545;margin-bottom:6px">Restart failed</div><pre style="max-height:240px;overflow:auto;background:#f8f9fa;padding:8px;border-radius:4px">${(errText||'unknown').toString().slice(0,1000)}</pre><div style="margin-top:8px;text-align:right"><button onclick="this.closest('div').parentElement.parentElement.remove()">Close</button></div>`;
      return;
    }
    // Poll up to 25s
    let ok=false;
    for (let i=0; i<25; i++){
      inner.querySelector('#rstMsg').textContent = `Checking status... ${i+1}/25`;
      try{
        const r = await fetch('/api/daemon/status');
        const d = await r.json();
        if (d && d.running) { ok = true; break; }
      }catch(e){}
      await new Promise(res=>setTimeout(res, 1000));
    }
    if (!ok){
      const errTxt = (data && (data.stderr || data.stdout)) || 'Daemon did not come up in time (25s)';
      inner.innerHTML = `<div style="font-weight:600;color:#dc3545;margin-bottom:6px">Restart timeout</div><pre style="max-height:240px;overflow:auto;background:#f8f9fa;padding:8px;border-radius:4px">${(errTxt||'').toString().slice(0,1000)}</pre><div style="margin-top:8px;text-align:right"><button onclick="this.closest('div').parentElement.parentElement.remove()">Close</button></div>`;
      return;
    }
    inner.innerHTML = `<div style="font-weight:600;color:#28a745;margin-bottom:6px">Daemon restarted successfully</div><div style="text-align:right"><button onclick="this.closest('div').parentElement.parentElement.remove()">Close</button></div>`;
  }catch(e){
    inner.innerHTML = `<div style="font-weight:600;color:#dc3545;margin-bottom:6px">Restart error</div><pre style="max-height:240px;overflow:auto;background:#f8f9fa;padding:8px;border-radius:4px">${(e.message||String(e)).slice(0,1000)}</pre><div style="margin-top:8px;text-align:right"><button onclick="this.closest('div').parentElement.parentElement.remove()">Close</button></div>`;
  } finally {
    btns.forEach(b=>{ b.disabled = false; b.textContent = '↻ Restart Daemon'; });
    updateDaemon();
  }
}

// // Chg_TEST_CONTROLS_2409: кнопки и индикаторы тестирования
async function runTests(){ 
  const btn = document.querySelector('button[onclick="runTests()"]');
  if (btn) { btn.disabled = true; btn.textContent = '🔄 Running...'; }
  // Плавающая плашка без затемнения экрана
  const toast = document.createElement('div');
  toast.style.cssText='position:fixed;right:12px;bottom:12px;z-index:9999;';
  const inner = document.createElement('div'); inner.style.cssText='background:#fff;box-shadow:0 6px 24px rgba(0,0,0,0.15);padding:12px 14px;border-radius:8px;min-width:320px;max-width:420px;font-size:13px;';
  inner.innerHTML = '<div style="display:flex;align-items:center;justify-content:space-between;font-weight:600;margin-bottom:6px"><span>Running all tests...</span><button id="testToastClose" style="border:none;background:transparent;font-size:16px;cursor:pointer">×</button></div><div id="testProgress" style="font-size:12px;color:#666">Initializing...</div><div id="testMsg" style="font-size:11px;color:#999;margin-top:4px"></div>';
  toast.appendChild(inner); document.body.appendChild(toast);
  const closeBtn = document.getElementById('testToastClose'); if (closeBtn){ closeBtn.onclick = ()=> toast.remove(); }
  
  const progressEl = document.getElementById('testProgress');
  const msgEl = document.getElementById('testMsg');
  
  try{ 
    if (progressEl) progressEl.textContent = 'Starting test run...';
    // // Chg_TESTS_PROGRESS_2609: периодический опрос статуса пока идёт запуск
    const startedAt = Date.now();
    const pollId = setInterval(async ()=>{
      try{
        const rs = await fetch('/api/tests/status');
        const dj = await rs.json();
        const secs = Math.round((Date.now()-startedAt)/1000);
        if (progressEl) progressEl.textContent = `Running... ${secs}s${dj && dj.success_rate ? ` (last: ${dj.success_rate}%)` : ''}`;
      }catch(_){ /* ignore */ }
    }, 2000);
    const response = await fetch('/api/tests/run', {method:'POST'}); 
    clearInterval(pollId);
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    updateTestStatus();
    if (progressEl) progressEl.textContent = `Tests started (async). Check details below...`;
    if (msgEl) msgEl.textContent = result.summary || 'All tests started';
    inner.innerHTML = `<div style="display:flex;align-items:center;justify-content:space-between;font-weight:600;margin-bottom:6px"><span>Tests started</span><button id="testToastClose2" style="border:none;background:transparent;font-size:16px;cursor:pointer">×</button></div><div style="font-size:12px;color:#666;margin-bottom:6px">Статус обновляется в карточке Tests. Откройте детали: <a href="#" id="openTestDetailsLink">Details</a></div>`;
    const link = inner.querySelector('#openTestDetailsLink'); if (link){ link.onclick = (e)=>{ e.preventDefault(); try{ showTestDetails(); }catch(_){ } } }
    const closeBtn2 = document.getElementById('testToastClose2'); if (closeBtn2){ closeBtn2.onclick = ()=> toast.remove(); }
  }catch(e){
    console.error('Test run failed:', e);
    if (progressEl) progressEl.textContent = 'Error occurred';
    if (msgEl) msgEl.textContent = e.message || String(e);
    inner.innerHTML = `<div style=\"font-weight:600;color:#dc3545;margin-bottom:6px\">Test run failed</div><div style=\"font-size:12px;margin-bottom:8px\">Failed to fetch - веб-сервер не отвечает на порту 8000</div><pre style=\"max-height:240px;overflow:auto;background:#f8f9fa;padding:8px;border-radius:4px\">${(e.message||String(e))}</pre>`;
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '🧪 Run Tests'; }
    setTimeout(()=>{ try{ toast.remove(); }catch(_){ } }, 10000);
  }
}

async function updateTestStatus() {
  try {
    const response = await fetch('/api/tests/status');
    const data = await response.json();
    
    const rateElem = document.getElementById('testSuccessRate');
    if (rateElem) {
      rateElem.textContent = `${data.success_rate || 0}%`;
      rateElem.style.color = (data.success_rate || 0) > 80 ? '#28a745' : '#dc3545';
    }
    
    const lastRunElem = document.getElementById('testLastRun');
    if (lastRunElem && data.last_run) {
      lastRunElem.textContent = new Date(data.last_run).toLocaleString('ru-RU');
    }
  } catch(e) {
    console.error('Failed to update test status:', e);
  }
}

function showTestDetails() {
  // Создаем модальное окно с результатами тестов
  const modal = document.createElement('div');
  modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.8);z-index:9999;display:flex;align-items:center;justify-content:center;';
  
  const content = document.createElement('div');
  content.style.cssText = 'background:white;padding:20px;border-radius:8px;max-width:80%;max-height:80%;overflow:auto;';
  
  content.innerHTML = `
    <h3>Test Results Details</h3>
    <div id="testDetailsContent">Loading...</div>
    <button onclick="this.parentElement.parentElement.remove()" style="margin-top:15px;padding:10px 20px;">Close</button>
  `;
  
  modal.appendChild(content);
  document.body.appendChild(modal);
  
  // Загружаем детальные результаты
  loadTestDetails();
}

async function loadTestDetails() {
  try {
    const response = await fetch('/api/tests/details');
    const data = await response.json();
    
    const content = document.getElementById('testDetailsContent');
    if (content && data) {
      let html = `<p><strong>Total:</strong> ${data.total_tests}, <strong>Passed:</strong> ${data.passed_tests}, <strong>Success Rate:</strong> ${data.success_rate}%</p>`;
      
      if (data.failed_tests && data.failed_tests.length > 0) {
        html += '<h4>Failed Tests:</h4><ul>';
        data.failed_tests.forEach(test => {
          html += `<li><strong>${test.name}:</strong> ${test.error}</li>`;
        });
        html += '</ul>';
      }
      
      if (data.union_test_log) {
        html += '<h4>Recent Test Log (union_test.log):</h4>';
        html += `<pre style="background:#f5f5f5;padding:10px;border-radius:4px;max-height:300px;overflow:auto;">${data.union_test_log}</pre>`;
      }
      
      content.innerHTML = html;
    }
  } catch(e) {
    const content = document.getElementById('testDetailsContent');
    if (content) {
      content.innerHTML = `<p style="color:red;">Failed to load test details: ${e.message}</p>`;
    }
  }
}

// // Chg_CTRL_ENDPOINTS_2409: кнопки управления воркерами и очередью
async function freezeWorkers(){
  try{
    const ok = confirm('Заморозить работу всех воркеров?');
    if(!ok) return;
    const r = await fetch('/api/workers/freeze',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({frozen:true})});
    const d = await r.json();
    if(!r.ok || d.status!=='ok') alert('Не удалось заморозить воркеров');
    updateQueueAndWorkers();
  }catch(e){ console.error(e); alert('Ошибка: '+e); }
}

async function clearQueue(){
  try{
    const ok = confirm('Очистить очередь задач со статусом pending?');
    if(!ok) return;
    const r = await fetch('/api/queue/clear',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({status:'pending'})});
    const d = await r.json();
    if(!r.ok || d.status!=='ok') alert('Не удалось очистить очередь');
    updateQueueAndWorkers(); updateTablesFromSources();
  }catch(e){ console.error(e); alert('Ошибка: '+e); }
}

// Stubs and helpers
function resetConfigEditor(){ const ed=document.getElementById('configEditor'); if (ed) ed.value=''; }

// // Chg_APP_LOG_DISPLAY_2409: отображение последних строк app.log
// // Chg_LOG_UI_2509: учитывать лимит строк из конфигурации и поддерживать 20..100
async function updateAppLog() {
  try {
    // Пытаемся получить лимит из конфигурации панели
    let limit = 100;
    try{
      const sysCard = (PANEL_CFG?.main_grid?.cards || []).find(c => c.id === 'system_resources');
      const appLogCfg = sysCard?.content?.app_log_display;
      const v = parseInt(appLogCfg?.max_lines || appLogCfg?.maxEntries || 100);
      if (!isNaN(v)) limit = Math.max(20, Math.min(100, v));
    }catch(e){ limit = 100; }

    const response = await fetch('/api/logs/app?limit=' + encodeURIComponent(limit));
    const data = await response.json();
    
    const logContainer = document.getElementById('appLogContainer');
    if (logContainer && data.lines) {
      // Создаем или обновляем контейнер лога
      let logDisplay = document.getElementById('appLogDisplay');
      if (!logDisplay) {
        logDisplay = document.createElement('pre');
        logDisplay.id = 'appLogDisplay';
        // Вычисляем высоту: в 2 раза больше (по умолчанию 240px)
        const h = parseInt((logContainer.style.height||'').replace('px','')) || 240;
        logDisplay.style.cssText = `font-family:Courier New,monospace;font-size:10px;background:#f8f9fa;padding:8px;border-radius:4px;max-height:${h}px;overflow-y:auto;margin-top:5px;`;
        logContainer.appendChild(logDisplay);
      }
      
      // Обновляем содержимое
      const logText = data.lines.join('\n');
      logDisplay.textContent = logText;
      
      // Автопрокрутка вниз
      logDisplay.scrollTop = logDisplay.scrollHeight;
    }
  } catch(e) {
    console.error('Failed to update app log:', e);
  }
}

// init
document.addEventListener('DOMContentLoaded', () => { buildPanel(); });
