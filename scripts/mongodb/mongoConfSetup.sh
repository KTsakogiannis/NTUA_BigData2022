#!/bin/bash

usage() {
  echo "Usage: ${0} -d <base-directory> -r <replica-set-no> -s <server-no> -h <host> -p <port>"
  exit 1
}

while getopts :d:r:s:h:p: flag
do
  case "${flag}" in
    d) dir=${OPTARG}  ;;
    r) rps=${OPTARG}  ;;
    s) svr=${OPTARG}  ;;
    h) host=${OPTARG} ;;
    p) port=${OPTARG} ;;
    : | \? | *) usage ;;
  esac
done

[[ "$#" -ne 10 ]] && usage

path="${dir}/confr${rps}/confr${rps}s${svr}"
db_dir="${path}/db"
log_file="${path}/conf.log"

mkdir -p ${db_dir}
touch ${log_file}

(cat << END
storage:
  dbPath: ${db_dir}
  journal:
    enabled: true

systemLog:
  destination: file
  logAppend: true
  path: ${log_file}

net:
  ipv6: true
  port: ${port}
  bindIp: localhost,${host}

sharding:
  clusterRole: configsvr

replication:
  replSetName: ConfigReplSet${rps}
END
) > "${path}/mongoConf.conf"
