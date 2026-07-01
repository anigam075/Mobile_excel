[app]
title = Mobile XL
package.name = mobilexl
package.domain = org.mobilexl
source.dir = .
source.include_exts = py,kv,png,jpg,jpeg,atlas,csv,xlsx,json,txt
source.exclude_dirs = env,.git,.github,.buildozer,bin,tests,__pycache__,.kivy
version = 0.1.0
requirements = python3,kivy==2.3.1,openpyxl==3.1.5,plyer==2.1.0
orientation = portrait
fullscreen = 0

android.permissions = READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE
android.api = 35
android.minapi = 23
android.ndk = 25b
android.archs = arm64-v8a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
