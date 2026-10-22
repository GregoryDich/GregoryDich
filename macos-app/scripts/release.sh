#!/bin/bash
# Выпуск «Морского аквариума» для раздачи с сайта (Developer ID, вне Mac App Store):
#   сборка (универсальная: Apple Silicon + Intel) → подпись (hardened runtime + метка времени Apple) →
#   DMG (приложение + ярлык «Программы») → подпись DMG → нотаризация в Apple → «скрепка» (staple)
#   для DMG и приложения → проверки (codesign, stapler, Gatekeeper) → dist/AquariumWallpaper-<версия>.dmg
#
#   ./scripts/release.sh --check                        — готово ли всё к выпуску (ничего не собирает)
#   ./scripts/release.sh                                — выпуск с версией из Resources/Info.plist
#   ./scripts/release.sh --version 1.0.1 --bump-build   — поднять версию и номер сборки, затем выпуск
#   ./scripts/release.sh --dry-run …                    — только показать команды, ничего не менять
#   ./scripts/release.sh --help                         — все параметры и разовая настройка
#
# Пишется под /bin/bash 3.2 из macOS: без ассоциативных массивов и mapfile; пустые массивы — через ${a[@]+…}.
set -euo pipefail
cd "$(dirname "$0")/.."            # macos-app/

APP="AquariumWallpaper"            # то же имя, что в build.sh (build/$APP.app)
PLIST="Resources/Info.plist"
PLISTBUDDY="${PLISTBUDDY:-/usr/libexec/PlistBuddy}"
PROFILE="${AQ_NOTARY_PROFILE:-AQ_NOTARY}"
IDENTITY="${AQ_SIGN_IDENTITY:-}"
ENTITLEMENTS=""
NEW_VERSION=""
NEW_BUILD=""
BUMP_BUILD=0
DRY=0
CHECK=0
NOTARIZE=1

usage() {
  cat <<'EOF'
Выпуск «Морского аквариума»: подпись Developer ID, DMG, нотаризация, «скрепка», проверки.

  ./scripts/release.sh [параметры]

Параметры:
  --check               только проверить готовность (инструменты, сертификат, профиль нотаризации,
                        версия) и выйти; ничего не собирается
  --dry-run             показать все команды выпуска, ничего не собирая и не меняя (смотрит только,
                        какие инструменты и сертификаты есть на Mac)
  --version 1.0.1       записать новую версию (CFBundleShortVersionString) в Resources/Info.plist
  --bump-build          номер сборки (CFBundleVersion) +1 в Resources/Info.plist
  --build 12            записать номер сборки явно
  --identity "…"        сертификат подписи: «Developer ID Application: Имя (TEAMID)» или его 40-значный
                        код из `security find-identity -v -p codesigning`. Без параметра берётся
                        единственный Developer ID Application из связки ключей (или $AQ_SIGN_IDENTITY)
  --profile ИМЯ         профиль нотаризации в связке ключей (по умолчанию AQ_NOTARY, или $AQ_NOTARY_PROFILE)
  --entitlements ФАЙЛ   файл исключений hardened runtime. Обычно НЕ нужен: JavaScript в WKWebView
                        исполняется в отдельном процессе WebKit со своими правами
  --no-notarize         подписать и собрать DMG без нотаризации (проверка на своём Mac, не для раздачи)
  -h, --help            эта справка

Итог: dist/AquariumWallpaper-<версия>.dmg (+ .txt: версия, SHA-256, id нотаризации, коммит).

Разовая настройка (один раз на Mac):
  1. Apple Developer Program (developer.apple.com/programs, 99 $ в год).
  2. Сертификат «Developer ID Application»:
     • с Xcode: Xcode → Settings → Accounts → ваш Apple ID → Manage Certificates → «+» →
       Developer ID Application;
     • без Xcode: «Связка ключей» → меню «Связка ключей» → «Ассистент сертификации» → «Запросить
       сертификат у бюро сертификации» (e-mail, имя, «Сохранен на диске») → developer.apple.com/account →
       Certificates → «+» → Developer ID Application (G2 Sub-CA) → загрузить запрос → скачать .cer →
       открыть двойным щелчком.
     Проверка:   security find-identity -v -p codesigning
     Нужна строка "Developer ID Application: Имя Фамилия (ABCDE12345)"; ABCDE12345 — ваш Team ID.
     Сертификат вместе с закрытым ключом сохраните в надёжное место: «Связка ключей» → правый щелчок →
     «Экспортировать…» (.p12 с паролем). Без ключа подписывать нечем — придётся выпускать новый.
  3. Пароль приложения: account.apple.com → «Вход и безопасность» → «Пароли приложений» → «+» →
     название «notarytool» → скопировать пароль вида xxxx-xxxx-xxxx-xxxx.
  4. Профиль нотаризации в связке ключей (пароль спросит сам и не покажет на экране):
       xcrun notarytool store-credentials AQ_NOTARY --apple-id "ваш@apple.id" --team-id ABCDE12345
  5. Проверка:   ./scripts/release.sh --check
При первой подписи macOS спросит пароль связки ключей для codesign — пароль входа в Mac и
«Всегда разрешать».
EOF
}

# ── Вывод ────────────────────────────────────────────────────────────────────────────────────────
STEP="подготовка"
STEP_NO=0
DIED=0
PROBLEMS=0
MOUNTED=0
MNT=""
PLIST_CHANGED=0

say()  { printf '%s\n' "$*"; }
ok()   { printf '  ✓ %s\n' "$*"; }
warn() { printf '  ! %s\n' "$*" >&2; }
step() { STEP_NO=$((STEP_NO + 1)); STEP="$*"; printf '\n▸ %s. %s\n' "$STEP_NO" "$*"; }
die()  { DIED=1; printf '\n✗ %s\n' "$*" >&2; exit 1; }

# Проблема подготовки: при выпуске — остановка; при --check и --dry-run — отметка и дальше.
fail() {
  if [ "$CHECK" = 1 ] || [ "$DRY" = 1 ]; then
    printf '  ✗ %s\n' "$*" >&2
    PROBLEMS=$((PROBLEMS + 1))
  else
    die "$*"
  fi
}

# Слово команды для показа: как есть, если в нём только «безопасные» символы, иначе в одинарных кавычках.
q() {
  case "$1" in
    '') printf "''" ;;
    *[!A-Za-z0-9_./:=@%+,-]*) printf "'%s'" "$(printf '%s' "$1" | sed "s/'/'\\\\''/g")" ;;
    *) printf '%s' "$1" ;;
  esac
}
show() {
  local s="" a
  for a in ${1+"$@"}; do s="$s $(q "$a")"; done
  printf '  $%s\n' "$s"
}
# Показать команду и выполнить (при --dry-run — только показать).
run() {
  show ${1+"$@"}
  if [ "$DRY" = 1 ]; then return 0; fi
  "$@"
}
dry() { [ "$DRY" = 1 ]; }

cleanup() {
  local rc=$?
  if [ "$MOUNTED" = 1 ] && [ -n "$MNT" ]; then
    hdiutil detach -quiet "$MNT" >/dev/null 2>&1 || hdiutil detach -force "$MNT" >/dev/null 2>&1 || true
  fi
  if [ "$rc" -ne 0 ] && [ "$DIED" = 0 ]; then
    printf '\n✗ Выпуск прерван (шаг «%s», код %s). Что случилось — в сообщениях выше.\n' "$STEP" "$rc" >&2
  fi
  if [ "$rc" -ne 0 ] && [ "$PLIST_CHANGED" = 1 ]; then
    printf '  Версия в %s уже записана: %s (сборка %s). Для повтора запустите ./scripts/release.sh\n' \
      "$PLIST" "$VERSION" "$BUILD" >&2
    printf '  без --version/--bump-build, чтобы не поднять её ещё раз.\n' >&2
  fi
}
trap cleanup EXIT

# ── Параметры ────────────────────────────────────────────────────────────────────────────────────
need_value() { # $1 — параметр, $2 — значение (если есть)
  if [ $# -lt 2 ] || [ -z "$2" ] || [ "${2#--}" != "$2" ]; then die "После $1 нужно значение (см. --help)"; fi
}
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1 ;;
    --check) CHECK=1 ;;
    --no-notarize) NOTARIZE=0 ;;
    --bump-build) BUMP_BUILD=1 ;;
    --version) need_value "$@"; NEW_VERSION=$2; shift ;;
    --version=*) NEW_VERSION=${1#*=} ;;
    --build) need_value "$@"; NEW_BUILD=$2; shift ;;
    --build=*) NEW_BUILD=${1#*=} ;;
    --identity) need_value "$@"; IDENTITY=$2; shift ;;
    --identity=*) IDENTITY=${1#*=} ;;
    --profile) need_value "$@"; PROFILE=$2; shift ;;
    --profile=*) PROFILE=${1#*=} ;;
    --entitlements) need_value "$@"; ENTITLEMENTS=$2; shift ;;
    --entitlements=*) ENTITLEMENTS=${1#*=} ;;
    -h|--help) usage; exit 0 ;;
    *) die "Неизвестный параметр: $1 (список: ./scripts/release.sh --help)" ;;
  esac
  shift
done
if [ -n "$NEW_BUILD" ] && [ "$BUMP_BUILD" = 1 ]; then die "Укажите что-то одно: --build N или --bump-build"; fi
if [ "$CHECK" = 1 ] && { [ -n "$NEW_VERSION" ] || [ -n "$NEW_BUILD" ] || [ "$BUMP_BUILD" = 1 ]; }; then
  die "--check ничего не меняет: уберите --version/--build/--bump-build"
fi

# ── Info.plist ───────────────────────────────────────────────────────────────────────────────────
plist_get() { # ключ [файл] — значение строкового ключа; без PlistBuddy (не Mac, --dry-run) — разбор текста
  local file="${2:-$PLIST}"
  if [ -x "$PLISTBUDDY" ]; then
    "$PLISTBUDDY" -c "Print :$1" "$file" 2>/dev/null || true
  else
    sed -n "/<key>$1<\/key>/{n;s/.*<string>\(.*\)<\/string>.*/\1/p;q;}" "$file"
  fi
}

# Значение ключа из JSON-ответа notarytool (plutil читает JSON; запасной вариант — sed).
json_get() { # ключ файл
  local v
  v=$(plutil -extract "$1" raw -o - "$2" 2>/dev/null || true)
  if [ -z "$v" ]; then
    v=$(sed -n 's/.*"'"$1"'"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' "$2" 2>/dev/null | sed -n '1p' || true)
  fi
  printf '%s' "$v"
}

# ── 1. Подготовка ────────────────────────────────────────────────────────────────────────────────
if [ "$CHECK" = 1 ]; then
  say "Проверка готовности к выпуску"
elif dry; then
  say "Пробный прогон (--dry-run): команды только показываются, ничего не выполняется и не меняется."
fi
step "Подготовка"

# Mac и инструменты
if [ "$(uname -s)" = "Darwin" ]; then
  ok "Mac, macOS $(sw_vers -productVersion 2>/dev/null || echo '?')"
else
  fail "Выпуск собирается только на Mac (здесь $(uname -s))"
fi
missing=""
for t in swiftc lipo codesign hdiutil ditto xattr spctl security shasum file plutil; do
  command -v "$t" >/dev/null 2>&1 || missing="$missing $t"
done
[ -x "$PLISTBUDDY" ] || missing="$missing PlistBuddy"
if [ -z "$missing" ]; then
  ok "Инструменты: swiftc, codesign, hdiutil, spctl, PlistBuddy"
else
  fail "Нет программ:$missing. Установите Xcode Command Line Tools: xcode-select --install"
fi
HAVE_NOTARYTOOL=0
if [ "$NOTARIZE" = 1 ]; then
  if command -v xcrun >/dev/null 2>&1 && xcrun --find notarytool >/dev/null 2>&1 && xcrun --find stapler >/dev/null 2>&1; then
    HAVE_NOTARYTOOL=1
    ok "notarytool и stapler: $(xcrun notarytool --version 2>/dev/null | sed -n '1p' || echo 'есть')"
  else
    fail "Нет notarytool/stapler (нужны Xcode 13+ или свежие Command Line Tools): обновите их в «Обновлении ПО» или выполните xcode-select --install"
  fi
fi

# Сертификат Developer ID Application
SIGN_ARG=""
SIGN_NAME=""
if command -v security >/dev/null 2>&1; then
  ids=$(security find-identity -v -p codesigning 2>/dev/null | grep '"Developer ID Application: ' || true)
  if [ -n "$IDENTITY" ]; then
    matches=$(printf '%s\n' "$ids" | grep -F -- "$IDENTITY" || true)
  else
    matches=$ids
  fi
  n=$(printf '%s' "$matches" | grep -c . || true)
  if [ "$n" = 1 ]; then
    SIGN_ARG=$(printf '%s\n' "$matches" | awk '{print $2}')       # 40-значный SHA-1: однозначно для codesign
    SIGN_NAME=$(printf '%s\n' "$matches" | sed 's/^[^"]*"\(.*\)"[^"]*$/\1/')
    ok "Сертификат: $SIGN_NAME"
  elif [ "$n" = 0 ]; then
    untrusted=$(security find-identity -p codesigning 2>/dev/null | grep '"Developer ID Application: ' || true)
    if [ -n "$IDENTITY" ]; then
      fail "Сертификат «$IDENTITY» не найден среди действующих. Действующие Developer ID Application:
$(printf '%s\n' "${ids:-    (нет)}")"
    elif [ -n "$untrusted" ]; then
      fail "Сертификат Developer ID Application есть, но недействителен (причина — в скобках):
$untrusted
    CSSMERR_TP_NOT_TRUSTED — установите промежуточный сертификат «Developer ID - G2» с
    https://www.apple.com/certificateauthority/ (двойной щелчок по DeveloperIDG2CA.cer) и повторите;
    CSSMERR_TP_CERT_EXPIRED или REVOKED — нужен новый сертификат (--help, шаг 2)."
    else
      fail "В связке ключей нет сертификата «Developer ID Application». Как его получить — ./scripts/release.sh --help, шаг 2.
    Проверка: security find-identity -v -p codesigning"
    fi
  else
    fail "Подходят несколько сертификатов — укажите один: --identity <40-значный код из списка>
$matches"
  fi
fi
if [ -z "$SIGN_ARG" ]; then
  SIGN_ARG=${IDENTITY:-"Developer ID Application: ИМЯ (TEAMID)"}
  SIGN_NAME=$SIGN_ARG
fi

# Профиль нотаризации (нужен интернет; при --dry-run не проверяется)
if [ "$NOTARIZE" = 1 ] && [ "$HAVE_NOTARYTOOL" = 1 ]; then
  if dry; then
    show xcrun notarytool history --keychain-profile "$PROFILE"
  elif xcrun notarytool history --keychain-profile "$PROFILE" >/dev/null 2>&1; then
    ok "Профиль нотаризации $PROFILE: вход в Apple работает"
  else
    fail "Профиль нотаризации «$PROFILE» не найден в связке ключей, пароль приложения отозван или нет интернета.
    Создать профиль: xcrun notarytool store-credentials $PROFILE --apple-id \"ваш@apple.id\" --team-id ВАШ_TEAM_ID
    (пароль приложения — account.apple.com → «Вход и безопасность» → «Пароли приложений»; подробнее — --help).
    Проверка: xcrun notarytool history --keychain-profile $PROFILE"
  fi
fi

# Исключения hardened runtime (обычно не нужны)
if [ -n "$ENTITLEMENTS" ]; then
  if [ ! -f "$ENTITLEMENTS" ]; then
    fail "Нет файла исключений: $ENTITLEMENTS"
  elif command -v plutil >/dev/null 2>&1 && ! plutil -lint "$ENTITLEMENTS" >/dev/null 2>&1; then
    fail "Файл исключений $ENTITLEMENTS повреждён (plutil -lint)"
  elif grep -q 'get-task-allow' "$ENTITLEMENTS"; then
    fail "В $ENTITLEMENTS есть com.apple.security.get-task-allow — с ним Apple отклоняет нотаризацию"
  else
    ok "Исключения hardened runtime: $ENTITLEMENTS"
  fi
fi

# Версия
[ -f "$PLIST" ] || die "Нет $PLIST"
BUNDLE_ID=$(plist_get CFBundleIdentifier)
DISPLAY_NAME=$(plist_get CFBundleDisplayName)
CUR_VERSION=$(plist_get CFBundleShortVersionString)
CUR_BUILD=$(plist_get CFBundleVersion)
[ -n "$BUNDLE_ID" ] || die "В $PLIST нет CFBundleIdentifier"
VERSION=${NEW_VERSION:-$CUR_VERSION}
if [ -n "$NEW_BUILD" ]; then
  BUILD=$NEW_BUILD
elif [ "$BUMP_BUILD" = 1 ]; then
  case "$CUR_BUILD" in ''|*[!0-9]*) die "Номер сборки в $PLIST («$CUR_BUILD») не целое число — задайте его: --build 1" ;; esac
  BUILD=$((10#$CUR_BUILD + 1))
else
  BUILD=$CUR_BUILD
fi
re_version='^[0-9]+\.[0-9]+(\.[0-9]+)?$'
re_build='^[0-9]+$'
[[ $VERSION =~ $re_version ]] || die "Версия «$VERSION» не подходит: нужно 1.0 или 1.0.1"
[[ $BUILD =~ $re_build ]] || die "Номер сборки «$BUILD» не подходит: нужно целое число (1, 2, 3…)"
if [ -n "$NEW_BUILD" ] && [[ $CUR_BUILD =~ $re_build ]] && [ "$((10#$BUILD))" -lt "$((10#$CUR_BUILD))" ]; then
  warn "Номер сборки уменьшается ($CUR_BUILD → $BUILD): обновления по номеру сборки его не увидят"
fi
if [ "$VERSION" = "$CUR_VERSION" ] && [ "$BUILD" = "$CUR_BUILD" ]; then
  ok "Версия: $VERSION (сборка $BUILD), из $PLIST"
else
  ok "Версия: $CUR_VERSION (сборка $CUR_BUILD) → $VERSION (сборка $BUILD)"
fi

DMG_NAME="$APP-$VERSION.dmg"
FINAL="dist/$DMG_NAME"
if [ "$CHECK" = 0 ] && [ "$NOTARIZE" = 1 ] && [ -e "$FINAL" ]; then
  fail "Выпуск $VERSION уже собран: $FINAL. Для нового выпуска поднимите версию (--version …);
    если этот файл никому не раздавали и нужно пересобрать — удалите его и повторите."
fi

if [ "$CHECK" = 1 ]; then
  if [ "$PROBLEMS" -gt 0 ]; then
    printf '\n✗ Не готово: %s. Как настроить — ./scripts/release.sh --help\n' "$PROBLEMS" >&2
    DIED=1
    exit 1
  fi
  say ""
  say "✓ Всё готово к выпуску: ./scripts/release.sh   (новая версия: --version 1.0.1 --bump-build)"
  exit 0
fi
if dry && [ "$PROBLEMS" -gt 0 ]; then
  warn "Проблем подготовки: $PROBLEMS — настоящий запуск на них остановится (подробнее: --check)"
fi

say ""
say "Выпуск «${DISPLAY_NAME:-$APP}» $VERSION (сборка $BUILD)"
say "  подпись:     $SIGN_NAME"
if [ "$NOTARIZE" = 1 ]; then say "  нотаризация: профиль $PROFILE"; else say "  нотаризация: пропущена (--no-notarize)"; fi

# ── 2. Версия ────────────────────────────────────────────────────────────────────────────────────
if [ "$VERSION" != "$CUR_VERSION" ] || [ "$BUILD" != "$CUR_BUILD" ]; then
  step "Версия → $VERSION (сборка $BUILD)"
  if [ "$VERSION" != "$CUR_VERSION" ]; then
    run "$PLISTBUDDY" -c "Set :CFBundleShortVersionString $VERSION" "$PLIST"
  fi
  if [ "$BUILD" != "$CUR_BUILD" ]; then
    run "$PLISTBUDDY" -c "Set :CFBundleVersion $BUILD" "$PLIST"
  fi
  dry || PLIST_CHANGED=1
fi

# ── 3. Сборка ────────────────────────────────────────────────────────────────────────────────────
step "Сборка (универсальная: Apple Silicon + Intel)"
# ARCHS и MIN_MACOS из окружения не наследуем: выпуск всегда универсальный и для macOS из Info.plist.
run env -u MIN_MACOS ARCHS="arm64 x86_64" ./build.sh || die "Сборка не удалась (сообщения build.sh — выше)"
APP_PATH="build/$APP.app"
EXE="$APP_PATH/Contents/MacOS/$APP"
show lipo -archs "$EXE"
if ! dry; then
  [ -x "$EXE" ] || die "После сборки нет $EXE"
  archs=$(lipo -archs "$EXE")
  case " $archs " in *" arm64 "*) ;; *) die "В $EXE нет arm64 (есть: $archs)" ;; esac
  case " $archs " in *" x86_64 "*) ;; *) die "В $EXE нет x86_64 (есть: $archs)" ;; esac
  ok "Архитектуры: $archs"
  got_v=$(plist_get CFBundleShortVersionString "$APP_PATH/Contents/Info.plist")
  got_b=$(plist_get CFBundleVersion "$APP_PATH/Contents/Info.plist")
  [ "$got_v" = "$VERSION" ] && [ "$got_b" = "$BUILD" ] ||
    die "В собранном приложении версия $got_v ($got_b), ожидалась $VERSION ($BUILD)"
  # Вложенного кода (фреймворков, помощников, .dylib) в бандле нет — поэтому подпись без --deep. Если он
  # появится (например, Sparkle), его надо подписывать отдельно, изнутри наружу; до тех пор — стоп.
  nested=$(find "$APP_PATH/Contents" -type f ! -path "$EXE" -exec file {} + | grep 'Mach-O' || true)
  [ -z "$nested" ] || die "В бандле есть исполняемый код кроме $EXE — его нужно подписать отдельно (скрипт пока этого не умеет):
$nested"
  ok "Вложенного кода нет: подписывается один исполняемый файл и ресурсы"
fi

# ── 4. Подпись приложения ────────────────────────────────────────────────────────────────────────
step "Подпись приложения (Developer ID, hardened runtime, метка времени Apple)"
codesign_hint="Возможные причины:
    • macOS спросила пароль связки ключей, а доступ не дан — повторите и нажмите «Всегда разрешать»;
    • errSecInternalComponent — связка ключей заблокирована (например, вход по SSH):
      security unlock-keychain ~/Library/Keychains/login.keychain-db
    • нет интернета — метку времени выдаёт сервер Apple (timestamp.apple.com);
    • «ambiguous» — подходят несколько сертификатов: --identity <40-значный код>."
# Расширенные атрибуты (Finder, карантин) внутри бандла ломают подпись («resource fork, Finder information,
# or similar detritus not allowed»).
run xattr -cr "$APP_PATH"
SIGN_OPTS=(--force --options runtime --timestamp --sign "$SIGN_ARG")
if [ -n "$ENTITLEMENTS" ]; then SIGN_OPTS+=(--entitlements "$ENTITLEMENTS"); fi
run codesign "${SIGN_OPTS[@]}" "$APP_PATH" || die "Не удалось подписать $APP_PATH. $codesign_hint"
run codesign --verify --deep --strict --verbose=2 "$APP_PATH" || die "Подпись $APP_PATH не проходит проверку"
show codesign -dvv "$APP_PATH"
if ! dry; then
  info=$(codesign -dvv "$APP_PATH" 2>&1 || true)
  printf '%s\n' "$info" | grep -Eq 'flags=0x[0-9a-f]+\([^)]*runtime' ||
    die "В подписи нет hardened runtime (--options runtime) — Apple отклонит нотаризацию"
  printf '%s\n' "$info" | grep -q '^Timestamp=' ||
    die "В подписи нет защищённой метки времени (--timestamp; нужен интернет) — Apple отклонит нотаризацию"
  printf '%s\n' "$info" | grep -q '^Authority=Developer ID Application:' ||
    die "Подписано не сертификатом Developer ID Application:
$(printf '%s\n' "$info" | grep '^Authority=' || true)"
  ents=$(codesign -d --entitlements - "$APP_PATH" 2>/dev/null || true)
  if printf '%s' "$ents" | grep -q 'get-task-allow'; then
    die "В подписи есть com.apple.security.get-task-allow — Apple отклонит нотаризацию"
  fi
  ok "Hardened runtime, метка времени, $(printf '%s\n' "$info" | grep '^Authority=Developer ID Application:' | sed 's/^Authority=//')"
fi

# ── 5. DMG ───────────────────────────────────────────────────────────────────────────────────────
step "Образ диска (DMG): приложение + ярлык «Программы»"
STAGE="build/dmg-root"
DMG="build/$DMG_NAME"
VOLNAME="${DISPLAY_NAME:-$APP}"
run rm -rf "$STAGE" "$DMG"
run mkdir -p "$STAGE"
run ditto "$APP_PATH" "$STAGE/$APP.app"        # ditto сохраняет подпись и ссылки
run ln -s /Applications "$STAGE/Applications"
show hdiutil create -volname "$VOLNAME" -srcfolder "$STAGE" -ov -fs HFS+ -format UDZO "$DMG"
if ! dry; then
  made=0
  for attempt in 1 2 3; do
    if hdiutil create -quiet -volname "$VOLNAME" -srcfolder "$STAGE" -ov -fs HFS+ -format UDZO "$DMG"; then
      made=1
      break
    fi
    warn "hdiutil не создал образ (попытка $attempt из 3; бывает, когда диск занят Spotlight) — повтор через 5 с"
    sleep 5
  done
  [ "$made" = 1 ] || die "Не удалось создать $DMG (hdiutil). Закройте окна Finder с build/ и повторите."
fi
# DMG подписывается тем же Developer ID Application (не Installer), без hardened runtime.
run codesign --force --timestamp --sign "$SIGN_ARG" --identifier "$BUNDLE_ID.dmg" "$DMG" ||
  die "Не удалось подписать $DMG. $codesign_hint"
run codesign --verify --verbose=2 "$DMG" || die "Подпись $DMG не проходит проверку"
run rm -rf "$STAGE"

# ── 6. Нотаризация ───────────────────────────────────────────────────────────────────────────────
NOTARY_ID=""
if [ "$NOTARIZE" = 1 ]; then
  step "Нотаризация в Apple"
  # Отправляется только внешний контейнер — DMG: служба выдаёт билеты и ему, и приложению внутри.
  if ! dry; then
    say "  Загрузка $(du -h "$DMG" | cut -f1 | tr -d ' ') и проверка в Apple: обычно 2–15 минут. Нужен интернет."
  fi
  SUBMIT_OUT="build/notary-submit.json"
  NOTARY_LOG="build/notary-log.json"
  show xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait --output-format json
  if ! dry; then
    rc=0
    xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait --output-format json >"$SUBMIT_OUT" || rc=$?
    NOTARY_ID=$(json_get id "$SUBMIT_OUT")
    status=$(json_get status "$SUBMIT_OUT")
    if [ -n "$NOTARY_ID" ]; then
      xcrun notarytool log "$NOTARY_ID" --keychain-profile "$PROFILE" "$NOTARY_LOG" >/dev/null 2>&1 || true
    fi
    if [ "$status" != "Accepted" ]; then
      [ -s "$SUBMIT_OUT" ] && { say "  Ответ Apple:"; sed 's/^/    /' "$SUBMIT_OUT" >&2; }
      [ -s "$NOTARY_LOG" ] && { say "  Журнал проверки ($NOTARY_LOG):"; sed 's/^/    /' "$NOTARY_LOG" >&2; }
      if [ -z "$status" ]; then
        die "Нотаризация не состоялась (код notarytool $rc): не удалось связаться с Apple или войти.
    • Интернет и профиль: xcrun notarytool history --keychain-profile $PROFILE
    • Пароль приложения отозван — создайте новый и повторите store-credentials (--help, шаги 3–4).
    • В ответе есть «agreement»/«contract» — войдите на developer.apple.com/account и примите новые соглашения."
      fi
      die "Apple не приняла DMG: статус «$status»${NOTARY_ID:+, id $NOTARY_ID}. Причины — в журнале выше (поле issues).
    Частые: нет метки времени или hardened runtime, подпись не Developer ID, неподписанный исполняемый файл в бандле."
    fi
    ok "Apple приняла: Accepted, id $NOTARY_ID"
    if [ -s "$NOTARY_LOG" ] && grep -q '"issues"[[:space:]]*:[[:space:]]*\[' "$NOTARY_LOG"; then
      warn "В журнале Apple есть замечания (выпуску не мешают, но их стоит исправить): $NOTARY_LOG"
    fi
  fi

  # ── 7. Скрепка ─────────────────────────────────────────────────────────────────────────────────
  step "Скрепка (staple): билет нотаризации в DMG и в приложение — Gatekeeper проверит и без интернета"
  run xcrun stapler staple "$DMG" || die "Не удалось прикрепить билет к $DMG (нужен интернет: билет скачивается у Apple)"
  run xcrun stapler staple "$APP_PATH" || die "Не удалось прикрепить билет к $APP_PATH"
  run xcrun stapler validate "$DMG" || die "Билет в $DMG не проходит проверку"
  run xcrun stapler validate "$APP_PATH" || die "Билет в $APP_PATH не проходит проверку"
fi

# ── 8. Проверки ──────────────────────────────────────────────────────────────────────────────────
step "Проверки"
run hdiutil verify -quiet "$DMG" || die "Образ $DMG повреждён (hdiutil verify)"
run codesign --verify --deep --strict --verbose=2 "$APP_PATH" || die "Подпись $APP_PATH не проходит проверку"

# Gatekeeper: «accepted» и «source=Notarized Developer ID». Без нотаризации — только показать ответ.
gatekeeper() { # что-проверяем путь [аргументы spctl…]
  local what=$1 path=$2 out
  shift 2
  show spctl -a -vvv ${1+"$@"} "$path"
  if dry; then return 0; fi
  out=$(spctl -a -vvv ${1+"$@"} "$path" 2>&1 || true)
  printf '%s\n' "$out" | sed 's/^/    /'
  if [ "$NOTARIZE" = 0 ]; then return 0; fi
  if printf '%s\n' "$out" | grep -q ': accepted' && printf '%s\n' "$out" | grep -q 'source=Notarized Developer ID'; then
    ok "Gatekeeper принимает $what"
  else
    die "Gatekeeper не принимает $what ($path) — см. ответ spctl выше"
  fi
}
gatekeeper "приложение" "$APP_PATH" -t exec
# Для DMG — тип open с контекстом primary-signature (TN2206); «-t install» — для пакетов .pkg.
gatekeeper "DMG" "$DMG" -t open --context context:primary-signature

# Содержимое образа: приложение с целой подписью и ярлык «Программы».
MNT="$PWD/build/dmg-mount"
run mkdir -p "$MNT"
run hdiutil attach -quiet -nobrowse -readonly -noautoopen -mountpoint "$MNT" "$DMG" ||
  die "Не удалось подключить $DMG для проверки"
dry || MOUNTED=1
run codesign --verify --deep --strict "$MNT/$APP.app" || die "Приложение внутри DMG не проходит проверку подписи"
show test -L "$MNT/Applications"
if ! dry; then
  [ -L "$MNT/Applications" ] || die "В DMG нет ярлыка «Программы» (Applications)"
fi
run hdiutil detach -quiet "$MNT" || warn "Не удалось отключить $MNT — отключите вручную в Finder"
MOUNTED=0
dry || ok "DMG: $APP.app и ярлык «Программы» на месте"

# ── 9. Итог ──────────────────────────────────────────────────────────────────────────────────────
if [ "$NOTARIZE" = 0 ]; then
  step "Готово (без нотаризации)"
  say "  $DMG — подписан, но НЕ нотаризован: только для проверки на этом Mac, не для раздачи."
  exit 0
fi
step "Готово"
run mkdir -p dist
run mv -f "$DMG" "$FINAL"
NOTES="dist/$APP-$VERSION.txt"
show shasum -a 256 "$FINAL"
if dry; then
  say "  (записать $NOTES: версия, SHA-256, сертификат, id нотаризации, коммит)"
  say ""
  say "Пробный прогон окончен: ничего не выполнено."
  exit 0
fi
SHA=$(shasum -a 256 "$FINAL" | awk '{print $1}')
commit=$(git rev-parse --short HEAD 2>/dev/null || echo '?')
if [ -n "$(git status --porcelain -- . ../aquarium 2>/dev/null || true)" ]; then
  commit="$commit + незакоммиченные изменения"
fi
{
  say "${DISPLAY_NAME:-$APP} $VERSION (сборка $BUILD)"
  say "Файл:        $DMG_NAME"
  say "SHA-256:     $SHA"
  say "Bundle ID:   $BUNDLE_ID"
  say "Подпись:     $SIGN_NAME"
  say "Нотаризация: Accepted, id $NOTARY_ID"
  say "Исходники:   git $commit"
  say "Собран:      $(date '+%Y-%m-%d %H:%M %z')"
} >"$NOTES"
say "  $PWD/$FINAL"
say "  SHA-256: $SHA"
say "  Сведения о выпуске: $NOTES"
if [ "$PLIST_CHANGED" = 1 ]; then
  say "  Версия в $PLIST изменена на $VERSION ($BUILD) — сохраните это изменение в git."
fi
say ""
say "Последняя проверка — как у пользователя: скачайте DMG с сайта (или пришлите себе) на другом Mac,"
say "откройте, перетащите в «Программы» и запустите — macOS не должна ругаться на разработчика."
if [ -t 1 ] && command -v open >/dev/null 2>&1; then open -R "$FINAL" || true; fi
