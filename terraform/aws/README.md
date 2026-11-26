# AWS infrastructure

Terraform manages the EC2, security group and GitHub/Systems Manager deployment
permissions in `us-east-1`. Requires Terraform 1.9+ and AWS CLI v2.

## Sign in

```powershell
aws login --profile gov-decisions
```

On this computer, Terraform uses the configured `gov-decisions-terraform`
profile to reuse that temporary login. No permanent access keys are needed.

For a new Windows computer, configure that profile once:

```powershell
$awsCliPath = "C:\Program Files\Amazon\AWSCLIV2\aws.exe"
$awsCliShort = (New-Object -ComObject Scripting.FileSystemObject).GetFile($awsCliPath).ShortPath
& $awsCliPath configure set credential_process "$awsCliShort configure export-credentials --profile gov-decisions --format process" --profile gov-decisions-terraform
& $awsCliPath configure set region us-east-1 --profile gov-decisions-terraform
```

## Review infrastructure changes

Run from the repository root. On a new computer, copy `terraform.tfvars.example`
to `terraform.tfvars`, fill in the existing resource values and restore your
Terraform state backup before planning changes.

```powershell
terraform -chdir=terraform/aws init
terraform -chdir=terraform/aws validate
terraform -chdir=terraform/aws plan
```

Review the plan before running `terraform -chdir=terraform/aws apply`.
The deployed resources are already imported. Keep the local `terraform.tfstate`
and backups safe and outside Git; they are needed to manage the existing setup.

## Deploy the application

Every push to `main` builds/tests and deploys that commit through GitHub Actions.
Pull requests run checks only. Manual deployment is also available:
**Actions → Deploy to AWS → Run workflow → main**.

The EC2 must be running and its Systems Manager agent Online. GitHub connects
through OIDC with temporary credentials; no SSH key is stored in GitHub.
The deployment retains the previous container and restores it if startup fails.
Replacing the app container causes a brief interruption.
