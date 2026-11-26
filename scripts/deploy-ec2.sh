#!/usr/bin/env bash
# Run as root on the existing EC2 through Systems Manager.
set -Eeuo pipefail
revision=${1:?Expected a commit SHA}
[[ "$revision" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid commit SHA" >&2; exit 1; }
exec 9>/var/lock/gov-decisions-deploy.lock
flock -n 9 || { echo "Another deployment is running" >&2; exit 1; }

repo=/home/ec2-user/GovDecisions
runuser -u ec2-user -- git -C "$repo" fetch origin main
runuser -u ec2-user -- git -C "$repo" merge-base --is-ancestor "$revision" origin/main
build_dir=$(mktemp -d /tmp/gov-decisions-build.XXXXXX)
trap 'rm -rf -- "$build_dir"' EXIT
runuser -u ec2-user -- git -C "$repo" archive "$revision" | tar -x -C "$build_dir"
# Finish building before stopping the working application.
docker build -t "gov-decisions:$revision" "$build_dir"

docker inspect gov-decisions >/dev/null
if docker container inspect gov-decisions-previous >/dev/null 2>&1; then
    obsolete_image=$(docker inspect --format '{{.Config.Image}}' gov-decisions-previous)
    docker rm gov-decisions-previous
    if [[ "$obsolete_image" =~ ^gov-decisions:[0-9a-f]{40}$ ]]; then
        docker image rm "$obsolete_image" || true
    fi
fi
docker stop gov-decisions
if ! docker rename gov-decisions gov-decisions-previous; then
    docker start gov-decisions
    exit 1
fi

rollback() {
    echo "Deployment failed; restoring previous container" >&2
    docker logs --tail 30 gov-decisions 2>/dev/null || true
    docker rm -f gov-decisions 2>/dev/null || true
    docker rename gov-decisions-previous gov-decisions
    docker start gov-decisions
}

if ! docker run -d --name gov-decisions --restart unless-stopped \
    -p 127.0.0.1:8080:8080 \
    --log-opt max-size=10m --log-opt max-file=3 \
    "gov-decisions:$revision"; then
    rollback
    exit 1
fi

for attempt in $(seq 1 30); do
    if curl --fail --silent --max-time 3 http://127.0.0.1:8080/ >/dev/null; then
        docker tag "gov-decisions:$revision" gov-decisions:latest
        echo "Deployed $revision successfully"
        exit 0
    fi
    sleep 2
done
rollback
exit 1
