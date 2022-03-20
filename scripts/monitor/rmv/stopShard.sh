#!/bin/bash

usage() {
  printf "Usage: ${0} -r <replica-set-no> -s <server-no> -h <host> -p <port>\n"
  exit 1
}

while getopts :c:r:s:h:p: flag
do
  case "${flag}" in
    r) rps=${OPTARG}    ;;
    s) svr=${OPTARG}    ;;
    h) host=${OPTARG}   ;;
    p) port=${OPTARG}   ;;
    : | \? | *) usage   ;;
  esac
done

[[ "$#" -ne 8 ]] && usage

# remote host
serverName="shardr${rps}s${svr}"
gmondPys="/usr/local/lib64/ganglia/python_modules/${serverName}.py*"

# commands to remote host
printf "Actions executed at ${host}\n"

ssh ${host} bash << EOSSH
set -e
# terminate mongod process through mongo
mongo localhost:${port} --quiet --eval "db.getSiblingDB('admin').shutdownServer()" > /dev/null
printf "> Terminated mongod process\n"

# rm gmond py module files
sudo rm ${gmondPys}
printf "> Removed ${gmondPys}\n"

# delete ufw rule (so is denied by default)
sudo ufw delete allow ${port} > /dev/null
printf "> Deleted ufw rule 'allow from anywhere to ${port}'\n"
set +e
EOSSH
