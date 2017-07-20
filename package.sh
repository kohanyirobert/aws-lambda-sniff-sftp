#! /bin/sh
rm -vf package-*.zip
zip -r package-$(basename $(pwd))-$(cat VERSION).zip \
  .libs_cffi_backend \
  asn1crypto \
  bcrypt \
  cffi \
  _cffi_backend.so \
  cryptography \
  enum \
  idna \
  ipaddress.py \
  nacl \
  paramiko \
  pyasn1 \
  pycparser \
  six.py \
  tagit \
  VERSION \
  handler.py
