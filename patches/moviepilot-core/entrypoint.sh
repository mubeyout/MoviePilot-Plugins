#!/bin/bash
# shellcheck shell=bash
# shellcheck disable=SC2016
# shellcheck disable=SC2155

Green="\033[32m"
Red="\033[31m"
Yellow='\033[33m'
Font="\033[0m"
INFO="[${Green}INFO${Font}]"
ERROR="[${Red}ERROR${Font}]"
WARN="[${Yellow}WARN${Font}]"
function INFO() {
    echo -e "${INFO} ${1}"
}
function ERROR() {
    echo -e "${ERROR} ${1}"
}
function WARN() {
    echo -e "${WARN} ${1}"
}

# 设置虚拟环境路径
VENV_PATH="${VENV_PATH:-/opt/venv}"
export PATH="${VENV_PATH}/bin:$PATH"

CONFIG_DIR="${CONFIG_DIR:-/config}"

declare -ga VARS_SET_BY_SCRIPT=()

# ============ 环境变量补全 ============

function load_config_from_app_env() {
    local env_file="${CONFIG_DIR}/app.env"
    declare -A vars_and_default_values=(
        ["PIP_PROXY"]=""
        ["GITHUB_PROXY"]=""
        ["PROXY_HOST"]=""
        ["GITHUB_TOKEN"]=""
        ["MOVIEPILOT_AUTO_UPDATE"]="release"
        ["DB_TYPE"]="sqlite"
        ["DB_POSTGRESQL_HOST"]="localhost"
        ["DB_POSTGRESQL_PORT"]="5432"
        ["DB_POSTGRESQL_DATABASE"]="moviepilot"
        ["DB_POSTGRESQL_USERNAME"]="moviepilot"
        ["DB_POSTGRESQL_PASSWORD"]="moviepilot"
        ["DB_POSTGRESQL_POOL_SIZE"]="20"
        ["DB_POSTGRESQL_MAX_OVERFLOW"]="30"
        ["ENABLE_SSL"]="false"
        ["SSL_DOMAIN"]=""
        ["NGINX_PORT"]="3000"
        ["PORT"]="3001"
        ["NGINX_CLIENT_MAX_BODY_SIZE"]="10m"
    )

    INFO "开始加载配置 (配置文件: ${env_file})..."
    shopt -s extglob
    declare -A values_from_env_file
    if [ -f "${env_file}" ]; then
        INFO "检测到 ${env_file} 文件，尝试解析..."
        while IFS= read -r line || [ -n "$line" ]; do
            if [[ "$line" =~ ^[[:space:]]*# || -z "$line" ]]; then continue; fi
            local key_in_file value_raw_in_file
            if [[ "$line" =~ ^[[:space:]]*([A-Za-z_][A-Za-z0-9_]*)[[:space:]]*=(.*) ]]; then
                key_in_file="${BASH_REMATCH[1]}"
                value_raw_in_file="${BASH_REMATCH[2]}"
                if [[ -n "${vars_and_default_values[$key_in_file]+_}" ]]; then
                    local temp_val_after_initial_trim
                    temp_val_after_initial_trim="${value_raw_in_file#"${value_raw_in_file%%[![:space:]]*}"}"
                    temp_val_after_initial_trim="${temp_val_after_initial_trim%"${temp_val_after_initial_trim##*[![:space:]]}"}"
                    local val_before_quote_check="${temp_val_after_initial_trim}"
                    if [[ ! ("${temp_val_after_initial_trim:0:1}" == "'" && "${temp_val_after_initial_trim: -1}" == "'") ]]; then
                        if [[ "${temp_val_after_initial_trim}" =~ ^(.*)[[:space:]]+# ]]; then
                            val_before_quote_check="${BASH_REMATCH[1]}"
                            val_before_quote_check="${val_before_quote_check%%+([[:space:]])}"
                        elif [[ "${temp_val_after_initial_trim:0:1}" == "#" ]]; then
                            val_before_quote_check=""
                        fi
                    fi
                    local parsed_value_from_file
                    if [[ "${val_before_quote_check:0:1}" == "'" && "${val_before_quote_check: -1}" == "'" && ${#val_before_quote_check} -ge 2 ]]; then
                        parsed_value_from_file="${val_before_quote_check:1:${#val_before_quote_check}-2}"
                        parsed_value_from_file="${parsed_value_from_file//\\\'/__MP_PARSER_SQUOTE__}"
                        parsed_value_from_file="${parsed_value_from_file//__MP_PARSER_SQUOTE__/\'}"
                    elif [ -z "${val_before_quote_check}" ]; then
                        parsed_value_from_file=""
                    else
                        WARN "位于 ${env_file} 中的键 ${key_in_file} 对应值 ${val_before_quote_check} 未按规范使用单引号包裹，将采用字面量解析。"
                        parsed_value_from_file="${val_before_quote_check}"
                    fi
                    values_from_env_file["${key_in_file}"]="${parsed_value_from_file}"
                fi
            else
                WARN "跳过 ${env_file} 中格式不正确的行: $line"
            fi
        done < <(sed -e '1s/^\xEF\xBB\xBF//' -e 's/\r$//g' "${env_file}")
        INFO "${env_file} 解析完毕。"
    else
        INFO "${env_file} 文件不存在，跳过文件加载。"
    fi

    INFO "正在根据优先级确定并导出配置值..."
    for var_name in "${!vars_and_default_values[@]}"; do
        local fallback_value="${vars_and_default_values[$var_name]}"
        local final_value
        local value_source="未设置"
        local set_by_initial_env=false
        if eval "[ -n \"\${${var_name}+x}\" ]"; then
            final_value="$(eval echo \"\$"${var_name}"\")"
            value_source="系统环境变量"
            set_by_initial_env=true
        elif [[ -n "${values_from_env_file["${var_name}"]+_}" ]]; then
            final_value="${values_from_env_file["${var_name}"]}"
            value_source=".env 文件"
        else
            final_value="${fallback_value}"
            value_source="内置默认值"
        fi
        if declare -gx "${var_name}=${final_value}"; then
            if [ -z "${final_value}" ]; then
                 INFO "变量 ${var_name}, 值为空 (来源: ${value_source})。"
            else
                 INFO "变量 ${var_name}, 值: ${final_value} (来源: ${value_source})。"
            fi
            if ! ${set_by_initial_env}; then
                local found_in_script_vars=false
                for item in "${VARS_SET_BY_SCRIPT[@]}"; do
                    if [[ "$item" == "$var_name" ]]; then found_in_script_vars=true; break; fi
                done
                if ! ${found_in_script_vars}; then VARS_SET_BY_SCRIPT+=("${var_name}"); fi
            fi
        else
            ERROR "导出变量 ${var_name}, 值: '${final_value}'失败 (来源: ${value_source}) "
        fi
    done
    shopt -u extglob
    INFO "配置加载流程执行完毕。"
}

# ============ 优雅退出 ============

function graceful_exit() {
    local exit_code=${1:-0}
    local reason=${2:-python_exit}
    if [ "$reason" = "signal" ]; then
        INFO "→ 收到停止信号，执行精准清理程序..."
    else
        INFO "→ 主进程已退出 (代码: $exit_code)，执行清理程序..."
    fi
    INFO "→ [1/3] 正在关闭前端 Nginx..."
    nginx -c /etc/nginx/nginx.conf -s stop 2>/dev/null || true
    if [ -n "$PYTHON_PID" ] && ps -p "$PYTHON_PID" > /dev/null; then
        INFO "→ [2/3] 正在等待 Python (PID: $PYTHON_PID) 完成清理..."
        wait "$PYTHON_PID" 2>/dev/null || true
    fi
    INFO "→ [3/3] 后端已安全退出，正在关闭 Docker Proxy..."
    if [ -S "/var/run/docker.sock" ]; then
        nginx -c /etc/nginx/docker_http_proxy.conf -s stop 2>/dev/null || true
    fi
    if [ "$exit_code" -eq 0 ] || [ "$exit_code" -eq 130 ] || [ "$exit_code" -eq 143 ]; then
        INFO "→ 所有服务已按序清理，容器正常退出 (ExitCode: $exit_code)。"
    else
        ERROR "→ 清理完成，但主进程检测到异常退出 (ExitCode: $exit_code)！"
    fi
    exit "$exit_code"
}

# ============ 主流程 ============

load_config_from_app_env

# HTTPS 配置
if [ "${ENABLE_SSL}" = "true" ]; then
    export HTTPS_SERVER_CONF=$(cat <<EOF
    server {
        include /etc/nginx/mime.types;
        default_type application/octet-stream;
        listen ${SSL_NGINX_PORT:-443} ssl;
        listen [::]:${SSL_NGINX_PORT:-443} ssl;
        server_name ${SSL_DOMAIN:-moviepilot};
        ssl_certificate ${CONFIG_DIR}/certs/latest/fullchain.pem;
        ssl_certificate_key ${CONFIG_DIR}/certs/latest/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
        ssl_prefer_server_ciphers on;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 10m;
        include common.conf;
    }
EOF
)
else
    export HTTPS_SERVER_CONF="# HTTPS未启用"
fi

envsubst '${NGINX_PORT}${PORT}${NGINX_CLIENT_MAX_BODY_SIZE}${ENABLE_SSL}${HTTPS_SERVER_CONF}' < /etc/nginx/nginx.template.conf > /etc/nginx/nginx.conf

# 自动更新检查
cd /
source /usr/local/bin/mp_update.sh
cd /app || exit

# 用户/权限
groupmod -o -g "${PGID}" moviepilot
usermod -o -u "${PUID}" moviepilot
chown -R moviepilot:moviepilot "${HOME}" /app /public "${CONFIG_DIR}" /var/lib/nginx /var/log/nginx
chown moviepilot:moviepilot /etc/hosts /tmp

# 浏览器内核
if [[ "$HTTPS_PROXY" =~ ^https?:// ]] || [[ "$PROXY_HOST" =~ ^https?:// ]]; then
  HTTPS_PROXY="${HTTPS_PROXY:-${https_proxy:-$PROXY_HOST}}" gosu moviepilot:moviepilot playwright install ${PLAYWRIGHT_BROWSER_TYPE:-chromium}
else
  gosu moviepilot:moviepilot playwright install ${PLAYWRIGHT_BROWSER_TYPE:-chromium}
fi

source /app/docker/cert.sh

# ============ 前端 Nginx ============

# nginx 缓存策略（禁用 JS/CSS 激进缓存）
if [ -f "/config/nginx_common_patched.conf" ]; then
    cp -f /config/nginx_common_patched.conf /etc/nginx/common.conf
    INFO "nginx common.conf patched"
fi

INFO "→ 启动前端nginx服务..."
nginx

trap 'graceful_exit 130 "signal"' SIGINT
trap 'graceful_exit 143 "signal"' SIGTERM

if [ -S "/var/run/docker.sock" ]; then
    INFO "→ 启动 Docker Proxy..."
    nginx -c /etc/nginx/docker_http_proxy.conf
    chown -R moviepilot:moviepilot /var/lib/nginx /var/log/nginx
fi

umask "${UMASK}"

# 清理非系统环境变量
INFO "清理非系统环境导入的变量..."
if [ ${#VARS_SET_BY_SCRIPT[@]} -gt 0 ]; then
    for var_to_unset in "${VARS_SET_BY_SCRIPT[@]}"; do
        if eval "[ -n \"\${${var_to_unset}+x}\" ]"; then
            INFO "取消设置环境变量: ${var_to_unset}"
            unset "${var_to_unset}"
        else
            WARN "变量 ${var_to_unset} 已不存在，无需取消设置。"
        fi
    done
else
    INFO "没有由非系统环境导入的变量需要清理。"
fi

# ============ 运行时补丁（插件安装） ============

# 插件从 /config 安装到系统目录（运行时必须，插件可能从外部更新）
_install_plugin() {
    local name="$1" src="$2"
    if [ -d "/config/plugins/v2/${src}" ]; then
        rm -rf "/app/app/plugins/${name}"
        cp -a "/config/plugins/v2/${src}" "/app/app/plugins/${name}"
        rm -rf "/app/app/plugins/${name}/__pycache__"
        INFO "Plugin ${name} installed"
    fi
}
_install_plugin "adultsubscribe" "adultsubscribe"
_install_plugin "metatubesource" "metatubesource"
_install_plugin "bytemusediscover" "bytemusediscover"

# 前端注入脚本（index.html 每次启动是镜像原始文件，需重新注入）
if [ -f "/config/stills-inject.js" ] && [ -f "/config/inject_stills.py" ]; then
    python3 /config/inject_stills.py
    INFO "Frontend stills injection applied"
fi

# ============ 启动后端 ============

INFO "Starting backend service..."
if [ "${START_NOGOSU:-false}" = "true" ]; then
    "${VENV_PATH}/bin/python3" app/main.py > /dev/stdout 2> /dev/stderr &
else
    gosu moviepilot:moviepilot "${VENV_PATH}/bin/python3" app/main.py > /dev/stdout 2> /dev/stderr &
fi
PYTHON_PID=$!

wait "$PYTHON_PID" 2>/dev/null
exit_code=$?
graceful_exit "$exit_code" "python_exit"
