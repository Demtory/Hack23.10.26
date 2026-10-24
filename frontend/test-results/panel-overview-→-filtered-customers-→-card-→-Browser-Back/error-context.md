# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: panel.spec.ts >> overview → filtered customers → card → Browser Back
- Location: e2e/panel.spec.ts:3:1

# Error details

```
Error: browserType.launch: Target page, context or browser has been closed
Browser logs:

<launching> /Users/vlad/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell --disable-field-trial-config --disable-background-networking --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-back-forward-cache --disable-breakpad --disable-client-side-phishing-detection --disable-component-extensions-with-background-pages --disable-component-update --no-default-browser-check --disable-default-apps --disable-dev-shm-usage --disable-edgeupdater --disable-extensions --disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,BlockOriginHeaderModificationOnRedirect,AvoidCorsURLLoaderRestartOnRedirect,Translate,AutoDeElevate,OptimizationHints,NetworkTimeServiceQuerying,AimEnabled,msForceBrowserSignIn,msEdgeUpdateLaunchServicesPreferredVersion --enable-features=CDPScreenshotNewSurface --allow-pre-commit-input --disable-hang-monitor --disable-ipc-flooding-protection --disable-popup-blocking --disable-prompt-on-repost --disable-renderer-backgrounding --disable-updater-scheduler --force-color-profile=srgb --metrics-recording-only --no-first-run --password-store=basic --use-mock-keychain --no-service-autorun --export-tagged-pdf --disable-search-engine-choice-screen --unsafely-disable-devtools-self-xss-warnings --edge-skip-compat-layer-relaunch --disable-infobars --disable-search-engine-choice-screen --disable-sync --enable-unsafe-swiftshader --headless --hide-scrollbars --mute-audio --blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4 --no-sandbox --user-data-dir=/var/folders/h5/1d57f9sn5sbbfsl0cw9s1rk80000gn/T/playwright_chromiumdev_profile-CP686c --remote-debugging-pipe --no-startup-window
<launched> pid=46623
[pid=46623][err] [1024/151129.840615:ERROR:base/power_monitor/thermal_state_observer_mac.mm:122] ThermalStateObserverMac unable to register to power notifications. Result: 9
[pid=46623][err] [1024/151129.862715:ERROR:net/dns/dns_config_service_posix.cc:139] DNS config watch failed to start.
[pid=46623][err] [1024/151129.865166:WARNING:net/dns/dns_config_service_posix.cc:198] Failed to read DnsConfig.
[pid=46623][err] [1024/151129.869978:FATAL:base/apple/mach_port_rendezvous_mac.cc:159] Check failed: kr == KERN_SUCCESS. bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer.46623: Permission denied (1100)
Call log:
  - <launching> /Users/vlad/Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell --disable-field-trial-config --disable-background-networking --disable-background-timer-throttling --disable-backgrounding-occluded-windows --disable-back-forward-cache --disable-breakpad --disable-client-side-phishing-detection --disable-component-extensions-with-background-pages --disable-component-update --no-default-browser-check --disable-default-apps --disable-dev-shm-usage --disable-edgeupdater --disable-extensions --disable-features=AvoidUnnecessaryBeforeUnloadCheckSync,DestroyProfileOnBrowserClose,DialMediaRouteProvider,GlobalMediaControls,HttpsUpgrades,LensOverlay,MediaRouter,PaintHolding,ThirdPartyStoragePartitioning,BlockOriginHeaderModificationOnRedirect,AvoidCorsURLLoaderRestartOnRedirect,Translate,AutoDeElevate,OptimizationHints,NetworkTimeServiceQuerying,AimEnabled,msForceBrowserSignIn,msEdgeUpdateLaunchServicesPreferredVersion --enable-features=CDPScreenshotNewSurface --allow-pre-commit-input --disable-hang-monitor --disable-ipc-flooding-protection --disable-popup-blocking --disable-prompt-on-repost --disable-renderer-backgrounding --disable-updater-scheduler --force-color-profile=srgb --metrics-recording-only --no-first-run --password-store=basic --use-mock-keychain --no-service-autorun --export-tagged-pdf --disable-search-engine-choice-screen --unsafely-disable-devtools-self-xss-warnings --edge-skip-compat-layer-relaunch --disable-infobars --disable-search-engine-choice-screen --disable-sync --enable-unsafe-swiftshader --headless --hide-scrollbars --mute-audio --blink-settings=primaryHoverType=2,availableHoverTypes=2,primaryPointerType=4,availablePointerTypes=4 --no-sandbox --user-data-dir=/var/folders/h5/1d57f9sn5sbbfsl0cw9s1rk80000gn/T/playwright_chromiumdev_profile-CP686c --remote-debugging-pipe --no-startup-window
  - <launched> pid=46623
  - [pid=46623][err] [1024/151129.840615:ERROR:base/power_monitor/thermal_state_observer_mac.mm:122] ThermalStateObserverMac unable to register to power notifications. Result: 9
  - [pid=46623][err] [1024/151129.862715:ERROR:net/dns/dns_config_service_posix.cc:139] DNS config watch failed to start.
  - [pid=46623][err] [1024/151129.865166:WARNING:net/dns/dns_config_service_posix.cc:198] Failed to read DnsConfig.
  - [pid=46623][err] [1024/151129.869978:FATAL:base/apple/mach_port_rendezvous_mac.cc:159] Check failed: kr == KERN_SUCCESS. bootstrap_check_in org.chromium.Chromium.MachPortRendezvousServer.46623: Permission denied (1100)
  - [pid=46623] <gracefully close start>
  - [pid=46623] <kill>
  - [pid=46623] <will force kill>
  - [pid=46623] exception while trying to kill process: Error: kill EPERM
  - [pid=46623] <process did exit: exitCode=null, signal=SIGTRAP>
  - [pid=46623] starting temporary directories cleanup
  - [pid=46623] finished temporary directories cleanup
  - [pid=46623] <gracefully close end>

```