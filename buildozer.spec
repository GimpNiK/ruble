[app]

# (str) Title of your application
title = Ruble Финансы

# (str) Package name
package.name = ruble_finance

# (str) Package domain
package.domain = com.ruble
ignore_root = True

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,toml,ttf,otf

# (list) Source files to exclude
source.exclude_exts = spec,pyc,pyo,pyd
source.exclude_dirs = tests, bin, dist, .vscode, .venv, __pycache__, .github, docs, examples

# (str) Application version
version = 1.0.0

# ============================================
# ИКОНКА ПРИЛОЖЕНИЯ
# ============================================

# (str) Icon of the application
icon.filename = %(source.dir)s/icons/icon.png

# ============================================
# ЗАВИСИМОСТИ (БЕЗ MATPLOTLIB И NUMPY)
# ============================================

# (list) Application requirements
requirements = python3==3.10.0,kivy==2.3.0,sqlalchemy==2.0.23,cryptography==41.0.7

# ============================================
# НАСТРОЙКИ ANDROID
# ============================================

# (str) Supported orientation
orientation = portrait
fullscreen = 1

# (list) Permissions
android.permissions = INTERNET,READ_EXTERNAL_STORAGE,WRITE_EXTERNAL_STORAGE

# (int) Android API
android.api = 33

# (int) Minimum API
android.minapi = 33

# (int) Android SDK
android.sdk = 33

# (str) Android NDK
android.ndk = 25c
android.ndk_api = 33

# (str) Android arch
android.arch = arm64-v8a

# (str) Android theme
android.theme = Theme.Holo.Light.NoTitleBar.Fullscreen

# (bool) Android GLES2
android.gles2 = True

# (bool) Accept SDK license
android.accept_sdk_license = True

# (bool) Android release
android.release = False

# (bool) Android Gradle
android.gradle_dependencies = True

# (str) Android gradle version
android.gradle_version = 8.4.0

# (str) Android gradle plugin version
android.gradle_plugin_version = 8.2.0

# ============================================
# ЛОГИРОВАНИЕ
# ============================================

# (bool) Показывать подробный вывод логов
android.logcat = True

# (str) Фильтры для logcat
android.logcat_filters = *:V python:D

# (bool) Показывать полный вывод сборки
android.verbose = True

# (bool) Сохранять логи в файл
android.log_file = True

# (str) Уровень логирования для Gradle
android.gradle_log_level = info

# (bool) Показывать все команды которые выполняются
android.verbose_commands = True

# (bool) Показывать вывод всех команд
android.debug = True

# (bool) Показывать детали сборки NDK
android.ndk_debug = True

# (bool) Показывать детали сборки SDK
android.sdk_debug = True

# (bool) Показывать процесс компиляции Python
android.python_debug = True

# (str) Дополнительные флаги для компиляции
android.extra_compile_args = -v -Wall

# (bool) Показывать процесс упаковки APK
android.apk_debug = True

# (bool) Сохранять промежуточные файлы
android.keep_build = True

# (bool) Показывать процесс подписи APK
android.sign_debug = True

# (bool) Показывать детали сборки ресурсов
android.resources_debug = True

# (bool) Показывать детали сборки Python
android.python_verbose = True

# (bool) Показывать детали сборки библиотек
android.libs_debug = True

# (bool) Показывать детали упаковки
android.packaging_debug = True