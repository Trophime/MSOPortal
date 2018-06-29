#!/bin/bash
set -e

#!/bin/bash
set -e

usage(){
   echo ""
   echo "Description:"
   echo "   setup MSO4SC portal env"
   echo "Usage:"
   echo "   setup.sh [ -d=DEBUG ] ..."
   echo ""
   echo "-p    define PYTHON_LOCAL_DIR (def: /usr/local/lib/python3.5/dist-packages)"
   echo "-n    define NGINX_LOCAL_DIR (def: $PWD)"
   echo ""
   exit 1
}

: ${DEBUG:="True"}
: ${PYTHON_LOCAL_DIR:="/usr/local/lib/python3.5/dist-packages"}
: ${NGINX_LOCAL_DIR:="$PWD"}

#########################################################
## parse parameters
##########################################################
while getopts "hd:" option ; do
   case $option in
       h ) usage ;;
       d ) DEBUG=$OPTARG ;;
       p ) PYTHON_LOCAL_DIR=$OPTARG ;;
       ? ) usage ;;
   esac
done

if [ ! -f portal/settings.in ]; then
    echo "Missing portal/settings.ini file"
    exit 1
fi

echo "Please be sure that DEBUG=False at portal/settings.ini"

if [ "$#" -ne 1 ]; then
    echo "Usage: "$0" [python-packages-dir]"
    exit
fi

./setup.sh $PYTHON_LOCAL_DIR

apt-get update
apt-get install -y selinux-utils
apt-get clean -y
    
apt-get install -y libpcre3 libpcre3-dev
apt-get clean -y
pip3 install uwsgi

apt-get install -y nginx
apt-get clean -y
sed -i 's/user www-data/user root/g' /etc/nginx/nginx.conf

ln -s  ${NGINX_LOCAL_DIR}/nginx.conf /etc/nginx/sites-available/portal_nginx.conf
ln -s /etc/nginx/sites-available/portal_nginx.conf /etc/nginx/sites-enabled/portal_nginx.conf

python3 manage.py collectstatic
