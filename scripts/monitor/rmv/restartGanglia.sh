#!/bin/bash

usage() {
  printf "Usage: ${0} -h <shard_hosts-h1|h2|...|hN>\n"
  exit 1
}

while getopts :h: flag
do
  case "${flag}" in
    h) hosts=${OPTARG}  ;;
    : | \? | *) usage   ;;
  esac
done

[[ "$#" -ne 2 ]] && usage

# read shard hosts into an array
hostsArr=(${hosts//|/ })

for i in 1 2; do
  set -e
  # commands to local host
  [[ i -eq 2 ]] && printf "Actions executed at localhost\n"

  # restart gmetad
  sudo systemctl restart gmetad
  [[ i -eq 2 ]] && printf "> Restarted gmetad\n"

  # restart gmond
  sudo systemctl restart gmond
  [[ i -eq 2 ]] && printf "> Restarted gmond\n"

  # commands to remote hosts
  [[ i -eq 2 ]] && printf "\nActions executed at remote hosts\n"

  for host in "${hostsArr[@]}"; do
    set -e
    ssh "${host}" "sudo systemctl restart gmond"
    [[ i -eq 2 ]] && printf "> Restarted gmond at ${host}\n"
    set +e
  done
  set +e
done
