[app]
# (str) Title of your application
title = WarCommand

# (str) Package name
package.name = warcommand

# (str) Package domain (needed for Android)
package.domain = org.spaceteam

# (str) Source code where the main.py lives
source.dir = .

# (str) The main .py file
source.main = main.py

# (str) Supported orientation (one of: landscape, portrait)
orientation = landscape

# (bool) Fullscreen mode
fullscreen = 1

# (str) Application versioning (method 1)
version = 0.1.0

# (str) Icon and Presplash
icon.filename = assets/icon.png
presplash.filename = assets/icon.png

# (list) Patterns to match for inclusion
source.include_exts = py,png,wav,json,ico

# (list) Application requirements
# Note: pygame on Android is supported through SDL2 bootstrap in recent python-for-android builds
requirements = python3,pygame==2.6.1,cython,android

# (str) Choose the Python-for-Android bootstrap
p4a.bootstrap = sdl2

# (list) Architectures to build
android.archs = armeabi-v7a, arm64-v8a

# (int) Target Android API (33 is Android 13)
android.api = 33

# (int) Minimum Android API (21 is Android 5.0)
android.minapi = 21

# (str) SDK/NDK versions (optional; let buildozer pick defaults if unspecified)
# android.sdk = 24
# android.ndk = 23b

# (list) Permissions (use internal app storage; external storage not required)
# android.permissions = WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# (int) Verbose logging (2 = info)
log_level = 2

[buildozer]
log_level = 2

[android]
# Use gradle for packaging
android.gradle_dependencies = 

