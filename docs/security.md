# Falconer Security Guide

This guide covers security best practices, threat models, and recommendations for running Falconer safely in production environments.

## Table of Contents

- [Security Model Overview](#security-model-overview)
- [Threat Model](#threat-model)
- [Key Management](#key-management)
- [Network Security](#network-security)
- [Operational Security](#operational-security)
- [Policy Configuration](#policy-configuration)
- [Monitoring & Incident Response](#monitoring--incident-response)
- [Compliance & Auditing](#compliance--auditing)
- [Security Checklist](#security-checklist)

## Security Model Overview

Falconer implements a **defense-in-depth** security model with multiple layers of protection:

### Core Security Principles

1. **🔐 No Hot Wallets**: Private keys never stored on internet-connected devices
2. **🛡️ Air-gapped Signing**: All transactions require manual PSBT signing
3. **📋 Policy Enforcement**: Every action validated against configurable rules
4. **👤 Human Oversight**: Critical decisions require human approval
5. **📊 Audit Trails**: Complete logging of all operations and decisions

### Security Layers

```
┌─────────────────────────────────────────────────────────────┐
│                    Human Approval Layer                     │
│  • Funding proposals • Emergency stops • Policy changes     │
├─────────────────────────────────────────────────────────────┤
│                    Policy Engine Layer                      │
│  • Spending limits • Risk controls • Time restrictions      │
├─────────────────────────────────────────────────────────────┤
│                    Application Layer                        │
│  • Authentication • Authorization • Input validation        │
├─────────────────────────────────────────────────────────────┤
│                    Network Layer                            │
│  • TLS encryption • Firewall rules • VPN access             │
├─────────────────────────────────────────────────────────────┤
│                    Infrastructure Layer                     │
│  • Secure hosting • Backup systems • Monitoring             │
└─────────────────────────────────────────────────────────────┘
```

## Threat Model

### Threat Categories

#### 1. **External Threats**
- **Malicious Actors**: Hackers attempting to steal funds or disrupt operations
- **Network Attacks**: Man-in-the-middle, DDoS, or network interception
- **Supply Chain**: Compromised dependencies or third-party services
- **Social Engineering**: Phishing, impersonation, or social manipulation

#### 2. **Internal Threats**
- **Insider Access**: Compromised credentials or malicious insiders
- **Configuration Errors**: Misconfigured policies or permissions
- **Software Bugs**: Vulnerabilities in Falconer or dependencies
- **Operational Mistakes**: Human error in configuration or operations

#### 3. **Systemic Threats**
- **Market Manipulation**: Attempts to influence AI decisions
- **Infrastructure Failure**: Hardware, network, or service outages
- **Regulatory Changes**: Legal or compliance requirement changes
- **Technology Obsolescence**: Deprecated protocols or standards

### Risk Assessment Matrix

| Threat | Likelihood | Impact | Risk Level | Mitigation |
|--------|------------|--------|------------|------------|
| Private key theft | Low | Critical | High | Air-gapped signing, hardware wallets |
| Network interception | Medium | High | High | TLS encryption, VPN, firewall |
| AI manipulation | Medium | Medium | Medium | Policy limits, human oversight |
| Configuration errors | High | Medium | Medium | Automated testing, validation |
| Infrastructure failure | Medium | High | Medium | Redundancy, monitoring, backups |

## Key Management

### Private Key Security

#### **Never Store Private Keys Online**
```bash
# ❌ NEVER DO THIS
echo "private_key_here" > ~/.falconer/keys.txt

# ✅ CORRECT APPROACH
# Use hardware wallets or air-gapped devices only
```

#### **Hardware Wallet Integration**
Falconer supports hardware wallet integration for maximum security:

```python
# Example: Ledger integration
from falconer.wallet.hardware import LedgerWallet

wallet = LedgerWallet()
# Private keys never leave the hardware device
```

#### **Multi-signature Setup**
For additional security, configure multi-signature wallets:

```bash
# 2-of-3 multisig configuration
FALCONER_MULTISIG_THRESHOLD=2
FALCONER_MULTISIG_TOTAL=3
FALCONER_MULTISIG_KEYS="key1,key2,key3"
```

### PSBT Workflow Security

#### **Air-gapped Signing Process**
1. **Generate PSBT**: Falconer creates Partially Signed Bitcoin Transaction
2. **Transfer to Air-gapped Device**: Use QR codes or USB transfer
3. **Sign Offline**: Sign transaction on air-gapped device
4. **Broadcast**: Transfer signed transaction back to online device

```bash
# Generate PSBT for funding proposal
falconer proposals approve <proposal-id> --generate-psbt

# Transfer PSBT to air-gapped device (QR code)
# Sign on air-gapped device
# Transfer signed transaction back
falconer proposals broadcast <signed-tx>
```

#### **PSBT Validation**
Always validate PSBTs before signing:

```python
# Validate PSBT structure and amounts
def validate_psbt(psbt_data):
    # Check input/output amounts
    # Verify destination addresses
    # Validate fee rates
    # Confirm policy compliance
    pass
```

## Network Security

### TLS/SSL Configuration

#### **Strong TLS Configuration**
```bash
# Use TLS 1.3 with strong cipher suites
TLS_VERSION=1.3
TLS_CIPHERS="TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256"

# Certificate configuration
SSL_CERT_PATH=/path/to/cert.pem
SSL_KEY_PATH=/path/to/private.key
SSL_CA_PATH=/path/to/ca.pem
```

#### **Certificate Management**
- Use valid SSL certificates from trusted CAs
- Implement certificate pinning for critical endpoints
- Regular certificate rotation and monitoring
- Use Let's Encrypt for automated certificate management

### Firewall Configuration

#### **Restrictive Firewall Rules**
```bash
# Allow only necessary ports
# Bitcoin RPC: 8332 (or custom port)
# LNbits: 443 (HTTPS)
# Falconer API: 8080 (custom port)
# SSH: 22 (restrict to specific IPs)

# Example iptables rules
iptables -A INPUT -p tcp --dport 8332 -s 127.0.0.1 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
iptables -A INPUT -p tcp --dport 8080 -s 10.0.0.0/8 -j ACCEPT
iptables -A INPUT -p tcp --dport 22 -s YOUR_IP -j ACCEPT
iptables -A INPUT -j DROP
```

### VPN Access
For remote access, use VPN instead of direct SSH:

```bash
# Configure WireGuard VPN
[Interface]
PrivateKey = your_private_key
Address = 10.0.0.2/24

[Peer]
PublicKey = server_public_key
Endpoint = your-server.com:51820
AllowedIPs = 10.0.0.0/24
```

## Operational Security

### Access Control

#### **Principle of Least Privilege**
```bash
# Create dedicated user for Falconer
sudo useradd -r -s /bin/false falconer
sudo usermod -aG bitcoin falconer

# Restrict file permissions
chmod 600 /etc/falconer/.env
chown falconer:falconer /etc/falconer/.env
```

#### **API Key Management**
```bash
# Use strong, unique API keys
LNBITS_API_KEY=$(openssl rand -hex 32)
N8N_SHARED_SECRET=$(openssl rand -hex 32)

# Rotate keys regularly
# Store keys in secure key management system
# Never commit keys to version control
```

### System Hardening

#### **Operating System Security**
```bash
# Disable unnecessary services
systemctl disable bluetooth
systemctl disable cups
systemctl disable avahi-daemon

# Configure automatic security updates
apt install unattended-upgrades
dpkg-reconfigure -plow unattended-upgrades

# Enable firewall
ufw enable
ufw default deny incoming
ufw default allow outgoing
```

#### **Process Isolation**
```bash
# Run Falconer in container for isolation
docker run -d \
  --name falconer \
  --restart unless-stopped \
  --cap-drop ALL \
  --cap-add NET_BIND_SERVICE \
  -v /etc/falconer:/config:ro \
  falconer:latest
```

### Backup Security

#### **Encrypted Backups**
```bash
# Create encrypted backups
tar -czf - /var/lib/falconer | \
  gpg --symmetric --cipher-algo AES256 --output falconer-backup-$(date +%Y%m%d).tar.gz.gpg

# Store backups in multiple locations
# Test backup restoration regularly
# Use different encryption keys for different backup locations
```

## Policy Configuration

### Spending Limits

#### **Conservative Policy Configuration**
```bash
# Start with very conservative limits
MAX_DAILY_SPEND_SATS=10000        # $5-10 per day
MAX_SINGLE_TX_SATS=5000           # $2.50-5 per transaction
MAX_DAILY_PROPOSALS=2             # Maximum 2 funding proposals per day
FUNDING_PROPOSAL_THRESHOLD_SATS=5000  # Request funding when below $2.50
```

#### **Time-based Restrictions**
```bash
# Only allow operations during business hours
ALLOWED_HOURS_START=9
ALLOWED_HOURS_END=17
ALLOWED_TIMEZONE=UTC

# Weekend restrictions
WEEKEND_OPERATIONS=false
```

### Risk Controls

#### **Market Risk Limits**
```bash
# Maximum fee rate for transactions
MAX_FEE_RATE_SATS_PER_VBYTE=50

# Minimum confirmation requirements
MIN_CONFIRMATIONS=3

# Maximum mempool congestion threshold
MAX_MEMPOOL_CONGESTION_PERCENT=80
```

#### **AI Decision Controls**
```bash
# Require human approval for large amounts
HUMAN_APPROVAL_THRESHOLD_SATS=10000

# Limit AI decision frequency
AI_DECISION_INTERVAL_SECONDS=300

# Require confirmation for new strategies
AUTO_APPROVE_NEW_STRATEGIES=false
```

## Monitoring & Incident Response

### Security Monitoring

#### **Log Analysis**
```bash
# Monitor for suspicious activity
tail -f /var/log/falconer/security.log | grep -E "(FAILED|ERROR|UNAUTHORIZED)"

# Set up log alerts
# Monitor for:
# - Failed authentication attempts
# - Policy violations
# - Unusual spending patterns
# - Network anomalies
```

#### **Real-time Alerts**
```bash
# Configure alerts for critical events
ALERT_ON_POLICY_VIOLATION=true
ALERT_ON_LARGE_TRANSACTION=true
ALERT_ON_FUNDING_PROPOSAL=true
ALERT_ON_SYSTEM_ERROR=true

# Notification channels
ALERT_EMAIL=security@yourdomain.com
ALERT_SLACK_WEBHOOK=https://hooks.slack.com/...
ALERT_SMS_NUMBER=+1234567890
```

### Incident Response Plan

#### **Security Incident Response**
1. **Detection**: Automated monitoring detects security event
2. **Assessment**: Determine severity and impact
3. **Containment**: Isolate affected systems
4. **Investigation**: Analyze logs and system state
5. **Recovery**: Restore normal operations
6. **Post-mortem**: Document lessons learned

#### **Emergency Procedures**
```bash
# Emergency stop script
#!/bin/bash
# emergency-stop.sh

echo "EMERGENCY STOP INITIATED" | logger -t falconer
systemctl stop falconer
systemctl stop bitcoin
# Notify administrators
# Preserve logs and system state
```

#### **Recovery Procedures**
```bash
# System recovery checklist
# 1. Verify system integrity
# 2. Check backup integrity
# 3. Restore from clean backup if needed
# 4. Update all security patches
# 5. Rotate all credentials
# 6. Reconfigure policies
# 7. Test all functionality
# 8. Resume operations with increased monitoring
```

## Compliance & Auditing

### Audit Trail Requirements

#### **Comprehensive Logging**
```python
# Log all critical operations
logger.info("Transaction initiated", 
    amount_sats=amount,
    destination=address,
    policy_check=passed,
    user_id=user_id,
    timestamp=datetime.utcnow().isoformat()
)
```

#### **Log Retention Policy**
```bash
# Retain logs for compliance period
LOG_RETENTION_DAYS=2555  # 7 years
LOG_ROTATION_SIZE=100M
LOG_COMPRESSION=true
LOG_ENCRYPTION=true
```

### Compliance Frameworks

#### **Financial Regulations**
- **KYC/AML**: Implement customer identification procedures
- **Transaction Reporting**: Maintain detailed transaction records
- **Audit Requirements**: Support external audit processes
- **Data Protection**: Comply with GDPR, CCPA, and other privacy laws

#### **Security Standards**
- **ISO 27001**: Information security management
- **SOC 2**: Security, availability, and confidentiality
- **PCI DSS**: Payment card industry standards (if applicable)

## Security Checklist

### Pre-deployment Security Checklist

#### **Infrastructure Security**
- [ ] Server hardened with security updates
- [ ] Firewall configured with restrictive rules
- [ ] VPN access configured for remote management
- [ ] SSL/TLS certificates properly configured
- [ ] Backup systems tested and verified
- [ ] Monitoring and alerting systems active

#### **Application Security**
- [ ] All default passwords changed
- [ ] API keys generated with strong entropy
- [ ] Environment variables properly secured
- [ ] Policy limits configured conservatively
- [ ] Logging configured for security events
- [ ] Error handling prevents information leakage

#### **Operational Security**
- [ ] Access controls implemented (least privilege)
- [ ] Incident response procedures documented
- [ ] Security monitoring active
- [ ] Regular security updates scheduled
- [ ] Backup and recovery procedures tested
- [ ] Staff trained on security procedures

### Ongoing Security Maintenance

#### **Daily Tasks**
- [ ] Review security logs for anomalies
- [ ] Check system resource usage
- [ ] Verify backup completion
- [ ] Monitor for policy violations
- [ ] Review funding proposal approvals

#### **Weekly Tasks**
- [ ] Update security patches
- [ ] Review access logs
- [ ] Test backup restoration
- [ ] Analyze spending patterns
- [ ] Review AI decision history

#### **Monthly Tasks**
- [ ] Rotate API keys and passwords
- [ ] Review and update policies
- [ ] Conduct security assessment
- [ ] Update incident response procedures
- [ ] Review compliance requirements

### Emergency Contacts

```bash
# Emergency contact information
SECURITY_EMAIL=security@yourdomain.com
SECURITY_PHONE=+1234567890
BITCOIN_EXPERT=bitcoin-expert@yourdomain.com
LEGAL_COUNSEL=legal@yourdomain.com
```

## Security Resources

### External Resources
- [Bitcoin Security Best Practices](https://bitcoin.org/en/secure-your-wallet)
- [Hardware Wallet Security](https://blog.ledger.com/security/)
- [Network Security Guidelines](https://www.nist.gov/cyberframework)
- [Incident Response Planning](https://www.sans.org/white-papers/incident-response/)

### Falconer-Specific Resources
- [Policy Configuration Guide](policy-config.md)
- [Hardware Wallet Integration](hardware-wallets.md)
- [Network Setup Guide](network-setup.md)
- [Incident Response Playbook](incident-response.md)

---

**Remember: Security is an ongoing process, not a one-time setup. Regular review, testing, and updates are essential for maintaining a secure Falconer deployment.**
