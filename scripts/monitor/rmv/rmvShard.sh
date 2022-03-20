#!/bin/bash

usage() {
  printf "Usage: ${0} -c <mongos-host:port> -r <replica-set-no>\n"
  exit 1
}

while getopts :c:r:s:h:p: flag
do
  case "${flag}" in
    c) msconn=${OPTARG} ;;
    r) rps=${OPTARG}    ;;
    : | \? | *) usage   ;;
  esac
done

[[ "$#" -ne 4 ]] && usage

shard="ShardReplSet${rps}"

# commands to local host
printf "Actions executed at localhost\n"

set -e
# remove shard from mongos and wait until completion
printf "> Draining from ${shard} "

isDraining() { mongo "${msconn}" --quiet --eval "db.adminCommand({ removeShard: \"${shard}\" }).ok"; }

until [[ "$(isDraining)" == "0" ]]
do
  printf "."
  sleep 20
done
printf "\n> Removed replica set ${shard} from shard cluster\n"
set +e
