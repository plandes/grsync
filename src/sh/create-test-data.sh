#!/bin/sh

TMP_DIR=${HOME}/tmp/grsync

rm -rf ${TMP_DIR}
mkdir -p ${TMP_DIR}/view
cp -a ~/view/{emacs,home-dir} ${TMP_DIR}/view
cd ${TMP_DIR}
ln -s view/home-dir/dot/os/darwin/profile .profile
