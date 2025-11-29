/* AI-Palindromikisa - Minimal JavaScript for tooltips and charts */

const tooltip = document.getElementById('tooltip');
let data = null;

// Fetch and render data
fetch('data.json')
  .then(r => r.json())
  .then(d => { data = d; render(); })
  .catch(e => console.error('Failed to load data:', e));

function render() {
  renderGeneratedAt();
  renderModelsTable();
  renderTotals();
  renderTasksTable();
  renderLegend();
  renderCharts();
}

function renderGeneratedAt() {
  document.getElementById('generated-at').textContent =
    `Generated: ${new Date(data.generated_at).toLocaleString()}`;
}

function renderModelsTable() {
  const tbody = document.querySelector('#models-table tbody');
  tbody.innerHTML = data.models.map((m, i) => `
    <tr>
      <td>${i + 1}</td>
      <td>${(m.accuracy * 100).toFixed(1)}%</td>
      <td>${m.correct}/${m.total}</td>
      <td>${(m.cost_per_task * 100).toFixed(2)}\u00a2</td>
      <td>${m.time_per_task.toFixed(1)}s</td>
      <td>${m.first_date ?? '-'}</td>
      <td>${m.last_date ?? '-'}</td>
      <td class="model-name">${m.name}</td>
    </tr>
  `).join('');
}

function renderTotals() {
  document.getElementById('totals').textContent =
    `Total cost across all logged tasks: $${data.totals.cost.toFixed(2)} (${data.totals.log_count} log files)`;
}

function renderTasksTable() {
  const tbody = document.querySelector('#tasks-table tbody');
  tbody.innerHTML = data.tasks.map(t => `
    <tr>
      <td>${(t.success_rate * 100).toFixed(0)}%</td>
      <td>${t.avg_time.toFixed(1)}s</td>
      <td>${(t.avg_cost * 100).toFixed(2)}\u00a2</td>
      <td class="model-markers">${buildMarkers(t.model_results)}</td>
      <td class="answer-text" data-tooltip="${t.reference.replaceAll('"', '&quot;')}">${t.reference}</td>
      <td class="prompt-text" data-tooltip="${t.prompt.replaceAll('"', '&quot;')}">${t.prompt}</td>
    </tr>
  `).join('');

  attachTooltips();
}

function buildMarkers(results) {
  return data.sorted_model_names.map(name => {
    const model = data.models.find(m => m.name === name) ?? { marker: '?', color: '#888' };
    const success = results[name];
    if (success === true) {
      return `<span class="marker marker-success" style="color:${model.color}" data-tooltip="${name}">${model.marker}</span>`;
    } else if (success === false) {
      return `<span class="marker marker-fail" data-tooltip="${name} (failed)">\u00b7</span>`;
    }
    return `<span class="marker">\u00a0</span>`;
  }).join('');
}

function renderLegend() {
  document.getElementById('legend-items').innerHTML = data.sorted_model_names.map(name => {
    const model = data.models.find(m => m.name === name) ?? { marker: '?', color: '#888' };
    return `<div class="legend-item">
      <span class="legend-marker" style="color:${model.color}">${model.marker}</span>
      <span class="legend-name">${name}</span>
    </div>`;
  }).join('');
}

function renderCharts() {
  // Convert cost from dollars to cents for charts
  const successVsCostCents = data.chart_data.success_vs_cost.map(p => ({ ...p, x: p.x * 100 }));
  const timeVsCostCents = data.chart_data.time_vs_cost_top5.map(p => ({ ...p, x: p.x * 100 }));
  const successVsCostPerSuccessCents = data.chart_data.success_vs_cost_per_success.map(p => ({ ...p, x: p.x * 100 }));

  // Success vs Cost: best = low cost (x: 0 to median), high success (y: median to 100)
  renderScatterChart('chart-success-cost', successVsCostCents, '\u00a2/Task', 'Success %', {
    xMin: 0,
    xMaxFn: (xMedian) => xMedian,
    yMinFn: (yMedian) => yMedian,
    yMax: 100,
    tooltipFn: p => `${p.marker} ${p.name}: ${p.y.toFixed(1)}%, ${p.x.toFixed(2)}\u00a2`
  });

  // Success vs Cost per Success: best = low cost per success (x: 0 to median), high success (y: median to 100)
  renderScatterChart('chart-success-cost-per-success', successVsCostPerSuccessCents, '\u00a2/Success', 'Success %', {
    xMin: 0,
    xMaxFn: (xMedian) => xMedian,
    yMinFn: (yMedian) => yMedian,
    yMax: 100,
    tooltipFn: p => `${p.marker} ${p.name}: ${p.y.toFixed(1)}%, ${p.x.toFixed(2)}\u00a2/success`
  });

  // Success vs Time: best = low time (x: 0 to median), high success (y: median to 100)
  renderScatterChart('chart-success-time', data.chart_data.success_vs_time, 'Time/Task (s)', 'Success %', {
    xMin: 0,
    xMaxFn: (xMedian) => xMedian,
    yMinFn: (yMedian) => yMedian,
    yMax: 100,
    tooltipFn: p => `${p.marker} ${p.name}: ${p.y.toFixed(1)}%, ${p.x.toFixed(1)}s`
  });

  // Time vs Cost (top 5): best = low cost (x: 0 to median), low time (y: 0 to median)
  renderScatterChart('chart-time-cost', timeVsCostCents, '\u00a2/Task', 'Time/Task (s)', {
    xMin: 0,
    xMaxFn: (xMedian) => xMedian,
    yMin: 0,
    yMaxFn: (yMedian) => yMedian,
    tooltipFn: p => `${p.marker} ${p.name}: ${p.y.toFixed(1)}s, ${p.x.toFixed(2)}\u00a2`
  });
}

function renderScatterChart(canvasId, points, xLabel, yLabel, quadrant) {
  const ctx = document.getElementById(canvasId).getContext('2d');

  const xValues = points.map(p => p.x);
  const yValues = points.map(p => p.y);
  const xMedian = median(xValues);
  const yMedian = median(yValues);
  const yMax = Math.max(...yValues);

  // Calculate quadrant bounds
  const boxXMin = quadrant.xMin ?? quadrant.xMinFn?.(xMedian) ?? 0;
  const boxXMax = quadrant.xMax ?? quadrant.xMaxFn?.(xMedian) ?? xMedian;
  const boxYMin = quadrant.yMinFn?.(yMedian) ?? quadrant.yMin ?? 0;
  const boxYMax = quadrant.yMaxFn?.(yMedian) ?? quadrant.yMax ?? yMax;

  new Chart(ctx, {
    type: 'scatter',
    data: {
      datasets: points.map(p => ({
        label: p.name,
        data: [{ x: p.x, y: p.y }],
        backgroundColor: p.color,
        borderColor: p.color,
        pointRadius: 8,
        pointStyle: 'circle'
      }))
    },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      aspectRatio: 1,
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => quadrant.tooltipFn(points[ctx.datasetIndex])
          }
        },
        annotation: {
          annotations: {
            bestQuadrant: {
              type: 'box',
              xMin: boxXMin,
              xMax: boxXMax,
              yMin: boxYMin,
              yMax: boxYMax,
              backgroundColor: 'rgba(59, 130, 246, 0.08)',
              borderWidth: 0
            }
          }
        }
      },
      scales: {
        x: {
          title: { display: true, text: xLabel, color: '#8b949e' },
          grid: { color: '#30363d' },
          ticks: { color: '#8b949e' },
          min: 0
        },
        y: {
          title: { display: true, text: yLabel, color: '#8b949e' },
          grid: { color: '#30363d' },
          ticks: { color: '#8b949e' },
          min: 0,
          ...(quadrant.yMax === 100 ? { max: 100 } : {})
        }
      }
    },
    plugins: [{
      afterDatasetsDraw(chart) {
        const ctx = chart.ctx;
        chart.data.datasets.forEach((_, i) => {
          const meta = chart.getDatasetMeta(i);
          const p = points[i];
          for (const point of meta.data) {
            ctx.save();
            ctx.font = 'bold 11px monospace';
            ctx.fillStyle = '#fff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(p.marker, point.x, point.y);
            ctx.restore();
          }
        });
      }
    }]
  });
}

const median = arr => {
  const sorted = arr.toSorted((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
};

// Tooltip handling
function attachTooltips() {
  for (const el of document.querySelectorAll('[data-tooltip]')) {
    el.addEventListener('pointerenter', showTooltip);
    el.addEventListener('pointerleave', hideTooltip);
    el.addEventListener('pointermove', moveTooltip);
  }
}

function showTooltip(e) {
  const text = e.target.dataset.tooltip;
  if (!text) return;
  tooltip.textContent = text;
  tooltip.classList.add('visible');
  moveTooltip(e);
}

function hideTooltip() {
  tooltip.classList.remove('visible');
}

function moveTooltip(e) {
  let x = e.clientX + 12;
  let y = e.clientY + 12;
  const rect = tooltip.getBoundingClientRect();
  if (x + rect.width > innerWidth) x = e.clientX - rect.width - 12;
  if (y + rect.height > innerHeight) y = e.clientY - rect.height - 12;
  tooltip.style.left = `${x}px`;
  tooltip.style.top = `${y}px`;
}
