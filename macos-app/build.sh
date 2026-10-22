#!/bin/bash
# Сборка живых обоев «Морской аквариум» в .app (без Xcode-проекта).
#   ./build.sh                  — собрать
#   ./build.sh --run            — собрать и запустить
#   ./build.sh --sign "Developer ID Application: ВАШЕ ИМЯ (TEAMID)"   — собрать и подписать
#   ./scripts/release.sh        — выпуск для сайта: подпись, DMG, нотаризация, «скрепка», проверки (--help)
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
# Только то, что движок грузит: без старых рендеров (render/), запасных фонов (alt/), скриптов Blender
# и документации (*.md, README.txt — лицензии и заметки остаются в репозитории, не в .app).
cp -R ../aquarium "$CONTENTS/Resources/aquarium"
AQ="$CONTENTS/Resources/aquarium"
rm -rf "$AQ/fish/render" "$AQ/assets/render" "$AQ/assets/alt" "$AQ/blender"
find "$AQ" \( -name '*.md' -o -name 'README.txt' -o -name '.DS_Store' \) -type f -delete

# Минимальная macOS — та же, что LSMinimumSystemVersion в Info.plist (без -target swiftc берёт
# версию и архитектуру Mac, на котором собирают: на macOS 15 получился бы бинарник только для 15+
# и только arm64). Собираем arm64 + x86_64 и склеиваем в один универсальный файл.
# Переопределить: MIN_MACOS=14.0 ARCHS="arm64" ./build.sh
MIN_MACOS="${MIN_MACOS:-$(/usr/libexec/PlistBuddy -c 'Print :LSMinimumSystemVersion' Resources/Info.plist 2>/dev/null || echo 13.0)}"
ARCHS="${ARCHS:-arm64 x86_64}"
# Фреймворки — по import в Sources: Cocoa, WebKit, IOKit (IOKit.ps), ServiceManagement. `import os` (Logger) —
# часть libSystem, отдельный -framework не нужен.
echo "▸ Компиляция Swift (Release, macOS $MIN_MACOS+, $ARCHS)"
mkdir -p build/bin
SLICES=()
for A in $ARCHS; do
  swiftc -O -target "$A-apple-macos$MIN_MACOS" \
    -framework Cocoa -framework WebKit -framework ServiceManagement -framework IOKit \
    Sources/*.swift \
    -o "build/bin/$APP-$A"
  SLICES+=("build/bin/$APP-$A")
done
lipo -create "${SLICES[@]}" -output "$CONTENTS/MacOS/$APP"
rm -rf build/bin

echo "✓ Готово: $OUT"

# Опциональная подпись вашим Developer ID (Apple-аккаунт разработчика) — только подпись, для проверки на своём
# Mac. Выпуск для раздачи (подпись + DMG + нотаризация + «скрепка» + проверки) — scripts/release.sh.
if [ "${1:-}" = "--sign" ]; then
  IDENTITY="${2:?Укажите Developer ID: ./build.sh --sign \"Developer ID Application: ... (TEAMID)\"}"
  echo "▸ Подпись: $IDENTITY"
  # Те же флаги, что в scripts/release.sh. Расширенные атрибуты (Finder, карантин) ломают подпись ресурсов.
  # Без --deep: вложенного кода в бандле нет. Hardened runtime (--options runtime) и метка времени Apple
  # (--timestamp, нужен интернет) обязательны для нотаризации. Исключений (entitlements) не нужно: JavaScript
  # WKWebView исполняется в отдельном процессе WebKit (WebContent) со своими правами, а не в нашем.
  xattr -cr "$OUT"
  codesign --force --options runtime --timestamp --sign "$IDENTITY" "$OUT"
  codesign --verify --deep --strict --verbose=2 "$OUT"
  echo "✓ Подписано"
fi

if [ "${1:-}" = "--run" ]; then
  echo "▸ Запуск"
  # Старая копия ещё работает → `open` лишь активирует её, и новая сборка не стартует. По полному пути (-f):
  # имя процесса (p_comm) в macOS обрезано до 16 символов (MAXCOMLEN), а "AquariumWallpaper" — 17: `pkill -x` не найдёт.
  pkill -f "$APP.app/Contents/MacOS/$APP" 2>/dev/null && sleep 1 || true
  open "$OUT"
fi
