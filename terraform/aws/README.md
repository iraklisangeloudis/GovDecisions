# Existing AWS deployment

This directory manages the existing EC2 instance and its security group. It uses
local state here, separate from any legacy GCP state in the parent folder.
The old GCP configuration and commented deployment job have been removed.
Always use `terraform -chdir=terraform/aws ...` from the repository root.
Existing GCP cloud resources have not been inspected or deleted.

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

## Deployment from GitHub Actions

`deployment.tf` adds a GitHub OIDC provider, a deployment role restricted to
this repository's `main` branch and this EC2, plus an instance role/profile for
Systems Manager. It attaches AmazonSSMManagedInstanceCore to the EC2 role.
No SSH private key or permanent AWS credentials are stored in GitHub.

These additions were applied on 2026-11-26: six IAM/OIDC resources were created
and the existing EC2 instance profile was updated in place. The subsequent
plan reported No changes. No security group ports changed.
The first manual GitHub deployment succeeded on 2026-11-26 for commit 00880dc.
Tests, OIDC authentication and the SSM deployment all passed. The running image
was verified to match the commit; the app returned 200 and public HTTPS returned
401 without credentials.

The SSM agent was verified active/enabled and Online after a restart on 2026-11-26.
It must remain running on the EC2 and appear Online in Systems
Manager. If needed, check from the existing SSH connection:

```bash
sudo systemctl status amazon-ssm-agent --no-pager
sudo systemctl enable --now amazon-ssm-agent
```

Every push to main runs the reusable Docker CI workflow once and deploys that
commit only if its build/tests pass. Pull requests run CI without deployment.
Manual deployment remains available via GitHub -> Actions -> Deploy to AWS ->
Run workflow -> main.
The EC2 must already be running; the workflow will not start it automatically.
The current repository must remain publicly cloneable by the EC2. A private
repository requires a separate read authentication setup.

The workflow builds/tests the pushed or manually selected main-branch commit, authenticates with OIDC,
then runs `scripts/deploy-ec2.sh` through SSM and checks the command's result.
The remote script builds that exact commit before stopping the app, keeps the
previous container, and restores it if startup or its HTTP check fails. There
is a brief interruption during container replacement. Caddy, certificates,
DuckDNS and app secrets are not changed. A single deployment runs at a time.
The deployment role can execute shell commands as root on this one instance;
protect write access to main and review deployment script changes accordingly.

Initial tests cover workflow syntax, SSM polling/failure handling and shell
syntax. The first real GitHub deployment has also been verified successfully. A successful HTTP check tests
the app homepage, not the availability of the upstream Diavgeia API.
