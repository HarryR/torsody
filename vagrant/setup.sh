#!/bin/sh
set -e

iptables -A PREROUTING -t nat -i eth1 -p tcp --dport 80 -j REDIRECT --to-port 8080
echo iptables-persistent iptables-persistent/autosave_v4 boolean true | debconf-set-selections
echo iptables-persistent iptables-persistent/autosave_v6 boolean true | debconf-set-selections

apt-get update
apt-get -y install tmux python-setuptools python-dev python-pip git pv \
                   make libpcre3-dev iptables-persistent pyflakes pychecker  \
                   python-gevent python-passlib memcached \ 
                   prosody lua-zlib openssl-blacklist lua5.1-sec lua5.1-event \
                   tor tor-geoipdb apparmor-utils lua-bitop

gpasswd -a vagrant debian-tor
gpasswd -a vagrant prosody

chown debian-tor /etc/tor -R

rm /etc/prosody/conf.d/localhost.cfg.lua
PROSODY_LOCAL=`< /dev/urandom tr -dc A-Za-z0-9 | head -c20`.prosody
cat << EOF > /etc/prosody/conf.d/$PROSODY_LOCAL.cfg.lua
VirtualHost "$PROSODY_LOCAL"
EOF

make -C /home/vagrant/app install

#
# To reduce storage space on the operating system 
#
echo << END_IGNORE

##echo << EOF > /etc/dpkg/dpkg.cfg.d/01_nodoc
#path-exclude /usr/share/doc/*
# we need to keep copyright files for legal reasons
#path-include /usr/share/doc/*/copyright
#path-exclude /usr/share/man/*
#path-exclude /usr/share/groff/*
#path-exclude /usr/share/info/*
# lintian stuff is small, but really unnecessary
#path-exclude /usr/share/lintian/*
#path-exclude /usr/share/linda/*
##EOF

apt-get purge puppet puppet-common chef chef-zero cloud-init ntfs-3g ruby \
        xserver-xorg-core byobu w3m screen strace vim-tiny \
        tcpd pppoeconf purge ppp pppconfig apport dosfstools w3m ltrace vim-common \
        vim-runtime  vim python-dev libpcre3-dev manpages-dev open-vm-tools nano \
        libc6-dev libc-dev-bin linux-libc-dev python-dbus-dev dpkg-dev \
        virtualbox-guest-utils virtualbox-guest-x11 \
        landscape-client landscape-common juju juju-core git \
        command-not-found command-not-found-data byobu \
        cpp cpp-4.9 ftp fuse tmux sosreport dbus screen rpcbind \
        manpages man-db python3-dbus libdbus-glib-1-2 netcat-openbsd \
        popularity-contest pychecker pyflakes pv python-apport \
        python-twisted-web at \
        python3-problem-report python3-software-properties \
        unattended-upgrades update-manager-core python3-update-manager \
        update-notifier-common python-cheetah python-twisted-bin \
        python-twisted-core python-twisted-names python-pip uuid-runtime \
        python-setuptools python-oauth python-serial cgmanager systemd-shim
find /usr/share/doc -depth -type f ! -name copyright|xargs rm || true
find /usr/share/doc -empty|xargs rmdir || true
rm -rf /usr/share/man/* /usr/share/groff/* /usr/share/info/*
rm -rf /usr/share/lintian/* /usr/share/linda/* /var/cache/man/*
apt-get purge openssh-server xauth sudo openssh-sftp-server
END_IGNORE

apt-get autoremove --purge
apt-get clean

