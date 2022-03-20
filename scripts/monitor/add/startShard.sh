#!/bin/bash

usage() {
  printf "Usage: ${0} -m <scripts-path> -d <base-directory> -r <replica-set-no> -s <server-no> -h <host> -p <port>\n"
  exit 1
}

while getopts :m:c:d:r:s:h:p: flag
do
  case "${flag}" in
    m) spath=${OPTARG}  ;;
    d) dir=${OPTARG}    ;;
    r) rps=${OPTARG}    ;;
    s) svr=${OPTARG}    ;;
    h) host=${OPTARG}   ;;
    p) port=${OPTARG}   ;;
    : | \? | *) usage   ;;
  esac
done

[[ "$#" -ne 12 ]] && usage

# local host
mongoShardSetup="${spath}/mongodb/mongoShardSetup.sh"
modulePy="${spath}/ganglia/mongodb.py"
modulePyconf="${spath}/ganglia/mongodb.pyconf.in"

# remote host
serverName="shardr${rps}s${svr}"
mongoShardDir="${dir}/shardr${rps}/${serverName}"
mongoShardDbDir="${mongoShardDir}/db"
mongoShardConfig="${mongoShardDir}/mongoShard.conf"
mongoShardPyConf="${mongoShardDir}/${serverName}.pyconf"
mongoShardPy="${mongoShardDir}/${serverName}.py"
gmondPyConf="/usr/local/etc/conf.d/${serverName}.pyconf"
gmondPy="/usr/local/lib64/ganglia/python_modules/${serverName}.py"


# commands to remote host
printf "Actions executed at ${host}\n"

# setup mongodb dirs if they do not exist
if ssh ${host} "! test -d ${mongoShardDir}"; then
  ssh ${host} "bash -s" -- < ${mongoShardSetup} -d ${dir} -r ${rps} -s ${svr} -h ${host} -p ${port} && \
  printf "> Created ${mongoShardDir}\n"
fi

# setup .pyconf and .py in mongoShard dir if they do not exist
if ssh ${host} "! test -f ${mongoShardPyConf}"; then
  sed "s|<PORT>|${port}|g; s|<SERVER_NAME>|${serverName}|g" ${modulePyconf} | \
  ssh ${host} "bash -c \"cat - > ${mongoShardPyConf} && sudo cp ${mongoShardPyConf} ${gmondPyConf}\"" && \
  printf "> Created ${mongoShardPyConf} and ${gmondPyConf}\n"

  scp ${modulePy} ${host}:${mongoShardPy} && \
  printf "> Created ${mongoShardPy}\n"
fi

ssh ${host} bash << EOSSH
set -e
# clean db directory if it is non-empty
if [ "\$(ls -A ${mongoShardDbDir})" ]; then
  rm -r ${mongoShardDbDir}
  mkdir ${mongoShardDbDir}
  printf "> Cleaned db directory ${mongoShardDbDir}\n"
fi

# copy .py from mongoShard dir to gmond dir if it does not exist (using -u flag)
sudo cp -u ${mongoShardPy} ${gmondPy}
printf "> Created ${gmondPy}\n"

# start new mongod
nohup mongod --config ${mongoShardConfig} &> /dev/null &
printf "> Started new mongod process\n"

# restart gmond
sudo systemctl restart gmond
printf "> Restarted gmond\n"

# allow rule for ufw
sudo ufw allow ${port} > /dev/null
printf "> Added ufw rule 'allow from anywhere to ${port}'\n"
set +e
EOSSH
