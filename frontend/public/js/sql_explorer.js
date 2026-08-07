// CivicPulse SQL Console Explorer Module

const SQLExplorerTab = {
  init() {
    console.log('Initializing SQL Explorer Tab...');
    this.clearEditor();
  },

  loadPreset(num) {
    const input = document.getElementById('sql-query-input');
    if (num === 1) {
      input.value = "SELECT id, category, priority, status, address FROM complaints WHERE priority = 'Urgent';";
    } else if (num === 2) {
      input.value = "SELECT c.id, c.category, c.status, f.crew_name, f.status AS crew_status FROM complaints c JOIN field_crews f ON c.category = f.department;";
    } else if (num === 3) {
      input.value = "SELECT category, COUNT(*) AS total_issues FROM complaints GROUP BY category;";
    } else if (num === 4) {
      input.value = "SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT 5;";
    }
    this.executeQuery();
  },

  clearEditor() {
    document.getElementById('sql-query-input').value = '';
    document.getElementById('sql-query-results-container').innerHTML = `
      <p class="text-center text-outline py-12 italic">Execute a query on the left to inspect tabular results.</p>
    `;
    document.getElementById('sql-result-status').textContent = 'Awaiting query...';
  },

  async executeQuery() {
    const sql = document.getElementById('sql-query-input').value.trim();
    const container = document.getElementById('sql-query-results-container');
    const status = document.getElementById('sql-result-status');

    if (!sql) {
      window.showToast('Please type or select a preset SQL query first.', 'error');
      return;
    }

    status.textContent = 'Executing query...';
    container.innerHTML = `
      <div class="flex items-center justify-center py-12">
        <span class="w-5 h-5 rounded-full border-2 border-secondary border-t-transparent animate-spin"></span>
      </div>
    `;

    try {
      const data = await window.API.executeSQL(sql);
      
      if (data.type === 'select') {
        status.textContent = `Executed in ${data.executionTimeMs}ms | ${data.rows.length} rows returned`;
        
        if (data.rows.length === 0) {
          container.innerHTML = `
            <p class="text-center text-outline py-12 italic">Empty set returned (0 rows).</p>
          `;
          return;
        }

        // Render Table
        container.innerHTML = `
          <table class="w-full text-left border-collapse border border-outline-variant rounded overflow-hidden">
            <thead>
              <tr class="bg-surface-container border-b border-outline-variant font-mono text-[10px] font-bold text-primary uppercase">
                ${data.columns.map(col => `<th class="p-2">${col}</th>`).join('')}
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant text-[10px] font-mono text-on-surface">
              ${data.rows.map(row => `
                <tr class="hover:bg-surface-container-low">
                  ${data.columns.map(col => `<td class="p-2 whitespace-nowrap overflow-hidden max-w-xs truncate" title="${row[col]}">${row[col] !== null ? row[col] : 'NULL'}</td>`).join('')}
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      } else {
        // Write statements (INSERT/UPDATE/DELETE)
        status.textContent = `Executed in ${data.executionTimeMs}ms | ${data.affectedRows} rows affected`;
        container.innerHTML = `
          <div class="p-4 bg-emerald-50 border border-emerald-300 rounded text-emerald-950 font-mono text-[11px] leading-relaxed">
            <strong class="block text-emerald-800 font-bold mb-1">✅ Statement Executed Successfully</strong>
            Affected Rows: ${data.affectedRows} row(s) updated/inserted in SQLite database.
          </div>
        `;
        window.showToast(`SQL query executed successfully! Affected rows: ${data.affectedRows}`);
      }
    } catch (err) {
      status.textContent = 'Query failed';
      container.innerHTML = `
        <div class="p-4 bg-red-50 border border-red-300 rounded text-red-950 font-mono text-[11px] leading-relaxed">
          <strong class="block text-error font-bold mb-1">❌ SQLite Engine Error</strong>
          ${err.message}
        </div>
      `;
      window.showToast('SQL Execution Error', 'error');
    }
  },

  downloadDump() {
    window.location.href = '/api/sql/dump';
    window.showToast('Database SQL Schema dump initiated!');
  }
};

// Bind functions to window global space
function loadSQLConsolePreset(num) {
  SQLExplorerTab.loadPreset(num);
}

function clearSQLEditor() {
  SQLExplorerTab.clearEditor();
}

function executeCustomSQLQuery() {
  SQLExplorerTab.executeQuery();
}

function downloadSQLDatabaseDump() {
  SQLExplorerTab.downloadDump();
}

window.SQLExplorerTab = SQLExplorerTab;
window.loadSQLConsolePreset = loadSQLConsolePreset;
window.clearSQLEditor = clearSQLEditor;
window.executeCustomSQLQuery = executeCustomSQLQuery;
window.downloadSQLDatabaseDump = downloadSQLDatabaseDump;
