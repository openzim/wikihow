#!/bin/sh

###
# download JS dependencies and place them in our assets folder
###

if ! command -v curl > /dev/null; then
    echo "you need curl."
    exit 1
fi

if ! command -v unzip > /dev/null; then
    echo "you need unzip."
    exit 1
fi

# Absolute path this script is in.
SCRIPT_PATH="$( cd "$(dirname "$0")" ; pwd -P )"
ASSETS_PATH="${SCRIPT_PATH}/wikihow2zim/assets/vendor"

echo "About to download JS assets to ${ASSETS_PATH}"

echo "getting video.js"
curl -L -O https://github.com/videojs/video.js/releases/download/v7.15.4/video-js-7.15.4.zip
rm -rf $ASSETS_PATH/videojs
mkdir -p $ASSETS_PATH/videojs
unzip -o -d $ASSETS_PATH/videojs video-js-7.15.4.zip
rm -rf $ASSETS_PATH/videojs/alt $ASSETS_PATH/videojs/examples
rm -f video-js-7.15.4.zip

echo "getting ogv.js"
curl -L -O https://github.com/brion/ogv.js/releases/download/1.8.4/ogvjs-1.8.4.zip
rm -rf $ASSETS_PATH/ogvjs
unzip -o ogvjs-1.8.4.zip
mv ogvjs-1.8.4 $ASSETS_PATH/ogvjs
rm -f ogvjs-1.8.4.zip

echo "getting videojs-ogvjs.js"
curl -L -O https://github.com/hartman/videojs-ogvjs/archive/v1.3.1.zip
rm -f $ASSETS_PATH/videojs-ogvjs.js
unzip -o v1.3.1.zip
mv videojs-ogvjs-1.3.1/dist/videojs-ogvjs.js $ASSETS_PATH/videojs-ogvjs.js
rm -rf videojs-ogvjs-1.3.1
rm -f v1.3.1.zip
