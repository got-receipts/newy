#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPORT_DIR="${ROOT_DIR}/../ipa"
API_BASE_URL="${API_BASE_URL:-https://YOUR-RAILWAY-BACKEND.up.railway.app}"
IOS_EXPORT_METHOD="${IOS_EXPORT_METHOD:-development}"

cd "${ROOT_DIR}"

if ! command -v flutter >/dev/null 2>&1; then
  echo "Flutter is required on macOS to build an IPA."
  exit 1
fi

if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "Xcode command line tools are required to build an IPA."
  exit 1
fi

if [ ! -d "ios" ]; then
  flutter create --platforms=ios .
fi

/usr/libexec/PlistBuddy -c "Set :NSLocationWhenInUseUsageDescription GigOS uses your location to find nearby break zones and confirm arrival before starting a break timer." ios/Runner/Info.plist 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :NSLocationWhenInUseUsageDescription string GigOS uses your location to find nearby break zones and confirm arrival before starting a break timer." ios/Runner/Info.plist

/usr/libexec/PlistBuddy -c "Set :NSLocationAlwaysAndWhenInUseUsageDescription GigOS uses your location only while you are using the app for break-zone guidance." ios/Runner/Info.plist 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :NSLocationAlwaysAndWhenInUseUsageDescription string GigOS uses your location only while you are using the app for break-zone guidance." ios/Runner/Info.plist

flutter pub get
flutter build ipa --release --export-method="${IOS_EXPORT_METHOD}" --dart-define=API_BASE_URL="${API_BASE_URL}"

mkdir -p "${EXPORT_DIR}"
cp build/ios/ipa/*.ipa "${EXPORT_DIR}/"

echo "IPA copied to ${EXPORT_DIR}"

