#!/bin/bash
# Сборка живых обоев «Морской аквариум» в .app (без Xcode-проекта).
#   ./build.sh                  — собрать
#   ./build.sh --run            — собрать и запустить
#   ./build.sh --sign "Developer ID Application: ВАШЕ ИМЯ (TEAMID)"   — собрать и подписать
set -euo pipefail
cd "$(dirname "$0")"

APP="AquariumWallpaper"
OUT="build/$APP.app"
CONTENTS="$OUT/Contents"

echo "▸ Очистка"
rm -rf build
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources"

echo "▸ Info.plist"
cp Resources/Info.plist "$CONTENTS/Info.plist"

echo "▸ Встраиваю аквариум (HTML + рыбы)"
cp -R ../aquarium "$CONTENTS/Resources/aquarium"

echo "▸ Компиляция Swift (Release)"
swiftc -O \
  -framework Cocoa -framework WebKit -framework ServiceManagement -framework IOKit \
  Sources/*.swift \
  -o "$CONTENTS/MacOS/$APP"

echo "✓ Готово: $OUT"

# Опциональная подпись вашим Developer ID (Apple-аккаунт разработчика)
if [ "${1:-}" = "--sign" ]; then
  IDENTITY="${2:?Укажите Developer ID: ./build.sh --sign \"Developer ID Application: ... (TEAMID)\"}"
  echo "▸ Подпись: $IDENTITY"
  codesign --force --deep --options runtime --sign "$IDENTITY" "$OUT"
  codesign --verify --strict --verbose=2 "$OUT" || true
  echo "✓ Подписано"
fi

if [ "${1:-}" = "--run" ]; then
  echo "▸ Запуск"
  open "$OUT"
fi
