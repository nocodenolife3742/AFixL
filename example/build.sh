#!/bin/bash -eu

cd /src
make CC="$CC" CFLAGS="$CFLAGS"
cp example /exe
