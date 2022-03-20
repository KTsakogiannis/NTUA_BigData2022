# A Simple Protocol for Resizing MongoDB Clusters
##### **NTUA ECE** - *Big Data Information Systems*

![MongoDB](https://img.shields.io/badge/MongoDB-%234ea94b.svg?style=for-the-badge&logo=mongodb&logoColor=white) ![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54) ![Ubuntu](https://img.shields.io/badge/Ubuntu-E95420?style=for-the-badge&logo=ubuntu&logoColor=white)

## Synopsis
>Implementation of an extension to MongoDB’s native elasticity capabilities; mainly sharding. The extension aims to provide a simple mechanism for dynamically resizing a cluster horizontally, based on an empirical, user-defined policy, whose main goal is to ensure, the functional requirements of the cluster are met using the minimum computational resources possible. The synergy of the tools used, results in -almost- real-time, dynamic horizontal resizing of a MongoDB data-store cluster.

## Features

- 1
- 2
- 3
- 4
- 5

## Tech

Within the project, a number of open source projects is used to work properly:

- [Ubuntu] - ...
- [MongoDB] - ...
- [Ganglia] - ...
- [Python] - ...
- [PHP] - ...

## Services

### Ganglia Services
```sh
sudo systemctl restart gmond
```
> Note: conf at `/usr/local/etc/gmond.conf`

```sh
sudo systemctl restart gmetad
```
> Note: conf at `/usr/local/etc/gmetad.conf`

```sh
sudo systemctl restart apache2
```
```sh
telnet localhost 8651
```

> Note: returns local gmetad response at xml format

> Note: rrds stored at `/usr/local/var/lib/ganglia/rrds/mongodb_cluster`

### Mongo Services
#### mongos 
> Note: stays idle generating a message so `bg` is needed

```sh
mongos --config ~/mongodb/mongoss1/mongos.conf&
bg
mongosh localhost:27015
```
#### mongod 
> Note: config server BigData1

```sh
mongod --config ~/mongodb/confr1/confr1s1/mongoConf.conf&
mongosh localhost:27016 --eval "rs.initiate()"
```

#### mongod 
> Note: shard server BigData2/3

```sh
mongod --config ~/mongodb/shardr1/shardr1s1/mongoShard.conf&
mongosh localhost:27017
```

### Ganglia python extension 
> Note: applies from gmond to locally running mongod

> IMPORTANT! Ganglia uses local python2.7 interpreter(unfortunately), specifically `/usr/bin/python` (which symlink to python2.7)

- 1 add python modules to `/usr/local/lib64/ganglia/python_modules`
- 2 add corresponding python conf files to `/usr/local/etc/conf.d`

### Shard database and collection
```sh
use dbname
sh.enableSharding("dbname")
```

### Create collection colname via ycsb load and then
```sh
db.colname.createIndex({ _id: 1})
sh.shardCollection( "dbname.colname", { '_id': 1 } )
```
