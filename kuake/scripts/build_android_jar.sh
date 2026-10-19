#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-}}"
if [[ -z "$SDK" ]]; then echo 'ANDROID_HOME / ANDROID_SDK_ROOT not set' >&2; exit 1; fi
ANDROID_JAR="$SDK/platforms/android-35/android.jar"
D8="$SDK/build-tools/35.0.0/d8"
[[ -s "$ANDROID_JAR" ]] || { echo "No Android SDK android.jar: $ANDROID_JAR"; exit 1; }
[[ -x "$D8" ]] || { echo "No Android D8: $D8"; exit 1; }
rm -rf build dist
mkdir -p build/compile-stubs build/classes build/dex dist
# The Spider stub ONLY provides compile-time method signatures. Never bundle it.
javac -encoding UTF-8 --release 8 -cp "$ANDROID_JAR"   -d build/compile-stubs tools/compile-stubs/com/github/catvod/crawler/Spider.java
mapfile -d '' java_files < <(find src -type f -name '*.java' -print0)
javac -encoding UTF-8 --release 8 -cp "$ANDROID_JAR:build/compile-stubs"   -d build/classes "${java_files[@]}"
mapfile -d '' classes < <(find build/classes -type f -name '*.class' -print0)
"$D8" --min-api 23 --lib "$ANDROID_JAR" --output build/dex "${classes[@]}"
[[ -s build/dex/classes.dex ]] || { echo 'DEX build failed' >&2; exit 1; }
(cd build/dex && jar cf ../../dist/QuarkSearch.jar classes.dex)
python3 - <<'PYX'
from zipfile import ZipFile
with ZipFile('dist/QuarkSearch.jar') as z:
    names=z.namelist()
    assert 'classes.dex' in names and z.read('classes.dex').startswith(b'dex\n'), names
    assert not any(n.startswith('android/') or n.startswith('org/json/') for n in names), names
print('Android DEX JAR packaging verified: dist/QuarkSearch.jar')
PYX
