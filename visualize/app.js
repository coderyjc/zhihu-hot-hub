const state = {
  index: null,
  globalData: null,
  selectedDate: null,
  selectedData: null,
  selectedTopic: null,
  activeTrack: 'daily',
  sort: 'rank',
  query: '',
};

const els = {
  statusStrip: document.querySelector('#statusStrip'),
  statusText: document.querySelector('#statusText'),
  dateCount: document.querySelector('#dateCount'),
  dateList: document.querySelector('#dateList'),
  selectedDate: document.querySelector('#selectedDate'),
  selectedMeta: document.querySelector('#selectedMeta'),
  searchInput: document.querySelector('#searchInput'),
  sortSelect: document.querySelector('#sortSelect'),
  topicCount: document.querySelector('#topicCount'),
  maxHeat: document.querySelector('#maxHeat'),
  historyCount: document.querySelector('#historyCount'),
  topicRows: document.querySelector('#topicRows'),
  emptyState: document.querySelector('#emptyState'),
  rowTemplate: document.querySelector('#rowTemplate'),
  dateTemplate: document.querySelector('#dateTemplate'),
  drawer: document.querySelector('#detailDrawer'),
  backdrop: document.querySelector('#drawerBackdrop'),
  closeDrawer: document.querySelector('#closeDrawer'),
  drawerRank: document.querySelector('#drawerRank'),
  drawerTitle: document.querySelector('#drawerTitle'),
  topicLink: document.querySelector('#topicLink'),
  dailyTrackButton: document.querySelector('#dailyTrackButton'),
  globalTrackButton: document.querySelector('#globalTrackButton'),
  chartTitle: document.querySelector('#chartTitle'),
  chartRange: document.querySelector('#chartRange'),
  heatChart: document.querySelector('#heatChart'),
  historyList: document.querySelector('#historyList'),
};

function setStatus(text, mode = 'loading') {
  els.statusText.textContent = text;
  els.statusStrip.classList.toggle('ready', mode === 'ready');
  els.statusStrip.classList.toggle('error', mode === 'error');
}

async function fetchJson(path) {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`${path} ${response.status}`);
  }
  return response.json();
}

function parseHeatValue(text) {
  if (!text) return null;
  const match = String(text).replace(/,/g, '').match(/(\d+(?:\.\d+)?)\s*([万亿]?)/);
  if (!match) return null;
  let value = Number(match[1]);
  if (!Number.isFinite(value)) return null;
  if (match[2] === '万') value *= 10000;
  if (match[2] === '亿') value *= 100000000;
  return Math.trunc(value);
}

function fromLegacyItem(item, rank, observedAt) {
  const target = item.target || {};
  const title = target.title_area?.text || '无标题';
  const url = target.link?.url || '#';
  const heatText = target.metrics_area?.text || '';
  const heatValue = parseHeatValue(heatText);
  return {
    key: item.card_id || url || title,
    title,
    url,
    first_seen: observedAt,
    last_seen: observedAt,
    first_rank: rank,
    latest_rank: rank,
    latest_heat_text: heatText,
    latest_heat_value: heatValue,
    latest_item: item,
    history: [{
      observed_at: observedAt,
      rank,
      heat_text: heatText,
      heat_value: heatValue,
      legacy_import: true,
    }],
  };
}

function normalizeData(data, fallbackDate) {
  if (data?.version === 2 && Array.isArray(data.items)) {
    return data;
  }
  const observedAt = data?.updated_at || `${fallbackDate} 00:00:00 +0800`;
  const source = Array.isArray(data?.data) ? data.data : [];
  return {
    version: 1,
    scope: 'legacy',
    date: fallbackDate,
    updated_at: observedAt,
    items: source.map((item, index) => fromLegacyItem(item, index + 1, observedAt)),
  };
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  return new Intl.NumberFormat('zh-CN').format(Number(value));
}

function formatShortTime(value) {
  if (!value) return '--';
  return value.replace(/\s\+0800$/, '');
}

function getHistory(item) {
  return Array.isArray(item?.history) ? item.history : [];
}

function getHeatValue(point) {
  if (point?.heat_value !== null && point?.heat_value !== undefined) return Number(point.heat_value);
  return parseHeatValue(point?.heat_text);
}

function getVisibleItems() {
  const query = state.query.trim().toLowerCase();
  let items = [...(state.selectedData?.items || [])];
  if (query) {
    items = items.filter((item) => `${item.title} ${item.url}`.toLowerCase().includes(query));
  }
  items.sort((a, b) => {
    if (state.sort === 'heat') {
      return (b.latest_heat_value || 0) - (a.latest_heat_value || 0);
    }
    if (state.sort === 'history') {
      return getHistory(b).length - getHistory(a).length;
    }
    return (a.latest_rank || 9999) - (b.latest_rank || 9999);
  });
  return items;
}

function renderDates() {
  els.dateList.textContent = '';
  const dates = state.index?.dates || [];
  els.dateCount.textContent = dates.length;
  dates.forEach((entry) => {
    const node = els.dateTemplate.content.firstElementChild.cloneNode(true);
    node.classList.toggle('active', entry.date === state.selectedDate);
    node.querySelector('.date-value').textContent = entry.date;
    node.querySelector('.date-meta').textContent = `${entry.item_count || 0} 条 / ${formatShortTime(entry.updated_at)}`;
    node.addEventListener('click', () => selectDate(entry.date));
    els.dateList.appendChild(node);
  });
}

function renderSummary(items) {
  const max = items.reduce((acc, item) => Math.max(acc, Number(item.latest_heat_value || 0)), 0);
  const historyCount = items.reduce((acc, item) => acc + getHistory(item).length, 0);
  els.topicCount.textContent = state.selectedData?.items?.length || 0;
  els.maxHeat.textContent = max ? formatNumber(max) : '--';
  els.historyCount.textContent = historyCount;
}

function renderTable() {
  const items = getVisibleItems();
  els.topicRows.textContent = '';
  els.emptyState.hidden = items.length > 0;
  items.forEach((item) => {
    const row = els.rowTemplate.content.firstElementChild.cloneNode(true);
    row.querySelector('.rank-cell').textContent = item.latest_rank ? `#${item.latest_rank}` : '--';
    row.querySelector('.title-cell').textContent = item.title || '无标题';
    row.querySelector('.heat-cell').textContent = item.latest_heat_text || '未知热度';
    row.querySelector('.value-cell').textContent = formatNumber(item.latest_heat_value);
    row.querySelector('.history-cell').textContent = getHistory(item).length;
    row.querySelector('.first-cell').textContent = formatShortTime(item.first_seen);
    row.querySelector('.last-cell').textContent = formatShortTime(item.last_seen);
    row.addEventListener('click', () => openTopic(item));
    els.topicRows.appendChild(row);
  });
}

function renderBoard() {
  const entry = state.index?.dates?.find((item) => item.date === state.selectedDate);
  els.selectedDate.textContent = state.selectedDate || '未选择日期';
  els.selectedMeta.textContent = entry
    ? `${entry.item_count || 0} 条记录，更新于 ${formatShortTime(entry.updated_at)}`
    : '等待数据';
  renderDates();
  renderSummary(state.selectedData?.items || []);
  renderTable();
}

async function selectDate(date) {
  const entry = state.index.dates.find((item) => item.date === date);
  if (!entry) return;
  try {
    setStatus(`正在载入 ${date}`);
    const data = await fetchJson(entry.path);
    state.selectedDate = date;
    state.selectedData = normalizeData(data, date);
    state.selectedTopic = null;
    renderBoard();
    setStatus(`已载入 ${date}`, 'ready');
  } catch (error) {
    setStatus(`载入 ${date} 失败：${error.message}`, 'error');
  }
}

function findGlobalTopic(key) {
  return (state.globalData?.items || []).find((item) => item.key === key);
}

function openTopic(item) {
  state.selectedTopic = item;
  state.activeTrack = 'daily';
  els.drawer.classList.add('open');
  els.drawer.setAttribute('aria-hidden', 'false');
  els.backdrop.hidden = false;
  renderDrawer();
}

function closeDrawer() {
  els.drawer.classList.remove('open');
  els.drawer.setAttribute('aria-hidden', 'true');
  els.backdrop.hidden = true;
}

function getActiveTrack() {
  if (!state.selectedTopic) return [];
  if (state.activeTrack === 'global') {
    return getHistory(findGlobalTopic(state.selectedTopic.key));
  }
  return getHistory(state.selectedTopic);
}

function renderDrawer() {
  const item = state.selectedTopic;
  if (!item) return;
  const globalTopic = findGlobalTopic(item.key);
  els.drawerRank.textContent = item.latest_rank ? `最新排名 #${item.latest_rank}` : '话题详情';
  els.drawerTitle.textContent = item.title || '无标题';
  els.topicLink.href = item.url || '#';
  els.globalTrackButton.disabled = !globalTopic;
  els.dailyTrackButton.classList.toggle('active', state.activeTrack === 'daily');
  els.globalTrackButton.classList.toggle('active', state.activeTrack === 'global');
  const history = getActiveTrack();
  els.chartTitle.textContent = state.activeTrack === 'global' ? '全局热度变化' : '当天热度变化';
  renderChart(history);
  renderHistory(history);
}

function renderHistory(history) {
  els.historyList.textContent = '';
  if (!history.length) {
    const item = document.createElement('li');
    item.textContent = '暂无轨迹记录';
    els.historyList.appendChild(item);
    return;
  }
  history.forEach((point) => {
    const item = document.createElement('li');
    const time = document.createElement('time');
    const rank = document.createElement('strong');
    const heat = document.createElement('span');
    time.textContent = formatShortTime(point.observed_at);
    rank.textContent = point.rank ? `#${point.rank}` : '排名未知';
    heat.textContent = `${point.heat_text || '未知热度'} / ${formatNumber(getHeatValue(point))}`;
    item.append(time, rank, heat);
    if (point.legacy_import) {
      const badge = document.createElement('span');
      badge.className = 'badge';
      badge.textContent = '旧格式导入';
      item.appendChild(badge);
    }
    els.historyList.appendChild(item);
  });
}

function renderChart(history) {
  const svg = els.heatChart;
  const width = 680;
  const height = 260;
  const pad = { top: 24, right: 24, bottom: 34, left: 58 };
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.textContent = '';

  const points = history
    .map((point, index) => ({ ...point, index, value: getHeatValue(point) }))
    .filter((point) => Number.isFinite(point.value));

  if (!points.length) {
    els.chartRange.textContent = '--';
    drawText(svg, width / 2, height / 2, '没有可绘制的热度数值', 'middle', 'chart-muted');
    return;
  }

  const values = points.map((point) => point.value);
  let min = Math.min(...values);
  let max = Math.max(...values);
  if (min === max) {
    min = Math.max(0, min * 0.92);
    max = max * 1.08 + 1;
  }
  const xMax = Math.max(points.length - 1, 1);
  const x = (idx) => pad.left + (idx / xMax) * (width - pad.left - pad.right);
  const y = (value) => pad.top + ((max - value) / (max - min)) * (height - pad.top - pad.bottom);

  drawAxis(svg, width, height, pad);
  const path = points.map((point, index) => `${index === 0 ? 'M' : 'L'} ${x(index)} ${y(point.value)}`).join(' ');
  const area = `${path} L ${x(points.length - 1)} ${height - pad.bottom} L ${x(0)} ${height - pad.bottom} Z`;
  drawPath(svg, area, 'chart-area');
  drawPath(svg, path, 'chart-line');
  points.forEach((point, index) => {
    drawCircle(svg, x(index), y(point.value), 'chart-point');
  });
  drawText(svg, pad.left - 8, y(max), formatNumber(max), 'end', 'chart-label');
  drawText(svg, pad.left - 8, y(min), formatNumber(min), 'end', 'chart-label');
  drawText(svg, x(0), height - 10, formatShortTime(points[0].observed_at), 'middle', 'chart-label');
  drawText(svg, x(points.length - 1), height - 10, formatShortTime(points[points.length - 1].observed_at), 'middle', 'chart-label');
  els.chartRange.textContent = `${formatNumber(min)} - ${formatNumber(max)}`;
}

function drawAxis(svg, width, height, pad) {
  const axis = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  axis.setAttribute('d', `M ${pad.left} ${pad.top} V ${height - pad.bottom} H ${width - pad.right}`);
  axis.setAttribute('fill', 'none');
  axis.setAttribute('stroke', '#94866e');
  axis.setAttribute('stroke-width', '1');
  svg.appendChild(axis);
}

function drawPath(svg, d, className) {
  const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
  path.setAttribute('d', d);
  path.setAttribute('class', className);
  svg.appendChild(path);
}

function drawCircle(svg, cx, cy, className) {
  const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
  circle.setAttribute('cx', cx);
  circle.setAttribute('cy', cy);
  circle.setAttribute('r', '4');
  circle.setAttribute('class', className);
  svg.appendChild(circle);
}

function drawText(svg, x, y, text, anchor, className) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', 'text');
  node.setAttribute('x', x);
  node.setAttribute('y', y);
  node.setAttribute('text-anchor', anchor);
  node.setAttribute('class', className);
  node.textContent = text;
  svg.appendChild(node);
}

async function init() {
  if (window.location.protocol === 'file:') {
    setStatus('请从仓库根目录运行 python -m http.server 后访问 /visualize/', 'error');
    return;
  }

  try {
    state.index = await fetchJson('./data-index.json');
  } catch (error) {
    setStatus(`缺少 data-index.json：请先运行 python visualize/build_index.py`, 'error');
    return;
  }

  try {
    state.globalData = normalizeData(await fetchJson(state.index.global_path), 'global');
  } catch {
    state.globalData = { version: 2, scope: 'global', items: [] };
  }

  if (!state.index.dates?.length) {
    setStatus('没有可视化数据', 'error');
    renderBoard();
    return;
  }

  await selectDate(state.index.dates[0].date);
}

els.searchInput.addEventListener('input', (event) => {
  state.query = event.target.value;
  renderTable();
});

els.sortSelect.addEventListener('change', (event) => {
  state.sort = event.target.value;
  renderTable();
});

els.closeDrawer.addEventListener('click', closeDrawer);
els.backdrop.addEventListener('click', closeDrawer);
els.dailyTrackButton.addEventListener('click', () => {
  state.activeTrack = 'daily';
  renderDrawer();
});
els.globalTrackButton.addEventListener('click', () => {
  state.activeTrack = 'global';
  renderDrawer();
});
document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') closeDrawer();
});

init();
