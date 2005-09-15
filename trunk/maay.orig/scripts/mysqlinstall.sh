#!/bin/sh


#
# edit these to specify your mysql super user
#
user=root
password=""



if [ -z "$MAAYHOME" ]; then
        echo "requires \$MAAYHOME to point to the maay source root" >& 2
        exit 1
fi


echo -n "attempting to create maay database on local mysql server: "
if mysql -u "$user" --password="$password" < "$MAAYHOME"/scripts/mysql.sql; then
        echo "succeeded"
else
        echo "failed"
fi
