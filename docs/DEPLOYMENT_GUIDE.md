# 🚀 Nekro-Agent Deployment Guide with AiPyApp

Complete step-by-step guide to clone, build, deploy, and use nekro-agent with the integrated aipyapp plugin.

---

## 📋 Prerequisites

### System Requirements

- **OS:** Linux (Ubuntu 20.04+), macOS, or Windows WSL2
- **Python:** 3.10, 3.11 (Python 3.12+ not supported)
- **Node.js:** 16+ (for frontend)
- **Memory:** Minimum 4GB RAM (8GB+ recommended)
- **Storage:** 5GB free space

### Required Tools

```bash
# Install Python 3.11 (if not installed)
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Install Node.js & pnpm
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
npm install -g pnpm

# Install Poetry (Python package manager)
curl -sSL https://install.python-poetry.org | python3 -

# Install Docker (optional, for containerized deployment)
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

---

## 🔧 Step 1: Clone the Repository

```bash
# Clone nekro-agent
git clone https://github.com/Zeeeepa/nekro-agent.git
cd nekro-agent

# Checkout the aipyapp integration branch (or main if merged)
git checkout main  # or your PR branch

# Verify aipyapp plugin exists
ls -la plugins/builtin/aipyapp_orchestrator.py
ls -la nekro_agent/services/aipyapp_executor/
```

**Expected Output:**
```
plugins/builtin/aipyapp_orchestrator.py ✓
nekro_agent/services/aipyapp_executor/
├── __init__.py
├── bridge.py
├── sandbox_executor.py
└── task_manager.py
```

---

## 🏗️ Step 2: Backend Setup & Build

### A. Install Python Dependencies

```bash
# Ensure Python 3.11 is active
python3.11 --version  # Should show 3.11.x

# Install Poetry dependencies
poetry env use python3.11
poetry install

# Install aipyapp plugin dependencies
poetry install --extras aipyapp
```

**Verify Installation:**
```bash
poetry run python -c "import aipyapp; print('aipyapp version:', aipyapp.__version__)"
# Expected: aipyapp version: 0.1.22 (or higher)
```

### B. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit configuration
nano .env  # or vim, code, etc.
```

**Minimum Required Configuration:**

```bash
# .env file
NEKRO_AGENT_PORT=8000
NEKRO_AGENT_HOST=0.0.0.0

# Database (optional, uses SQLite by default)
DATABASE_URL=sqlite+aiosqlite:///./data/nekro_agent.db

# AI Provider (choose one)
# OpenAI
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional

# OR Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here

# OR Custom OpenAI-compatible endpoint
OPENAI_API_KEY=your-key
OPENAI_BASE_URL=https://your-custom-endpoint/v1
```

### C. Initialize Database

```bash
# Run migrations
poetry run python -m nekro_agent.cli migrate

# Create admin user (interactive)
poetry run python -m nekro_agent.cli user create-admin
# Username: admin
# Password: [your secure password]
# Email: admin@example.com
```

---

## 🎨 Step 3: Frontend Setup & Build

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
pnpm install

# Build for production
pnpm build

# OR run in development mode (hot reload)
pnpm dev
```

**Development Mode URLs:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

---

## 🚀 Step 4: Start the Application

### Option A: Development Mode (Recommended for Testing)

**Terminal 1 - Backend:**
```bash
cd /path/to/nekro-agent
poetry run python -m nekro_agent
```

**Terminal 2 - Frontend:**
```bash
cd /path/to/nekro-agent/frontend
pnpm dev
```

### Option B: Production Mode

**Backend (with systemd service):**

Create `/etc/systemd/system/nekro-agent.service`:

```ini
[Unit]
Description=Nekro Agent Backend
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/nekro-agent
Environment="PATH=/home/youruser/.local/bin:/usr/bin"
ExecStart=/home/youruser/.local/bin/poetry run python -m nekro_agent
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable nekro-agent
sudo systemctl start nekro-agent
sudo systemctl status nekro-agent
```

**Frontend (with Nginx):**

Build and serve:
```bash
cd frontend
pnpm build
# Built files in: frontend/dist/
```

Nginx config (`/etc/nginx/sites-available/nekro-agent`):

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /path/to/nekro-agent/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/nekro-agent /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Option C: Docker Deployment

```bash
# Build Docker image
docker build -t nekro-agent:latest .

# Run with Docker Compose
docker-compose up -d

# Check logs
docker-compose logs -f
```

---

## 🎯 Step 5: Access the UI

### Login

1. Open browser: http://localhost:5173 (dev) or http://your-domain.com (prod)
2. Login with admin credentials:
   - Username: `admin`
   - Password: [password you set in Step 2C]

### UI Overview

```
┌────────────────────────────────────────────────────┐
│  Nekro Agent - Dashboard                     [🌙]  │
├────────────────────────────────────────────────────┤
│                                                     │
│  📊 Dashboard   💬 Chats   🧩 Plugins   ⚙️ Settings │
│                                                     │
│  [Main content area]                               │
│                                                     │
└────────────────────────────────────────────────────┘
```

---

## 🔌 Step 6: Enable AiPyApp Plugin

### Navigate to Plugins Page

1. Click **"🧩 Plugins"** in sidebar
2. Find **"AiPyApp Executor"** in the list
3. It should show **[内置] [已启用]** badges

### Configure AiPyApp (Optional)

1. Click on **"AiPyApp Executor"** to open details
2. Switch to **"配置"** (Configuration) tab
3. Adjust settings:

```
┌─────────────────────────────────────────────────┐
│ 配置                                              │
├─────────────────────────────────────────────────┤
│                                                   │
│ Enable aipyapp execution                         │
│ [✓] Enabled                                      │
│                                                   │
│ Task timeout (seconds)                           │
│ [    300    ]  ← Max execution time              │
│                                                   │
│ Maximum memory per task (MB)                     │
│ [    512    ]  ← Memory limit                    │
│                                                   │
│ Working directory                                │
│ [./data/aipyapp_workdir]  ← Sandbox directory   │
│                                                   │
│          [重置]  [保存配置]                       │
└─────────────────────────────────────────────────┘
```

4. Click **"保存配置"** (Save Configuration)

### Verify Plugin Methods

Switch to **"方法"** (Methods) tab:

| Method Name | Type | Description |
|-------------|------|-------------|
| `execute_python_task` | 🛠️ TOOL | Execute single Python task |
| `execute_python_workflow` | 🛠️ TOOL | Execute multi-step workflow |

---

## 💬 Step 7: Use AiPyApp via Chat

### Create a Chat Session

1. Go to **"💬 Chats"** page
2. Click **"+ New Chat"**
3. Select AI model (GPT-4, Claude, etc.)
4. Start chatting!

### Example Usage

**Example 1: Data Analysis**

```
User: Can you analyze this CSV data?
      [Upload file: sales_data.csv]

AI: I'll analyze the CSV file using Python.

    [Executes: execute_python_task]
    Instruction: "Load sales_data.csv and calculate 
                  total revenue, average order value,
                  and top 5 products"

    Results:
    - Total Revenue: $125,430
    - Average Order Value: $83.62
    - Top 5 Products:
      1. Product A ($23,450)
      2. Product B ($18,920)
      ...
```

**Example 2: Data Visualization**

```
User: Create a bar chart of monthly sales trends

AI: I'll generate a visualization for you.

    [Executes: execute_python_task]
    Instruction: "Load sales data, group by month,
                  calculate totals, create bar chart
                  and save as monthly_sales.png"

    [Displays: monthly_sales.png]
    The chart shows an upward trend with...
```

**Example 3: Multi-Step Workflow**

```
User: Clean the data, calculate statistics, and 
      generate a report with visualizations

AI: I'll execute this as a multi-step workflow.

    [Executes: execute_python_workflow]
    Steps:
    1. Load and clean data (remove nulls, duplicates)
    2. Calculate descriptive statistics
    3. Generate correlation heatmap
    4. Create distribution plots
    5. Export summary report

    [Shows artifacts: cleaned_data.csv, heatmap.png, 
                      distributions.png, report.txt]
```

---

## 🔍 Step 8: Monitor Execution

### Check Logs

**Backend Logs:**
```bash
# If running with systemd
sudo journalctl -u nekro-agent -f

# If running manually
# Check terminal output
```

**AiPyApp Execution Logs:**
```bash
# Task execution logs
tail -f data/aipyapp_workdir/*/logs/*.log

# Sandbox directories
ls -la data/aipyapp_workdir/
# Shows: chat_key_user_id/  (isolated per session)
```

### Verify Artifacts

```bash
# Check generated files
ls -la data/aipyapp_workdir/chat_123_user_456/
# Example output:
# - plot.png
# - results.csv
# - report.txt
```

---

## 🧪 Step 9: Test Integration

### Run Integration Tests

```bash
# Backend tests
poetry run pytest tests/services/aipyapp_executor/ -v

# Expected output:
# test_bridge.py::test_create_aipyapp_context ✓
# test_bridge.py::test_format_result ✓
# test_task_manager.py::test_session_management ✓
# ...
# 32 tests passed
```

### Manual Testing

**Test execute_python_task via API:**

```bash
curl -X POST http://localhost:8000/api/sandbox/execute \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "execute_python_task",
    "chat_key": "test_chat",
    "params": {
      "instruction": "Calculate 2 + 2 and print the result",
      "context": null
    }
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "output": "Result: 4",
  "artifacts": [],
  "execution_time": 0.5,
  "variables": {"result": 4}
}
```

---

## 🛠️ Troubleshooting

### Issue 1: aipyapp Not Found

**Error:**
```
ModuleNotFoundError: No module named 'aipyapp'
```

**Solution:**
```bash
poetry install --extras aipyapp
# OR
poetry add aipyapp
```

### Issue 2: Plugin Not Appearing in UI

**Checks:**
1. Verify plugin file exists:
   ```bash
   ls plugins/builtin/aipyapp_orchestrator.py
   ```

2. Check backend logs for errors:
   ```bash
   grep -i aipyapp logs/nekro_agent.log
   ```

3. Restart backend:
   ```bash
   # Kill and restart
   pkill -f "python -m nekro_agent"
   poetry run python -m nekro_agent
   ```

4. Clear frontend cache:
   ```bash
   # In browser DevTools: Application > Clear Storage
   # OR
   Ctrl+Shift+R (hard refresh)
   ```

### Issue 3: Task Execution Timeout

**Error:**
```
Task execution exceeded 300s timeout
```

**Solution:**
1. Increase timeout in plugin config:
   - UI: Plugins > AiPyApp > Config > Task timeout: `600`

2. Or edit config file:
   ```bash
   # Edit: data/config/plugins/aipyapp_orchestrator.json
   {
     "TASK_TIMEOUT": 600
   }
   ```

### Issue 4: Permission Denied (Workdir)

**Error:**
```
PermissionError: [Errno 13] Permission denied: './data/aipyapp_workdir'
```

**Solution:**
```bash
# Create directory with proper permissions
mkdir -p data/aipyapp_workdir
chmod 755 data/aipyapp_workdir

# OR run with proper user
sudo chown -R $USER:$USER data/
```

### Issue 5: Python Version Mismatch

**Error:**
```
This project requires Python >=3.10,<3.12
```

**Solution:**
```bash
# Check Python version
python --version

# Use pyenv to manage versions
pyenv install 3.11.7
pyenv local 3.11.7

# Recreate Poetry env
poetry env remove python
poetry env use 3.11
poetry install
```

---

## 📚 Additional Resources

### Documentation

- **Plugin Development:** `docs/Extension_Development.md`
- **AiPyApp Plugin Spec:** `docs/aipyapp-integration-spec.xml`
- **AiPyApp User Guide:** `docs/AIPYAPP_PLUGIN.md`
- **API Documentation:** http://localhost:8000/docs

### Examples

**Python Task Examples:**
```python
# Simple calculation
"Calculate the factorial of 10"

# Data processing
"Load data.csv, filter rows where price > 100, export to filtered.csv"

# Visualization
"Create a scatter plot of height vs weight from dataset.csv"

# Machine learning
"Load iris dataset, train a decision tree classifier, show accuracy"
```

**Workflow Examples:**
```python
# Multi-step analysis
[
  "Load and clean customer_data.csv",
  "Calculate customer lifetime value",
  "Segment customers into 3 groups",
  "Create visualization of segments",
  "Export segment_report.csv"
]
```

---

## 🎉 Success Checklist

- [ ] Repository cloned
- [ ] Python 3.11 environment set up
- [ ] Poetry dependencies installed (including aipyapp)
- [ ] Backend started successfully
- [ ] Frontend built and served
- [ ] Admin user created
- [ ] UI accessible and logged in
- [ ] AiPyApp plugin visible in plugins list
- [ ] Plugin configuration saved
- [ ] Test execution successful
- [ ] Logs showing no errors

**🚀 You're now ready to use nekro-agent with aipyapp!**

---

## 🆘 Support

If you encounter issues:

1. **Check Logs:** `data/logs/nekro_agent.log`
2. **Discord:** https://discord.gg/eMsgwFnxUB
3. **QQ Group:** 636925153 (1群) | 679808796 (2群)
4. **GitHub Issues:** https://github.com/Zeeeepa/nekro-agent/issues

---

**Last Updated:** 2025-01-04
**Version:** nekro-agent v1.0 + aipyapp integration

