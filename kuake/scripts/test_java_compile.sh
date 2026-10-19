#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
mkdir -p build/java-test
mapfile -d '' sources < <(find src tools/test-stubs tests -name '*.java' -type f -print0)
javac -encoding UTF-8 --release 8 -d build/java-test "${sources[@]}"
java -cp build/java-test LocalSmoke
echo 'JVM syntax / offline fixture tests passed (NOT an Android runtime test)'
