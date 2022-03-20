#!/bin/bash

usage() {
  printf "Usage: ${0} -c <mongos-host:port> -r <replica_set_no> -s <replica_servers-h1:p1|h2:p2|...|hN:pN>\n"
  exit 1
}

while getopts :c:r:s: flag
do
  case "${flag}" in
    c) msconn=${OPTARG}  ;;
    r) rps=${OPTARG}     ;;
    s) servers=${OPTARG} ;;
    : | \? | *) usage   ;;
  esac
done

[[ "$#" -ne 6 ]] && usage

# read replica set members into an array
svrsArr=(${servers//|/ })

# secondary servers
secArr=(${svrsArr[@]:1})

# primary shard host and port array
read -r primHost primPort <<< "${svrsArr[0]//:/ }"
shard="ShardReplSet${rps}/${primHost}:${primPort}"

# commands to local host
printf "Actions executed at ${primHost}\n"

set -e
# initiate replica set from first as primary
ssh ${primHost} bash << EOSSH
# wait for mongod to start
printf "> Waiting primary mongod listening at port ${primPort} to start "
until [[ \$(lsof -ti tcp@localhost:${primPort}) ]]; do
  printf "."
  sleep 0.5
done
printf "\n"

set -e
# initiate replica set
mongo localhost:${primPort} --quiet --eval "rs.initiate()" > /dev/null
printf "> Initiated replica set\n"

# add replica set members
for s in ${secArr[@]}; do
  mongo localhost:${primPort} --quiet --eval "rs.add(\${s})" > /dev/null
  printf "> Added \${s} to replica set\n"
done
set +e
EOSSH


printf "\nActions executed at localhost\n"

# add new shard to cluster from mongos
mongo ${msconn} --quiet --eval "sh.addShard(\"${shard}\")" > /dev/null
printf "> Added replica set with primary ${shard} to cluster\n"
set +e
