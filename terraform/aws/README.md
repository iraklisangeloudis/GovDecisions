# Existing AWS deployment

This directory manages the existing EC2 instance and its security group. It uses
local state here, separate from the legacy GCP configuration/state in the parent
folder. Always use `terraform -chdir=terraform/aws ...` from the repository root.
Do not run the legacy GCP configuration as part of AWS deployment.

The VPC, subnet and SSH key pair remain external resources. The root disk is
managed through the instance. Terraform does not configure Docker, Caddy,
DuckDNS, passwords or deploy application updates.

## Authentication

AWS CLI v2 is required. Sign in with the existing IAM user:

```powershell
aws login --profile gov-decisions
```

The local `gov-decisions-terraform` profile uses `credential_process` to reuse
this temporary session. Its configuration is in the user's AWS config, outside
this repository. No static AWS access keys are required. To configure it on a
new Windows computer (adjust the executable path if needed):

```powershell
$awsCliPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$awsCliShort = (New-Object -ComObject Scripting.FileSystemObject).GetFile($awsCliPath).ShortPath
& $awsCliPath configure set credential_process "$awsCliShort configure export-credentials --profile gov-decisions --format process" --profile gov-decisions-terraform
aws configure set region us-east-1 --profile gov-decisions-terraform
```

Use the full path to aws.exe if it is not available in PATH yet.

## Current status

On 2026-11-26, both resources were imported into local state with `terraform import`.
The subsequent plan reported **No changes**. No cloud resources were modified.
Do not repeat setup/import on this computer unless recovering missing state.

## Review the existing resources

Copy `terraform.tfvars.example` to `terraform.tfvars` and fill in actual existing
AMI/subnet/VPC IDs and the SSH source IPv4 /32. The local file is already filled
for the current deployment and is gitignored.

```powershell
terraform -chdir=terraform/aws init
terraform -chdir=terraform/aws validate
terraform -chdir=terraform/aws plan
```

`imports.tf` identifies the two existing resources. The first plan must show
**2 to import, 0 to add, 0 to change, 0 to destroy** before importing. Do not apply
if it proposes replacement or other changes. Review unexpected differences first.
After explicit approval, applying that reviewed import plan records resources in
local state; it should not change the running infrastructure. After import, a new
plan should show no changes. Import blocks can remain in the configuration.

Both resources have `prevent_destroy`. This is a guard against accidental
replacement/deletion while the resource blocks remain; it is not a backup.
Keep `terraform.tfstate` and its backup safe and outside Git. Do not discard the
AWS state or mix it with the old GCP state. Saved plans may contain sensitive
values: keep them local too.

Changing an AMI/subnet can replace an EC2 instance. Changing `ssh_cidr` changes
SSH access. Docker/Caddy files, certificates and the DuckDNS token live on the
current server's disk; this configuration alone does not rebuild those services.
