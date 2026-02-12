#!/bin/bash
set -e  

clickable build     --arch amd64 --skip-review
clickable build     --arch arm64 --skip-review
clickable build     --arch armhf --skip-review

cp  ./build/aarch64-linux-gnu/app/wireguard.sysadmin_1.1.2_arm64.click \
    ./build/arm-linux-gnueabihf/app/wireguard.sysadmin_1.1.2_armhf.click \
    ./build/x86_64-linux-gnu/app/wireguard.sysadmin_1.1.2_amd64.click \
    ./packages/
