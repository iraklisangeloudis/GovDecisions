"""Send a deployment to SSM and wait for its actual result (AWS CLI required)."""
import base64
import json
import os
from pathlib import Path
import subprocess
import time


def aws(*args):
    result = subprocess.run(
        ["aws", "ssm", *args, "--output", "json", "--no-cli-pager"],
        check=True, capture_output=True, text=True,
    )
    return json.loads(result.stdout)


def main():
    instance = os.environ["INSTANCE_ID"]
    revision = os.environ["GITHUB_SHA"]
    if len(revision) != 40 or any(c not in "0123456789abcdef" for c in revision):
        raise ValueError("Invalid commit SHA")
    nodes = aws("describe-instance-information", "--filters", f"Key=InstanceIds,Values={instance}")
    if not any(node["PingStatus"] == "Online" for node in nodes["InstanceInformationList"]):
        raise RuntimeError("EC2 is not online in Systems Manager. Start the instance and check its SSM agent/role.")
    encoded = base64.b64encode(Path("scripts/deploy-ec2.sh").read_bytes()).decode()
    parameters = {
        "commands": [f"printf '%s' '{encoded}' | base64 -d | bash -s -- {revision}"],
        "executionTimeout": ["1800"],
    }
    response = aws("send-command", "--instance-ids", instance,
                   "--document-name", "AWS-RunShellScript", "--timeout-seconds", "60",
                   "--comment", f"Deploy GovDecisions {revision}",
                   "--parameters", json.dumps(parameters))
    command = response["Command"]["CommandId"]
    print(f"SSM command: {command}", flush=True)
    deadline = time.monotonic() + 1900
    while time.monotonic() < deadline:
        time.sleep(10)
        try:
            result = aws("get-command-invocation", "--command-id", command, "--instance-id", instance)
        except subprocess.CalledProcessError as error:
            if "InvocationDoesNotExist" in error.stderr:
                continue
            raise
        if result["Status"] in {"Pending", "InProgress", "Delayed", "Cancelling"}:
            continue
        print(result.get("StandardOutputContent", ""))
        print(result.get("StandardErrorContent", ""))
        if result["Status"] != "Success" or result.get("ResponseCode") != 0:
            raise RuntimeError(f"Deployment failed: {result['Status']}")
        return
    raise TimeoutError(f"SSM command {command} is still running; check it before starting another deployment.")


if __name__ == "__main__":
    main()
