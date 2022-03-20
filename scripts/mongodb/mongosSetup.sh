#!/bin/bash

usage() {
  echo "Usage: ${0} -d <base-directory> -s <server-no> -h <host> -p <port> -R <config-replica-set-no> -C <config-server-host:port>"
  exit 1
}

while getopts :d:s:h:p:R:C: flag
do
  case "${flag}" in
    d) dir=${OPTARG}  ;;
    s) svr=${OPTARG}  ;;
    h) host=${OPTARG} ;;
    p) port=${OPTARG} ;;
    R) Crps=${OPTARG} ;;
    C) Ccon=${OPTARG} ;;
    : | \? | *) usage ;;
  esac
done

[[ "$#" -ne 14 ]] && usage

path="${dir}/mongoss${svr}"
log_file="${path}/mongos.log"

mkdir -p ${path}
touch ${log_file}

(cat << END
systemLog:
  destination: file
  logAppend: true
  path: ${log_file}

net:
  ipv6: true
  port: ${port}
  bindIp: localhost,${host}

sharding:
  configDB: ConfigReplSet${Crps}/${Ccon}
END
) > "${path}/mongos.conf"
