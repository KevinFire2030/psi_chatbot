# GSCM PSI Chatbot Android WebView

Android WebView wrapper for the hosted GSCM PSI PoC2 web UI.

## Target URL

```text
https://psi.possible-connect.com/
```

## Build prerequisites

- JDK 17
- Android SDK with:
  - `platforms;android-35`
  - `build-tools;35.0.0`
- Gradle 8.9 or the generated Gradle wrapper

This project was built in WSL with locally downloaded tools under:

```text
~/.local/android-build-tools/
```

## Build

From repository root:

```bash
cd android/psi-webview
./gradlew assembleDebug
```

Debug APK output:

```text
android/psi-webview/app/build/outputs/apk/debug/app-debug.apk
```

For convenience, the latest generated debug APK is also copied to:

```text
artifacts/android/gscm-psi-chatbot-webview-debug.apk
```

## App behavior

- Launches directly to `https://psi.possible-connect.com/`
- Enables JavaScript, DOM storage, cookies, and WebView navigation history
- Uses Android back button to go back inside WebView before exiting
- Uses HTTPS-only external URL access (`usesCleartextTraffic=false`)
