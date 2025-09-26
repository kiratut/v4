function createStatusCard(cardConfig) {
    const card = document.createElement('div');
    card.className = 'card status-card';
    card.id = cardConfig.id;

    // Добавляем data-metric атрибут если указан
    if (cardConfig.data_metric) {
        card.setAttribute('data-metric', cardConfig.data_metric);
    }

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
