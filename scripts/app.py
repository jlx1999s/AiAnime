import streamlit as st
import subprocess
import os
import sys
from pathlib import Path
import glob
import json
import pandas as pd
import datetime
import time
import io
import zipfile
import shutil
import filelock
import re
import urllib.request
import urllib.error
import urllib.parse

# Page Config
st.set_page_config(
    page_title="漫剧剧本与分镜工作流助手",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for Cards
st.markdown("""
<style>
    .project-card {
        background-color: #262730;
        border: 1px solid #464b59;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
        transition: transform 0.2s;
    }
    .project-card:hover {
        border-color: #4da6ff;
        transform: translateY(-2px);
    }
    .card-title {
        font-size: 18px;
        font-weight: bold;
        color: #ffffff;
        margin-bottom: 8px;
    }
    .card-info {
        font-size: 12px;
        color: #a0a0a0;
    }
    .big-button {
        width: 100%;
        height: 100px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Session State
if 'page' not in st.session_state:
    st.session_state.page = 'home'
if 'current_project' not in st.session_state:
    st.session_state.current_project = None
if 'show_create_modal' not in st.session_state:
    st.session_state.show_create_modal = False
if 'processing_key' not in st.session_state:
    st.session_state.processing_key = None

def set_processing(key):
    st.session_state.processing_key = key

# --- Helper Functions ---

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_config(config):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        st.error(f"Failed to save config: {e}")

def api_post_json(url, payload):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8")
        raise Exception(detail or f"HTTP {e.code}")
    except urllib.error.URLError as e:
        raise Exception(str(e))

def init_auth():
    if "auth_user" not in st.session_state:
        st.session_state.auth_user = None

    config = load_config()
    if "user_api_base_input" not in st.session_state:
        st.session_state.user_api_base_input = config.get("user_api_base", "http://localhost:8001")

    user_api_base_val = st.session_state.user_api_base_input

    if st.session_state.auth_user:
        uid = st.session_state.auth_user.get("id")
        if uid:
            current_qp = st.query_params.get("auth_user_id")
            if current_qp != uid:
                st.query_params["auth_user_id"] = uid
        return

    qp_user_id = st.query_params.get("auth_user_id")
    if qp_user_id:
        try:
            restored_user = api_get_json(f"{user_api_base_val}/auth/user/{qp_user_id}")
        except Exception:
            restored_user = None

        if restored_user:
            st.session_state.auth_user = restored_user
            st.toast(f"欢迎回来, {restored_user.get('username')}")
            return
        if "auth_user_id" in st.query_params:
            del st.query_params["auth_user_id"]

    try:
        restored_user = api_get_json(f"{user_api_base_val}/auth/whoami")
    except Exception:
        restored_user = None

    if restored_user:
        st.session_state.auth_user = restored_user
        uid = restored_user.get("id")
        if uid:
            st.query_params["auth_user_id"] = uid
        st.toast(f"欢迎回来, {restored_user.get('username')}")

def api_get_json(url, params=None):
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            text = resp.read().decode("utf-8")
            return json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8")
        raise Exception(detail or f"HTTP {e.code}")
    except urllib.error.URLError as e:
        raise Exception(str(e))

def get_base_dir():
    return os.getcwd()

def get_projects(base_dir):
    ignored_dirs = {
        "__pycache__", "outputs", "scripts", "script", "novel", 
        "storyboard_output", "venv", "env", "node_modules", ".git", ".claude", "test"
    }
    subdirs = [d for d in os.listdir(base_dir) 
               if os.path.isdir(os.path.join(base_dir, d)) 
               and not d.startswith('.') 
               and d not in ignored_dirs]
    return sorted(subdirs)

def get_file_info_df(directory, pattern="*.md"):
    if not os.path.exists(directory):
        return pd.DataFrame(columns=["文件名", "大小", "修改时间", "path"])
        
    files = glob.glob(os.path.join(directory, pattern))
    data = []
    for f in files:
        try:
            stats = os.stat(f)
            data.append({
                "文件名": os.path.basename(f),
                "大小": f"{stats.st_size / 1024:.1f} KB",
                "修改时间": datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                "path": f
            })
        except Exception:
            continue
    
    if not data:
        return pd.DataFrame(columns=["文件名", "大小", "修改时间", "path"])
    
    df = pd.DataFrame(data)
    df = df.sort_values(by="修改时间", ascending=False)
    # Reset index to ensure iloc matches 0..N
    df = df.reset_index(drop=True)
    return df

def read_file_content(filepath):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def get_plot_counts(plot_text):
    status_by_num = {}
    for line in plot_text.splitlines():
        m = re.search(r"【剧情(\d+)】.*第(\d+)集.*状态：([^，,\s]+)", line)
        if not m:
            continue
        status_by_num[int(m.group(1))] = m.group(3)
    total = len(status_by_num)
    used = sum(1 for s in status_by_num.values() if s == "已用")
    unused = sum(1 for s in status_by_num.values() if s == "未用")
    return total, used, unused

def write_file_content(filepath, content):
    try:
        # Try to get project lock if possible, assuming filepath is inside a project
        # Simple heuristic: look for .project_lock in parent directories
        lock_path = None
        p = Path(filepath).resolve()
        for parent in p.parents:
            if (parent / "plot-breakdown.md").exists() or (parent / "scripts").exists():
                 lock_path = parent / ".project_lock"
                 break
        
        if lock_path:
             lock = filelock.FileLock(str(lock_path), timeout=10)
             with lock:
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
        else:
             # Fallback if not in a recognized project structure or just a loose file
             with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

        return True
    except Exception as e:
        return f"Error writing file: {e}"

def run_command(cmd_list, cwd=None, env_vars=None, description="Running command..."):
    """Runs a command and displays output in Streamlit."""
    with st.spinner(f"⏳ {description}"):
        try:
            # Join command list for display
            cmd_str = " ".join(cmd_list)
            st.code(f"$ {cmd_str}", language="bash")
            
            # Run command
            result = subprocess.run(
                cmd_list,
                cwd=cwd,
                env=env_vars,
                capture_output=True,
                text=True,
                shell=True if sys.platform == "win32" else False
            )
            
            if result.stdout:
                with st.expander("📄 查看标准输出 (Stdout)", expanded=True):
                    st.text(result.stdout)
            
            if result.stderr:
                with st.expander("⚠️ 查看错误输出 (Stderr)", expanded=True):
                    st.text(result.stderr)
            
            if result.returncode == 0:
                st.success("✅ 执行成功 (Success)")
            else:
                st.error(f"❌ 执行失败 (Failed with code {result.returncode})")
                
            return result.stdout
        except Exception as e:
            st.error(f"❌ 发生异常: {str(e)}")
            return None

# --- Sidebar Global Config (Shared) ---
def render_sidebar():
    with st.sidebar:
        if st.session_state.page == 'project':
            if st.button("⬅️ 返回项目列表", use_container_width=True):
                st.session_state.page = 'home'
                st.session_state.current_project = None
                st.rerun()
            st.divider()
            
            if st.session_state.current_project:
                st.info(f"当前项目: {os.path.basename(st.session_state.current_project)}")

        st.header("⚙️ 全局设置")
        
        # Load config
        config = load_config()

        # --- Presets Migration & Initialization ---
        if "presets" not in config:
            default_preset = {
                "api_key": config.get("api_key", ""),
                "api_base": config.get("api_base", "https://api.openai.com/v1"),
                "model_name": config.get("model_name", "gpt-4o"),
                "api_style": config.get("api_style", "openai")
            }
            config["presets"] = {"Default": default_preset}
            config["current_preset"] = "Default"
            # Cleanup old keys
            for k in ["api_key", "api_base", "model_name", "api_style"]:
                if k in config:
                    del config[k]
            save_config(config)

        presets = config.get("presets", {})
        current_preset_name = config.get("current_preset", "Default")
        
        # Fallback if current_preset_name is invalid or presets empty
        if not presets:
             presets = {"Default": {"api_key": "", "api_base": "https://api.openai.com/v1", "model_name": "gpt-4o", "api_style": "openai"}}
             config["presets"] = presets
             current_preset_name = "Default"
             config["current_preset"] = "Default"
             save_config(config)
        elif current_preset_name not in presets:
             current_preset_name = list(presets.keys())[0]
             config["current_preset"] = current_preset_name
             save_config(config)

        # --- Preset Selector UI ---
        st.subheader("🛠️ API 配置预设")
        col_p1, col_p2 = st.columns([3, 1])
        with col_p1:
             preset_options = list(presets.keys())
             try:
                 idx = preset_options.index(current_preset_name)
             except ValueError:
                 idx = 0
             selected_preset = st.selectbox("选择预设", preset_options, index=idx, key="preset_selector", label_visibility="collapsed")
        
        with col_p2:
             if st.button("➕", help="新建配置预设"):
                 st.session_state.show_add_preset = True

        if st.session_state.get("show_add_preset", False):
             with st.container(border=True):
                 new_preset_name = st.text_input("新预设名称", key="new_preset_name_input")
                 c1, c2 = st.columns(2)
                 with c1:
                     if st.button("确认", use_container_width=True):
                         if new_preset_name and new_preset_name not in presets:
                             presets[new_preset_name] = presets.get(current_preset_name, {}).copy()
                             config["presets"] = presets
                             config["current_preset"] = new_preset_name
                             save_config(config)
                             st.session_state.show_add_preset = False
                             st.rerun()
                         elif new_preset_name in presets:
                             st.error("名称已存在")
                 with c2:
                     if st.button("取消", use_container_width=True):
                         st.session_state.show_add_preset = False
                         st.rerun()

        # Handle Preset Switch
        if selected_preset != current_preset_name:
            config["current_preset"] = selected_preset
            save_config(config)
            # Force reload of inputs from new preset
            preset_data = presets[selected_preset]
            st.session_state.api_key_input = preset_data.get("api_key", "")
            st.session_state.api_base_input = preset_data.get("api_base", "")
            st.session_state.model_name_input = preset_data.get("model_name", "")
            st.session_state.api_style_input = preset_data.get("api_style", "")
            st.rerun()

        # Get current preset data
        current_data = presets[selected_preset]

        # Initialize session state with config values if not set
        if "api_key_input" not in st.session_state:
            st.session_state.api_key_input = current_data.get("api_key", "")
        if "api_base_input" not in st.session_state:
            st.session_state.api_base_input = current_data.get("api_base", "https://api.openai.com/v1")
        if "model_name_input" not in st.session_state:
            st.session_state.model_name_input = current_data.get("model_name", "gpt-4o")
        if "api_style_input" not in st.session_state:
            st.session_state.api_style_input = current_data.get("api_style", "openai")
        if "user_api_base_input" not in st.session_state:
            st.session_state.user_api_base_input = config.get("user_api_base", "http://localhost:8001")
        if "auth_user" not in st.session_state:
            st.session_state.auth_user = None
        if "user_list" not in st.session_state:
            st.session_state.user_list = None


        def save_settings():
            presets[selected_preset] = {
                "api_key": st.session_state.api_key_input,
                "api_base": st.session_state.api_base_input,
                "model_name": st.session_state.model_name_input,
                "api_style": st.session_state.api_style_input
            }
            new_config = {
                **config,
                "presets": presets,
                "current_preset": selected_preset,
                "user_api_base": st.session_state.user_api_base_input
            }
            # Remove legacy keys if present
            for k in ["api_key", "api_base", "model_name", "api_style"]:
                if k in new_config:
                    del new_config[k]
            save_config(new_config)
            st.toast(f"✅ 预设 '{selected_preset}' 已保存")

        api_key = st.text_input("API Key", type="password", help="OpenAI or Anthropic API Key", key="api_key_input")
        api_base = st.text_input("API Base URL", help="e.g. https://api.openai.com/v1", key="api_base_input")
        model_name = st.text_input("Model Name", help="e.g. gpt-4o, claude-3-5-sonnet", key="model_name_input")
        api_style = st.selectbox("API Style", ["openai", "anthropic"], key="api_style_input")

        c_save, c_del = st.columns([2, 1])
        with c_save:
            if st.button("💾 保存当前配置", use_container_width=True):
                save_settings()
        with c_del:
            if selected_preset != "Default":
                if st.button("🗑️ 删除", use_container_width=True, help="删除当前预设"):
                    del presets[selected_preset]
                    new_current = "Default" if "Default" in presets else list(presets.keys())[0]
                    config["presets"] = presets
                    config["current_preset"] = new_current
                    save_config(config)
                    # Force reload inputs
                    preset_data = presets[new_current]
                    st.session_state.api_key_input = preset_data.get("api_key", "")
                    st.session_state.api_base_input = preset_data.get("api_base", "")
                    st.session_state.model_name_input = preset_data.get("model_name", "")
                    st.session_state.api_style_input = preset_data.get("api_style", "")
                    st.rerun()

        st.subheader("👤 用户系统")
        user_api_base = st.text_input("用户系统 API", key="user_api_base_input")
        auth_user = st.session_state.auth_user
        if auth_user:
            st.success(f"已登录: {auth_user.get('username', '')}")
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button("退出登录", use_container_width=True):
                    try:
                        api_post_json(f"{user_api_base}/auth/logout", {})
                    except Exception:
                        pass
                    st.session_state.auth_user = None
                    st.session_state.user_list = None
                    if "auth_user_id" in st.query_params:
                        del st.query_params["auth_user_id"]
                    st.rerun()
            with c2:
                if auth_user.get("is_admin"):
                    if st.button("刷新用户列表", use_container_width=True):
                        try:
                            users = api_get_json(f"{user_api_base}/admin/users", {"admin_user_id": auth_user.get("id")})
                            st.session_state.user_list = users
                            st.toast("✅ 已刷新用户列表")
                        except Exception as e:
                            st.error(f"获取用户列表失败: {e}")
        else:
            username = st.text_input("用户名", key="auth_username")
            password = st.text_input("密码", type="password", key="auth_password")
            if st.button("登录", use_container_width=True):
                try:
                    user = api_post_json(f"{user_api_base}/auth/login", {"username": username, "password": password})
                    st.session_state.auth_user = user
                    st.query_params["auth_user_id"] = user.get("id")
                    if user.get("is_admin"):
                        try:
                            users = api_get_json(f"{user_api_base}/admin/users", {"admin_user_id": user.get("id")})
                            st.session_state.user_list = users
                        except Exception as e:
                            st.error(f"获取用户列表失败: {e}")
                    st.rerun()
                except Exception as e:
                    st.error(f"登录失败: {e}")

        return api_key, api_base, model_name, api_style

# --- Main Views ---

def render_home(base_dir, projects):
    st.title("田 漫剧项目管理")
    config = load_config()
    project_owners = config.get("project_owners", {})
    auth_user = st.session_state.get("auth_user")
    user_list = st.session_state.get("user_list") or []
    user_name_by_id = {u.get("id"): u.get("username") for u in user_list if isinstance(u, dict)}
    if not auth_user:
        st.info("请先登录后查看项目列表")
        return
    if auth_user and not auth_user.get("is_admin"):
        projects = [p for p in projects if project_owners.get(p) == auth_user.get("id")]
    
    # Top Bar
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("＋ 新建项目", use_container_width=True, type="primary"):
            st.session_state.show_create_modal = not st.session_state.show_create_modal

    # Create Project Area
    if st.session_state.show_create_modal:
        with st.container():
            st.markdown("### 创建新项目")
            c1, c2 = st.columns([3, 1])
            with c1:
                new_project_name = st.text_input("项目名称", placeholder="输入项目名称 (例如: MyNewNovel)")
                new_novel_name = st.text_input("小说名称", value="我的小说")
                new_novel_type = st.text_input("小说类型", value="重生/古言")
            with c2:
                st.write("") # Spacer
                st.write("") 
                st.write("") 
                st.write("") 
                if st.button("确认创建", use_container_width=True):
                    if new_project_name:
                        new_path = os.path.join(base_dir, new_project_name)
                        try:
                            # 1. Create Directory
                            os.makedirs(new_path, exist_ok=True)
                            
                            # 2. Auto Init
                            script_py_path = os.path.join(os.getcwd(), "script_workflow.py")
                            cmd = ["python", script_py_path, "--project-dir", new_path,
                                   "--novel-name", new_novel_name, "--novel-type", new_novel_type, "init"]
                            
                            # We run this synchronously without showing output in UI, or show a toast
                            subprocess.run(cmd, check=True, cwd=os.getcwd())
                            
                            st.success(f"已创建并初始化: {new_path}")
                            if auth_user:
                                project_owners[new_project_name] = auth_user.get("id")
                                config["project_owners"] = project_owners
                                save_config(config)
                            st.session_state.show_create_modal = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"创建失败: {e}")
                    else:
                        st.error("请输入项目名称")

    st.divider()

    # Project Grid
    columns_count = 3
    cols = st.columns(columns_count)

    # Render Projects
    for i, project in enumerate(projects):
        col_idx = i % columns_count
        with cols[col_idx]:
            project_path = os.path.join(base_dir, project)
            
            # Try to read some metadata if available (e.g. from a meta.json or just folder info)
            # For now, just show name
            
            with st.container(border=True):
                st.markdown(f"#### 📂 {project}")
                st.caption(f"Path: {project_path}")
                owner_id = project_owners.get(project)
                owner_name = user_name_by_id.get(owner_id, owner_id) if owner_id else "未分配"
                st.caption(f"负责人: {owner_name}")
                if auth_user and auth_user.get("is_admin"):
                    if not user_list:
                        st.caption("请先在侧边栏刷新用户列表")
                    else:
                        options = [{"label": "未分配", "id": None}] + [
                            {"label": u.get("username"), "id": u.get("id")} for u in user_list if isinstance(u, dict)
                        ]
                        current_idx = next((idx for idx, opt in enumerate(options) if opt.get("id") == owner_id), 0)
                        selected = st.selectbox(
                            "负责人",
                            options,
                            index=current_idx,
                            format_func=lambda x: x.get("label", ""),
                            key=f"owner_select_{project}"
                        )
                        if st.button("分配", key=f"assign_{project}", use_container_width=True):
                            if selected.get("id") is None:
                                project_owners.pop(project, None)
                            else:
                                project_owners[project] = selected.get("id")
                            config["project_owners"] = project_owners
                            save_config(config)
                            st.toast("✅ 已更新负责人")
                            st.rerun()
                
                if st.button("打开项目", key=f"open_{project}", use_container_width=True):
                    st.session_state.current_project = project_path
                    st.session_state.page = 'project'
                    st.rerun()

def render_project_detail(project_dir, api_key, api_base, model_name, api_style):
    st.title(f"📂 {os.path.basename(project_dir)}")
    st.caption(f"项目路径: {project_dir}")
    config = load_config()
    project_owners = config.get("project_owners", {})
    auth_user = st.session_state.get("auth_user")
    project_name = os.path.basename(project_dir)
    if not auth_user:
        st.error("请先登录后访问项目")
        st.session_state.page = 'home'
        st.session_state.current_project = None
        st.rerun()
    if auth_user and not auth_user.get("is_admin"):
        if project_owners.get(project_name) != auth_user.get("id"):
            st.error("当前账号无权限访问该项目")
            st.session_state.page = 'home'
            st.session_state.current_project = None
            st.rerun()
    
    # Prepare Env Vars
    env_vars = os.environ.copy()
    if api_key: env_vars["API_KEY"] = api_key
    if api_base: env_vars["API_BASE"] = api_base
    if model_name: env_vars["MODEL_NAME"] = model_name
    if model_name: env_vars["MODEL"] = model_name
    if api_style: env_vars["API_STYLE"] = api_style

    def get_api_args():
        args = []
        if api_key: args.extend(["--api-key", api_key])
        if api_base: args.extend(["--api-base", api_base])
        if model_name: args.extend(["--model", model_name])
        if api_style: args.extend(["--api-style", api_style])
        return args

    # Tabs
    tab_project, tab_script, tab_storyboard, tab_char, tab_scene, tab_shots = st.tabs(["📂 文件管理", "📜 剧本工作流", "🖼️ 分镜工作流", "👥 角色概览", "🎬 场景概览", "🎬 分镜表"])

    def render_overview_tab(file_name, title, icon, initial_content=None):
        st.header(f"{icon} {title}")
        file_path = os.path.join(project_dir, file_name)
        
        def run_extraction_workflow():
             sb_output_dir = os.path.join(project_dir, "storyboard_output")
             # Find all sequence board files
             seq_files = glob.glob(os.path.join(sb_output_dir, "*__sequence_board_prompts.md"))
             
             if not seq_files:
                 st.warning("⚠️ 未找到任何四宫格分镜文件 (sequence_board_prompts.md)")
             else:
                 st.info(f"找到 {len(seq_files)} 个分镜文件，开始提取...")
                 progress_bar = st.progress(0)
                 
                 for i, fpath in enumerate(seq_files):
                     # Derive script path from sequence board filename
                     # Format: {script_base}__sequence_board_prompts.md
                     fname = os.path.basename(fpath)
                     base_name = fname.replace("__sequence_board_prompts.md", "")
                     
                     # We construct the path to the script. Even if the script file doesn't exist, 
                     # storyboard_workflow.py uses the name to locate the output file, so it might work.
                     # But get_file_paths uses script_file argument to determine prefix.
                     script_path = os.path.join(project_dir, "scripts", f"{base_name}.md")
                     
                     cmd = ["python", storyboard_py_path, "--project-dir", project_dir]
                     cmd.extend(get_api_args())
                     cmd.append("extract")
                     cmd.extend(["--script-file", script_path])
                     
                     run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description=f"Extracting from {base_name}...")
                     progress_bar.progress((i + 1) / len(seq_files))
                 
                 st.success("✅ 提取完成")
                 time.sleep(1)
                 st.rerun()
        
        if os.path.exists(file_path):
            content = read_file_content(file_path)
            
            # Display rendered markdown
            with st.container(border=True):
                st.markdown(content)
            
            st.divider()
            
            # Editor
            with st.expander(f"✏️ 编辑 {title}", expanded=False):
                new_content = st.text_area(f"内容编辑器", value=content, height=500, key=f"edit_{file_name}")
                col_save, col_dl = st.columns([1, 5])
                with col_save:
                    if st.button(f"💾 保存更改", key=f"save_{file_name}"):
                        res = write_file_content(file_path, new_content)
                        if res is True:
                            st.success("✅ 已保存")
                            time.sleep(1) # Give time to see success message
                            st.rerun()
                        else:
                            st.error(f"❌ 保存失败: {res}")
                with col_dl:
                    st.download_button(f"⬇️ 下载 {file_name}", data=content, file_name=file_name, mime="text/markdown", key=f"dl_{file_name}")
            
            # Extract Button for Existing File
            if file_name in ["character-overview.md", "scene-overview.md"]:
                 with st.expander(f"🔄 更新数据 (从分镜表提取)", expanded=False):
                     st.caption("扫描所有已生成的四宫格分镜文件，提取角色和场景信息并合并到当前文件中。")
                     if st.button(f"🚀 开始提取并合并数据", key=f"extract_existing_{file_name}"):
                          run_extraction_workflow()

        else:
            st.info(f"暂无 {title} 数据。")
            st.caption("ℹ️ 当您使用【剧本工作流】生成剧本时，系统会自动提取相关信息并追加到此处。")
            
            # Allow manual creation
            c1, c2 = st.columns([1, 1])
            with c1:
                if st.button(f"➕ 手动创建 {file_name}", key=f"create_{file_name}"):
                    if initial_content is None:
                        initial_content = f"# {title}\n\n| 名称 | 描述 | 生图提示词 |\n| --- | --- | --- |\n| 示例 | 这是一个示例描述 | 少女，微笑，长发，白色连衣裙 |\n"
                    write_file_content(file_path, initial_content)
                    st.rerun()
            
            with c2:
                # Special logic for Character and Scene overviews
                if file_name in ["character-overview.md", "scene-overview.md"]:
                    if st.button(f"🔄 从分镜表提取数据", key=f"extract_{file_name}", help="扫描所有已生成的四宫格分镜文件，提取角色和场景信息并追加到此处"):
                         run_extraction_workflow()

    # --- Tab 0: Project Management ---
    with tab_project:
        st.header("📂 项目文件管理")
        
        # 1. Upload Novel
        st.subheader("📤 上传小说 (Upload Novel)")
        uploaded_files = st.file_uploader("选择小说文件 (.txt)", type=["txt"], accept_multiple_files=True)
        if uploaded_files:
            novel_dir = os.path.join(project_dir, "novel")
            if not os.path.exists(novel_dir):
                os.makedirs(novel_dir)
            
            for uploaded_file in uploaded_files:
                file_path = os.path.join(novel_dir, uploaded_file.name)
                try:
                    with open(file_path, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                    st.success(f"✅ 已保存: {uploaded_file.name} -> novel/")
                except Exception as e:
                    st.error(f"❌ 保存失败 {uploaded_file.name}: {e}")
        
        st.divider()

        # 2. File Browser
        st.subheader("🗂️ 项目文件概览")
        
        def get_file_tree(root_dir):
            tree = {}
            if not os.path.exists(root_dir):
                return tree
            
            key_dirs = ["novel", "scripts", "storyboard_output"]
            for d in key_dirs:
                path = os.path.join(root_dir, d)
                if os.path.exists(path) and os.path.isdir(path):
                    files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) and not f.startswith('.')]
                    tree[d] = sorted(files)
                else:
                    tree[d] = []
            
            root_files = [f for f in os.listdir(root_dir) 
                          if os.path.isfile(os.path.join(root_dir, f)) 
                          and not f.startswith('.')
                          and f != "app.py"] 
            tree["root"] = sorted(root_files)
            return tree

        file_tree = get_file_tree(project_dir)
        
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            st.markdown("### 📖 Novel (小说)")
            if file_tree.get("novel"):
                for f in file_tree["novel"]:
                    st.text(f"📄 {f}")
            else:
                st.caption("（空）")

        with col_p2:
            st.markdown("### 📜 Scripts (剧本)")
            if file_tree.get("scripts"):
                for f in file_tree["scripts"]:
                    st.text(f"📄 {f}")
            else:
                st.caption("（空）")
                
        with col_p3:
            st.markdown("### 🖼️ Storyboard (分镜)")
            if file_tree.get("storyboard_output"):
                for f in file_tree["storyboard_output"]:
                    st.text(f"📄 {f}")
            else:
                st.caption("（空）")
        
        st.markdown("### 📁 Root Files (根目录)")
        if file_tree.get("root"):
            st.code("\n".join(file_tree["root"]), language="text")

    # --- Tab 1: Script Workflow ---
    with tab_script:
        st.header("剧本生成工作流")
        script_py_path = os.path.join(os.getcwd(), "script_workflow.py")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.subheader("项目状态概览")
            plot_path = os.path.join(project_dir, "plot-breakdown.md")
            plot_text = read_file_content(plot_path) if os.path.exists(plot_path) else ""
            total_plots, used_plots, unused_plots = get_plot_counts(plot_text)
            scripts_dir = os.path.join(project_dir, "scripts")
            eps = []
            if os.path.exists(scripts_dir):
                for f in os.listdir(scripts_dir):
                    if f.startswith("Episode-") and f.endswith(".md"):
                        eps.append(f)
                eps = sorted(eps)
            novel_dir = os.path.join(project_dir, "novel")
            chs = []
            if os.path.exists(novel_dir):
                for f in os.listdir(novel_dir):
                    if f.startswith("chapter-") and f.endswith(".txt"):
                        num = f[len("chapter-"):-4]
                        if num.isdigit():
                            chs.append(int(num))
                chs = sorted(chs)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.metric("剧情点总数", total_plots)
            with c2:
                st.metric("未用剧情点", unused_plots)
            with c3:
                st.metric("已用剧情点", used_plots)
            st.caption(f"剧本文件：{len(eps)} 集" + (f"，最新：{eps[-1]}" if eps else ""))
            if chs:
                st.caption(f"小说章节：{len(chs)} 章，范围：{chs[0]}-{chs[-1]}")
            else:
                st.caption("小说章节：0 章")

            st.divider()
            
            st.subheader("1. 剧情拆解")
            use_range = st.checkbox("指定章节范围", value=False)
            chapters_range = st.text_input("章节范围 (e.g. 1-6)", value="1-6", disabled=not use_range)
            
            col_opts1, col_opts2 = st.columns(2)
            with col_opts1:
                process_all = st.checkbox("自动拆解所有剩余章节", value=False, disabled=use_range, help="如果勾选，将自动按批次拆解所有剩余章节")
            with col_opts2:
                batch_size = st.number_input("每批章节数", min_value=1, max_value=20, value=6, help="批量拆解时，每批包含的章节数量")

            if st.button("🧩 生成剧情拆解", key="script_breakdown", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("script_breakdown",)):
                pass
            
            if st.session_state.processing_key == "script_breakdown":
                cmd = ["python", script_py_path, "--project-dir", project_dir]
                cmd.extend(get_api_args())
                cmd.append("breakdown")
                cmd.extend(["--batch-size", str(batch_size)])
                
                if use_range:
                    cmd.extend(["--chapters", chapters_range])
                else:
                    cmd.extend(["--include-examples", "--include-output-style"])
                    if process_all:
                        cmd.append("--all")
                
                run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description="Generating breakdown...")
                st.session_state.processing_key = None
                st.rerun()

            st.divider()
            
            st.subheader("2. 生成剧本")
            episode_num = st.number_input("集数 (Episode)", min_value=1, value=1)
            overwrite_script = st.checkbox("允许覆盖 (--overwrite)", value=True)
            check_script = st.checkbox("生成后质检 (--check)", value=False)
            
            if st.button("✍️ 生成单集剧本", key="script_gen", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("script_gen",)):
                pass
            
            if st.session_state.processing_key == "script_gen":
                cmd = ["python", script_py_path, "--project-dir", project_dir]
                cmd.extend(get_api_args())
                cmd.extend(["script", "--episode", str(episode_num)])
                if overwrite_script:
                    cmd.append("--overwrite")
                if check_script:
                    cmd.append("--check")
                run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description=f"Generating script for Episode {episode_num}...")
                st.session_state.processing_key = None
                st.rerun()

            st.markdown("#### 批量生成设置")
            concurrency = st.slider("并发数 (Workers)", min_value=1, max_value=10, value=1, help="同时生成的剧本数量。注意API速率限制。")

            if st.button("🚀 批量生成所有未用集数", key="script_gen_all", help="自动查找所有未用剧情点并批量生成剧本", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("script_gen_all",)):
                pass
            
            if st.session_state.processing_key == "script_gen_all":
                cmd = ["python", script_py_path, "--project-dir", project_dir]
                cmd.extend(get_api_args())
                cmd.append("script")
                cmd.append("--all")
                cmd.extend(["--concurrency", str(concurrency)])
                if overwrite_script:
                    cmd.append("--overwrite")
                if check_script:
                    cmd.append("--check")
                run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description="Batch generating all unused episodes...")
                # Clear all script editor keys
                for k in list(st.session_state.keys()):
                    if k.startswith("edit_script_"):
                        del st.session_state[k]
                time.sleep(0.5)
                st.session_state.processing_key = None
                st.rerun()

        with col2:
            st.subheader("文件预览")
            breakdown_path = os.path.join(project_dir, "plot-breakdown.md")
            if os.path.exists(breakdown_path):
                with st.expander("📂 plot-breakdown.md (剧情拆解)", expanded=False):
                    bd_content = read_file_content(breakdown_path)
                    new_bd_content = st.text_area("编辑剧情拆解", value=bd_content, height=600, key="edit_breakdown")
                    st.download_button("⬇️ 下载剧情拆解", data=bd_content, file_name="plot-breakdown.md", mime="text/markdown", key="download_breakdown")
                    if st.button("💾 保存剧情拆解", key="save_breakdown"):
                        res = write_file_content(breakdown_path, new_bd_content)
                        if res is True:
                            st.success("✅ 已保存")
                        else:
                            st.error(f"❌ 保存失败: {res}")
            else:
                st.info("暂无 plot-breakdown.md 文件")

            scripts_dir = os.path.join(project_dir, "scripts")
            if os.path.exists(scripts_dir):
                st.markdown("### 📜 已生成剧本 (Generated Scripts)")
                df_scripts_preview = get_file_info_df(scripts_dir)
                
                selected_script_preview = None
                if not df_scripts_preview.empty:
                    all_select_scripts = st.checkbox("全选剧本", value=False, key="script_select_all")
                    height = min(len(df_scripts_preview) * 35 + 38, 300)
                    selection_preview = st.dataframe(
                        df_scripts_preview[["文件名", "大小", "修改时间"]],
                        on_select="rerun",
                        selection_mode="multi-row",
                        use_container_width=True,
                        hide_index=True,
                        height=height,
                        key="script_preview_table"
                    )
                    selected_rows_scripts = list(range(len(df_scripts_preview))) if all_select_scripts else selection_preview.selection.rows
                    if selected_rows_scripts:
                        if len(selected_rows_scripts) == 1:
                            idx = selected_rows_scripts[0]
                            selected_script_preview = df_scripts_preview.iloc[idx]["文件名"]
                            st.info(f"📄 正在预览: **{selected_script_preview}**")
                        else:
                            st.info(f"已选择 {len(selected_rows_scripts)} 个剧本，可批量操作")
                        
                        c_dl_scr, c_del_scr = st.columns([1, 1])
                        with c_dl_scr:
                            if st.button("⬇️ 下载选中剧本为 ZIP", key="download_scripts_zip", use_container_width=True):
                                buf_scripts = io.BytesIO()
                                with zipfile.ZipFile(buf_scripts, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                                    for idx in selected_rows_scripts:
                                        fname = df_scripts_preview.iloc[idx]["文件名"]
                                        fpath = os.path.join(scripts_dir, fname)
                                        try:
                                            with open(fpath, "rb") as f:
                                                zf.writestr(fname, f.read())
                                        except Exception:
                                            pass
                                st.download_button(
                                    "⬇️ 点击下载剧本 ZIP",
                                    data=buf_scripts.getvalue(),
                                    file_name="scripts_selected.zip",
                                    mime="application/zip",
                                    key="download_scripts_zip_btn",
                                    use_container_width=True
                                )
                        
                        with c_del_scr:
                            with st.popover("🗑️ 删除选中剧本", use_container_width=True):
                                st.warning("确定要删除选中的剧本吗？此操作不可恢复。")
                                if st.button("确认删除", key="delete_scripts_btn", type="primary", use_container_width=True):
                                    del_count = 0
                                    for idx in selected_rows_scripts:
                                        fname = df_scripts_preview.iloc[idx]["文件名"]
                                        fpath = os.path.join(scripts_dir, fname)
                                        try:
                                            os.remove(fpath)
                                            del_count += 1
                                        except Exception as e:
                                            st.error(f"删除失败 {fname}: {e}")
                                    if del_count > 0:
                                        st.success(f"已删除 {del_count} 个剧本")
                                        time.sleep(1)
                                        st.rerun()
                    else:
                        st.info("👈 请在列表中选择一个或多个剧本")
                else:
                    st.info("scripts 目录下暂无 .md 文件")
                
                if selected_script_preview:
                    script_content_path = os.path.join(scripts_dir, selected_script_preview)
                    sc_content = read_file_content(script_content_path)
                    new_sc_content = st.text_area(f"编辑 {selected_script_preview}", value=sc_content, height=600, key=f"edit_script_{selected_script_preview}")
                    st.download_button(f"⬇️ 下载 {selected_script_preview}", data=sc_content, file_name=selected_script_preview, mime="text/markdown", key=f"download_script_{selected_script_preview}")
                    if st.button(f"💾 保存 {selected_script_preview}", key=f"save_script_{selected_script_preview}"):
                        res = write_file_content(script_content_path, new_sc_content)
                        if res is True:
                            st.success("✅ 已保存")
                        else:
                            st.error(f"❌ 保存失败: {res}")
            else:
                st.info("scripts 目录不存在")

    # --- Tab 2: Storyboard Workflow ---
    with tab_storyboard:
        st.header("分镜生成工作流")
        storyboard_py_path = os.path.join(os.getcwd(), "storyboard_workflow.py")
        sb_output_dir = os.path.join(project_dir, "storyboard_output")
        
        col3, col4 = st.columns([1, 2])
        
        with col3:
            st.subheader("分镜状态概览")
            # 全局统计（不依赖选择）
            outputs_dir = sb_output_dir
            breakdown_count = 0
            beatboard_count = 0
            sequence_count = 0
            motion_count = 0
            voiceover_count = 0
            latest_file = None
            latest_mtime = None
            if os.path.exists(outputs_dir):
                for f in os.listdir(outputs_dir):
                    fp = os.path.join(outputs_dir, f)
                    if not os.path.isfile(fp):
                        continue
                    if f.endswith(".md"):
                        if "beat_breakdown.md" in f:
                            breakdown_count += 1
                        elif "beat_board_prompts.md" in f:
                            beatboard_count += 1
                        elif "sequence_board_prompts.md" in f:
                            sequence_count += 1
                        elif "motion_prompts.md" in f:
                            motion_count += 1
                        elif "voiceover_table.md" in f:
                            voiceover_count += 1
                        try:
                            mt = os.path.getmtime(fp)
                            if latest_mtime is None or mt > latest_mtime:
                                latest_mtime = mt
                                latest_file = f
                        except Exception:
                            pass
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                st.metric("节拍拆解表", breakdown_count)
            with c2:
                st.metric("九宫格提示词", beatboard_count)
            with c3:
                st.metric("四宫格提示词", sequence_count)
            with c4:
                st.metric("动态提示词", motion_count)
            with c5:
                st.metric("配音表", voiceover_count)
            if latest_file:
                st.caption(f"最新输出：{latest_file}")
            else:
                st.caption("暂无分镜输出文件")

            st.divider()
            
            # 在操作面板顶部选择脚本文件，后续操作共用
            st.markdown("#### 1. 选择脚本文件 (Select Script)")
            scripts_dir = os.path.join(project_dir, "scripts")
            df_scripts = get_file_info_df(scripts_dir)
            
            selected_scripts = []
            if not df_scripts.empty:
                # Calculate reasonable height
                height = min(len(df_scripts) * 35 + 38, 300)
                
                selection = st.dataframe(
                    df_scripts[["文件名", "大小", "修改时间"]],
                    on_select="rerun",
                    selection_mode="multi-row",
                    use_container_width=True,
                    hide_index=True,
                    height=height,
                    key="sb_script_table"
                )
                
                if selection.selection.rows:
                    for idx in selection.selection.rows:
                        selected_scripts.append(df_scripts.iloc[idx]["文件名"])
                    
                    if len(selected_scripts) == 1:
                        st.info(f"✅ 当前已选: **{selected_scripts[0]}**")
                    else:
                        st.info(f"✅ 当前已选: **{len(selected_scripts)}** 个文件")
                else:
                    st.warning("👈 请在上方列表中点击选择一个或多个脚本文件")
            else:
                st.info("scripts 目录下暂无 .md 文件，请先在剧本工作流生成或添加脚本。")
            
            st.divider()

            # 状态重置按钮（用于解决按钮卡死问题）
            if st.session_state.processing_key is not None:
                if st.sidebar.button("⚠️ 重置工作流状态", help="如果按钮一直处于禁用状态，请点击此按钮重置"):
                    st.session_state.processing_key = None
                    st.rerun()

            st.subheader("🚀 一键全流程 (One-Click Workflow)")
            if st.button("⚡ 一键执行所有步骤 (Breakdown -> Dubbing)", key="sb_auto", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("sb_auto",), use_container_width=True, type="primary"):
                pass
            
            if st.session_state.processing_key == "sb_auto":
                if selected_scripts:
                    for script in selected_scripts:
                        selected_path = os.path.join(scripts_dir, script)
                        cmd = ["python", storyboard_py_path, "--project-dir", project_dir]
                        cmd.extend(get_api_args())
                        cmd.append("auto")
                        cmd.extend(["--script-file", selected_path])
                        run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description=f"Running full storyboard workflow for {script}...")
                    
                    # Clear storyboard editor keys
                    for k in list(st.session_state.keys()):
                        if k.startswith("edit_sb_"):
                            del st.session_state[k]
                    time.sleep(0.5)
                else:
                    st.warning("⚠️ 请先在上方列表中选择至少一个脚本文件")
                    time.sleep(2)
                
                st.session_state.processing_key = None
                st.rerun()

            st.divider()
            
            st.subheader("2. 节拍拆解")
            if st.button("🎵 生成节拍拆解表", key="sb_breakdown", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("sb_breakdown",)):
                pass
            
            if st.session_state.processing_key == "sb_breakdown":
                if selected_scripts:
                    for script in selected_scripts:
                        selected_path = os.path.join(scripts_dir, script)
                        cmd = ["python", storyboard_py_path, "--project-dir", project_dir]
                        cmd.extend(get_api_args())
                        cmd.append("breakdown")
                        cmd.extend(["--script-file", selected_path])
                        run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description=f"Generating beat breakdown from {script}...")
                    
                    # Clear storyboard editor keys
                    for k in list(st.session_state.keys()):
                        if k.startswith("edit_sb_"):
                            del st.session_state[k]
                    time.sleep(0.5)
                else:
                    st.warning("⚠️ 请先在上方列表中选择至少一个脚本文件")
                    time.sleep(2)

                st.session_state.processing_key = None
                st.rerun()
                
            st.subheader("3. 九宫格")
            if st.button("🎨 生成九宫格提示词", key="sb_beatboard", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("sb_beatboard",)):
                pass
            
            if st.session_state.processing_key == "sb_beatboard":
                if selected_scripts:
                    for script in selected_scripts:
                        selected_path = os.path.join(scripts_dir, script)
                        cmd = ["python", storyboard_py_path, "--project-dir", project_dir]
                        cmd.extend(get_api_args())
                        cmd.append("beatboard")
                        cmd.extend(["--script-file", selected_path])
                        run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description=f"Generating beat board prompts from {script}...")
                else:
                    st.warning("⚠️ 请先在上方列表中选择至少一个脚本文件")
                    time.sleep(2)
                st.session_state.processing_key = None
                st.rerun()
                
            st.subheader("4. 四宫格")
            if st.button("🎞️ 生成四宫格提示词", key="sb_sequence", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("sb_sequence",)):
                pass
            
            if st.session_state.processing_key == "sb_sequence":
                if selected_scripts:
                    for script in selected_scripts:
                        selected_path = os.path.join(scripts_dir, script)
                        cmd = ["python", storyboard_py_path, "--project-dir", project_dir]
                        cmd.extend(get_api_args())
                        cmd.append("sequence")
                        cmd.extend(["--script-file", selected_path])
                        run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description=f"Generating sequence board prompts from {script}...")
                        
                        # Chain Extract command
                        cmd_ext = ["python", storyboard_py_path, "--project-dir", project_dir]
                        cmd_ext.extend(get_api_args())
                        cmd_ext.append("extract")
                        cmd_ext.extend(["--script-file", selected_path])
                        run_command(cmd_ext, cwd=os.getcwd(), env_vars=env_vars, description=f"Extracting character/scene overviews from {script}...")
                else:
                    st.warning("⚠️ 请先在上方列表中选择至少一个脚本文件")
                    time.sleep(2)
                st.session_state.processing_key = None
                st.rerun()
                
            st.subheader("5. 动态提示词")
            if st.button("🎥 生成动态提示词", key="sb_motion", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("sb_motion",)):
                pass
            
            if st.session_state.processing_key == "sb_motion":
                if selected_scripts:
                    for script in selected_scripts:
                        selected_path = os.path.join(scripts_dir, script)
                        cmd = ["python", storyboard_py_path, "--project-dir", project_dir]
                        cmd.extend(get_api_args())
                        cmd.append("motion")
                        cmd.extend(["--script-file", selected_path])
                        run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description=f"Generating motion prompts from {script}...")
                    
                    # Clear storyboard editor keys
                    for k in list(st.session_state.keys()):
                        if k.startswith("edit_sb_"):
                            del st.session_state[k]
                    time.sleep(0.5)
                else:
                    st.warning("⚠️ 请先在上方列表中选择至少一个脚本文件")
                    time.sleep(2)
                st.session_state.processing_key = None
                st.rerun()

            st.subheader("6. 配音表")
            if st.button("🎙️ 生成配音表", key="sb_voiceover", disabled=(st.session_state.processing_key is not None), on_click=set_processing, args=("sb_voiceover",)):
                pass
            
            if st.session_state.processing_key == "sb_voiceover":
                if selected_scripts:
                    for script in selected_scripts:
                        selected_path = os.path.join(scripts_dir, script)
                        cmd = ["python", storyboard_py_path, "--project-dir", project_dir]
                        cmd.extend(get_api_args())
                        cmd.append("dubbing")
                        cmd.extend(["--script-file", selected_path])
                        run_command(cmd, cwd=os.getcwd(), env_vars=env_vars, description=f"Generating voiceover table from {script}...")
                    
                    for k in list(st.session_state.keys()):
                        if k.startswith("edit_sb_"):
                            del st.session_state[k]
                    time.sleep(0.5)
                else:
                    st.warning("⚠️ 请先在上方列表中选择至少一个脚本文件")
                    time.sleep(2)
                st.session_state.processing_key = None
                st.rerun()

        with col4:
            st.subheader("输出预览 (Output Preview)")
            
            # Get all files first
            df_outputs = get_file_info_df(sb_output_dir)
            
            # Filter if script selected
            if selected_scripts and not df_outputs.empty:
                import re
                bases = [os.path.splitext(s)[0] for s in selected_scripts]
                # Filter rows where '文件名' starts with any base + "__"
                # Use regex for multi-match
                pattern = "^(" + "|".join([re.escape(b) for b in bases]) + ")__"
                df_outputs = df_outputs[df_outputs['文件名'].str.contains(pattern, regex=True, na=False)]
            
            chosen_output = None
            
            if not df_outputs.empty:
                # Reset index is crucial for selection mapping
                df_outputs = df_outputs.reset_index(drop=True)
                all_select = st.checkbox("全选", value=False, key="sb_output_select_all")
                height = min(len(df_outputs) * 35 + 38, 400)
                selection_out = st.dataframe(
                    df_outputs[["文件名", "大小", "修改时间"]],
                    on_select="rerun",
                    selection_mode="multi-row",
                    use_container_width=True,
                    hide_index=True,
                    height=height,
                    key="sb_output_table"
                )
                
                selected_rows = list(range(len(df_outputs))) if all_select else selection_out.selection.rows
                if selected_rows:
                    if len(selected_rows) == 1:
                        idx = selected_rows[0]
                        chosen_output = df_outputs.iloc[idx]["文件名"]
                        st.info(f"📄 正在预览: **{chosen_output}**")
                    else:
                        st.info(f"已选择 {len(selected_rows)} 个文件，可批量操作")
                    
                    c_dl, c_del = st.columns([1, 1])
                    with c_dl:
                        if st.button("⬇️ 下载选中为 ZIP", key="download_selected_zip", use_container_width=True):
                            buf = io.BytesIO()
                            with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                                for idx in selected_rows:
                                    fname = df_outputs.iloc[idx]["文件名"]
                                    fpath = os.path.join(sb_output_dir, fname)
                                    try:
                                        with open(fpath, "rb") as f:
                                            zf.writestr(fname, f.read())
                                    except Exception:
                                        pass
                            st.download_button(
                                "⬇️ 点击下载 ZIP",
                                data=buf.getvalue(),
                                file_name="storyboard_outputs.zip",
                                mime="application/zip",
                                key="download_selected_zip_btn",
                                use_container_width=True
                            )
                    
                    with c_del:
                        with st.popover("🗑️ 删除选中文件", use_container_width=True):
                            st.warning("确定要删除选中的文件吗？此操作不可恢复。")
                            if st.button("确认删除", key="delete_sb_output_btn", type="primary", use_container_width=True):
                                del_count = 0
                                for idx in selected_rows:
                                    fname = df_outputs.iloc[idx]["文件名"]
                                    fpath = os.path.join(sb_output_dir, fname)
                                    try:
                                        os.remove(fpath)
                                        del_count += 1
                                    except Exception as e:
                                        st.error(f"删除失败 {fname}: {e}")
                                if del_count > 0:
                                    st.success(f"已删除 {del_count} 个文件")
                                    time.sleep(1)
                                    st.rerun()
                else:
                    st.info("👈 请在列表中选择一个或多个文件")
            else:
                if selected_scripts:
                    st.info(f"当前选中脚本 ({', '.join(selected_scripts)}) 暂无对应的分镜输出文件。")
                else:
                    st.info("暂无分镜输出文件。")
            
            if chosen_output:
                full_path = os.path.join(sb_output_dir, chosen_output)
                sb_content = read_file_content(full_path)
                new_sb_content = st.text_area(f"编辑 {chosen_output}", value=sb_content, height=600, key=f"edit_sb_{chosen_output}")
                st.download_button(f"⬇️ 下载 {chosen_output}", data=sb_content, file_name=chosen_output, mime="text/markdown", key=f"download_sb_{chosen_output}")
                if st.button(f"💾 保存 {chosen_output}", key=f"save_sb_{chosen_output}"):
                    res = write_file_content(full_path, new_sb_content)
                    if res is True:
                        st.success("✅ 已保存")
                    else:
                        st.error(f"❌ 保存失败: {res}")

    # --- Tab 4: Character Overview ---
    with tab_char:
        render_overview_tab("character-overview.md", "角色概览", "👥")

    # --- Tab 5: Scene Overview ---
    with tab_scene:
        render_overview_tab("scene-overview.md", "场景概览", "🎬")

    # --- Tab 6: Storyboard Table ---
    with tab_shots:
        st.header("🎬 分镜表")
        # Discover available storyboard tables (global + per-episode)
        table_files_data = []
        try:
            for f in os.listdir(project_dir):
                if f.startswith("storyboard-table") and f.endswith(".md"):
                    full_path = os.path.join(project_dir, f)
                    # Get file stats
                    try:
                        stats = os.stat(full_path)
                        mod_time = datetime.datetime.fromtimestamp(stats.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                        size_kb = f"{stats.st_size / 1024:.1f} KB"
                    except:
                        mod_time = "-"
                        size_kb = "-"
                    
                    display_name = f.replace("storyboard-table__", "").replace(".md", "")
                    if display_name == "storyboard-table":
                         display_name = "Global (Default)"
                    
                    table_files_data.append({
                        "文件名": f,
                        "说明": display_name,
                        "修改时间": mod_time,
                        "大小": size_kb
                    })
        except Exception:
            table_files_data = []
        
        # Sort
        table_files_data.sort(key=lambda x: x["文件名"])
        
        if not table_files_data:
             table_files_data.append({"文件名": "storyboard-table.md", "说明": "Global (Default)", "修改时间": "-", "大小": "0 KB"})

        df_files = pd.DataFrame(table_files_data)
        
        st.caption("👇 请在列表中点击选择要查看的分镜表")
        event = st.dataframe(
            df_files,
            column_config={
                "文件名": st.column_config.TextColumn("文件名", width="medium"),
                "说明": st.column_config.TextColumn("说明", width="small"),
                "修改时间": st.column_config.TextColumn("修改时间", width="small"),
                "大小": st.column_config.TextColumn("大小", width="small"),
            },
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="storyboard_file_list"
        )
        
        selected_rows = event.selection.rows
        if selected_rows:
            selected_index = selected_rows[0]
            selected_table = df_files.iloc[selected_index]["文件名"]
            
            # Delete Option for Storyboard Table
            st.divider()
            with st.popover(f"🗑️ 删除 {selected_table}", use_container_width=True):
                 st.warning(f"确定要删除分镜表 {selected_table} 吗？此操作不可恢复。")
                 if st.button("确认删除", key="delete_sb_table_btn", type="primary", use_container_width=True):
                     full_path = os.path.join(project_dir, selected_table)
                     try:
                         os.remove(full_path)
                         st.success(f"已删除: {selected_table}")
                         time.sleep(1)
                         st.rerun()
                     except Exception as e:
                         st.error(f"删除失败: {e}")
        else:
            if not df_files.empty:
                selected_table = df_files.iloc[0]["文件名"]
            else:
                selected_table = "storyboard-table.md"
            st.info(f"当前默认查看: {selected_table}")
        
        shots_header = "| 编号 | 出场人物 | 场景 | 分镜提示词 | 视频提示词 |\n| --- | --- | --- | --- | --- |\n| 1 | 示例人物 | 示例场景 | 镜头描述... | 视频生成提示词... |\n"
        title = "分镜表" + (f"（{selected_table.replace('storyboard-table__','').replace('.md','')}）" if selected_table != "storyboard-table.md" else "")
        render_overview_tab(selected_table, title, "🎬", initial_content=f"# {title}\n\n{shots_header}")

# --- Main Logic ---

init_auth()

api_key, api_base, model_name, api_style = render_sidebar()
base_dir = get_base_dir()
projects = get_projects(base_dir)

if st.session_state.page == 'home':
    render_home(base_dir, projects)
elif st.session_state.page == 'project' and st.session_state.current_project:
    render_project_detail(st.session_state.current_project, api_key, api_base, model_name, api_style)
else:
    # Fallback
    st.session_state.page = 'home'
    st.rerun()
