# Building GigOS as an IPA for Diawi

Railway hosts the GigOS backend and database. The iOS app is built separately on macOS and points at the Railway backend URL.

## Requirements

- macOS
- Xcode installed and opened once
- Flutter installed
- Apple Developer signing configured in Xcode
- Railway backend deployed and reachable over HTTPS

## Build

From this folder on a Mac:

```bash
cd frontend
chmod +x scripts/build_ios_ipa.sh
API_BASE_URL=https://your-railway-backend.up.railway.app IOS_EXPORT_METHOD=development ./scripts/build_ios_ipa.sh
```

The script copies the finished IPA to:

```text
ipa/
```

Upload that `.ipa` to Diawi.

## Signing Notes

Diawi still needs an IPA signed for the target device. For quick device testing, use `IOS_EXPORT_METHOD=development` with registered devices. For broader testing, use `ad-hoc` or TestFlight/App Store workflows.

If Xcode asks for a bundle identifier, use something unique, for example:

```text
com.yourname.gigos
```

