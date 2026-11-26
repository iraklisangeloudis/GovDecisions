variable "aws_profile" {
  description = "Local AWS profile used by Terraform."
  type        = string
  default     = "gov-decisions-terraform"
}

variable "ami_id" {
  description = "AMI of the existing EC2 instance; do not automatically select latest."
  type        = string
}

variable "subnet_id" {
  description = "Existing subnet; no new networking is created."
  type        = string
}

variable "vpc_id" {
  description = "Existing VPC."
  type        = string
}

variable "ssh_cidr" {
  description = "Your public IPv4 address with /32, matching the current SSH rule."
  type        = string
  validation {
    condition     = can(cidrnetmask(var.ssh_cidr)) && endswith(var.ssh_cidr, "/32")
    error_message = "SSH must be restricted to a single IPv4 address (/32)."
  }
}
