# Terraform - EC2 Deployment

## Prerequisites
1. AWS CLI configured: `aws configure` (use account 226563001214)
2. Terraform installed: https://terraform.io/downloads

## Setup

### Generate SSH key pair:
```bash
ssh-keygen -t rsa -b 4096 -f ecloud-trade-key -N ""
```
This creates `ecloud-trade-key` (private) and `ecloud-trade-key.pub` (public).

### Deploy:
```bash
cd terraform
terraform init
terraform plan
terraform apply
```

### Output will show:
- Public IP
- SSH command
- Cloudflare DNS record to add

## Destroy:
```bash
terraform destroy
```
