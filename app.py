import subprocess
import os
from flask import Flask, request, render_template_string
from datetime import datetime

app = Flask(__name__)

# Configuration paths
KUBECONFIG_PATH = "/path/path/.kube/config"
NGINX_ACCESS = "/var/log/nginx/access.log"
NGINX_ERROR = "/var/log/nginx/error.log"
DOCKER_LOG_DIR = "/var/lib/docker/containers"

def run_cmd(cmd, env=None):
    """Execute a shell command and return its output."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, env=env)
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"Error running command:\n{e.stderr or str(e)}"

def read_file_tail(path, tail=500):
    """Read the last N lines from a file."""
    try:
        with open(path, "r") as f:
            lines = f.readlines()
        return "".join(lines[-tail:])
    except Exception as e:
        return f"Failed to read log file: {e}"

def get_docker_containers():
    """Get list of running Docker containers."""
    try:
        output = run_cmd(["docker", "ps", "--format", "{{.Names}}"])
        return output.strip().splitlines()
    except:
        return []

def get_k8s_namespaces():
    """Get list of Kubernetes namespaces."""
    try:
        env = os.environ.copy()
        env["KUBECONFIG"] = KUBECONFIG_PATH
        output = run_cmd(["kubectl", "get", "ns", "-o", "jsonpath={.items[*].metadata.name}"], env)
        return output.strip().split()
    except:
        return []

def get_k8s_pods(namespace):
    """Get list of pods in a Kubernetes namespace."""
    try:
        env = os.environ.copy()
        env["KUBECONFIG"] = KUBECONFIG_PATH
        output = run_cmd(["kubectl", "get", "pods", "-n", namespace, "-o", "jsonpath={.items[*].metadata.name}"], env)
        return output.strip().split()
    except:
        return []

def get_docker_logs(container, tail=500):
    """Get logs from a Docker container."""
    # First try the standard docker logs command
    try:
        logs = run_cmd(["docker", "logs", "--tail", str(tail), container])
        if "configured logging driver does not support reading" not in logs:
            return logs
    except:
        pass
    
    # Fallback to reading log files directly
    try:
        # Get container ID from name
        container_id = run_cmd(["docker", "inspect", "--format", "{{.Id}}", container]).strip()
        if not container_id:
            return "Could not determine container ID"
            
        # Find the log file (works with json-file logging driver)
        log_file = os.path.join(DOCKER_LOG_DIR, container_id, f"{container_id}-json.log")
        if os.path.exists(log_file):
            return read_file_tail(log_file, tail)
        else:
            return f"Log file not found at {log_file}"
    except Exception as e:
        return f"Failed to get logs via fallback method: {str(e)}"

HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Container Log Viewer</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet" />
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" />
  <style>
    :root {
      --primary: #3b82f6;
      --primary-dark: #2563eb;
      --dark: #1f2937;
      --light: #f9fafb;
      --gray: #9ca3af;
      --gray-dark: #6b7280;
      --danger: #ef4444;
      --success: #10b981;
      --warning: #f59e0b;
      --border-radius: 8px;
      --shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
      --shadow-lg: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    * {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }
    
    body {
      font-family: 'Inter', sans-serif;
      background-color: #f3f4f6;
      color: var(--dark);
      line-height: 1.6;
      min-height: 100vh;
      padding: 0;
    }
    
    .container {
      max-width: 1200px;
      margin: 0 auto;
      padding: 1.5rem;
    }
    
    header {
      margin-bottom: 2rem;
      padding-bottom: 1rem;
      border-bottom: 1px solid #e5e7eb;
    }
    
    .logo {
      display: flex;
      align-items: center;
      gap: 0.75rem;
      font-size: 1.25rem;
      font-weight: 600;
      color: var(--primary-dark);
    }
    
    .logo i {
      font-size: 1.5rem;
    }
    
    .card {
      background: white;
      border-radius: var(--border-radius);
      box-shadow: var(--shadow);
      padding: 1.5rem;
      margin-bottom: 1.5rem;
      transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .card:hover {
      box-shadow: var(--shadow-lg);
    }
    
    .card-header {
      margin-bottom: 1.25rem;
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    
    .card-title {
      font-size: 1.1rem;
      font-weight: 600;
      color: var(--dark);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    
    .form-group {
      margin-bottom: 1.25rem;
    }
    
    label {
      display: block;
      margin-bottom: 0.5rem;
      font-weight: 500;
      color: var(--gray-dark);
      font-size: 0.875rem;
    }
    
    select, input[type="text"], input[type="number"] {
      width: 100%;
      padding: 0.625rem 0.875rem;
      border: 1px solid #e5e7eb;
      border-radius: var(--border-radius);
      font-size: 0.9375rem;
      transition: all 0.2s;
      background-color: white;
    }
    
    select:focus, input[type="text"]:focus, input[type="number"]:focus {
      outline: none;
      border-color: var(--primary);
      box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
    }
    
    button {
      background-color: var(--primary);
      color: white;
      border: none;
      padding: 0.75rem 1.25rem;
      border-radius: var(--border-radius);
      font-size: 0.9375rem;
      font-weight: 500;
      cursor: pointer;
      transition: background-color 0.2s;
      width: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 0.5rem;
    }
    
    button:hover {
      background-color: var(--primary-dark);
    }
    
    .log-container {
      margin-top: 1.5rem;
    }
    
    .log-box {
      background-color: #111827;
      color: #e5e7eb;
      padding: 1.25rem;
      border-radius: var(--border-radius);
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 0.8125rem;
      line-height: 1.7;
      max-height: 500px;
      overflow-y: auto;
      white-space: pre-wrap;
    }
    
    .log-box::-webkit-scrollbar {
      width: 6px;
    }
    
    .log-box::-webkit-scrollbar-track {
      background: #1f2937;
    }
    
    .log-box::-webkit-scrollbar-thumb {
      background: #4b5563;
      border-radius: 3px;
    }
    
    .log-box::-webkit-scrollbar-thumb:hover {
      background: #6b7280;
    }
    
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 1rem;
      margin-bottom: 1.5rem;
    }
    
    .status-card {
      background: white;
      border-radius: var(--border-radius);
      padding: 1rem;
      box-shadow: var(--shadow);
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }
    
    .status-icon {
      width: 2.5rem;
      height: 2.5rem;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    
    .status-icon.primary {
      background-color: rgba(59, 130, 246, 0.1);
      color: var(--primary);
    }
    
    .status-icon.success {
      background-color: rgba(16, 185, 129, 0.1);
      color: var(--success);
    }
    
    .status-icon.warning {
      background-color: rgba(245, 158, 11, 0.1);
      color: var(--warning);
    }
    
    .status-content h3 {
      font-size: 0.8125rem;
      font-weight: 500;
      color: var(--gray-dark);
      margin-bottom: 0.25rem;
    }
    
    .status-content p {
      font-size: 1rem;
      font-weight: 600;
      color: var(--dark);
    }
    
    .badge {
      display: inline-block;
      padding: 0.25rem 0.5rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 500;
    }
    
    .badge.primary {
      background-color: rgba(59, 130, 246, 0.1);
      color: var(--primary);
    }
    
    .empty-state {
      text-align: center;
      padding: 2rem;
      color: var(--gray);
    }
    
    .empty-state i {
      font-size: 2.5rem;
      margin-bottom: 1rem;
      color: #d1d5db;
    }
    
    .empty-state p {
      margin-top: 0.5rem;
    }
    
    .tab-container {
      display: flex;
      border-bottom: 1px solid #e5e7eb;
      margin-bottom: 1.5rem;
    }
    
    .tab {
      padding: 0.75rem 1rem;
      cursor: pointer;
      font-weight: 500;
      color: var(--gray-dark);
      border-bottom: 2px solid transparent;
      transition: all 0.2s;
    }
    
    .tab.active {
      color: var(--primary);
      border-bottom-color: var(--primary);
    }
    
    .tab:hover:not(.active) {
      color: var(--dark);
    }
    
    .refresh-controls {
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }
    
    .refresh-btn {
      background: none;
      border: none;
      color: var(--gray-dark);
      cursor: pointer;
      font-size: 1rem;
      padding: 0.25rem;
      border-radius: 50%;
      width: 30px;
      height: 30px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    
    .refresh-btn:hover {
      background-color: #f3f4f6;
      color: var(--primary);
    }
    
    .refresh-interval {
      display: flex;
      align-items: center;
      gap: 0.25rem;
      font-size: 0.75rem;
      color: var(--gray-dark);
    }
    
    .refresh-interval select {
      width: auto;
      padding: 0.25rem 0.5rem;
      font-size: 0.75rem;
    }
    
    .timestamp {
      font-size: 0.75rem;
      color: var(--gray-dark);
      margin-left: auto;
    }
    
    @media (max-width: 768px) {
      .container {
        padding: 1rem;
      }
      
      .card {
        padding: 1rem;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div class="logo">
        <i class="fas fa-terminal"></i>
        <span>Container Log Viewer</span>
      </div>
    </header>
    
    <div class="tab-container">
      <div class="tab active" onclick="showTab('docker')">
        <i class="fab fa-docker"></i> Docker
      </div>
      <div class="tab" onclick="showTab('kubernetes')">
        <i class="fas fa-network-wired"></i> Kubernetes
      </div>
      <div class="tab" onclick="showTab('system')">
        <i class="fas fa-server"></i> System
      </div>
    </div>
    
    <div class="grid">
      <div class="status-card">
        <div class="status-icon primary">
          <i class="fab fa-docker"></i>
        </div>
        <div class="status-content">
          <h3>Docker Containers</h3>
          <p>{{ docker_containers|length }} running</p>
        </div>
      </div>
      
      <div class="status-card">
        <div class="status-icon success">
          <i class="fas fa-network-wired"></i>
        </div>
        <div class="status-content">
          <h3>K8s Namespaces</h3>
          <p>{{ k8s_namespaces|length }} available</p>
        </div>
      </div>
    </div>
    
    <div class="card" id="docker-tab">
      <div class="card-header">
        <h2 class="card-title">
          <i class="fab fa-docker"></i> Docker Logs
        </h2>
      </div>
      
      <form method="post" autocomplete="off">
        <input type="hidden" name="log_type" value="docker">
        <div class="form-group">
          <label for="docker_container">Select Container</label>
          <select name="docker_container" id="docker_container">
            {% for container in docker_containers %}
              <option value="{{ container }}" {% if docker_container == container %}selected{% endif %}>{{ container }}</option>
            {% endfor %}
          </select>
        </div>
        
        <div class="form-group">
          <label for="docker_tail">Lines to Display</label>
          <input type="number" name="docker_tail" id="docker_tail" 
                 value="{{ docker_tail or 500 }}" min="10" max="5000" />
        </div>
        
        <button type="submit">
          <i class="fas fa-search"></i> View Logs
        </button>
      </form>
    </div>
    
    <div class="card" id="kubernetes-tab" style="display: none;">
      <div class="card-header">
        <h2 class="card-title">
          <i class="fas fa-network-wired"></i> Kubernetes Logs
        </h2>
      </div>
      
      <form method="post" autocomplete="off">
        <input type="hidden" name="log_type" value="k8s">
        <div class="form-group">
          <label for="k8s_ns">Namespace</label>
          <select name="k8s_ns" id="k8s_ns" onchange="this.form.submit()">
            {% for ns in k8s_namespaces %}
              <option value="{{ ns }}" {% if k8s_ns == ns %}selected{% endif %}>{{ ns }}</option>
            {% endfor %}
          </select>
        </div>
        
        <div class="form-group">
          <label for="k8s_pod">Pod</label>
          <select name="k8s_pod" id="k8s_pod">
            {% for pod in k8s_pods %}
              <option value="{{ pod }}" {% if k8s_pod == pod %}selected{% endif %}>{{ pod }}</option>
            {% endfor %}
          </select>
        </div>
        
        <div class="form-group">
          <label for="k8s_tail">Lines to Display</label>
          <input type="number" name="k8s_tail" id="k8s_tail" 
                 value="{{ k8s_tail or 500 }}" min="10" max="5000" />
        </div>
        
        <button type="submit">
          <i class="fas fa-search"></i> View Logs
        </button>
      </form>
    </div>
    
    <div class="card" id="system-tab" style="display: none;">
      <div class="card-header">
        <h2 class="card-title">
          <i class="fas fa-server"></i> System Logs
        </h2>
      </div>
      
      <form method="post" autocomplete="off">
        <input type="hidden" name="log_type" value="system">
        <div class="form-group">
          <label for="syslog_path">Log File Path</label>
          <input type="text" name="syslog_path" id="syslog_path" 
                 value="{{ syslog_path or '/var/log/syslog' }}" />
        </div>
        
        <div class="form-group">
          <label for="syslog_tail">Lines to Display</label>
          <input type="number" name="syslog_tail" id="syslog_tail" 
                 value="{{ syslog_tail or 500 }}" min="10" max="5000" />
        </div>
        
        <button type="submit">
          <i class="fas fa-search"></i> View Logs
        </button>
      </form>
    </div>
    
    {% if logs %}
      <div class="card">
        <div class="card-header">
          <h2 class="card-title">
            <i class="fas fa-file-alt"></i> Log Output
            <span class="badge primary" style="margin-left: auto;">
              {{ log_type|upper }} {% if docker_container %}- {{ docker_container }}{% elif k8s_pod %}- {{ k8s_pod }}{% endif %}
            </span>
          </h2>
          <div class="refresh-controls">
            <span class="timestamp" id="last-updated">Last updated: {{ timestamp }}</span>
            <button class="refresh-btn" onclick="refreshLogs()" title="Refresh">
              <i class="fas fa-sync-alt"></i>
            </button>
            <div class="refresh-interval">
              <span>Auto-refresh:</span>
              <select id="refresh-interval" onchange="updateRefreshInterval()">
                <option value="0">Off</option>
                <option value="5">5s</option>
                <option value="10" selected>10s</option>
                <option value="30">30s</option>
                <option value="60">1m</option>
              </select>
            </div>
          </div>
        </div>
        <div class="log-box" id="log-output">
          {{ logs }}
        </div>
      </div>
    {% else %}
      <div class="card">
        <div class="empty-state">
          <i class="fas fa-file-alt"></i>
          <h3>No Logs Selected</h3>
          <p>Select a container or log file to view its logs</p>
        </div>
      </div>
    {% endif %}
  </div>
  
  <script>
    let refreshIntervalId = null;
    let currentRefreshInterval = 10;
    
    function showTab(tabName) {
      // Hide all tabs
      document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
      });
      document.querySelectorAll('.card[id$="-tab"]').forEach(tab => {
        tab.style.display = 'none';
      });
      
      // Show selected tab
      document.querySelector(`.tab[onclick="showTab('${tabName}')"]`).classList.add('active');
      document.getElementById(`${tabName}-tab`).style.display = 'block';
    }
    
    function refreshLogs() {
      const form = document.querySelector('form[method="post"]');
      if (!form) return;
      
      fetch(window.location.href, {
        method: 'POST',
        body: new FormData(form),
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        }
      })
      .then(response => response.text())
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const newLogs = doc.getElementById('log-output');
        const newTimestamp = doc.getElementById('last-updated');
        
        if (newLogs) {
          document.getElementById('log-output').innerHTML = newLogs.innerHTML;
        }
        if (newTimestamp) {
          document.getElementById('last-updated').textContent = newTimestamp.textContent;
        }
        
        // Scroll to bottom of log output
        const logBox = document.getElementById('log-output');
        logBox.scrollTop = logBox.scrollHeight;
      })
      .catch(error => console.error('Error refreshing logs:', error));
    }
    
    function updateRefreshInterval() {
      const intervalSelect = document.getElementById('refresh-interval');
      const newInterval = parseInt(intervalSelect.value);
      
      // Clear existing interval if it exists
      if (refreshIntervalId) {
        clearInterval(refreshIntervalId);
        refreshIntervalId = null;
      }
      
      // Set new interval if not 0
      if (newInterval > 0) {
        currentRefreshInterval = newInterval;
        refreshIntervalId = setInterval(refreshLogs, newInterval * 1000);
      }
    }
    
    // Set initial tab based on log type
    window.onload = function() {
      const logType = "{{ log_type }}";
      if (logType === 'docker') {
        showTab('docker');
      } else if (logType === 'k8s') {
        showTab('kubernetes');
      } else if (logType === 'system' || logType === 'nginx_access' || logType === 'nginx_error') {
        showTab('system');
      }
      
      // Set up auto-refresh with default interval
      updateRefreshInterval();
      
      // Scroll to bottom of log output on load
      const logBox = document.getElementById('log-output');
      if (logBox) {
        logBox.scrollTop = logBox.scrollHeight;
      }
    };
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    logs = ""
    log_type = request.form.get("log_type", "")
    docker_container = request.form.get("docker_container", "")
    docker_tail = int(request.form.get("docker_tail", 500)) if request.form.get("docker_tail") else 500
    syslog_path = request.form.get("syslog_path", "/var/log/syslog")
    syslog_tail = int(request.form.get("syslog_tail", 500)) if request.form.get("syslog_tail") else 500
    k8s_ns = request.form.get("k8s_ns", "default")
    k8s_pod = request.form.get("k8s_pod", "")
    k8s_tail = int(request.form.get("k8s_tail", 500)) if request.form.get("k8s_tail") else 500

    docker_containers = get_docker_containers()
    k8s_namespaces = get_k8s_namespaces()
    k8s_pods = get_k8s_pods(k8s_ns) if log_type == "k8s" else []

    if request.method == "POST":
        if log_type == "docker" and docker_container:
            logs = get_docker_logs(docker_container, docker_tail)
        elif log_type == "system":
            logs = read_file_tail(syslog_path, syslog_tail)
        elif log_type == "nginx_access":
            logs = read_file_tail(NGINX_ACCESS, syslog_tail)
        elif log_type == "nginx_error":
            logs = read_file_tail(NGINX_ERROR, syslog_tail)
        elif log_type == "k8s" and k8s_ns and k8s_pod:
            env = os.environ.copy()
            env["KUBECONFIG"] = KUBECONFIG_PATH
            logs = run_cmd(["kubectl", "logs", "--tail", str(k8s_tail), k8s_pod, "-n", k8s_ns], env)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template_string(
        HTML_TEMPLATE,
        logs=logs,
        log_type=log_type,
        docker_container=docker_container,
        docker_tail=docker_tail,
        syslog_path=syslog_path,
        syslog_tail=syslog_tail,
        k8s_ns=k8s_ns,
        k8s_pod=k8s_pod,
        k8s_tail=k8s_tail,
        docker_containers=docker_containers,
        k8s_namespaces=k8s_namespaces,
        k8s_pods=k8s_pods,
        timestamp=timestamp
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
