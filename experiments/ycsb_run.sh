#!/bin/bash

usage() {
  echo "Usage: ${0} -t <threads> -o <operations> -p <throughput> -f <outdir>"
  exit 1
}

while getopts :t:o:p:f: flag
do
  case "${flag}" in
    t) threads=${OPTARG} ;;
    o) ops=${OPTARG}     ;;
    p) target=${OPTARG}  ;;
    f) outdir=${OPTARG}  ;;
    : | \? | *) usage    ;;
  esac
done

[[ "$#" -ne 8 ]] && usage

ycsb_dir="/home/user/ycsb/ycsb-0.17.0"
outfile="${outdir}/ts_${threads}_${ops}_${target}_abcf"

touch "${outfile}"
cd "${ycsb_dir}"

for w in a b c f
do
  ./bin/ycsb run mongodb -s -P workloads/workload${w} \
  -threads "${threads}" -p operationcount="${ops}" -target "${target}" \
  -p mongodb.url="mongodb://localhost:27015/ycsba" \
  | grep "\[OVERALL\], Throughput(ops/sec)" >> "${outfile}"
done
