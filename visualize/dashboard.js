const els = {
  statusStrip: document.querySelector('#statusStrip'),
  statusText: document.querySelector('#statusText'),
  generatedAt: document.querySelector('#generatedAt'),
  dayCount: document.querySelector('#dayCount'),
  recordCount: document.querySelector('#recordCount'),
  uniqueCount: document.querySelector('#uniqueCount'),
  historyPointCount: document.querySelector('#historyPointCount'),
  v2FileCount: document.querySelector('#v2FileCount'),
  legacyFileCount: document.querySelector('#legacyFileCount'),
  dailyRange: document.querySelector('#dailyRange'),
  dailyHeatChart: document.querySelector('#dailyHeatChart'),
  dailyFocus: document.querySelector('#dailyFocus'),
  topHeatList: document.querySelector('#topHeatList'),
};

let dashboardStats = null;

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

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '--';
  return new Intl.NumberFormat('zh-CN').format(Number(value));
}

function formatShortTime(value) {
  if (!value) return '--';
  return value.replace(/\s\+0800$/, '');
}

function renderTotals(totals) {
  els.dayCount.textContent = formatNumber(totals.day_count);
  els.recordCount.textContent = formatNumber(totals.topic_record_count);
  els.uniqueCount.textContent = formatNumber(totals.unique_topic_count);
  els.historyPointCount.textContent = formatNumber(totals.history_point_count);
  els.v2FileCount.textContent = formatNumber(totals.v2_file_count);
  els.legacyFileCount.textContent = formatNumber(totals.legacy_file_count);
}

function renderTopHeatList(points) {
  els.topHeatList.textContent = '';
  if (!points.length) {
    const empty = document.createElement('li');
    empty.className = 'top-item';
    empty.textContent = '暂无可统计热度';
    els.topHeatList.appendChild(empty);
    return;
  }

  points.forEach((point, index) => {
    const item = document.createElement('li');
    item.className = 'top-item';

    const rank = document.createElement('span');
    rank.className = 'top-rank';
    rank.textContent = `#${index + 1}`;

    const body = document.createElement('div');
    body.className = 'top-body';

    const title = document.createElement('a');
    title.href = point.url || '#';
    title.target = '_blank';
    title.rel = 'noreferrer';
    title.textContent = point.title || '无标题';

    const meta = document.createElement('p');
    meta.textContent = `${point.date} / ${formatShortTime(point.observed_at)} / 榜单 #${point.rank || '--'} / ${point.heat_text || '未知热度'}`;

    body.append(title, meta);

    const heat = document.createElement('strong');
    heat.textContent = formatNumber(point.heat_value);

    item.append(rank, body, heat);
    els.topHeatList.appendChild(item);
  });
}

function renderDailyFocus(point) {
  if (!point) {
    els.dailyFocus.innerHTML = '<span>悬停或点击折线点查看某日摘要</span>';
    return;
  }

  const link = point.top_topic_url
    ? `<a href="${point.top_topic_url}" target="_blank" rel="noreferrer">${escapeHtml(point.top_topic_title || '当日最高热度话题')}</a>`
    : escapeHtml(point.top_topic_title || '当日最高热度话题');
  els.dailyFocus.innerHTML = `
    <strong>${point.date}</strong>
    <span>总热度 ${formatNumber(point.total_heat_value)}</span>
    <span>最高热度 ${formatNumber(point.max_heat_value)}</span>
    <span>话题 ${formatNumber(point.topic_count)}</span>
    <span>${link}</span>
  `;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function renderDailyChart(series) {
  const svg = els.dailyHeatChart;
  const width = 1100;
  const height = 330;
  const pad = { top: 28, right: 30, bottom: 42, left: 74 };
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  svg.textContent = '';

  const points = series
    .map((point, index) => ({ ...point, index, value: Number(point.total_heat_value || 0) }))
    .filter((point) => Number.isFinite(point.value));

  if (!points.length) {
    els.dailyRange.textContent = '--';
    drawText(svg, width / 2, height / 2, '没有可绘制的每日热度数据', 'middle', 'chart-muted');
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
    const circle = drawCircle(svg, x(index), y(point.value), 'chart-point daily-point');
    circle.addEventListener('mouseenter', () => renderDailyFocus(point));
    circle.addEventListener('focus', () => renderDailyFocus(point));
    circle.addEventListener('click', () => renderDailyFocus(point));
    circle.setAttribute('tabindex', '0');
    circle.setAttribute('role', 'button');
    circle.setAttribute('aria-label', `${point.date} 总热度 ${formatNumber(point.total_heat_value)}`);
  });

  drawText(svg, pad.left - 8, y(max), formatNumber(max), 'end', 'chart-label');
  drawText(svg, pad.left - 8, y(min), formatNumber(min), 'end', 'chart-label');
  drawText(svg, x(0), height - 12, points[0].date, 'middle', 'chart-label');
  drawText(svg, x(points.length - 1), height - 12, points[points.length - 1].date, 'middle', 'chart-label');
  els.dailyRange.textContent = `${formatNumber(min)} - ${formatNumber(max)}`;
  renderDailyFocus(points[points.length - 1]);
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
  circle.setAttribute('r', '4.5');
  circle.setAttribute('class', className);
  svg.appendChild(circle);
  return circle;
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

function renderDashboard(stats) {
  els.generatedAt.textContent = `生成于 ${formatShortTime(stats.generated_at)}`;
  renderTotals(stats.totals || {});
  renderDailyChart(stats.daily_series || []);
  renderTopHeatList(stats.top_heat_points || []);
}

async function init() {
  if (window.location.protocol === 'file:') {
    setStatus('请从仓库根目录运行 python -m http.server 后访问 /visualize/dashboard.html', 'error');
    return;
  }

  try {
    dashboardStats = await fetchJson('./dashboard-stats.json');
  } catch (error) {
    setStatus('缺少 dashboard-stats.json：请先运行 python visualize/build_index.py', 'error');
    return;
  }

  renderDashboard(dashboardStats);
  setStatus('统计数据已载入', 'ready');
}

init();
