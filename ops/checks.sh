#!/bin/bash

# Falconer Health Checks Script
# This script performs comprehensive health checks on the Falconer system

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_NAME="falconer"
LOG_FILE="/var/log/falconer/health_checks.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

check_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((CHECKS_PASSED++))
}

check_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((CHECKS_FAILED++))
}

check_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((CHECKS_WARNING++))
}

# Check systemd service status
check_service_status() {
    log "Checking systemd service status..."
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        check_pass "Service $SERVICE_NAME is running"
    else
        check_fail "Service $SERVICE_NAME is not running"
        return 1
    fi
    
    if systemctl is-enabled --quiet "$SERVICE_NAME"; then
        check_pass "Service $SERVICE_NAME is enabled"
    else
        check_warning "Service $SERVICE_NAME is not enabled"
    fi
}

# Check service logs for errors
check_service_logs() {
    log "Checking service logs for errors..."
    
    local error_count=$(journalctl -u "$SERVICE_NAME" --since "1 hour ago" --no-pager | grep -i "error\|exception\|traceback" | wc -l)
    
    if [[ $error_count -eq 0 ]]; then
        check_pass "No errors in service logs (last hour)"
    elif [[ $error_count -lt 5 ]]; then
        check_warning "Few errors in service logs (last hour): $error_count"
    else
        check_fail "Many errors in service logs (last hour): $error_count"
    fi
}

# Check disk space
check_disk_space() {
    log "Checking disk space..."
    
    local usage=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
    
    if [[ $usage -lt 80 ]]; then
        check_pass "Disk usage is healthy: ${usage}%"
    elif [[ $usage -lt 90 ]]; then
        check_warning "Disk usage is high: ${usage}%"
    else
        check_fail "Disk usage is critical: ${usage}%"
    fi
}

# Check memory usage
check_memory_usage() {
    log "Checking memory usage..."
    
    local mem_usage=$(free | awk 'NR==2{printf "%.0f", $3*100/$2}')
    
    if [[ $mem_usage -lt 80 ]]; then
        check_pass "Memory usage is healthy: ${mem_usage}%"
    elif [[ $mem_usage -lt 90 ]]; then
        check_warning "Memory usage is high: ${mem_usage}%"
    else
        check_fail "Memory usage is critical: ${mem_usage}%"
    fi
}

# Check network connectivity
check_network_connectivity() {
    log "Checking network connectivity..."
    
    # Check if we can reach external services
    local services=("google.com:80" "github.com:443")
    
    for service in "${services[@]}"; do
        local host=$(echo "$service" | cut -d: -f1)
        local port=$(echo "$service" | cut -d: -f2)
        
        if timeout 5 bash -c "</dev/tcp/$host/$port" 2>/dev/null; then
            check_pass "Network connectivity to $host:$port"
        else
            check_fail "Network connectivity to $host:$port"
        fi
    done
}

# Check Bitcoin Core connectivity
check_bitcoin_connectivity() {
    log "Checking Bitcoin Core connectivity..."
    
    # This would need to be adapted based on your Bitcoin Core setup
    # For now, we'll check if the port is open
    local bitcoind_host="${BITCOIND_HOST:-localhost}"
    local bitcoind_port="${BITCOIND_PORT:-8332}"
    
    if timeout 5 bash -c "</dev/tcp/$bitcoind_host/$bitcoind_port" 2>/dev/null; then
        check_pass "Bitcoin Core connectivity to $bitcoind_host:$bitcoind_port"
    else
        check_fail "Bitcoin Core connectivity to $bitcoind_host:$bitcoind_port"
    fi
}

# Check Electrs connectivity
check_electrs_connectivity() {
    log "Checking Electrs connectivity..."
    
    local electrs_host="${ELECTRS_HOST:-localhost}"
    local electrs_port="${ELECTRS_PORT:-50001}"
    
    if timeout 5 bash -c "</dev/tcp/$electrs_host/$electrs_port" 2>/dev/null; then
        check_pass "Electrs connectivity to $electrs_host:$electrs_port"
    else
        check_fail "Electrs connectivity to $electrs_host:$electrs_port"
    fi
}

# Check LNbits connectivity
check_lnbits_connectivity() {
    log "Checking LNbits connectivity..."
    
    local lnbits_host="${LNBITS_HOST:-localhost}"
    local lnbits_port="${LNBITS_PORT:-5000}"
    
    if timeout 5 bash -c "</dev/tcp/$lnbits_host/$lnbits_port" 2>/dev/null; then
        check_pass "LNbits connectivity to $lnbits_host:$lnbits_port"
    else
        check_fail "LNbits connectivity to $lnbits_host:$lnbits_port"
    fi
}

# Check log file permissions
check_log_permissions() {
    log "Checking log file permissions..."
    
    local log_dir="/var/log/falconer"
    
    if [[ -d "$log_dir" ]]; then
        if [[ -w "$log_dir" ]]; then
            check_pass "Log directory is writable: $log_dir"
        else
            check_fail "Log directory is not writable: $log_dir"
        fi
    else
        check_warning "Log directory does not exist: $log_dir"
    fi
}

# Check configuration files
check_configuration() {
    log "Checking configuration files..."
    
    local config_files=(
        "/opt/falconer/ops/systemd/falconer.env"
        "/opt/falconer/policy/prod.policy.json"
    )
    
    for config_file in "${config_files[@]}"; do
        if [[ -f "$config_file" ]]; then
            check_pass "Configuration file exists: $config_file"
            
            # Check if file is readable
            if [[ -r "$config_file" ]]; then
                check_pass "Configuration file is readable: $config_file"
            else
                check_fail "Configuration file is not readable: $config_file"
            fi
        else
            check_warning "Configuration file missing: $config_file"
        fi
    done
}

# Check Python environment
check_python_environment() {
    log "Checking Python environment..."
    
    local venv_path="/opt/falconer/venv"
    
    if [[ -d "$venv_path" ]]; then
        check_pass "Python virtual environment exists: $venv_path"
        
        # Check if falconer module can be imported
        if "$venv_path/bin/python" -c "import falconer" 2>/dev/null; then
            check_pass "Falconer module can be imported"
        else
            check_fail "Falconer module cannot be imported"
        fi
    else
        check_fail "Python virtual environment missing: $venv_path"
    fi
}

# Run application-specific health checks
check_application_health() {
    log "Running application-specific health checks..."
    
    # Try to run a simple falconer command
    if /opt/falconer/venv/bin/python -m falconer.cli status >/dev/null 2>&1; then
        check_pass "Falconer CLI status command works"
    else
        check_fail "Falconer CLI status command failed"
    fi
}

# Generate health report
generate_report() {
    log "Generating health check report..."
    
    local total_checks=$((CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARNING))
    
    echo
    echo "=========================================="
    echo "Falconer Health Check Report"
    echo "=========================================="
    echo "Total checks: $total_checks"
    echo "Passed: $CHECKS_PASSED"
    echo "Failed: $CHECKS_FAILED"
    echo "Warnings: $CHECKS_WARNING"
    echo "=========================================="
    
    if [[ $CHECKS_FAILED -eq 0 ]]; then
        if [[ $CHECKS_WARNING -eq 0 ]]; then
            echo -e "${GREEN}Overall Status: HEALTHY${NC}"
            exit 0
        else
            echo -e "${YELLOW}Overall Status: HEALTHY WITH WARNINGS${NC}"
            exit 0
        fi
    else
        echo -e "${RED}Overall Status: UNHEALTHY${NC}"
        exit 1
    fi
}

# Main function
main() {
    log "Starting Falconer health checks..."
    
    # Load environment variables if available
    if [[ -f "/opt/falconer/ops/systemd/falconer.env" ]]; then
        source "/opt/falconer/ops/systemd/falconer.env"
    fi
    
    # Run all health checks
    check_service_status
    check_service_logs
    check_disk_space
    check_memory_usage
    check_network_connectivity
    check_bitcoin_connectivity
    check_electrs_connectivity
    check_lnbits_connectivity
    check_log_permissions
    check_configuration
    check_python_environment
    check_application_health
    
    # Generate final report
    generate_report
}

# Run main function
main "$@"
