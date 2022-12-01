#!/bin/bash
# -*- coding: utf-8 -*-

if [ -z "$1" ]; then
    loc=日本
    zom=4
else
    loc=$1
    zom=${2:-10}
fi

tmpfile=/tmp/ame.sh.${loc}
if [ ! -f ${tmpfile} ]; then
    curl -s https://www.geocoding.jp/api/?q=$loc > $tmpfile
fi

lat=$(cat $tmpfile | sed -e 's,<lat>\(.*\)</lat>,\1,p;d')
lng=$(cat $tmpfile | sed -e 's,<lng>\(.*\)</lng>,\1,p;d')

if [ ! -z "${lat}" -a ! -z "${lng}" ]; then
    url="https://weather.yahoo.co.jp/weather/zoomradar/?lat=${lat}&lon=${lng}&z=${zom}"
    ogi=$(curl -s ${url} | sed -e 's,^.*<meta content="\(.*\)" property="og:image"/>.*$,\1,p;d' | sed -e 's/\&amp;/\&/g')
    curl -s "${ogi}" | img2sixel
fi
