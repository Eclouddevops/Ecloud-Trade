terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  required_version = ">= 1.5.0"
}

provider "aws" {
  region = "us-east-1"
}

# VPC - use default
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

# Security Group
resource "aws_security_group" "ecloud_trade" {
  name        = "ecloud-trade-sg"
  description = "Security group for Ecloud-Trade app"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "Flask"
    from_port   = 5000
    to_port     = 5000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ecloud-trade-sg"
  }
}

# Key Pair
resource "aws_key_pair" "ecloud_trade" {
  key_name   = "ecloud-trade-key"
  public_key = file("${path.module}/ecloud-trade-key.pub")
}

# EC2 Instance
resource "aws_instance" "ecloud_trade" {
  ami                    = "ami-0c7217cdde317cfec" # Ubuntu 22.04 LTS us-east-1
  instance_type          = "t2.medium"
  key_name               = aws_key_pair.ecloud_trade.key_name
  vpc_security_group_ids = [aws_security_group.ecloud_trade.id]
  subnet_id              = data.aws_subnets.default.ids[0]

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data = file("${path.module}/user_data.sh")

  tags = {
    Name        = "ecloud-trade"
    Project     = "Ecloud-Trade"
    Environment = "production"
  }
}

# Elastic IP
resource "aws_eip" "ecloud_trade" {
  instance = aws_instance.ecloud_trade.id
  domain   = "vpc"

  tags = {
    Name = "ecloud-trade-eip"
  }
}

# Outputs
output "public_ip" {
  value       = aws_eip.ecloud_trade.public_ip
  description = "Public IP of the EC2 instance"
}

output "ssh_command" {
  value       = "ssh -i ecloud-trade-key ubuntu@${aws_eip.ecloud_trade.public_ip}"
  description = "SSH command to connect"
}

output "app_url" {
  value       = "http://${aws_eip.ecloud_trade.public_ip}"
  description = "App URL"
}

output "cloudflare_dns" {
  value       = "Add A record: ecloud-trade → ${aws_eip.ecloud_trade.public_ip}"
  description = "Cloudflare DNS record to add"
}
