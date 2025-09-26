// HH v4 Dashboard - динамическая генерация из dashboard_layout.json
// Автор: AI Assistant
// Дата: 23.09.2025

let dashboardConfig = null;
let refreshInterval = null;

// Загрузка конфигурации панели
async function loadDashboardConfig() {
    try {
        const response = await fetch('/api/dashboard/config');
        dashboardConfig = await response.json();
        console.log('Dashboard config loaded:', dashboardConfig);
        return dashboardConfig;
    } catch (error) {
        console.error('Failed to load dashboard config:', error);
        // Загрузка из локального файла как фолбек
        try {
            const response = await fetch('/static/dashboard_layout.json');
            dashboardConfig = await response.json();
            return dashboardConfig;
        } catch (fallbackError) {
            console.error('Failed to load fallback config:', fallbackError);
            return null;
        }
    }
}

// Создание карточки статуса
function createStatusCard(cardConfig) {
    const card = document.createElement('div');
    card.className = 'card status-card';
    card.id = cardConfig.id;
    
    const title = document.createElement('div');
    title.className = 'status-title';
    title.textContent = cardConfig.title;
    
    if (cardConfig.subtitle) {
        const subtitle = document.createElement('div');
        subtitle.style.fontSize = '11px';
        subtitle.style.opacity = '0.8';
        subtitle.textContent = cardConfig.subtitle;
        title.appendChild(subtitle);
    }
    
    const value = document.createElement('div');
    value.className = 'status-value';
    value.id = cardConfig.value_id || `${cardConfig.id}_value`;
    value.textContent = cardConfig.value || 'Loading...';
    
    if (cardConfig.unix_time_id) {
        const unixSpan = document.createElement('span');
        unixSpan.id = cardConfig.unix_time_id;
        value.appendChild(unixSpan);
    }
    
    card.appendChild(title);
    card.appendChild(value);
    
    return card;
}

// Создание основной карточки
function createMainCard(cardConfig) {
    const card = document.createElement('div');
    card.className = 'card';
    card.id = cardConfig.id;
    
    // Заголовок
    const header = document.createElement('div');
    header.className = 'card-header';
    
    const title = document.createElement('div');
    title.className = 'card-title';
    title.textContent = cardConfig.title;
    header.appendChild(title);
    
    card.appendChild(header);
    
    // Контент карточки
    const content = cardConfig.content;
    if (content) {
        // Статус дисплей
        if (content.status_display) {
            const statusDiv = document.createElement('div');
            statusDiv.style.fontSize = '16px';
            statusDiv.style.marginBottom = '8px';
            statusDiv.style.textAlign = 'center';
            
            const statusText = document.createElement('div');
            statusText.style.color = content.status_display.color;
            statusText.style.fontWeight = 'bold';
            statusText.textContent = content.status_display.text;
            statusDiv.appendChild(statusText);
            
            const lastCheck = document.createElement('div');
            lastCheck.style.fontSize = '12px';
            lastCheck.style.color = '#666';
            lastCheck.textContent = `Last check: ${content.status_display.last_check}`;
            statusDiv.appendChild(lastCheck);
            
            card.appendChild(statusDiv);
        }
        
        // Кнопки действий
        if (content.actions) {
            const actionsDiv = document.createElement('div');
            actionsDiv.style.display = 'grid';
            actionsDiv.style.gridTemplateColumns = '1fr 1fr';
            actionsDiv.style.gap = '4px';
            actionsDiv.style.marginBottom = '8px';
            
            content.actions.forEach(action => {
                const btn = document.createElement('button');
                btn.textContent = action.text;
                btn.title = action.tooltip || '';
                btn.onclick = () => eval(action.action);
                btn.style.padding = '6px 8px';
                btn.style.fontSize = '12px';
                btn.style.border = '1px solid #ddd';
                btn.style.borderRadius = '4px';
                btn.style.cursor = 'pointer';
                
                // Стили кнопок
                if (action.style === 'success') {
                    btn.style.background = '#28a745';
                    btn.style.color = 'white';
                } else if (action.style === 'danger') {
                    btn.style.background = '#dc3545';
                    btn.style.color = 'white';
                }
                
                actionsDiv.appendChild(btn);
            });
            
            card.appendChild(actionsDiv);
        }
        
        // Activity log
        if (content.activity_log) {
            const logDiv = document.createElement('div');
            logDiv.style.fontSize = '12px';
            logDiv.style.height = content.activity_log.height;
            logDiv.style.overflow = content.activity_log.overflow;
            logDiv.style.background = '#f8f9fa';
            logDiv.style.padding = '4px';
            logDiv.style.borderRadius = '4px';
            logDiv.id = `${cardConfig.id}_activity_log`;
            
            if (content.activity_log.entries) {
                content.activity_log.entries.forEach(entry => {
                    const entryDiv = document.createElement('div');
                    entryDiv.textContent = entry;
                    logDiv.appendChild(entryDiv);
                });
            }
            
            card.appendChild(logDiv);
        }
        
        // Config editor
        if (content.config_editor) {
            const editorContainer = document.createElement('div');
            editorContainer.style.borderTop = '1px solid #eee';
            editorContainer.style.paddingTop = '8px';
            editorContainer.style.marginTop = '8px';
            
            const editorTitle = document.createElement('div');
            editorTitle.style.fontSize = '12px';
            editorTitle.style.marginBottom = '4px';
            editorTitle.style.fontWeight = '600';
            editorTitle.textContent = content.config_editor.title;
            editorContainer.appendChild(editorTitle);
            
            // Контролы редактора
            if (content.config_editor.controls) {
                const controlsDiv = document.createElement('div');
                controlsDiv.style.display = 'grid';
                controlsDiv.style.gridTemplateColumns = '1fr 1fr 1fr';
                controlsDiv.style.gap = '4px';
                controlsDiv.style.marginBottom = '4px';
                
                content.config_editor.controls.forEach(control => {
                    const btn = document.createElement('button');
                    btn.textContent = control.text;
                    btn.title = control.tooltip || '';
                    btn.onclick = () => eval(control.action);
                    btn.style.padding = '4px 6px';
                    btn.style.fontSize = '10px';
                    btn.style.border = '1px solid #ddd';
                    btn.style.borderRadius = '3px';
                    btn.style.cursor = 'pointer';
                    
                    if (control.style === 'primary') {
                        btn.style.background = '#007bff';
                        btn.style.color = 'white';
                    } else if (control.style === 'success') {
                        btn.style.background = '#28a745';
                        btn.style.color = 'white';
                    } else if (control.style === 'secondary') {
                        btn.style.background = '#6c757d';
                        btn.style.color = 'white';
                    }
                    
                    controlsDiv.appendChild(btn);
                });
                
                editorContainer.appendChild(controlsDiv);
            }
            
            // Текстовый редактор
            const textarea = document.createElement('textarea');
            textarea.id = 'configEditor';
            textarea.style.width = '100%';
            textarea.style.height = content.config_editor.height;
            textarea.style.fontFamily = "'Courier New', monospace";
            textarea.style.fontSize = '11px';
            textarea.style.border = '1px solid #ddd';
            textarea.style.borderRadius = '4px';
            textarea.style.padding = '4px';
            textarea.style.resize = 'vertical';
            textarea.placeholder = 'JSON config will be loaded here...';
            editorContainer.appendChild(textarea);
            
            card.appendChild(editorContainer);
        }
        
        // Фильтры и расписание
        if (content.schedule_control) {
            const scheduleDiv = document.createElement('div');
            scheduleDiv.style.fontSize = '14px';
            scheduleDiv.style.marginBottom = '8px';
            
            // Частота загрузок
            if (content.schedule_control.frequency) {
                const freqDiv = document.createElement('div');
                freqDiv.style.display = 'flex';
                freqDiv.style.justifyContent = 'space-between';
                freqDiv.style.alignItems = 'center';
                freqDiv.style.marginBottom = '4px';
                
                const label = document.createElement('span');
                label.textContent = content.schedule_control.frequency.label;
                freqDiv.appendChild(label);
                
                const input = document.createElement('input');
                input.id = content.schedule_control.frequency.input_id;
                input.type = 'number';
                input.value = content.schedule_control.frequency.value;
                input.min = content.schedule_control.frequency.min;
                input.max = content.schedule_control.frequency.max;
                input.title = content.schedule_control.frequency.tooltip;
                input.style.width = '50px';
                input.style.padding = '2px';
                input.style.fontSize = '12px';
                freqDiv.appendChild(input);
                
                scheduleDiv.appendChild(freqDiv);
            }
            
            // Следующая загрузка
            if (content.schedule_control.next_load) {
                const nextDiv = document.createElement('div');
                nextDiv.style.display = 'flex';
                nextDiv.style.justifyContent = 'space-between';
                
                const label = document.createElement('span');
                label.textContent = content.schedule_control.next_load.label;
                nextDiv.appendChild(label);
                
                const value = document.createElement('span');
                value.id = content.schedule_control.next_load.value_id;
                value.textContent = content.schedule_control.next_load.value;
                nextDiv.appendChild(value);
                
                scheduleDiv.appendChild(nextDiv);
            }
            
            card.appendChild(scheduleDiv);
        }
    }
    
    return card;
}

// Построение панели из конфигурации
async function buildDashboard() {
    const config = await loadDashboardConfig();
    if (!config || !config.dashboard_config) {
        console.error('Invalid dashboard configuration');
        return;
    }
    
    const dashConfig = config.dashboard_config;
    
    // Обновление заголовка
    if (dashConfig.header) {
        const headerTitle = document.querySelector('.header h1');
        if (headerTitle) {
            headerTitle.textContent = dashConfig.header.title;
        }
        
        const subtitle = document.querySelector('.header .subtitle');
        if (subtitle) {
            subtitle.textContent = dashConfig.header.version;
        }
        
        // Кнопка обновления
        const refreshBtn = document.getElementById('manualRefreshBtn');
        if (refreshBtn && dashConfig.header.refresh_button) {
            refreshBtn.textContent = dashConfig.header.refresh_button.text;
            refreshBtn.title = dashConfig.header.refresh_button.tooltip;
            refreshBtn.onclick = () => eval(dashConfig.header.refresh_button.action);
        }
    }
    
    // Статусная строка
    if (dashConfig.status_row && dashConfig.status_row.cards) {
        const statusRow = document.querySelector('.status-row');
        if (statusRow) {
            statusRow.innerHTML = ''; // Очищаем
            dashConfig.status_row.cards.forEach(cardConfig => {
                const card = createStatusCard(cardConfig);
                statusRow.appendChild(card);
            });
        }
    }
    
    // Основная сетка
    if (dashConfig.main_grid && dashConfig.main_grid.cards) {
        const mainGrid = document.querySelector('.dashboard-grid');
        if (mainGrid) {
            mainGrid.innerHTML = ''; // Очищаем
            dashConfig.main_grid.cards.forEach(cardConfig => {
                const card = createMainCard(cardConfig);
                mainGrid.appendChild(card);
            });
        }
    }
    
    // Настройка автообновления
    if (dashConfig.refresh_interval_ms) {
        startAutoRefresh(dashConfig.refresh_interval_ms);
    }
}

// Функции управления
function startSystem() {
    console.log('Starting system...');
    fetch('/api/daemon/start', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log('System started:', data);
            refreshAll();
        })
        .catch(error => console.error('Failed to start system:', error));
}

function stopSystem() {
    console.log('Stopping system...');
    fetch('/api/daemon/stop', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log('System stopped:', data);
            refreshAll();
        })
        .catch(error => console.error('Failed to stop system:', error));
}

function toggleAllFilters(enable) {
    console.log('Toggle all filters:', enable);
    fetch('/api/filters/toggle-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enable })
    })
        .then(response => response.json())
        .then(data => {
            console.log('Filters toggled:', data);
            refreshAll();
        })
        .catch(error => console.error('Failed to toggle filters:', error));
}

function invertFilters() {
    console.log('Inverting filters...');
    fetch('/api/filters/invert', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log('Filters inverted:', data);
            refreshAll();
        })
        .catch(error => console.error('Failed to invert filters:', error));
}

function updateFrequency() {
    const input = document.getElementById('loadFrequency');
    if (input) {
        const value = parseInt(input.value);
        console.log('Updating frequency to:', value);
        fetch('/api/schedule/frequency', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ frequency_hours: value })
        })
            .then(response => response.json())
            .then(data => {
                console.log('Frequency updated:', data);
                refreshAll();
            })
            .catch(error => console.error('Failed to update frequency:', error));
    }
}

function manualRefresh() {
    console.log('Manual refresh triggered');
    refreshAll();
}

function refreshAll() {
    console.log('Refreshing all data...');
    updateStats();
    updateFilters();
    updateTasks();
    
    // Обновление времени последнего обновления
    const lastRefresh = document.getElementById('lastRefresh');
    if (lastRefresh) {
        const now = new Date();
        lastRefresh.textContent = now.toLocaleTimeString('ru-RU');
    }
}

async function updateStats() {
    try {
        const response = await fetch('/api/stats');
        const data = await response.json();
        
        // Обновление значений на панели
        if (data.system_info) {
            const systemHealth = document.getElementById('system_health');
            if (systemHealth) {
                const cpu = data.system_info.cpu_percent || 0;
                const mem = data.system_info.memory_percent || 0;
                const disk = data.system_info.disk_percent || 0;
                const healthScore = ((100 - cpu) + (100 - mem) + (100 - disk)) / 3;
                
                const subtitle = systemHealth.querySelector('.status-title div');
                if (subtitle) {
                    subtitle.textContent = `${healthScore.toFixed(1)}% = CPU ${cpu.toFixed(0)}% + RAM ${mem.toFixed(0)}% + Disk ${disk.toFixed(0)}%`;
                }
            }
        }
        
        if (data.daemon_status) {
            const daemonStatus = document.getElementById('daemonStatus');
            if (daemonStatus) {
                daemonStatus.textContent = `PID: ${data.daemon_status.pid || 'N/A'} • Started: ${data.daemon_status.start_time || 'N/A'}`;
            }
            
            const unixTime = document.getElementById('daemonUnixTime');
            if (unixTime) {
                unixTime.textContent = `, Unix: ${data.daemon_status.unix_time || Math.floor(Date.now() / 1000)}`;
            }
        }
        
        if (data.task_stats) {
            const taskStats = document.getElementById('taskStats');
            if (taskStats) {
                taskStats.textContent = `${data.task_stats.running || 0} running, ${data.task_stats.pending || 0} pending`;
            }
        }
        
        if (data.api_status) {
            const apiHealth = document.getElementById('apiHealth');
            if (apiHealth) {
                apiHealth.textContent = `${data.api_status.status || '200 OK'} • ${data.api_status.bans || 0} bans`;
            }
        }
    } catch (error) {
        console.error('Failed to update stats:', error);
    }
}

async function updateFilters() {
    try {
        const response = await fetch('/api/filters/list');
        const data = await response.json();
        
        const activeFilters = document.getElementById('activeFilters');
        if (activeFilters && data.filters) {
            const active = data.filters.filter(f => f.active).length;
            activeFilters.textContent = active;
        }
    } catch (error) {
        console.error('Failed to update filters:', error);
    }
}

async function updateTasks() {
    try {
        const response = await fetch('/api/daemon/tasks');
        const data = await response.json();
        
        const vacancyCount = document.getElementById('vacancyCount');
        if (vacancyCount) {
            vacancyCount.textContent = data.vacancies_count || '0';
        }
        
        const employerCount = document.getElementById('employerCount');
        if (employerCount) {
            employerCount.textContent = data.employers_count || '0';
        }
        
        const queueEta = document.getElementById('queueEta');
        if (queueEta) {
            queueEta.textContent = data.queue_eta || '~0min';
        }
        
        const activeWorkers = document.getElementById('activeWorkers');
        if (activeWorkers) {
            activeWorkers.textContent = `${data.active_workers || 0}/${data.total_workers || 5}`;
        }
    } catch (error) {
        console.error('Failed to update tasks:', error);
    }
}

function startAutoRefresh(intervalMs) {
    if (refreshInterval) {
        clearInterval(refreshInterval);
    }
    
    refreshInterval = setInterval(() => {
        refreshAll();
    }, intervalMs);
    
    console.log(`Auto-refresh started with interval: ${intervalMs}ms`);
}

// Config editor функции
async function readConfigFromDisk() {
    try {
        const response = await fetch('/api/config/read');
        const data = await response.json();
        
        const editor = document.getElementById('configEditor');
        if (editor) {
            editor.value = JSON.stringify(data, null, 2);
        }
    } catch (error) {
        console.error('Failed to read config:', error);
    }
}

async function writeConfigToDisk() {
    const editor = document.getElementById('configEditor');
    if (!editor) return;
    
    try {
        const config = JSON.parse(editor.value);
        const response = await fetch('/api/config/write', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            alert('Config saved successfully!');
        } else {
            alert('Failed to save config');
        }
    } catch (error) {
        console.error('Failed to write config:', error);
        alert('Invalid JSON format');
    }
}

function resetConfigEditor() {
    const editor = document.getElementById('configEditor');
    if (editor) {
        editor.value = '';
        readConfigFromDisk();
    }
}

// Инициализация при загрузке страницы
document.addEventListener('DOMContentLoaded', () => {
    console.log('Dashboard v4 initializing...');
    buildDashboard();
    refreshAll();
});
