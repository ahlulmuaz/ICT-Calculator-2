[app]

title = ICT Calculator
package.name = ictcalculator
package.domain = org.ictcalculator
source.dir = .
version = 1.0
requirements = python3,kivy
source.include_exts = py,png,jpg,jpeg,kv,atlas
orientation = portrait
fullscreen = 0

# icon.filename = %(source.dir)s/icon.png
# presplash.filename = %(source.dir)s/presplash.png


[buildozer]

log_level = 2
warn_on_root = 1


[app:android]

android.archs = arm64-v8a
android.enable_androidx = 1
