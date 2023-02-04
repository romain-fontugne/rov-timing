#!/bin/bash

#Install dependencies
apt-get update
apt-get install -y curl apt-transport-https ssl-cert ca-certificates gnupg lsb-release 

#Install wandio repository
curl -1sLf 'https://dl.cloudsmith.io/public/wand/libwandio/cfg/setup/bash.deb.sh' | sudo -E bash 

#Install CAIDA repository
echo "deb https://pkg.caida.org/os/$(lsb_release -si|awk '{print tolower($0)}') $(lsb_release -sc) main" | sudo tee /etc/apt/sources.list.d/caida.list
wget -O /etc/apt/trusted.gpg.d/caida.gpg https://pkg.caida.org/os/ubuntu/keyring.gpg 

#Install BGPStream packages
apt update; apt-get install -y bgpstream

#Install all the requirements
pip install -r requirements.txt

mkdir tmp cache data
