## BigData1 (master with gmetad)

```sh
add-apt-repository ppa:deadsnakes/ppa
apt update
apt-get install python2 make gcc rrdtool pkg-config checkinstall
apt-get install libapr1 libc6 libconfuse2 libganglia1 libpcre3 zlib1g
```
```sh
apt-get install librrd-dev libapr1-dev libconfuse-dev libexpat-dev libpcre3-dev zlib1g
```
## get and make sources

```sh
wget -O ganglia.gz https://sourceforge.net/projects/ganglia/files/latest/download
tar zxfv ganglia.gz
rm ganglia.gz
cd ganglia-*
./configure --with-gmetad --with-python=/usr/bin/python2.7
make
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
dpkg -i ganglia-*.deb
```
