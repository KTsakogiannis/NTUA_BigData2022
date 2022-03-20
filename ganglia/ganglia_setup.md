## Compile Ganglia and Ganglia-Web from source
> In the compiling VM
```sh
add-apt-repository ppa:deadsnakes/ppa
apt update
apt-get install python2 make gcc rrdtool pkg-config checkinstall
apt-get install libapr1 libc6 libconfuse2 libganglia1 libpcre3 zlib1g

# compile dependencies
apt-get install librrd-dev libapr1-dev libconfuse-dev libexpat-dev libpcre3-dev zlib1g
```
> Get and make sources

```sh
wget -O ganglia.gz https://sourceforge.net/projects/ganglia/files/latest/download
tar zxfv ganglia.gz
rm ganglia.gz
cd ganglia-*
./configure --with-gmetad --with-python=/usr/bin/python2.7
make
# install into .deb package
checkinstall
```
```sh
wget -O gfe.gz https://sourceforge.net/projects/ganglia/files/ganglia-web/3.7.2/ganglia-web-3.7.2.tar.gz/download
tar zxfv gfe.gz
rm gfe.gz
cd ganglia-*
vim Makefile
checkinstall
```
```sh
# install packages in the VM using
dpkg -i ganglia-*.deb
```
> In VMs of monogdb shards
```
# send only the ganglia compiled package
add-apt-repository ppa:deadsnakes/ppa
apt update
apt-get install libpython2.7
sudo -H pip install pymongo # for mongodb plugin
dpkg -i ganglia-*.deb
```
## After compiling
Remember to create gmetad.conf and gmond.conf and move them to /usr/local/etc
## Easy solution
Use the above compiled packages, list contents with `dpkg -c ganglia-*.deb` to check the installing paths
