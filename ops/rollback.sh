#!/bin/bash

# Falconer Rollback Script
# This script handles rollback of Falconer deployments

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DEPLOY_USER="falconer"
DEPLOY_DIR="/opt/falconer"
SERVICE_NAME="falconer"
BACKUP_DIR="/opt/falconer/backups"
LOG_FILE="/var/log/falconer/rollback.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

# List available backups
list_backups() {
    log "Available backups:"
    
    if [[ ! -d "$BACKUP_DIR" ]]; then
        warning "No backup directory found"
        return 1
    fi
    
    local backups=($(ls -1t "$BACKUP_DIR" | grep "^backup_" | head -10))
    
    if [[ ${#backups[@]} -eq 0 ]]; then
        warning "No backups found"
        return 1
    fi
    
    for i in "${!backups[@]}"; do
        local backup="${backups[$i]}"
        local backup_path="$BACKUP_DIR/$backup"
        local backup_date=$(stat -c %y "$backup_path" 2>/dev/null || stat -f %Sm "$backup_path" 2>/dev/null)
        echo "  $((i+1)). $backup ($backup_date)"
    done
    
    return 0
}

# Select backup interactively
select_backup() {
    list_backups
    
    if [[ $? -ne 0 ]]; then
        return 1
    fi
    
    echo
    read -p "Select backup to rollback to (1-10): " selection
    
    if ! [[ "$selection" =~ ^[0-9]+$ ]] || [[ "$selection" -lt 1 ]] || [[ "$selection" -gt 10 ]]; then
        error "Invalid selection"
    fi
    
    local backups=($(ls -1t "$BACKUP_DIR" | grep "^backup_" | head -10))
    local selected_backup="${backups[$((selection-1))]}"
    
    echo "$BACKUP_DIR/$selected_backup"
}

# Rollback to specific backup
rollback_to_backup() {
    local backup_path="$1"
    
    if [[ ! -d "$backup_path" ]]; then
        error "Backup path does not exist: $backup_path"
    fi
    
    log "Rolling back to backup: $backup_path"
    
    # Stop service
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log "Stopping $SERVICE_NAME service..."
        sudo systemctl stop "$SERVICE_NAME"
    fi
    
    # Create current state backup before rollback
    local current_backup="$BACKUP_DIR/current_before_rollback_$(date +'%Y%m%d_%H%M%S')"
    if [[ -d "$DEPLOY_DIR" ]]; then
        cp -r "$DEPLOY_DIR" "$current_backup"
        log "Current state backed up to: $current_backup"
    fi
    
    # Remove current deployment
    if [[ -d "$DEPLOY_DIR" ]]; then
        rm -rf "$DEPLOY_DIR"
    fi
    
    # Restore from backup
    cp -r "$backup_path" "$DEPLOY_DIR"
    
    # Set permissions
    sudo chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"
    chmod +x "$DEPLOY_DIR/ops"/*.sh
    
    # Update systemd service
    sudo cp "$DEPLOY_DIR/ops/systemd/falconer.service" "/etc/systemd/system/"
    sudo systemctl daemon-reload
    
    # Start service
    log "Starting $SERVICE_NAME service..."
    if ! sudo systemctl start "$SERVICE_NAME"; then
        error "Failed to start service after rollback"
    fi
    
    # Wait for service to be ready
    sleep 5
    
    # Check service status
    if ! systemctl is-active --quiet "$SERVICE_NAME"; then
        error "Service is not running after rollback"
    fi
    
    success "Rollback completed successfully!"
    log "Service status: $(systemctl is-active $SERVICE_NAME)"
}

# Rollback to latest backup
rollback_latest() {
    local latest_backup=$(ls -1t "$BACKUP_DIR" | grep "^backup_" | head -1)
    
    if [[ -z "$latest_backup" ]]; then
        error "No backups found for rollback"
    fi
    
    rollback_to_backup "$BACKUP_DIR/$latest_backup"
}

# Main rollback function
main() {
    log "Starting Falconer rollback..."
    
    # Check if running as correct user
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root. Please run as the deploy user."
    fi
    
    # Check if backup directory exists
    if [[ ! -d "$BACKUP_DIR" ]]; then
        error "Backup directory does not exist: $BACKUP_DIR"
    fi
    
    # Handle command line arguments
    case "${1:-interactive}" in
        "latest")
            rollback_latest
            ;;
        "list")
            list_backups
            ;;
        "interactive")
            local backup_path=$(select_backup)
            if [[ -n "$backup_path" ]]; then
                rollback_to_backup "$backup_path"
            fi
            ;;
        *)
            if [[ -d "$1" ]]; then
                rollback_to_backup "$1"
            else
                error "Invalid backup path: $1"
            fi
            ;;
    esac
}

# Run main function
main "$@"
